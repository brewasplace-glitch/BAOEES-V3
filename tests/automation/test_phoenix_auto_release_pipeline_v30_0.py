import importlib.util,json,unittest
from pathlib import Path
def root():
    p=Path(__file__).resolve()
    for x in p.parents:
        if (x/".git").exists(): return x
class Tests(unittest.TestCase):
    def test_policy(self):
        d=json.loads((root()/"configs/phoenix/auto_release_pipeline_policy_v30_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(d["policy_version"],"v30.0"); self.assertTrue(d["automatic_commit"]); self.assertFalse(d["allow_manual_git_finalize"])
    def test_registry(self):
        d=json.loads((root()/"configs/phoenix/auto_release_pipeline_registry_v30_0.json").read_text(encoding="utf-8-sig"))
        self.assertGreaterEqual(len(d["stages"]),13)
    def test_import(self):
        p=root()/"apps/brewster_engineering_wizard/project_analyzer/phoenix_auto_release_pipeline_v30_0.py"
        s=importlib.util.spec_from_file_location("v30",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
        self.assertTrue(hasattr(m,"Pipeline"))
if __name__=="__main__": unittest.main()
