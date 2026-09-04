#!/usr/bin/env python3
"""Pure validation helpers for OpenClaw GitHub release metadata."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
import re
from typing import Any


_VERSION_RE = re.compile(r"^\d+(?:\.\d+){2,}$")
_DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")


class ReleaseError(ValueError):
    """Raised when release metadata cannot safely produce a package update."""


@dataclass(frozen=True)
class ReleaseAsset:
    version: str
    name: str
    url: str
    digest: str


def version_tuple(version: str) -> tuple[int, ...]:
    if not _VERSION_RE.fullmatch(version):
        raise ReleaseError(f"invalid package version: {version!r}")
    return tuple(int(part) for part in version.split("."))


def _expected_asset(version: str) -> str:
    version_tuple(version)
    return f"OpenClaw-{version}-amd64.deb"


def validate_release(payload: dict[str, Any], version: str) -> ReleaseAsset:
    """Validate one stable release and return its exact official .deb asset."""
    version_tuple(version)
    expected_tag = f"v{version}"
    if payload.get("tag_name") != expected_tag:
        raise ReleaseError(
            f"release tag {payload.get('tag_name')!r} does not match {expected_tag!r}"
        )
    if payload.get("draft") is True:
        raise ReleaseError("draft releases are not package candidates")
    if payload.get("prerelease") is True:
        raise ReleaseError("prereleases are not package candidates")

    expected_name = _expected_asset(version)
    matches = [asset for asset in payload.get("assets", []) if asset.get("name") == expected_name]
    if len(matches) != 1:
        raise ReleaseError(f"release is missing exactly one {expected_name} asset")
    asset = matches[0]

    url = asset.get("browser_download_url")
    expected_path = f"/openclaw/openclaw/releases/download/{expected_tag}/{expected_name}"
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.path != expected_path:
        raise ReleaseError("asset URL is not the expected official GitHub release URL")

    digest = asset.get("digest")
    if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
        raise ReleaseError("asset is missing a valid sha256 digest")
    if asset.get("state") not in (None, "uploaded"):
        raise ReleaseError(f"asset is not uploaded: {asset.get('state')!r}")

    return ReleaseAsset(version=version, name=expected_name, url=url, digest=digest.removeprefix("sha256:"))


def version_from_tag(tag: str) -> str:
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ReleaseError(f"release tag is not a v-prefixed version: {tag!r}")
    version = tag[1:]
    version_tuple(version)
    return version
