import importlib.util,json,unittest
from pathlib import Path
def root():
    p=Path(__file__).resolve()
    for x in p.parents:
        if (x/".git").exists():return x
class Tests(unittest.TestCase):
    def test_policy(self):
        d=json.loads((root()/"configs/phoenix/patch_generation_policy_v29_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(d["policy_version"],"v29.0")
        self.assertFalse(d["allow_automatic_patch_application"])
    def test_registry(self):
        d=json.loads((root()/"configs/phoenix/patch_template_registry_v29_0.json").read_text(encoding="utf-8-sig"))
        self.assertGreaterEqual(len(d["templates"]),2)
    def test_import(self):
        p=root()/"apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_patch_generation_engine_v29_0.py"
        s=importlib.util.spec_from_file_location("v29",p)
        m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        self.assertTrue(hasattr(m,"PatchEngine"))
if __name__=="__main__":unittest.main()
