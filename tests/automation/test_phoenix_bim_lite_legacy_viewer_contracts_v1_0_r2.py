import json,tempfile,unittest
from pathlib import Path
from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design

class TestPhoenixBimLiteLegacyViewerContractsR2(unittest.TestCase):
 def test_legacy_geometry_markers_and_new_house_renderer_coexist(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=r/"projects/runtime/PHOENIX-PAT-TEST";a=w/"results/session_adapters/architecture";a.mkdir(parents=True)
   (a/"architectural_model.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","description":"Vrijstaande woning van twee bouwlagen"}))
   (a/"architectural_session_intake.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","prompt":"Ontwerp een vrijstaande woning van twee bouwlagen"}))
   (a/"project_context.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST","parcel_width":28,"parcel_depth":42}))
   (a/"site_context.json").write_text("{}")
   for p in (w/"results/session_adapters/digital_twin/central_project_digital_twin.json",w/"digital_twin/central_project_digital_twin.json"):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST"}))
   run_multivariant_design(r,w)
   t=(w/"results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html").read_text()
   self.assertIn("const W=11.5,D=9.5,H=6.4",t)
   self.assertIn("V=[[-W/2,0,-D/2]",t)
   self.assertIn("E=[[0,1],[1,2],[2,3],[3,0]",t)
   self.assertIn("drawHouse",t)
   self.assertIn("door(W*.5)",t)
   self.assertIn("onpointermove",t)
   self.assertIn("onwheel",t)

if __name__=="__main__":unittest.main()
