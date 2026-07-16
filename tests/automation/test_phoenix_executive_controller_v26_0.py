from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


class ExecutiveControllerTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/executive_controller_policy_v26_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v26.0")
        self.assertFalse(data["allow_automatic_execution"])
        self.assertTrue(data["automatic_commit_after_tests"])
        self.assertTrue(data["automatic_push_after_commit"])

    def test_registry(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/executive_controller_registry_v26_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["registry_version"], "v26.0")
        self.assertGreaterEqual(len(data["components"]), 9)
        self.assertIn("phoenix_executive_core", data["workflows"])

    def test_import(self) -> None:
        path = (
            project_root()
            / "apps/brewster_engineering_wizard/project_analyzer"
            / "phoenix_executive_controller_v26_0.py"
        )
        spec = importlib.util.spec_from_file_location(
            "executive_controller",
            path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixExecutiveController"))


if __name__ == "__main__":
    unittest.main()
