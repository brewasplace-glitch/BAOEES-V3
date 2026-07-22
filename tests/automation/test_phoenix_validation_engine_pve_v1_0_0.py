import json
import tempfile
import unittest
from pathlib import Path

from phoenix.validation_engine import PhoenixValidationEngine, ValidationError


class PhoenixValidationEngineTests(unittest.TestCase):
    def test_valid_repository_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "configs").mkdir()
            (root / "configs/test.json").write_text("{}", encoding="utf-8")
            report = PhoenixValidationEngine().run(
                project_id="PHX",
                repo_root=root,
                required_paths=("configs",),
                json_paths=("configs/test.json",),
                import_modules=("json",),
            )
            self.assertTrue(report.passed)
            self.assertEqual(len(report.evidence_sha256), 64)

    def test_missing_path_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            report = PhoenixValidationEngine().run(
                project_id="PHX",
                repo_root=Path(folder),
                required_paths=("missing",),
            )
            self.assertFalse(report.passed)

    def test_invalid_json_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bad.json").write_text("{", encoding="utf-8")
            report = PhoenixValidationEngine().run(
                project_id="PHX",
                repo_root=root,
                json_paths=("bad.json",),
            )
            self.assertFalse(report.passed)

    def test_import_failure_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            report = PhoenixValidationEngine().run(
                project_id="PHX",
                repo_root=Path(folder),
                import_modules=("module_that_does_not_exist_phoenix",),
            )
            self.assertFalse(report.passed)

    def test_release_manifest_validates_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "x.txt").write_text("x", encoding="utf-8")
            manifest = {
                "release_id": "PHX",
                "version": "1.0.0",
                "include_files": ["x.txt"],
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            report = PhoenixValidationEngine().run(
                project_id="PHX",
                repo_root=root,
                release_manifest="manifest.json",
            )
            self.assertTrue(report.passed)

    def test_unsafe_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValidationError):
                PhoenixValidationEngine().run(
                    project_id="PHX",
                    repo_root=Path(folder),
                    required_paths=("../outside",),
                )


if __name__ == "__main__":
    unittest.main()
