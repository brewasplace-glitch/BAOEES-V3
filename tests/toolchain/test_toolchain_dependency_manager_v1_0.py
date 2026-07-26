from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.toolchain import (
    DependencyKind,
    DependencySpec,
    DependencyStatus,
    ToolchainDependencyManager,
)
from phoenix.toolchain.detectors import detect_executable


class ToolchainDependencyManagerTests(unittest.TestCase):
    def test_environment_override_detects_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "fake-tool.exe"
            executable.write_text("placeholder", encoding="utf-8")
            spec = DependencySpec(
                id="TEST-EXE",
                name="Test executable",
                kind=DependencyKind.EXECUTABLE,
                required=True,
                capability="test",
                environment_variables=("PHOENIX_TEST_EXE",),
            )
            with patch.dict(os.environ, {"PHOENIX_TEST_EXE": str(executable)}):
                result = detect_executable(spec)
            self.assertEqual(DependencyStatus.AVAILABLE, result.status)
            self.assertEqual(str(executable), result.detected_path)

    def test_invalid_environment_override_is_reported(self) -> None:
        spec = DependencySpec(
            id="TEST-BAD",
            name="Bad executable",
            kind=DependencyKind.EXECUTABLE,
            required=True,
            capability="test",
            environment_variables=("PHOENIX_TEST_BAD_EXE",),
        )
        with patch.dict(
            os.environ,
            {"PHOENIX_TEST_BAD_EXE": r"C:\missing\tool.exe"},
        ):
            result = detect_executable(spec)
        self.assertEqual(DependencyStatus.INVALID, result.status)

    def test_installation_plan_does_not_auto_execute(self) -> None:
        catalog = (
            DependencySpec(
                id="TEST-PKG",
                name="Test package",
                kind=DependencyKind.PYTHON_PACKAGE,
                required=True,
                capability="test",
                python_import_name="definitely_missing_phoenix_package",
                python_distribution_name="definitely-missing-phoenix-package",
            ),
        )
        manager = ToolchainDependencyManager(catalog)
        report = manager.scan()
        plan = manager.create_installation_plan(report)
        self.assertEqual(1, len(plan))
        self.assertFalse(plan[0]["automatic_execution"])

    def test_exported_report_contains_fingerprint_and_plan(self) -> None:
        manager = ToolchainDependencyManager(())
        report = manager.scan()
        with tempfile.TemporaryDirectory() as tmp:
            path = manager.export_report(report, Path(tmp) / "report.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("fingerprint_sha256", data)
        self.assertIn("installation_plan", data)
        self.assertTrue(data["required_ready"])

    def test_default_catalog_has_unique_ids(self) -> None:
        manager = ToolchainDependencyManager()
        ids = [spec.id for spec in manager.catalog]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
