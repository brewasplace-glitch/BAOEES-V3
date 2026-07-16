from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path

def root():
    p=Path(__file__).resolve()
    for x in p.parents:
        if (x/".git").exists(): return x
    raise RuntimeError

class Tests(unittest.TestCase):
    def test_policy(self):
        d=json.loads((root()/"configs/phoenix/autonomous_decision_policy_v25_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(d["policy_version"],"v25.0")
        self.assertFalse(d["allow_automatic_execution"])
        self.assertTrue(d["automatic_commit_after_tests"])
    def test_registry(self):
        d=json.loads((root()/"configs/phoenix/decision_strategy_registry_v25_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(d["registry_version"],"v25.0")
        self.assertGreaterEqual(len(d["strategies"]),3)
    def test_import(self):
        p=root()/"apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_decision_planning_engine_v25_0.py"
        s=importlib.util.spec_from_file_location("decision_planning",p)
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        self.assertTrue(hasattr(m,"DecisionPlanning"))

if __name__=="__main__": unittest.main()
