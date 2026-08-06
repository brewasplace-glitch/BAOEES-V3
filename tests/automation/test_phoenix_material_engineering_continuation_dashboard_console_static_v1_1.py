from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class StaticIntegrationTests(unittest.TestCase):
    def test_policy_default_checked_and_availability_nonblocking(self):
        data=json.loads((ROOT/"configs/phoenix/material_engineering_continuation_policy_v1_1.json").read_text(encoding="utf-8"))
        self.assertTrue(data["dashboard_control"]["default_checked"])
        self.assertFalse(data["availability_continuation"]["unknown_or_unavailable_blocks_engineering"])
        self.assertEqual(data["production_release"],"LOCKED")
    def test_session_adapter_markers_present(self):
        text=(ROOT/"phoenix/autonomy/session_adapters.py").read_text(encoding="utf-8-sig")
        self.assertIn("PHOENIX_MATERIAL_ENGINEERING_CONTINUATION_v1_1",text)
        self.assertIn("postprocess_structural_result",text)
        self.assertIn("postprocess_cost_result",text)
    def test_fixed_r1_repository_wide_gate_hooks_present(self):
        structural=[]
        cost=[]
        for path in ROOT.rglob("*.py"):
            rel=path.relative_to(ROOT)
            if any(part in {".git","outputs","projects","tests","__pycache__"} for part in rel.parts):
                continue
            try:
                text=path.read_text(encoding="utf-8-sig")
            except Exception:
                continue
            if "_phoenix_material_mode_structural_gate(locals())" in text:
                structural.append(rel.as_posix())
            if "_phoenix_material_mode_cost_gate(locals())" in text:
                cost.append(rel.as_posix())
        self.assertTrue(structural, "structural material gate hook missing")
        self.assertTrue(cost, "cost material gate hook missing")
    def test_launcher_console_marker_present(self):
        text=(ROOT/"START_PROJECT_PHOENIX_OFFICIAL.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("PHOENIX_ACTIVE_CONSOLE_REGISTRATION_v1_1",text)
    def test_console_bridge_has_no_secret_value(self):
        text=(ROOT/"phoenix/local_app/console_return_bridge.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_BRAVE_SEARCH_API_KEY",text); self.assertNotIn("BSA",text)
if __name__=="__main__": unittest.main()
