import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_foundation_design_reinforcement_detailing_v8_9_0.py"
spec = importlib.util.spec_from_file_location("phx_v890", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralFoundationDesignReinforcementDetailingV890(unittest.TestCase):
    def setUp(self):
        self.payload = mod._demo_payload()

    def report(self):
        return mod.build_foundation_design_report(self.payload)

    def test_01_engine_identity(self):
        r = self.report()
        self.assertEqual(r["engine"]["id"], mod.ENGINE_ID)
        self.assertEqual(r["engine"]["version"], "8.9.0")

    def test_02_v88_source_contract_required(self):
        b = deepcopy(self.payload)
        b["source_engine"] = "PHX-OLD"
        with self.assertRaisesRegex(ValueError, "v8.8.0"):
            mod.build_foundation_design_report(b)

    def test_03_v88_state_gate_required(self):
        b = deepcopy(self.payload)
        b["foundation_interface_soil_support_state"] = "FOUNDATION_INTERFACE_SOIL_SUPPORT_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "not accepted"):
            mod.build_foundation_design_report(b)

    def test_04_basis_requires_traceable_source(self):
        b = deepcopy(self.payload)
        b["foundation_design_basis"]["source_reference"] = ""
        with self.assertRaisesRegex(ValueError, "source_reference"):
            mod.build_foundation_design_report(b)

    def test_05_unknown_concrete_material_rejected(self):
        b = deepcopy(self.payload)
        b["foundation_elements"][0]["concrete_material_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown concrete material"):
            mod.build_foundation_design_report(b)

    def test_06_unsupported_foundation_type_rejected(self):
        b = deepcopy(self.payload)
        b["foundation_elements"][0]["type"] = "MAGIC_FOUNDATION"
        with self.assertRaisesRegex(ValueError, "unsupported foundation type"):
            mod.build_foundation_design_report(b)

    def test_07_nonpositive_geometry_rejected(self):
        b = deepcopy(self.payload)
        b["foundation_elements"][0]["dimensions"]["length_m"] = 0
        with self.assertRaisesRegex(ValueError, "must be > 0"):
            mod.build_foundation_design_report(b)

    def test_08_unknown_reinforcement_element_rejected(self):
        b = deepcopy(self.payload)
        b["reinforcement_groups"][0]["foundation_element_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown foundation element"):
            mod.build_foundation_design_report(b)

    def test_09_unknown_reinforcement_material_rejected(self):
        b = deepcopy(self.payload)
        b["reinforcement_groups"][0]["material_id"] = "NOPE"
        with self.assertRaisesRegex(ValueError, "unknown reinforcement material"):
            mod.build_foundation_design_report(b)

    def test_10_reinforcement_area_and_mass_generated(self):
        r = self.report()
        g = r["reinforcement_groups"][0]
        expected_area = 11 * math.pi * 16 ** 2 / 4.0
        self.assertAlmostEqual(g["provided_area_mm2"], expected_area)
        self.assertGreater(g["estimated_mass_kg"], 0)
        self.assertGreater(r["reinforcement_schedule"]["estimated_reinforcement_mass_kg"], 0)

    def test_11_concrete_quantity_generated(self):
        r = self.report()
        f1 = next(x for x in r["foundation_elements"] if x["id"] == "F1")
        self.assertAlmostEqual(f1["concrete_volume_m3"], 2.0 * 2.0 * 0.45)
        self.assertGreater(r["quantity_takeoff"]["total_concrete_volume_m3"], f1["concrete_volume_m3"])

    def test_12_capacity_utilization(self):
        r = self.report()
        c = next(x for x in r["verification_checks"] if x["check_type"] == "PAD_FLEXURAL_CAPACITY")
        self.assertAlmostEqual(c["utilization"], c["demand"] / c["capacity"])
        self.assertEqual(c["status"], "PASS")

    def test_13_failed_capacity_creates_review_state(self):
        b = deepcopy(self.payload)
        b["verification_checks"][0]["demand"] = 200
        b["verification_checks"][0]["capacity"] = 100
        r = mod.build_foundation_design_report(b)
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_REVIEW_REQUIRED")
        self.assertGreater(r["summary"]["review_item_count"], 0)

    def test_14_evidence_failure_creates_review_state(self):
        b = deepcopy(self.payload)
        c = next(x for x in b["verification_checks"] if x["check_type"] == "CONCRETE_COVER_EVIDENCE")
        c["verified"] = False
        r = mod.build_foundation_design_report(b)
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_REVIEW_REQUIRED")

    def test_15_missing_mandatory_type_detected(self):
        b = deepcopy(self.payload)
        b["verification_checks"] = [x for x in b["verification_checks"] if x["check_type"] != "PAD_PUNCHING_SHEAR_CAPACITY"]
        r = mod.build_foundation_design_report(b)
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_INCOMPLETE")
        self.assertIn("PAD_PUNCHING_SHEAR_CAPACITY", r["summary"]["missing_mandatory_check_types"])

    def test_16_missing_reinforcement_definition_detected(self):
        b = deepcopy(self.payload)
        b["reinforcement_groups"] = [x for x in b["reinforcement_groups"] if x["foundation_element_id"] != "PC1"]
        r = mod.build_foundation_design_report(b)
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_INCOMPLETE")
        self.assertIn("PC1", r["summary"]["foundation_elements_without_reinforcement"])

    def test_17_missing_defined_drawing_detail_detected(self):
        b = deepcopy(self.payload)
        d = next(x for x in b["drawing_details"] if x["foundation_element_id"] == "FB1")
        d["status"] = "PENDING"
        r = mod.build_foundation_design_report(b)
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_INCOMPLETE")
        self.assertIn("FB1", r["summary"]["foundation_elements_without_defined_detail"])

    def test_18_missing_normative_reference_rejected(self):
        b = deepcopy(self.payload)
        b["verification_checks"][0]["normative_reference"] = ""
        with self.assertRaisesRegex(ValueError, "missing normative_reference"):
            mod.build_foundation_design_report(b)

    def test_19_nonfinite_demand_rejected(self):
        b = deepcopy(self.payload)
        b["verification_checks"][0]["demand"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            mod.build_foundation_design_report(b)

    def test_20_zero_capacity_rejected(self):
        b = deepcopy(self.payload)
        b["verification_checks"][0]["capacity"] = 0
        with self.assertRaisesRegex(ValueError, "must be > 0"):
            mod.build_foundation_design_report(b)

    def test_21_all_supported_types_present_and_pass(self):
        r = self.report()
        self.assertEqual({x["check_type"] for x in r["verification_checks"]}, mod.SUPPORTED_CHECK_TYPES)
        self.assertTrue(all(x["status"] == "PASS" for x in r["verification_checks"]))

    def test_22_candidate_state_and_envelope(self):
        r = self.report()
        self.assertEqual(r["verification_state"], "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED")
        self.assertEqual(r["summary"]["review_item_count"], 0)
        self.assertIsNotNone(r["summary"]["maximum_utilization"])
        self.assertLessEqual(r["summary"]["maximum_utilization"], 1.0)

    def test_23_digital_twin_writeback_enabled(self):
        r = self.report()
        self.assertTrue(r["digital_twin_writeback"]["enabled"])
        self.assertIn("reinforcement_schedule", r["digital_twin_writeback"]["write_fields"])
        self.assertIn("quantity_takeoff", r["digital_twin_writeback"]["write_fields"])

    def test_24_release_safety_locked(self):
        r = self.report()
        self.assertFalse(r["release"]["automatic_code_compliance_claim"])
        self.assertFalse(r["release"]["automatic_geotechnical_approval"])
        self.assertFalse(r["release"]["automatic_structural_approval"])
        self.assertFalse(r["release"]["automatic_foundation_approval"])
        self.assertFalse(r["release"]["automatic_detailing_approval"])
        self.assertEqual(r["release"]["construction_release"], "LOCKED")
        self.assertEqual(r["release"]["structural_model_release"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
