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

class MainRunnerTests(unittest.TestCase):
    def test_registry(self) -> None:
        root = project_root()
        path = root / "configs" / "phoenix" / "main_runner_registry_v9_1.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertIn("platform_foundation", data["workflows"])
        self.assertIn("repository_preflight", data["modules"])

    def test_engine_import(self) -> None:
        root = project_root()
        path = root / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_main_runner_orchestrator.py"
        spec = importlib.util.spec_from_file_location("phoenix_main_runner_orchestrator", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixMainRunnerOrchestrator"))

if __name__ == "__main__":
    unittest.main()
