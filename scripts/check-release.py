#!/usr/bin/env python3
"""Check for a newer stable OpenClaw source tag without changing files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.request import Request, urlopen

CHECK_NEWER_EXIT = 10
REPO = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+(?:\.\d+){2,}$")


class ReleaseError(ValueError):
    pass


def version_tuple(version: str) -> tuple[int, ...]:
    if not VERSION_RE.fullmatch(version):
        raise ReleaseError(f"invalid version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def validate_release(payload: dict[str, Any]) -> str:
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ReleaseError(f"release tag is not a v-prefixed version: {tag!r}")
    version = tag[1:]
    version_tuple(version)
    if payload.get("draft") is True:
        raise ReleaseError("draft releases are not package candidates")
    if payload.get("prerelease") is True:
        raise ReleaseError("prereleases are not package candidates")
    return version


def current_version() -> str:
    text = (REPO / "PKGBUILD").read_text(encoding="utf-8")
    match = re.search(r"(?m)^pkgver=([^\n]+)$", text)
    if not match:
        raise ReleaseError("PKGBUILD has no single-line pkgver")
    version = match.group(1).strip()
    version_tuple(version)
    return version


def fetch_latest() -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "openclaw-desktop-maintainer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        "https://api.github.com/repos/openclaw/openclaw/releases/latest",
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ReleaseError("GitHub response is not a JSON object")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-json", type=Path, help="use fixture metadata instead of GitHub")
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = (
        json.loads(args.release_json.read_text(encoding="utf-8"))
        if args.release_json
        else fetch_latest()
    )
    target = validate_release(payload)
    current = current_version()
    newer = version_tuple(target) > version_tuple(current)
    result = {
        "current_version": current,
        "target_version": target,
        "newer": newer,
        "source_url": f"https://github.com/openclaw/openclaw/archive/refs/tags/v{target}.tar.gz",
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.json_out:
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return CHECK_NEWER_EXIT if newer else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ReleaseError) as error:
        print(f"check-release: {error}", file=sys.stderr)
        raise SystemExit(1)
