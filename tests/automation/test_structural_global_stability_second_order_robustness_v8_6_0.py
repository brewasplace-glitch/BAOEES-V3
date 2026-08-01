import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_global_stability_second_order_robustness_v8_6_0.py"
spec = importlib.util.spec_from_file_location("phx_v860", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralGlobalStabilitySecondOrderRobustnessV860(unittest.TestCase):
    def setUp(self):
        self.payload = mod._demo_payload()

    def report(self):
        return mod.build_stability_report(self.payload)

    def test_engine_identity(self):
        report = self.report()
        self.assertEqual(report["engine"]["id"], mod.ENGINE_ID)
        self.assertEqual(report["engine"]["version"], "8.6.0")

    def test_v85_source_contract_required(self):
        bad = deepcopy(self.payload)
        bad["source_engine"] = "PHX-OLD"
        with self.assertRaisesRegex(ValueError, "v8.5.0"):
            mod.build_stability_report(bad)

    def test_member_verification_state_gate(self):
        bad = deepcopy(self.payload)
        bad["member_verification_state"] = "MEMBER_VERIFICATION_FAILED_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "not accepted"):
            mod.build_stability_report(bad)

    def test_stability_basis_requires_traceable_source(self):
        bad = deepcopy(self.payload)
        bad["stability_basis"]["source_reference"] = ""
        with self.assertRaisesRegex(ValueError, "source_reference"):
            mod.build_stability_report(bad)

    def test_second_order_amplification(self):
        report = self.report()
        check = next(r for r in report["stability_checks"] if r["id"] == "GS-2ND")
        self.assertAlmostEqual(check["amplification_factor"], 0.0207 / 0.018)
        self.assertEqual(check["status"], "PASS")

    def test_storey_stability_index(self):
        report = self.report()
        check = next(r for r in report["stability_checks"] if r["id"] == "GS-THETA-L2")
        expected = 5200.0 * 0.008 / (680.0 * 3.4)
        self.assertAlmostEqual(check["stability_index"], expected)
        self.assertEqual(check["status"], "PASS")

    def test_global_buckling_factor(self):
        report = self.report()
        check = next(r for r in report["stability_checks"] if r["id"] == "GS-BUCKLING")
        self.assertEqual(check["critical_load_factor"], 8.2)
        self.assertEqual(check["status"], "PASS")

    def test_torsional_ratio(self):
        report = self.report()
        check = next(r for r in report["stability_checks"] if r["id"] == "GS-TORSION-L2")
        self.assertAlmostEqual(check["torsional_drift_ratio"], 0.0102 / 0.0085)
        self.assertEqual(check["status"], "PASS")

    def test_soft_and_weak_storey_ratios(self):
        report = self.report()
        soft = next(r for r in report["stability_checks"] if r["id"] == "GS-SOFT-L1")
        weak = next(r for r in report["stability_checks"] if r["id"] == "GS-WEAK-L1")
        self.assertAlmostEqual(soft["stiffness_ratio"], 125000.0 / 150000.0)
        self.assertAlmostEqual(weak["strength_ratio"], 1550.0 / 1750.0)
        self.assertEqual(soft["status"], "PASS")
        self.assertEqual(weak["status"], "PASS")

    def test_load_path_connectivity(self):
        report = self.report()
        check = next(r for r in report["stability_checks"] if r["id"] == "GS-LOADPATH")
        self.assertEqual(check["disconnected_loaded_nodes"], [])
        self.assertEqual(check["status"], "PASS")

    def test_disconnected_load_path_fails_and_creates_review(self):
        bad = deepcopy(self.payload)
        for check in bad["stability_checks"]:
            if check["id"] == "GS-LOADPATH":
                check["load_path_edges"] = [{"from": "N3", "to": "N2"}]
        report = mod.build_stability_report(bad)
        self.assertEqual(report["verification_state"], "GLOBAL_STABILITY_REVIEW_REQUIRED")
        self.assertTrue(any(r["check_id"] == "GS-LOADPATH" for r in report["review_items"]))

    def test_failed_second_order_check_requires_review(self):
        bad = deepcopy(self.payload)
        for check in bad["stability_checks"]:
            if check["id"] == "GS-2ND":
                check["max_amplification_factor"] = 1.05
        report = mod.build_stability_report(bad)
        self.assertEqual(report["verification_state"], "GLOBAL_STABILITY_REVIEW_REQUIRED")
        self.assertGreater(report["summary"]["review_item_count"], 0)

    def test_missing_mandatory_check_type_detected(self):
        bad = deepcopy(self.payload)
        bad["stability_checks"] = [c for c in bad["stability_checks"] if c["check_type"] != "ALTERNATE_LOAD_PATH_EVIDENCE"]
        report = mod.build_stability_report(bad)
        self.assertEqual(report["verification_state"], "GLOBAL_STABILITY_VERIFICATION_INCOMPLETE")
        self.assertIn("ALTERNATE_LOAD_PATH_EVIDENCE", report["summary"]["missing_mandatory_check_types"])

    def test_missing_normative_reference_rejected(self):
        bad = deepcopy(self.payload)
        bad["stability_checks"][0]["normative_reference"] = ""
        with self.assertRaisesRegex(ValueError, "missing normative_reference"):
            mod.build_stability_report(bad)

    def test_nonfinite_input_rejected(self):
        bad = deepcopy(self.payload)
        bad["stability_checks"][0]["second_order_displacement_m"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            mod.build_stability_report(bad)

    def test_diaphragm_and_alternate_path_evidence(self):
        report = self.report()
        d = next(r for r in report["stability_checks"] if r["id"] == "GS-DIAPH")
        a = next(r for r in report["stability_checks"] if r["id"] == "GS-ALP")
        self.assertTrue(d["continuity_verified"])
        self.assertTrue(a["alternate_path_verified"])
        self.assertEqual(d["status"], "PASS")
        self.assertEqual(a["status"], "PASS")

    def test_release_safety_and_digital_twin_contract(self):
        report = self.report()
        self.assertFalse(report["release"]["automatic_code_compliance_claim"])
        self.assertFalse(report["release"]["automatic_structural_approval"])
        self.assertFalse(report["release"]["automatic_robustness_approval"])
        self.assertEqual(report["release"]["structural_model_release"], "LOCKED")
        self.assertTrue(report["digital_twin_writeback"]["enabled"])


if __name__ == "__main__":
    unittest.main()
