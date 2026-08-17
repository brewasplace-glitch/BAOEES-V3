import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock

from phoenix.engines.visual_engine_provisioning_v1_0 import (
    PACKAGE_IDS,winget_install,winget_list,blender_headless_smoke
)
from phoenix.engines.visual_engine_discovery_v1_0 import discover_visual_stack
from phoenix.engines.open_source_engine_registry import evaluate_registry

class TestPhoenixVisualEngineProvisioningV10(unittest.TestCase):
 def test_package_ids_are_exact(self):
  self.assertEqual(PACKAGE_IDS["blender"],"BlenderFoundation.Blender")
  self.assertEqual(PACKAGE_IDS["sweethome3d"],"eTeks.SweetHome3D")
  self.assertEqual(PACKAGE_IDS["comfyui"],"Comfy.ComfyUI-Desktop")

 def test_winget_install_is_silent_and_exact(self):
  proc=MagicMock(returncode=0,stdout="ok",stderr="")
  with patch("shutil.which",return_value=r"C:\Windows\winget.exe"),patch("subprocess.run",return_value=proc) as run:
   result=winget_install("blender")
  self.assertTrue(result["passed"])
  cmd=run.call_args.args[0]
  self.assertIn("--exact",cmd)
  self.assertIn("--silent",cmd)
  self.assertIn("--disable-interactivity",cmd)
  self.assertIn("BlenderFoundation.Blender",cmd)

 def test_comfyui_models_are_not_part_of_provisioner(self):
  repo=Path(__file__).resolve().parents[2]
  policy=json.loads((repo/"configs/phoenix/visual_engine_provisioning_policy_v1_0.json").read_text())
  self.assertFalse(policy["engines"]["comfyui"]["models_auto_install"])
  self.assertIn("NO_MODEL_WEIGHTS_AUTO_DOWNLOAD",policy["rules"])

 def test_registry_provisioning_contract(self):
  repo=Path(__file__).resolve().parents[2]
  data=json.loads((repo/"configs/phoenix/open_source_engine_registry_v1_0.json").read_text())
  ids={e["id"]:e for e in data["engines"]}
  self.assertEqual(data["registry_version"],"1.3.0")
  self.assertEqual(ids["blender"]["provisioning"]["package_id"],"BlenderFoundation.Blender")
  self.assertEqual(ids["sweethome3d"]["provisioning"]["package_id"],"eTeks.SweetHome3D")
  self.assertEqual(ids["comfyui"]["provisioning"]["package_id"],"Comfy.ComfyUI-Desktop")

 def test_blender_is_available_and_headless(self):
  repo=Path(__file__).resolve().parents[2]
  state=discover_visual_stack(repo)
  blender=state["engines"]["blender"]
  self.assertTrue(blender["available"],"Blender must be provisioned before regression")
  smoke=blender_headless_smoke(Path(blender["executable"]),timeout=180)
  self.assertTrue(smoke["passed"],smoke)

 def test_central_registry_reports_comfy_desktop_state(self):
  repo=Path(__file__).resolve().parents[2]
  state=evaluate_registry(repo/"configs/phoenix/open_source_engine_registry_v1_0.json")
  ids={x["id"]:x for x in state["states"]}
  self.assertIn("desktop_package_installed",ids["comfyui"])

if __name__=="__main__":unittest.main()
