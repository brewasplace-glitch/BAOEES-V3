from __future__ import annotations
import importlib.util, json, unittest
from pathlib import Path

def root() -> Path:
    p = Path(__file__).resolve()
    for x in p.parents:
        if (x / ".git").exists():
            return x
    raise RuntimeError

class PlannerTests(unittest.TestCase):
    def test_template_registry(self):
        data = json.loads(
            (root() / "configs/phoenix/ai_planner_templates_v14_0.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.assertEqual(data["registry_version"], "v14.0")
        self.assertGreaterEqual(len(data["templates"]), 1)

    def test_engine_import(self):
        path = root() / "apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_ai_planner_v14_0.py"
        spec = importlib.util.spec_from_file_location("planner", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "Planner"))

if __name__ == "__main__":
    unittest.main()
