import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2];RUNNER=ROOT/'phoenix/validation/moskee_bunschoten_real_project_e2e_v1_0.py';spec=importlib.util.spec_from_file_location('e',RUNNER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class T(unittest.TestCase):
 def test_project(self):self.assertEqual(m.CANONICAL_PROJECT_FILE,'configs/projects/moskee_bunschoten.json');self.assertEqual(m.PROJECT_FILE,'configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json')
 def test_states(self):self.assertIn('completed',m.OK);self.assertIn('failed',m.BAD)
 def test_categories(self):
  c=m.cats([pathlib.Path('a.ifc'),pathlib.Path('a.FCStd'),pathlib.Path('a.blend'),pathlib.Path('viewer.html'),pathlib.Path('a.pdf'),pathlib.Path('a.inp'),pathlib.Path('a.frd'),pathlib.Path('manifest.json')]);self.assertTrue(all(len(c[k])==1 for k in ('ifc','freecad','blender','visual','drawing','inp','raw','manifest')))
 def test_ui(self):
  s=RUNNER.read_text(encoding='utf-8');self.assertIn('.phx-cap-project',s);self.assertIn('button.phx-cap-run:not([disabled])',s)
 def test_browsers(self):
  s=RUNNER.read_text(encoding='utf-8');self.assertIn('sync_playwright',s);self.assertIn('selenium',s)
 def test_calculix(self):self.assertIn("'-i'",RUNNER.read_text(encoding='utf-8'))
 def test_manifest(self):self.assertIn('E2E_SHA256_MANIFEST.json',RUNNER.read_text(encoding='utf-8'))
 def test_release(self):
  s=RUNNER.read_text(encoding='utf-8');self.assertIn('PRODUCTION_RELEASE=LOCKED',s);self.assertIn('FOR_CONSTRUCTION=LOCKED',s)
if __name__=='__main__':unittest.main(verbosity=2)
