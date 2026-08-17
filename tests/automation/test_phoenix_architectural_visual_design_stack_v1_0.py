import tempfile,unittest
from unittest.mock import patch
from pathlib import Path

from phoenix.engines.visual_engine_discovery_v1_0 import discover_visual_stack
from phoenix.engines.ifc_visual_mesh_adapter_v1_0 import ifc_to_obj
from phoenix.engines.adapters.blender_visual_adapter_v1_0 import capability_state as blender_state
from phoenix.engines.adapters.freecad_adapter_v1_0 import capability_state as freecad_state
from phoenix.engines.adapters.sweethome3d_adapter_v1_0 import capability_state as sweet_state
from phoenix.engines.adapters.comfyui_adapter_v1_0 import capability_state as comfy_state
from phoenix.engines.open_source_engine_registry import evaluate_registry
from phoenix.engines.architectural_visual_pipeline_v1_0 import resolve_authoritative_ifc

class T(unittest.TestCase):
 def test_visual_discovery_contract(self):
  repo=Path(__file__).resolve().parents[2]
  s=discover_visual_stack(repo)
  self.assertEqual(set(s["engines"]),{"blender","freecad","sweethome3d","comfyui"})
  for v in s["engines"].values(): self.assertIn("available",v)

 def test_adapters_report_capabilities(self):
  repo=Path(__file__).resolve().parents[2]
  for fn in (blender_state,freecad_state,sweet_state,comfy_state):
   s=fn(repo);self.assertIn("available",s);self.assertTrue(s["capabilities"])

 def test_registry_contains_visual_engines(self):
  repo=Path(__file__).resolve().parents[2]
  state=evaluate_registry(repo/"configs/phoenix/open_source_engine_registry_v1_0.json")
  ids={x["id"] for x in state["states"]}
  for eid in ("blender","freecad","sweethome3d","comfyui"):self.assertIn(eid,ids)

 def test_authoritative_ifc_resolution(self):
  import json
  with tempfile.TemporaryDirectory() as td:
   w=Path(td)/"projects/runtime/P";a=w/"results/session_adapters/architecture";(a/"ifc").mkdir(parents=True)
   p=a/"ifc/P_architectural_authoritative.ifc";p.write_text("IFC")
   (a/"architectural_model.json").write_text(json.dumps({"authoritative_ifc":str(p)}))
   self.assertEqual(resolve_authoritative_ifc(w),p.resolve())

 def test_freecad_gui_is_not_version_probed(self):
  import phoenix.engines.visual_engine_discovery_v1_0 as dmod
  with tempfile.TemporaryDirectory() as td:
   exe=Path(td)/"freecad.exe";exe.write_text("fake")
   with patch("subprocess.run") as run:
    r=dmod._result("freecad",exe,"TEST")
   self.assertFalse(run.called)
   self.assertIsNone(r["version"])
   self.assertTrue(r["gui_executable"])
   self.assertFalse(r["automation_executable"])

 def test_freecadcmd_is_console_candidate(self):
  import phoenix.engines.visual_engine_discovery_v1_0 as dmod
  with tempfile.TemporaryDirectory() as td:
   exe=Path(td)/"FreeCADCmd.exe";exe.write_text("fake")
   with patch("subprocess.run") as run:
    run.return_value.stdout="FreeCAD 1.1.1";run.return_value.stderr=""
    r=dmod._result("freecad",exe,"TEST")
   self.assertTrue(run.called)
   self.assertTrue(r["automation_executable"])

 def test_ifc_to_obj_real_geometry(self):
  import ifcopenshell,ifcopenshell.api.project,ifcopenshell.api.root,ifcopenshell.api.unit,ifcopenshell.api.context,ifcopenshell.api.geometry
  import numpy as np
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);m=ifcopenshell.api.project.create_file(version="IFC4")
   ifcopenshell.api.root.create_entity(m,ifc_class="IfcProject",name="T")
   ifcopenshell.api.unit.assign_unit(m)
   ctx=ifcopenshell.api.context.add_context(m,context_type="Model")
   body=ifcopenshell.api.context.add_context(m,context_type="Model",context_identifier="Body",target_view="MODEL_VIEW",parent=ctx)
   wall=ifcopenshell.api.root.create_entity(m,ifc_class="IfcWall",name="Wall")
   rep=ifcopenshell.api.geometry.add_wall_representation(m,context=body,length=4,height=3,thickness=.2)
   ifcopenshell.api.geometry.assign_representation(m,product=wall,representation=rep)
   ifcopenshell.api.geometry.edit_object_placement(m,product=wall,matrix=np.eye(4),is_si=True)
   ip=r/"a.ifc";op=r/"a.obj";m.write(str(ip))
   e=ifc_to_obj(ip,op)
   self.assertTrue(op.exists());self.assertGreater(e["triangles"],0);self.assertIn("v ",op.read_text())

if __name__=="__main__":unittest.main()
