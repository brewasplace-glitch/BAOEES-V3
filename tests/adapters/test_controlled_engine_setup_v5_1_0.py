from pathlib import Path
import hashlib,json,tempfile,unittest
from phoenix.adapters.open_source.controlled_install import find_artifact,register_portable,load_registry

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"configs/phoenix/third_party_engine_registry_v5_1_0.json"

class T(unittest.TestCase):
 def test_registry(self):
  r=load_registry(REG)
  self.assertEqual(len(r["engines"]),7)
  self.assertTrue(r["policy"]["verify_sha256_before_install_or_registration"])
 def test_hash_rejection_and_registration(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);src=td/"src";src.mkdir()
   exe=src/"OpenSees.exe";exe.write_bytes(b"not-a-real-executable")
   with self.assertRaises(ValueError):
    register_portable("opensees",src,td/"managed",REG,"0"*64)
   digest=hashlib.sha256(exe.read_bytes()).hexdigest()
   result=register_portable("opensees",src,td/"managed",REG,digest)
   self.assertIn(result.status,{"REGISTERED","REGISTERED_REVIEW_REQUIRED"})
   self.assertTrue(Path(result.registered_path).is_file())
 def test_artifact_discovery_case_insensitive(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"CCX.EXE";p.write_bytes(b"x")
   self.assertEqual(find_artifact(Path(td),["ccx.exe"]),p)

if __name__=="__main__":unittest.main()
