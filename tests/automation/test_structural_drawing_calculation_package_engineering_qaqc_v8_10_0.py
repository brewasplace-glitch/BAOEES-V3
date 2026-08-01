import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_drawing_calculation_package_engineering_qaqc_v8_10_0.py"
spec = importlib.util.spec_from_file_location("phx_v8100", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralDrawingCalculationPackageEngineeringQAQCV8100(unittest.TestCase):
    def setUp(self):
        self.payload = mod._demo_payload()

    def report(self):
        return mod.build_engineering_package_report(self.payload)

    def test_01_engine_identity(self):
        r = self.report()
        self.assertEqual(r["engine"]["id"], mod.ENGINE_ID)
        self.assertEqual(r["engine"]["version"], "8.10.0")

    def test_02_v89_source_engine_required(self):
        b = deepcopy(self.payload)
        b["source_engine"] = "PHX-OLD"
        with self.assertRaisesRegex(ValueError, "v8.9.0"):
            mod.build_engineering_package_report(b)

    def test_03_v89_candidate_state_required(self):
        b = deepcopy(self.payload)
        b["foundation_design_reinforcement_detailing_state"] = "REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "not accepted"):
            mod.build_engineering_package_report(b)

    def test_04_package_basis_requires_source_reference(self):
        b = deepcopy(self.payload)
        b["engineering_package_basis"]["source_reference"] = ""
        with self.assertRaisesRegex(ValueError, "source_reference"):
            mod.build_engineering_package_report(b)

    def test_05_duplicate_source_layer_rejected(self):
        b = deepcopy(self.payload)
        b["source_layers"].append(deepcopy(b["source_layers"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate source layer"):
            mod.build_engineering_package_report(b)

    def test_06_wrong_source_layer_identity_rejected(self):
        b = deepcopy(self.payload)
        b["source_layers"][0]["layer_id"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "expected layer_id"):
            mod.build_engineering_package_report(b)

    def test_07_missing_source_layer_is_incomplete(self):
        b = deepcopy(self.payload)
        b["source_layers"] = [x for x in b["source_layers"] if x["version"] != "v8.4.0"]
        r = mod.build_engineering_package_report(b)
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_INCOMPLETE")
        self.assertIn("v8.4.0", r["summary"]["missing_required_source_versions"])

    def test_08_nonpassed_mandatory_source_layer_requires_review(self):
        b = deepcopy(self.payload)
        b["source_layers"][0]["state"] = "REVIEW_REQUIRED"
        r = mod.build_engineering_package_report(b)
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_REVIEW_REQUIRED")
        self.assertTrue(any(x["code"] == "SOURCE_LAYER_NOT_PASSED" for x in r["qaqc_findings"]))

    def test_09_duplicate_drawing_id_rejected(self):
        b = deepcopy(self.payload)
        b["drawings"].append(deepcopy(b["drawings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate drawing id"):
            mod.build_engineering_package_report(b)

    def test_10_unsupported_drawing_status_rejected(self):
        b = deepcopy(self.payload)
        b["drawings"][0]["status"] = "CONSTRUCTION_RELEASED"
        with self.assertRaisesRegex(ValueError, "unsupported status"):
            mod.build_engineering_package_report(b)

    def test_11_drawing_revision_mismatch_requires_review(self):
        b = deepcopy(self.payload)
        b["drawings"][0]["revision"] = "P02"
        r = mod.build_engineering_package_report(b)
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_REVIEW_REQUIRED")
        self.assertTrue(any(x["code"] == "DRAWING_REVISION_MISMATCH" for x in r["qaqc_findings"]))

    def test_12_calculation_revision_mismatch_requires_review(self):
        b = deepcopy(self.payload)
        b["calculation_sections"][0]["revision"] = "P99"
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "CALCULATION_REVISION_MISMATCH" for x in r["qaqc_findings"]))

    def test_13_calculation_normative_reference_required(self):
        b = deepcopy(self.payload)
        b["calculation_sections"][0]["normative_reference"] = ""
        with self.assertRaisesRegex(ValueError, "normative_reference"):
            mod.build_engineering_package_report(b)

    def test_14_drawing_unknown_calculation_reference_detected(self):
        b = deepcopy(self.payload)
        b["drawings"][0]["related_calculation_ids"].append("NOPE")
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "DRAWING_UNKNOWN_CALCULATION_REFERENCE" for x in r["qaqc_findings"]))

    def test_15_calculation_unknown_drawing_reference_detected(self):
        b = deepcopy(self.payload)
        b["calculation_sections"][0]["related_drawing_ids"].append("NOPE")
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "CALCULATION_UNKNOWN_DRAWING_REFERENCE" for x in r["qaqc_findings"]))

    def test_16_duplicate_verification_register_rejected(self):
        b = deepcopy(self.payload)
        b["verification_registers"].append(deepcopy(b["verification_registers"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate verification register"):
            mod.build_engineering_package_report(b)

    def test_17_missing_verification_register_is_incomplete(self):
        b = deepcopy(self.payload)
        b["verification_registers"] = [x for x in b["verification_registers"] if x["category"] != "CONNECTION_SUPPORT_JOINT"]
        r = mod.build_engineering_package_report(b)
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_INCOMPLETE")
        self.assertIn("CONNECTION_SUPPORT_JOINT", r["summary"]["missing_verification_registers"])

    def test_18_verification_register_state_failure_requires_review(self):
        b = deepcopy(self.payload)
        b["verification_registers"][0]["status"] = "MEMBER_VERIFICATION_REVIEW_REQUIRED"
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "VERIFICATION_REGISTER_NOT_PASSED" for x in r["qaqc_findings"]))

    def test_19_open_verification_review_items_require_review(self):
        b = deepcopy(self.payload)
        b["verification_registers"][0]["open_review_items"] = 2
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "OPEN_VERIFICATION_REVIEW_ITEMS" for x in r["qaqc_findings"]))

    def test_20_nonfinite_utilization_rejected(self):
        b = deepcopy(self.payload)
        b["verification_registers"][0]["maximum_utilization"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            mod.build_engineering_package_report(b)

    def test_21_open_assumption_requires_review(self):
        b = deepcopy(self.payload)
        b["assumptions"][0]["status"] = "OPEN"
        r = mod.build_engineering_package_report(b)
        self.assertIn("ASM-001", r["summary"]["open_assumptions"])
        self.assertTrue(any(x["code"] == "OPEN_ENGINEERING_ASSUMPTION" for x in r["qaqc_findings"]))

    def test_22_invalid_assumption_status_rejected(self):
        b = deepcopy(self.payload)
        b["assumptions"][0]["status"] = "MAGIC"
        with self.assertRaisesRegex(ValueError, "unsupported status"):
            mod.build_engineering_package_report(b)

    def test_23_missing_mandatory_qaqc_check_is_incomplete(self):
        b = deepcopy(self.payload)
        missing = "DIGITAL_TWIN_CROSS_REFERENCE"
        b["qaqc_checks"] = [x for x in b["qaqc_checks"] if x["check_type"] != missing]
        r = mod.build_engineering_package_report(b)
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_INCOMPLETE")
        self.assertIn(missing, r["summary"]["missing_mandatory_qaqc_check_types"])

    def test_24_failed_qaqc_check_requires_review(self):
        b = deepcopy(self.payload)
        b["qaqc_checks"][0]["verified"] = False
        r = mod.build_engineering_package_report(b)
        self.assertTrue(any(x["code"] == "QAQC_CHECK_FAILED" for x in r["qaqc_findings"]))

    def test_25_qaqc_evidence_reference_required(self):
        b = deepcopy(self.payload)
        b["qaqc_checks"][0]["evidence_reference"] = ""
        with self.assertRaisesRegex(ValueError, "evidence_reference"):
            mod.build_engineering_package_report(b)

    def test_26_human_engineering_review_gate_must_remain_required(self):
        b = deepcopy(self.payload)
        b["human_engineering_review_gate"]["required"] = False
        with self.assertRaisesRegex(ValueError, "must remain required"):
            mod.build_engineering_package_report(b)

    def test_27_invalid_human_review_status_rejected(self):
        b = deepcopy(self.payload)
        b["human_engineering_review_gate"]["status"] = "AUTO_APPROVED"
        with self.assertRaisesRegex(ValueError, "unsupported human engineering review status"):
            mod.build_engineering_package_report(b)

    def test_28_candidate_state_is_passed_with_pending_human_review(self):
        r = self.report()
        self.assertEqual(r["verification_state"], "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_CANDIDATE_PASSED")
        self.assertTrue(r["summary"]["technical_candidate_ready"])
        self.assertEqual(r["human_engineering_review_gate"]["status"], "PENDING")

    def test_29_manifest_counts_and_max_utilization(self):
        r = self.report()
        self.assertEqual(r["package_manifest"]["source_layer_count"], 10)
        self.assertEqual(r["package_manifest"]["drawing_count"], 3)
        self.assertEqual(r["package_manifest"]["calculation_section_count"], 3)
        self.assertEqual(r["package_manifest"]["verification_register_count"], 5)
        self.assertAlmostEqual(r["summary"]["maximum_reported_utilization"], 0.9583)

    def test_30_evidence_index_and_fingerprints_generated(self):
        r = self.report()
        self.assertGreater(r["package_manifest"]["evidence_record_count"], 20)
        self.assertTrue(all(len(x["record_fingerprint_sha256"]) == 64 for x in r["engineering_evidence_index"]))
        self.assertEqual(len(r["package_manifest"]["package_fingerprint_sha256"]), 64)

    def test_31_digital_twin_writeback_enabled(self):
        r = self.report()
        self.assertTrue(r["digital_twin_writeback"]["enabled"])
        self.assertIn("qaqc_findings", r["digital_twin_writeback"]["write_fields"])
        self.assertIn("release_readiness", r["digital_twin_writeback"]["write_fields"])

    def test_32_human_approval_does_not_automatically_unlock_release(self):
        b = deepcopy(self.payload)
        b["human_engineering_review_gate"]["status"] = "APPROVED"
        r = mod.build_engineering_package_report(b)
        self.assertTrue(r["release_readiness"]["human_engineering_review_complete"])
        self.assertFalse(r["release"]["automatic_structural_approval"])
        self.assertFalse(r["release"]["automatic_construction_release"])
        self.assertEqual(r["release"]["construction_release"], "LOCKED")
        self.assertEqual(r["release"]["structural_model_release"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
