from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path

def root():
    p=Path(__file__).resolve()
    for x in p.parents:
        if (x/".git").exists():return x
    raise RuntimeError

class T(unittest.TestCase):
    def test_policy(self):
        d=json.loads((root()/"configs/phoenix/knowledge_reasoning_policy_v18_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(d["policy_version"],"v18.0")
        self.assertFalse(d["automatic_commit"])
        self.assertFalse(d["automatic_push"])
    def test_import(self):
        p=root()/"apps/brewster_engineering_wizard/project_analyzer/phoenix_knowledge_reasoning_v18_0.py"
        s=importlib.util.spec_from_file_location("knowledge_reasoning",p)
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        self.assertTrue(hasattr(m,"KnowledgeReasoning"))
if __name__=="__main__":unittest.main()
