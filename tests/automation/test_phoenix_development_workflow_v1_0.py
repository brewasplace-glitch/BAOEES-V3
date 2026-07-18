from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.dev.cli import cleanup, find_root, validate_manifest


class PhoenixDevelopmentWorkflowTests(unittest.TestCase):
    def test_find_root(self) -> None:
        root = find_root(Path(__file__).resolve())
        self.assertTrue((root / ".git").exists())

    def test_manifest_validation_passes(self) -> None:
        root = find_root(Path(__file__).resolve())
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "release": "test",
                        "source_paths": ["phoenix"],
                        "required_tests": ["unit"],
                        "commit_message": "test: release",
                    }
                ),
                encoding="utf-8",
            )
            result = validate_manifest(root, manifest)
            self.assertEqual(result["status"], "PASS")

    def test_manifest_validation_rejects_missing_path(self) -> None:
        root = find_root(Path(__file__).resolve())
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "release": "test",
                        "source_paths": ["does-not-exist"],
                        "required_tests": ["unit"],
                        "commit_message": "test: release",
                    }
                ),
                encoding="utf-8",
            )
            result = validate_manifest(root, manifest)
            self.assertEqual(result["status"], "FAIL")

    def test_cleanup_is_safe(self) -> None:
        root = find_root(Path(__file__).resolve())
        result = cleanup(root)
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
