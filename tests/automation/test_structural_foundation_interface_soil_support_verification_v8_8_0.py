import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_foundation_interface_soil_support_verification_v8_8_0.py"
spec = importlib.util.spec_from_file_location("phx_v880", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralFoundationInterfaceSoilSupportV880(unittest.TestCase):
    def setUp(self): self.payload = mod._demo_payload()
    def report(self): return mod.build_foundation_report(self.payload)

    def test_01_engine_identity(self):
        r = self.report(); self.assertEqual(r["engine"]["id"], mod.ENGINE_ID); self.assertEqual(r["engine"]["version"], "8.8.0")
    def test_02_v87_source_contract_required(self):
        b = deepcopy(self.payload); b["source_engine"] = "PHX-OLD"
        with self.assertRaisesRegex(ValueError, "v8.7.0"): mod.build_foundation_report(b)
    def test_03_connection_state_gate(self):
        b = deepcopy(self.payload); b["connection_support_joint_state"] = "CONNECTION_SUPPORT_JOINT_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "not accepted"): mod.build_foundation_report(b)
    def test_04_basis_requires_traceable_source(self):
        b = deepcopy(self.payload); b["foundation_geotechnical_basis"]["source_reference"] = ""
        with self.assertRaisesRegex(ValueError, "source_reference"): mod.build_foundation_report(b)
    def test_05_complete_support_mapping(self):
        r = self.report(); self.assertEqual(r["summary"]["unmapped_support_ids"], []); self.assertEqual(len(r["support_foundation_interface"]["interfaces"]), 2)
    def test_06_missing_support_mapping_creates_incomplete_state(self):
        b = deepcopy(self.payload); b["support_foundation_interfaces"] = b["support_foundation_interfaces"][:1]
        r = mod.build_foundation_report(b); self.assertEqual(r["verification_state"], "FOUNDATION_INTERFACE_SOIL_SUPPORT_VERIFICATION_INCOMPLETE"); self.assertIn("S2", r["summary"]["unmapped_support_ids"])
    def test_07_unknown_support_mapping_rejected(self):
        b = deepcopy(self.payload); b["support_foundation_interfaces"][0]["support_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown support"): mod.build_foundation_report(b)
    def test_08_unknown_foundation_mapping_rejected(self):
        b = deepcopy(self.payload); b["support_foundation_interfaces"][0]["foundation_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown foundation"): mod.build_foundation_report(b)
    def test_09_unknown_soil_zone_mapping_rejected(self):
        b = deepcopy(self.payload); b["support_foundation_interfaces"][0]["soil_zone_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown soil zone"): mod.build_foundation_report(b)
    def test_10_capacity_ratio(self):
        r = self.report(); c = next(x for x in r["verification_checks"] if x["check_type"] == "SOIL_BEARING_PRESSURE")
        self.assertAlmostEqual(c["utilization"], c["demand"] / c["capacity"]); self.assertEqual(c["status"], "PASS")
    def test_11_failed_capacity_creates_review(self):
        b = deepcopy(self.payload); b["verification_checks"][0]["demand"] = 900; b["verification_checks"][0]["capacity"] = 600
        r = mod.build_foundation_report(b); self.assertEqual(r["verification_state"], "FOUNDATION_INTERFACE_SOIL_SUPPORT_REVIEW_REQUIRED"); self.assertGreater(r["summary"]["review_item_count"], 0)
    def test_12_unknown_pile_rejected(self):
        b = deepcopy(self.payload); c = next(x for x in b["verification_checks"] if x["check_type"] == "PILE_AXIAL_CAPACITY"); c["pile_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown pile"): mod.build_foundation_report(b)
    def test_13_unknown_pile_group_rejected(self):
        b = deepcopy(self.payload); c = next(x for x in b["verification_checks"] if x["check_type"] == "PILE_GROUP_CAPACITY"); c["pile_group_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown pile group"): mod.build_foundation_report(b)
    def test_14_evidence_failure_creates_review(self):
        b = deepcopy(self.payload); c = next(x for x in b["verification_checks"] if x["check_type"] == "SOIL_SPRING_STIFFNESS_EVIDENCE"); c["verified"] = False
        r = mod.build_foundation_report(b); self.assertEqual(r["verification_state"], "FOUNDATION_INTERFACE_SOIL_SUPPORT_REVIEW_REQUIRED")
    def test_15_missing_mandatory_type_detected(self):
        b = deepcopy(self.payload); b["verification_checks"] = [x for x in b["verification_checks"] if x["check_type"] != "UPLIFT_RESISTANCE"]
        r = mod.build_foundation_report(b); self.assertEqual(r["verification_state"], "FOUNDATION_INTERFACE_SOIL_SUPPORT_VERIFICATION_INCOMPLETE"); self.assertIn("UPLIFT_RESISTANCE", r["summary"]["missing_mandatory_check_types"])
    def test_16_missing_normative_reference_rejected(self):
        b = deepcopy(self.payload); b["verification_checks"][0]["normative_reference"] = ""
        with self.assertRaisesRegex(ValueError, "missing normative_reference"): mod.build_foundation_report(b)
    def test_17_nonfinite_rejected(self):
        b = deepcopy(self.payload); b["verification_checks"][0]["demand"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"): mod.build_foundation_report(b)
    def test_18_zero_capacity_rejected(self):
        b = deepcopy(self.payload); b["verification_checks"][0]["capacity"] = 0
        with self.assertRaisesRegex(ValueError, "must be > 0"): mod.build_foundation_report(b)
    def test_19_all_supported_types_present_and_pass(self):
        r = self.report(); self.assertEqual({x["check_type"] for x in r["verification_checks"]}, mod.SUPPORTED_CHECK_TYPES); self.assertTrue(all(x["status"] == "PASS" for x in r["verification_checks"]))
    def test_20_release_safety_and_digital_twin(self):
        r = self.report(); self.assertFalse(r["release"]["automatic_geotechnical_approval"]); self.assertFalse(r["release"]["automatic_structural_approval"]); self.assertFalse(r["release"]["automatic_foundation_approval"]); self.assertEqual(r["release"]["structural_model_release"], "LOCKED"); self.assertTrue(r["digital_twin_writeback"]["enabled"])


if __name__ == "__main__": unittest.main()
