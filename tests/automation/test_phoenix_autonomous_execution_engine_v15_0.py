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
    raise RuntimeError

class ExecutionEngineTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (project_root() / "configs/phoenix/autonomous_execution_policy_v15_0.json")
            .read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v15.0")
        self.assertFalse(data["automatic_commit"])
        self.assertFalse(data["automatic_push"])

    def test_import(self) -> None:
        path = (
            project_root()
            / "apps/brewster_engineering_wizard/project_analyzer"
            / "phoenix_autonomous_execution_engine_v15_0.py"
        )
        spec = importlib.util.spec_from_file_location("execution_engine", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "ExecutionEngine"))

if __name__ == "__main__":
    unittest.main()
