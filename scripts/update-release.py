#!/usr/bin/env python3
"""Validate an upstream release and prepare a reviewable PKGBUILD update.

The script never commits, pushes, publishes, or changes AUR state. It verifies
both GitHub's asset digest and the downloaded bytes before editing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from release import ReleaseError, validate_release, version_from_tag, version_tuple  # noqa: E402


CHECK_NEWER_EXIT = 10
REPO = Path(__file__).resolve().parents[1]
PKGBUILD = REPO / "PKGBUILD"


def fetch_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "openclaw-desktop-bin-maintainer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ReleaseError("GitHub response is not a JSON object")
    return payload


def current_version() -> str:
    text = PKGBUILD.read_text(encoding="utf-8")
    match = re.search(r"(?m)^pkgver=([^\n]+)$", text)
    if not match:
        raise ReleaseError("PKGBUILD has no single-line pkgver")
    version = match.group(1).strip()
    version_tuple(version)
    return version


def download(url: str, destination: Path) -> str:
    request = Request(url, headers={"User-Agent": "openclaw-desktop-bin-maintainer"})
    with urlopen(request, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def download_and_verify(url: str, digest: str, directory: Path) -> str:
    actual = download(url, directory / "release.deb")
    if actual != digest:
        raise ReleaseError(f"downloaded asset digest mismatch: expected {digest}, got {actual}")
    return actual


def write_srcinfo() -> None:
    result = subprocess.run(
        [REPO / "scripts" / "regenerate-srcinfo.sh"],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ReleaseError(f".SRCINFO regeneration failed: {result.stderr.strip()}")


def update_pkgbuild(version: str, deb_digest: str, license_digest: str) -> None:
    original = PKGBUILD.read_text(encoding="utf-8")
    updated, version_count = re.subn(r"(?m)^pkgver=[^\n]+$", f"pkgver={version}", original, count=1)
    updated, pkgrel_count = re.subn(r"(?m)^pkgrel=[^\n]+$", "pkgrel=1", updated, count=1)
    updated, checksum_count = re.subn(
        r"(?ms)^sha256sums=\(\n\s*'[0-9a-f]+'\n\s*'[0-9a-f]+'\n\)$",
        f"sha256sums=(\n  '{deb_digest}'\n  '{license_digest}'\n)",
        updated,
        count=1,
    )
    if (version_count, pkgrel_count, checksum_count) != (1, 1, 1):
        raise ReleaseError("PKGBUILD shape is not the expected two-source layout")
    PKGBUILD.write_text(updated, encoding="utf-8")
    try:
        write_srcinfo()
    except Exception:
        PKGBUILD.write_text(original, encoding="utf-8")
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="explicit stable version, for deterministic updates")
    parser.add_argument("--version", dest="version_option", help="same as the positional version")
    parser.add_argument("--release-json", type=Path, help="read release metadata from a fixture/file instead of GitHub")
    parser.add_argument("--api-url", help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="validate only; exit 10 when a newer valid release exists")
    parser.add_argument("--json-out", type=Path, help="write a machine-readable check result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    explicit = args.version_option or args.version
    if args.version and args.version_option and args.version != args.version_option:
        raise ReleaseError("positional version and --version disagree")
    if explicit:
        version_tuple(explicit)

    if args.release_json:
        payload = json.loads(args.release_json.read_text(encoding="utf-8"))
    else:
        if explicit:
            api_url = f"https://api.github.com/repos/openclaw/openclaw/releases/tags/v{explicit}"
        else:
            api_url = "https://api.github.com/repos/openclaw/openclaw/releases/latest"
        if args.api_url:
            api_url = args.api_url
        payload = fetch_json(api_url)

    target = explicit or version_from_tag(payload.get("tag_name"))
    asset = validate_release(payload, target)
    current = current_version()
    with tempfile.TemporaryDirectory(prefix=".update-", dir=REPO) as temporary:
        temporary_path = Path(temporary)
        download_and_verify(asset.url, asset.digest, temporary_path)
        license_url = f"https://raw.githubusercontent.com/openclaw/openclaw/v{target}/LICENSE"
        license_digest = download(license_url, temporary_path / "LICENSE")
        if (temporary_path / "LICENSE").read_bytes()[:64].find(b"MIT License") == -1:
            raise ReleaseError("upstream LICENSE is not the expected MIT license")

    newer = version_tuple(target) > version_tuple(current)
    result = {
        "current_version": current,
        "target_version": target,
        "newer": newer,
        "asset": asset.name,
        "digest": asset.digest,
        "license_digest": license_digest,
        "url": asset.url,
    }
    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if not newer:
        print(f"{current} is current; verified {asset.name} and its SHA-256 digest")
        return 0
    if args.check:
        print(f"newer valid release available: {target}")
        return CHECK_NEWER_EXIT

    update_pkgbuild(target, asset.digest, license_digest)
    print(f"updated PKGBUILD and .SRCINFO to {target}; review the diff before committing")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ReleaseError, json.JSONDecodeError) as error:
        print(f"update-release: {error}", file=sys.stderr)
        raise SystemExit(1)
