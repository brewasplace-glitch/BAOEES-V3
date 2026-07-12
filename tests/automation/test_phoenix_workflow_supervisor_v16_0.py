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


class WorkflowSupervisorTests(unittest.TestCase):
    def test_policy(self) -> None:
        path = project_root() / "configs" / "phoenix" / "workflow_supervisor_policy_v16_0.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertEqual(data["policy_version"], "v16.0")
        self.assertFalse(data["allow_automatic_resume"])
        self.assertFalse(data["automatic_commit"])
        self.assertFalse(data["automatic_push"])

    def test_engine_import(self) -> None:
        path = project_root() / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_workflow_supervisor_v16_0.py"
        spec = importlib.util.spec_from_file_location("phoenix_workflow_supervisor_v16_0", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixWorkflowSupervisor"))


if __name__ == "__main__":
    unittest.main()
