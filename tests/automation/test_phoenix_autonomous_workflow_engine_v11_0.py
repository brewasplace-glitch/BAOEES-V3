from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


class AutonomousWorkflowTests(unittest.TestCase):
    def test_registry(self) -> None:
        root = project_root()
        data = json.loads((root / "configs" / "phoenix" / "autonomous_workflow_registry_v11_0.json").read_text(encoding="utf-8-sig"))
        self.assertIn("platform_foundation", data["workflows"])
        self.assertIn("foundation_validation", data["steps"])

    def test_engine_import_and_order(self) -> None:
        root = project_root()
        path = root / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_autonomous_workflow_engine.py"
        spec = importlib.util.spec_from_file_location("phoenix_autonomous_workflow_engine", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        engine = module.PhoenixAutonomousWorkflowEngine()
        self.assertEqual(
            engine._resolve_order(["runtime_checkpoint"]),
            ["foundation_validation", "kernel_validation", "runtime_checkpoint"],
        )


if __name__ == "__main__":
    unittest.main()
