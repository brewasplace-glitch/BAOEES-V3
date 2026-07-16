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


class MultiAgentOrchestratorTests(unittest.TestCase):
    def test_registry(self) -> None:
        path = project_root() / "configs/phoenix/multi_agent_registry_v19_0.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertEqual(data["registry_version"], "v19.0")
        self.assertGreaterEqual(len(data["agents"]), 5)

    def test_policy(self) -> None:
        path = project_root() / "configs/phoenix/multi_agent_policy_v19_0.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertFalse(data["automatic_commit"])
        self.assertFalse(data["automatic_push"])

    def test_import(self) -> None:
        path = (
            project_root()
            / "apps/brewster_engineering_wizard/project_analyzer"
            / "phoenix_multi_agent_orchestrator_v19_0.py"
        )
        spec = importlib.util.spec_from_file_location("multi_agent", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixMultiAgentOrchestrator"))


if __name__ == "__main__":
    unittest.main()
