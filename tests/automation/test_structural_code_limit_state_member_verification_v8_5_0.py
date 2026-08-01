import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_code_limit_state_member_verification_v8_5_0.py"
spec = importlib.util.spec_from_file_location("phx_v850", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralCodeLimitStateMemberVerificationV850(unittest.TestCase):
    def setUp(self):
        self.payload = mod._demo_payload()

    def test_engine_identity(self):
        report = mod.build_verification_report(self.payload)
        self.assertEqual(report["engine"]["id"], mod.ENGINE_ID)
        self.assertEqual(report["engine"]["version"], "8.5.0")

    def test_code_basis_required(self):
        bad = deepcopy(self.payload)
        bad["code_basis"]["source_reference"] = ""
        with self.assertRaisesRegex(ValueError, "source_reference"):
            mod.build_verification_report(bad)

    def test_v84_source_contract_required(self):
        bad = deepcopy(self.payload)
        bad["source_engine"] = "PHX-OLD"
        with self.assertRaisesRegex(ValueError, "v8.4.0"):
            mod.build_verification_report(bad)

    def test_analysis_validation_state_gate(self):
        bad = deepcopy(self.payload)
        bad["analysis_validation_state"] = "ENGINEERING_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "not accepted"):
            mod.build_verification_report(bad)

    def test_compression_capacity_ratio(self):
        report = mod.build_verification_report(self.payload)
        check = next(r for r in report["verification_results"] if r["id"] == "R-N")
        self.assertAlmostEqual(check["utilization"], 180.0 / 420.0)
        self.assertEqual(check["status"], "PASS")

    def test_linear_interaction(self):
        report = mod.build_verification_report(self.payload)
        check = next(r for r in report["verification_results"] if r["id"] == "R-INT")
        self.assertAlmostEqual(check["interaction_value"], 180.0 / 420.0 + 70.0 / 160.0)
        self.assertEqual(check["status"], "PASS")

    def test_buckling_resistance_ratio(self):
        report = mod.build_verification_report(self.payload)
        check = next(r for r in report["verification_results"] if r["id"] == "R-BUCK")
        self.assertAlmostEqual(check["utilization"], 0.5)

    def test_sls_displacement_check(self):
        report = mod.build_verification_report(self.payload)
        check = next(r for r in report["verification_results"] if r["id"] == "R-DEF")
        self.assertAlmostEqual(check["utilization"], 0.55)
        self.assertEqual(check["status"], "PASS")

    def test_failure_creates_review_item(self):
        bad = deepcopy(self.payload)
        for rule in bad["verification_rules"]:
            if rule["id"] == "R-MY":
                rule["capacity"] = 50.0
        report = mod.build_verification_report(bad)
        self.assertEqual(report["verification_state"], "MEMBER_VERIFICATION_FAILED_REVIEW_REQUIRED")
        self.assertGreater(report["summary"]["review_item_count"], 0)

    def test_missing_mandatory_sls_coverage_detected(self):
        bad = deepcopy(self.payload)
        bad["verification_rules"] = [r for r in bad["verification_rules"] if r["id"] not in {"R-DEF"}]
        report = mod.build_verification_report(bad)
        self.assertEqual(report["verification_state"], "MEMBER_VERIFICATION_INCOMPLETE")
        self.assertTrue(any(r["type"] == "MANDATORY_LIMIT_STATE_COVERAGE_INCOMPLETE" for r in report["review_items"]))

    def test_missing_normative_reference_rejected(self):
        bad = deepcopy(self.payload)
        bad["verification_rules"][0]["normative_reference"] = ""
        with self.assertRaisesRegex(ValueError, "missing normative_reference"):
            mod.build_verification_report(bad)

    def test_unknown_member_rejected(self):
        bad = deepcopy(self.payload)
        bad["verification_rules"][0]["member_id"] = "M999"
        with self.assertRaisesRegex(ValueError, "unknown member"):
            mod.build_verification_report(bad)

    def test_nonfinite_capacity_rejected(self):
        bad = deepcopy(self.payload)
        bad["verification_rules"][0]["capacity"] = math.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            mod.build_verification_report(bad)

    def test_release_safety_and_digital_twin_contract(self):
        report = mod.build_verification_report(self.payload)
        self.assertFalse(report["release"]["automatic_code_compliance_claim"])
        self.assertFalse(report["release"]["automatic_structural_approval"])
        self.assertEqual(report["release"]["structural_model_release"], "LOCKED")
        self.assertTrue(report["digital_twin_writeback"]["enabled"])


if __name__ == "__main__":
    unittest.main()
