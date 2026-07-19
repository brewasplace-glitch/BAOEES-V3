from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from phoenix.updater.runtime_policy import (
    DEFAULT_RUNTIME_POLICY,
    PathClass,
    RuntimePolicy,
    classify_path,
)


class RuntimePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RuntimePolicy()

    def test_normalize_windows_path(self) -> None:
        self.assertEqual(
            self.policy.normalize(r".\runtime_reports\report.json"),
            "runtime_reports/report.json",
        )

    def test_runtime_paths(self) -> None:
        runtime_paths = (
            "updates/incoming/update.zip",
            "runtime/session.json",
            "runtime_reports/updater.json",
            ".phoenix/runtime/state.json",
            "artifacts/runtime/result.json",
        )
        for path in runtime_paths:
            with self.subTest(path=path):
                self.assertEqual(self.policy.classify(path), PathClass.RUNTIME)
                self.assertTrue(self.policy.is_runtime(path))

    def test_version_controlled_paths(self) -> None:
        expectations = {
            "phoenix/updater/engine.py": PathClass.SOURCE,
            "apps/brewster_engineering_wizard/main.py": PathClass.SOURCE,
            "docs/automation/PHOENIX_UPDATER_v2_0.md": PathClass.DOCUMENTATION,
            "tests/updater/test_runtime_policy.py": PathClass.TEST,
            "configs/projects/project.json": PathClass.CONFIGURATION,
            "artifacts/releases/release.json": PathClass.TRACKED_ARTIFACT,
        }

        for path, expected in expectations.items():
            with self.subTest(path=path):
                self.assertEqual(self.policy.classify(path), expected)

    def test_unknown_path(self) -> None:
        self.assertEqual(self.policy.classify("misc/file.txt"), PathClass.UNKNOWN)

    def test_default_helper(self) -> None:
        self.assertIs(DEFAULT_RUNTIME_POLICY.classify("updates/a.zip"), PathClass.RUNTIME)
        self.assertIs(classify_path("docs/readme.md"), PathClass.DOCUMENTATION)

    def test_ensure_runtime_directories(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            directories = self.policy.ensure_runtime_directories(root)

            self.assertTrue(directories)
            for directory in directories:
                self.assertTrue(directory.is_dir())
                self.assertTrue(directory.is_relative_to(root))


if __name__ == "__main__":
    unittest.main()