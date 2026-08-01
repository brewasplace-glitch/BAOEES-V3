import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_analysis_results_validation_v8_4_0.py"

spec = importlib.util.spec_from_file_location("phx_v840", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralAnalysisResultsValidationV840(unittest.TestCase):
    def setUp(self):
        self.payload = mod._demo_payload()

    def test_engine_identity(self):
        report = mod.build_validation_report(self.payload)
        self.assertEqual(report["engine"]["id"], mod.ENGINE_ID)
        self.assertEqual(report["engine"]["version"], "8.4.0")

    def test_base_result_sets_and_solvers_counted(self):
        report = mod.build_validation_report(self.payload)
        self.assertEqual(report["summary"]["base_result_set_count"], 4)
        self.assertEqual(report["summary"]["solver_count"], 2)

    def test_linear_combination_synthesized(self):
        report = mod.build_validation_report(self.payload)
        uz = report["synthesized_combination_results"]["opensees"]["ULS1"]["node_displacements"]["N2"]["UZ"]
        self.assertAlmostEqual(uz, 1.35 * -0.002 + 1.5 * -0.003)

    def test_nonfinite_numeric_result_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["node_displacements"]["N2"]["UZ"] = math.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            mod.build_validation_report(bad)

    def test_missing_raw_solver_evidence_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["raw_solver_evidence_reference"] = ""
        with self.assertRaisesRegex(ValueError, "raw solver evidence"):
            mod.build_validation_report(bad)

    def test_unconverged_result_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["converged"] = False
        with self.assertRaisesRegex(ValueError, "not explicitly completed and converged"):
            mod.build_validation_report(bad)

    def test_unknown_entity_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["node_displacements"]["N999"] = {"UX": 0.0}
        with self.assertRaisesRegex(ValueError, "unknown node IDs"):
            mod.build_validation_report(bad)

    def test_unit_mismatch_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["units"]["force"] = "N"
        with self.assertRaisesRegex(ValueError, "unit mismatch"):
            mod.build_validation_report(bad)

    def test_missing_required_load_case_rejected(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"] = [r for r in bad["analysis_result_sets"] if not (r["solver"] == "opensees" and r["case_id"] == "Q")]
        with self.assertRaisesRegex(ValueError, "missing load cases"):
            mod.build_validation_report(bad)

    def test_equilibrium_failure_creates_review_item(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][0]["node_reactions"]["N1"]["FZ"] = 80.0
        report = mod.build_validation_report(bad)
        self.assertGreater(report["checks"]["review_item_count"], 0)
        self.assertEqual(report["validation_state"], "ENGINEERING_REVIEW_REQUIRED")

    def test_cross_solver_mismatch_creates_review_item(self):
        bad = deepcopy(self.payload)
        bad["analysis_result_sets"][2]["node_displacements"]["N2"]["UZ"] = -0.02
        report = mod.build_validation_report(bad)
        self.assertTrue(any(c["status"] == "REVIEW_REQUIRED" for c in report["checks"]["cross_solver"]))

    def test_release_safety_and_digital_twin_contract(self):
        report = mod.build_validation_report(self.payload)
        self.assertFalse(report["release"]["automatic_code_compliance_claim"])
        self.assertFalse(report["release"]["automatic_structural_approval"])
        self.assertEqual(report["release"]["structural_model_release"], "LOCKED")
        self.assertTrue(report["digital_twin_writeback"]["enabled"])


if __name__ == "__main__":
    unittest.main()
