#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "lib"))
from release import ReleaseError, validate_release, version_from_tag, version_tuple  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ReleaseValidationTests(unittest.TestCase):
    def test_current_release_is_valid_and_extracts_digest(self) -> None:
        asset = validate_release(fixture("current.json"), "2026.8.2")
        self.assertEqual(asset.name, "OpenClaw-2026.8.2-amd64.deb")
        self.assertEqual(asset.digest, "6021ac38b398fc3b4c1364f72fb83a5d89e2d6c20ed6bbe6d3ceed0cddbeaa85")

    def test_newer_stable_release_is_valid(self) -> None:
        asset = validate_release(fixture("newer-stable.json"), "2026.8.3")
        self.assertEqual(version_tuple(asset.version), (2026, 8, 3))

    def test_prerelease_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "prereleases"):
            validate_release(fixture("prerelease.json"), "2026.9.0")

    def test_missing_asset_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "missing exactly one"):
            validate_release(fixture("missing-asset.json"), "2026.8.3")

    def test_missing_digest_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReleaseError, "missing a valid sha256 digest"):
            validate_release(fixture("missing-digest.json"), "2026.8.3")

    def test_wrong_tag_is_rejected(self) -> None:
        payload = fixture("current.json")
        payload["tag_name"] = "v2026.8.1"
        with self.assertRaisesRegex(ReleaseError, "does not match"):
            validate_release(payload, "2026.8.2")

    def test_tag_and_version_parser_are_strict(self) -> None:
        self.assertEqual(version_from_tag("v2026.8.2"), "2026.8.2")
        with self.assertRaises(ReleaseError):
            version_from_tag("2026.8.2")
        with self.assertRaises(ReleaseError):
            version_tuple("2026.8")


if __name__ == "__main__":
    unittest.main()
