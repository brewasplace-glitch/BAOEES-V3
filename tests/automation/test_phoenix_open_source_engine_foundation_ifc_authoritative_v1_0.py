import json,tempfile,unittest
from pathlib import Path
from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design
from phoenix.engines.open_source_engine_registry import evaluate_registry

class T(unittest.TestCase):
 def ws(self,r):
  w=r/"projects/runtime/PHOENIX-PAT-IFC";a=w/"results/session_adapters/architecture";a.mkdir(parents=True)
  (a/"architectural_model.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-IFC","description":"Vrijstaande woning van twee bouwlagen"}))
  (a/"architectural_session_intake.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-IFC","prompt":"Ontwerp een vrijstaande woning van twee bouwlagen"}))
  (a/"project_context.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-IFC","parcel_width":28,"parcel_depth":42}))
  (a/"site_context.json").write_text("{}")
  for p in (w/"results/session_adapters/digital_twin/central_project_digital_twin.json",w/"digital_twin/central_project_digital_twin.json"):
   p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({"project_id":"PHOENIX-PAT-IFC"}))
  return w

 def test_registry_ifcopenshell_available(self):
  repo=Path(__file__).resolve().parents[2]
  state=evaluate_registry(repo/"configs/phoenix/open_source_engine_registry_v1_0.json")
  ifc=next(s for s in state["states"] if s["id"]=="ifcopenshell")
  self.assertTrue(ifc["available"])
  self.assertTrue(state["ifc_authoritative_ready"])

 def test_real_ifc_authoritative_model(self):
  import ifcopenshell
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);x=run_multivariant_design(r,w)
   self.assertEqual(x["status"],"PASSED")
   a=w/"results/session_adapters/architecture"
   p=a/"ifc/PHOENIX-PAT-IFC_architectural_authoritative.ifc"
   self.assertTrue(p.exists())
   model=ifcopenshell.open(str(p))
   self.assertEqual(len(model.by_type("IfcProject")),1)
   self.assertEqual(len(model.by_type("IfcSite")),1)
   self.assertEqual(len(model.by_type("IfcBuilding")),1)
   self.assertEqual(len(model.by_type("IfcBuildingStorey")),2)
   self.assertGreaterEqual(len(model.by_type("IfcWall")),12)
   self.assertEqual(len(model.by_type("IfcSlab")),2)
   self.assertGreaterEqual(len(model.by_type("IfcSpace")),10)
   self.assertEqual(len(model.by_type("IfcDoor")),1)
   self.assertGreaterEqual(len(model.by_type("IfcWindow")),6)
   self.assertEqual(len(model.by_type("IfcRoof")),1)

 def test_ifc_becomes_authoritative_and_bim_lite_fallback(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);run_multivariant_design(r,w)
   a=w/"results/session_adapters/architecture"
   m=json.loads((a/"architectural_model.json").read_text())
   self.assertEqual(m["architectural_model_source"],"REAL_MULTI_VARIANT_PARAMETRIC_DESIGN")
   self.assertEqual(m["authoritative_geometry_source"],"IFC_AUTHORITATIVE")
   self.assertEqual(m["authoritative_geometry_format"],"IFC")
   self.assertEqual(m["bim_lite_role"],"PRESENTATION_FALLBACK_ONLY")
   e=json.loads((a/"ifc/ifc_authoritative_model_evidence.json").read_text())
   self.assertEqual(e["authoritative_geometry_format"],"IFC")
   self.assertEqual(e["production_release"],"LOCKED")
   twin=json.loads((w/"digital_twin/central_project_digital_twin.json").read_text())
   self.assertEqual(twin["authoritative_architectural_geometry"]["format"],"IFC")
   self.assertEqual(twin["authoritative_architectural_geometry"]["source"],"IFC_AUTHORITATIVE")

if __name__=="__main__":unittest.main()
