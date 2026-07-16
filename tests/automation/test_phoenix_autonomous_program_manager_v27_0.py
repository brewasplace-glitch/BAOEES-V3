from __future__ import annotations
import importlib.util, json, unittest
from pathlib import Path

def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

class AutonomousProgramManagerTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads((project_root() / "configs/phoenix/program_manager_policy_v27_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(data["policy_version"], "v27.0")
        self.assertFalse(data["allow_automatic_program_execution"])
        self.assertTrue(data["automatic_commit_after_tests"])
        self.assertTrue(data["automatic_push_after_commit"])

    def test_registry(self) -> None:
        data = json.loads((project_root() / "configs/phoenix/program_portfolio_registry_v27_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(data["registry_version"], "v27.0")
        self.assertIn("project-phoenix-core-program", data["programs"])

    def test_import(self) -> None:
        path = project_root() / "apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_program_manager_v27_0.py"
        spec = importlib.util.spec_from_file_location("program_manager", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "PhoenixAutonomousProgramManager"))

if __name__ == "__main__":
    unittest.main()
