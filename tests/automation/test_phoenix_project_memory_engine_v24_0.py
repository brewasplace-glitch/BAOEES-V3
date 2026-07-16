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


class ProjectMemoryEngineTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/project_memory_policy_v24_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v24.0")
        self.assertFalse(data["allow_automatic_source_changes"])
        self.assertTrue(data["automatic_commit_after_tests"])
        self.assertTrue(data["automatic_push_after_commit"])

    def test_schema(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/project_memory_schema_v24_0.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["schema_version"], "v24.0")
        self.assertIn("fingerprint", data["required_fields"])

    def test_import(self) -> None:
        path = (
            project_root()
            / "apps/brewster_engineering_wizard/project_analyzer"
            / "phoenix_project_memory_engine_v24_0.py"
        )
        spec = importlib.util.spec_from_file_location("project_memory", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixProjectMemoryEngine"))


if __name__ == "__main__":
    unittest.main()
