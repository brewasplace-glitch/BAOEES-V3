import json,tempfile,unittest
from pathlib import Path
from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design

class T(unittest.TestCase):
 def ws(self,r):
  w=r/"projects/runtime/PHOENIX-PAT-TEST";a=w/"results/session_adapters/architecture";a.mkdir(parents=True)
  (a/"architectural_model.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","description":"Vrijstaande woning van twee bouwlagen"}))
  (a/"architectural_session_intake.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","prompt":"Ontwerp een vrijstaande woning van twee bouwlagen"}))
  (a/"project_context.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","parcel_width":28,"parcel_depth":42}))
  (a/"site_context.json").write_text("{}")
  for p in (w/"results/session_adapters/digital_twin/central_project_digital_twin.json",w/"digital_twin/central_project_digital_twin.json"):
   p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST"}))
  return w
 def test_bim_lite_elements_and_house(self):
  with tempfile.TemporaryDirectory() as d:
   w=self.ws(Path(d));run_multivariant_design(Path(d),w)
   m=json.loads((w/"results/session_adapters/architecture/architectural_bim_lite_model.json").read_text())
   types={e["type"] for e in m["elements"]}
   for k in ("wall","internal_wall","slab","roof","window","door","stairs"):self.assertIn(k,types)
   self.assertGreaterEqual(len(m["elements"]),30)
   h=(w/"results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html").read_text()
   for s in ("drawHouse","door(W*.5)","win(true","BIM-Lite"):self.assertIn(s,h)
 def test_five_real_presentation_artifacts(self):
  with tempfile.TemporaryDirectory() as d:
   w=self.ws(Path(d));run_multivariant_design(Path(d),w)
   paths=["viewer_3d/phoenix_3d_viewer.html","walkthrough/phoenix_walkthrough.html","drivethrough/phoenix_drivethrough.html","bird_view/phoenix_bird_view.html","auto_video/phoenix_auto_video_presentation.html"]
   for rel in paths:
    p=w/"results/generated_visual_media"/rel;self.assertTrue(p.exists(),rel);self.assertIn("VARIANT B",p.read_text())
 def test_contract_locked(self):
  with tempfile.TemporaryDirectory() as d:
   w=self.ws(Path(d));run_multivariant_design(Path(d),w)
   c=json.loads((w/"results/session_adapters/architecture/strict_presentation_output_contract.json").read_text())
   self.assertEqual(len(c["presentation_outputs"]),5)
   self.assertTrue(c["technical_evidence_is_not_presentation_output"])
   self.assertTrue(c["cross_project_presentation_forbidden"])
   m=json.loads((w/"results/session_adapters/architecture/architectural_bim_lite_model.json").read_text())
   self.assertEqual(m["production_release"],"LOCKED")
if __name__=="__main__":unittest.main()
