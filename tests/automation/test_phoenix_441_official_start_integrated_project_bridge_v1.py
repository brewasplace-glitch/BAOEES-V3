from __future__ import annotations

from pathlib import Path
import json
import unittest

from phoenix.local_app.integrated_project_bridge import (
    MODE_MAP,
    OfficialStartIntegratedProjectBridge,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


class Phase19OfficialStartBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = OfficialStartIntegratedProjectBridge(ROOT)
        cls.policy = json.loads((CFG / "start_screen_integrated_project_bridge_v1.json").read_text(encoding="utf-8"))
        cls.html = (ROOT / "phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_phase19_integrated_project_bridge_v1_0.js").read_text(encoding="utf-8")
        cls.server = (ROOT / "phoenix/local_app/server.py").read_text(encoding="utf-8")

    def session(self, mode="autonomous"):
        return {
            "session_id": "PHX-20261004T010000Z-1234abcd",
            "project_type": "BOUW",
            "project_mode": mode,
            "brief": "Ontwerp een nieuw woonhuis met volledige technische uitwerking.",
            "selected_project": "",
            "location_reference": "geo:test-site",
            "desired_outputs": ["reports", "calculations", "cost_estimate", "project_zip"],
            "verified_inputs": {},
        }

    def test_01_policy_schema(self): self.assertEqual(self.policy["schema"], "PHOENIX_START_SCREEN_INTEGRATED_PROJECT_BRIDGE_POLICY_V1")
    def test_02_policy_active(self): self.assertEqual(self.policy["status"], "ACTIVE_GOVERNED")
    def test_03_policy_fail_closed(self): self.assertTrue(self.policy["fail_closed"])
    def test_04_no_fabrication(self): self.assertTrue(self.policy["no_output_fabrication"])
    def test_05_no_engine_activation(self): self.assertFalse(self.policy["automatic_engine_activation"])
    def test_06_no_auto_release(self): self.assertFalse(self.policy["automatic_professional_release"])
    def test_07_professional_release_required(self): self.assertTrue(self.policy["professional_release_required"])
    def test_08_exact_stage_count(self): self.assertEqual(self.policy["stage_count"], 15)
    def test_09_exact_discipline_count(self): self.assertEqual(self.policy["discipline_count"], 14)
    def test_10_exact_variant_count(self): self.assertEqual(self.policy["variant_count"], 5)
    def test_11_mode_count(self): self.assertEqual(len(MODE_MAP), 3)
    def test_12_manual_mapping(self): self.assertEqual(MODE_MAP["manual"], "LEVEL_0_MANUAL")
    def test_13_guided_mapping(self): self.assertEqual(MODE_MAP["guided"], "LEVEL_2_SEMI_AUTONOMOUS")
    def test_14_autonomous_mapping(self): self.assertIn("LEVEL_3", MODE_MAP["autonomous"])
    def test_15_contract_project_id(self): self.assertTrue(self.bridge.build_contract(self.session())["project_id"].startswith("PHX-"))
    def test_16_contract_instruction(self): self.assertIn("woonhuis", self.bridge.build_contract(self.session())["instruction"])
    def test_17_contract_location(self): self.assertEqual(self.bridge.build_contract(self.session())["location_reference"], "geo:test-site")
    def test_18_contract_outputs(self): self.assertEqual(len(self.bridge.build_contract(self.session())["requested_outputs"]), 4)
    def test_19_contract_does_not_invent_variants(self): self.assertEqual(self.bridge.build_contract(self.session())["design_variants"], [])
    def test_20_contract_does_not_select_variant(self): self.assertIsNone(self.bridge.build_contract(self.session())["selected_variant_id"])
    def test_21_brief_evidence_hash(self): self.assertEqual(len(self.bridge.build_contract(self.session())["evidence"]["project_intake"]["project_brief"]["sha256"]), 64)
    def test_22_bad_mode_denied(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_MODE_DENY"): self.bridge.build_contract(self.session("unsafe"))
    def test_23_outputs_array_required(self):
        value = self.session(); value["desired_outputs"] = "reports"
        with self.assertRaisesRegex(ValueError, "OUTPUTS_ARRAY"): self.bridge.build_contract(value)
    def test_24_plan_schema(self): self.assertEqual(self.bridge.plan(self.session(), persist=False).payload["schema"], "PHOENIX_START_SCREEN_INTEGRATED_PROJECT_BRIDGE_V1")
    def test_25_plan_run_id(self): self.assertRegex(self.bridge.plan(self.session(), persist=False).run_id, r"^P19-[A-F0-9]{16}$")
    def test_26_plan_stage_count(self): self.assertEqual(self.bridge.plan(self.session(), persist=False).payload["stage_count"], 15)
    def test_27_plan_disciplines(self): self.assertEqual(len(self.bridge.plan(self.session(), persist=False).payload["discipline_plan"]["engines"]), 14)
    def test_28_plan_no_release(self): self.assertFalse(self.bridge.plan(self.session(), persist=False).payload["professional_release"])
    def test_29_plan_no_mutation_claim(self): self.assertFalse(self.bridge.plan(self.session(), persist=False).payload["repository_mutation"])
    def test_30_plan_no_activation(self): self.assertFalse(self.bridge.plan(self.session(), persist=False).payload["automatic_engine_activation"])
    def test_31_plan_no_fabrication(self): self.assertTrue(self.bridge.plan(self.session(), persist=False).payload["no_output_fabrication"])
    def test_32_variant_stage_waits(self):
        rows = self.bridge.plan(self.session(), persist=False).payload["stages"]
        self.assertEqual(next(x for x in rows if x["stage_id"] == "five_design_variants")["status"], "WAITING_FOR_FIVE_VARIANTS")
    def test_33_html_loads_bridge(self): self.assertIn("PROJECT_PHOENIX_phase19_integrated_project_bridge_v1_0.js", self.html)
    def test_34_js_binds_start(self): self.assertIn('$("startBtn")', self.js)
    def test_35_js_calls_session_api(self): self.assertIn('/api/project-analysis/start', self.js)
    def test_36_js_calls_integrated_api(self): self.assertIn('/api/integrated-project/plan', self.js)
    def test_37_js_displays_variants(self): self.assertIn("Varianten", self.js)
    def test_38_js_displays_stages(self): self.assertIn("Geintegreerde projectvoortgang", self.js)
    def test_39_server_post_route(self): self.assertIn('parsed.path == "/api/integrated-project/plan"', self.server)
    def test_40_server_get_route(self): self.assertIn('/api/integrated-project/runs/', self.server)
    def test_41_server_status_advertises_bridge(self): self.assertIn('integrated_project_orchestration_bridge', self.server)
    def test_42_result_hash_bound(self): self.assertEqual(len(self.bridge.plan(self.session(), persist=False).payload["orchestration_result_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
