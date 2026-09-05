#!/usr/bin/env python3
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_release", REPO / "scripts/check-release.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ReleaseTests(unittest.TestCase):
    def fixture(self, name: str) -> dict:
        return json.loads((Path(__file__).parent / "fixtures" / name).read_text())

    def test_current_stable_release(self) -> None:
        self.assertEqual(module.validate_release(self.fixture("current.json")), "2026.9.1")

    def test_newer_stable_release(self) -> None:
        version = module.validate_release(self.fixture("newer.json"))
        self.assertGreater(module.version_tuple(version), module.version_tuple("2026.9.1"))

    def test_prerelease_is_rejected(self) -> None:
        with self.assertRaisesRegex(module.ReleaseError, "prereleases"):
            module.validate_release(self.fixture("prerelease.json"))

    def test_version_parser_is_strict(self) -> None:
        for invalid in ("2026.9", "v2026.9.1", "2026.09.x"):
            with self.subTest(invalid=invalid), self.assertRaises(module.ReleaseError):
                module.version_tuple(invalid)

    def test_malformed_release_is_rejected(self) -> None:
        with self.assertRaisesRegex(module.ReleaseError, "v-prefixed"):
            module.validate_release({"tag_name": "2026.9.2"})

    def run_main(self, fixture: str) -> tuple[int, dict, str]:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            args = SimpleNamespace(
                release_json=Path(__file__).parent / "fixtures" / fixture,
                json_out=output,
            )
            stdout = io.StringIO()
            with patch.object(module, "parse_args", return_value=args), redirect_stdout(stdout):
                status = module.main()
            return status, json.loads(output.read_text()), stdout.getvalue()

    def test_main_reports_current_release(self) -> None:
        status, result, stdout = self.run_main("current.json")
        self.assertEqual(status, 0)
        self.assertFalse(result["newer"])
        self.assertEqual(json.loads(stdout), result)

    def test_main_uses_distinct_exit_for_newer_release(self) -> None:
        status, result, stdout = self.run_main("newer.json")
        self.assertEqual(status, module.CHECK_NEWER_EXIT)
        self.assertTrue(result["newer"])
        self.assertEqual(json.loads(stdout), result)


if __name__ == "__main__":
    unittest.main()
