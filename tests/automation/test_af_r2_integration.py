import importlib.util
import pathlib
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('af_r2', ROOT/'phoenix/afoundation/integration.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
 def test_module_registry_has_required_functions(self):
  self.assertIn('geometry_consistency',mod.MODULES)
  self.assertIn('build_runner',mod.MODULES)
 def test_invalid_hash_rejected(self):
  with self.assertRaises(ValueError):mod.assess(pathlib.Path('.'),'invalid')
 def test_digest(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'x';p.write_bytes(b'abc')
   self.assertEqual(mod.digest(p),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
 def test_dirty_repo_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t)
   def git(*args):return subprocess.check_output(['git','-C',str(r),*args],text=True).strip()
   git('init','-q','-b','project-phoenix')
   git('config','user.email','test@example.com');git('config','user.name','Test')
   (r/'one.txt').write_text('one');git('add','.');git('commit','-qm','base')
   head=git('rev-parse','HEAD');(r/'dirty.txt').write_text('dirty')
   # no upstream + dirty + missing modules => blocked
   with self.assertRaises(RuntimeError):mod.assess(r,head)
if __name__=='__main__':unittest.main()
