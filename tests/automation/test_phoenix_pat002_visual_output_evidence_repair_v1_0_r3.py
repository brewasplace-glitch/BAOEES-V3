import json,tempfile,unittest
from pathlib import Path
from phoenix.autonomy.desired_output_evidence import validate_desired_output_evidence

class TestVisualEvidenceR3(unittest.TestCase):
 def ws(self,r):
  w=r/"projects"/"runtime"/"PHOENIX-PAT-002-TEST"; p=w/"results"/"session_adapters"/"digital_twin"/"central_project_digital_twin.json";p.parent.mkdir(parents=True);p.write_text(json.dumps({"project_id":"PHOENIX-PAT-002-TEST"}));return w
 def test_viewer(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);x=validate_desired_output_evidence(repository=r,workspace=w,output_id="viewer_3d",capability_states={});self.assertEqual(x["status"],"PASSED");self.assertTrue(any(v.endswith(".html") for v in x["evidence"]));html=next(w.rglob("*.html")).read_text(encoding="utf-8");self.assertIn("height:100%",html)
 def test_video(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);x=validate_desired_output_evidence(repository=r,workspace=w,output_id="auto_video",capability_states={});self.assertEqual(x["status"],"PASSED");self.assertTrue(any(v.endswith(".avi") for v in x["evidence"]));raw=next(w.rglob("*.avi")).read_bytes();self.assertEqual(raw[:4],b"RIFF");self.assertEqual(raw[8:12],b"AVI ")
 def test_fail_closed_without_twin(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=r/"projects"/"runtime"/"NO-TWIN";w.mkdir(parents=True);a=validate_desired_output_evidence(repository=r,workspace=w,output_id="viewer_3d",capability_states={});b=validate_desired_output_evidence(repository=r,workspace=w,output_id="auto_video",capability_states={});self.assertEqual(a["status"],"BLOCKED");self.assertEqual(b["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
