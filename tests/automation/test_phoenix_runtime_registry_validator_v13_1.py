from __future__ import annotations
import importlib.util,json,unittest
from pathlib import Path

def root():
    p=Path(__file__).resolve()
    for x in p.parents:
        if (x/".git").exists():return x
    raise RuntimeError

class T(unittest.TestCase):
    def test_import(self):
        p=root()/"apps/brewster_engineering_wizard/project_analyzer/phoenix_runtime_registry_validator_v13_1.py"
        s=importlib.util.spec_from_file_location("validator",p)
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        self.assertTrue(hasattr(m,"Validator"))
    def test_unique_ids(self):
        d=json.loads((root()/"configs/phoenix/ai_runtime_registry_v13_0.json").read_text(encoding="utf-8-sig"))
        ids=[x["engine_id"] for x in d["engines"]]
        self.assertEqual(len(ids),len(set(ids)))
if __name__=="__main__":unittest.main()
