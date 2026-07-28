from pathlib import Path
import hashlib,tempfile,unittest
from phoenix.architecture.integrated_suite_v4_0_0 import run
ROOT=Path(__file__).resolve().parents[2];MODEL=ROOT/"configs/projects/moskee_bunschoten_architectural_model_v4_0_0.json"
def tree(p): return {x.relative_to(p).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(p.rglob("*")) if x.is_file()}
class T(unittest.TestCase):
 def test_generate(self):
  with tempfile.TemporaryDirectory() as d:
   o=Path(d)/"o";m=run(MODEL,o)
   self.assertEqual(m["release_status"],"CONCEPT_REVIEW_REQUIRED")
   self.assertTrue((o/"drawings/floor_plan_L00.svg").is_file())
   self.assertTrue((o/"drawings/elevation_concept.svg").is_file())
   self.assertTrue((o/"05_artifact_manifest.json").is_file())
 def test_deterministic(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/"a";b=Path(d)/"b";run(MODEL,a);run(MODEL,b);self.assertEqual(tree(a),tree(b))
if __name__=="__main__":unittest.main()
