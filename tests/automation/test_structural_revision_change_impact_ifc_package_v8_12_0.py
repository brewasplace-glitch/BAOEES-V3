import copy
import hashlib
import importlib.util
import pathlib
import unittest

RUNNER = pathlib.Path(__file__).resolve().parents[2] / "runners" / "PROJECT_PHOENIX_structural_revision_change_impact_ifc_package_v8_12_0.py"
spec = importlib.util.spec_from_file_location("v812", RUNNER)
v812 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v812)

class V812Tests(unittest.TestCase):
    def setUp(self):
        self.p = v812.self_test_payload()

    def run_engine(self):
        return v812.evaluate(self.p)

    def test_01_valid_case_issues_ifc(self):
        self.assertEqual(self.run_engine()["status"], "IFC_PACKAGE_ISSUED")

    def test_02_ifc_gate_true(self):
        self.assertTrue(self.run_engine()["ifc_package"]["can_issue_ifc"])

    def test_03_valid_case_has_no_blockers(self):
        self.assertEqual(self.run_engine()["blockers"], [])

    def test_04_change_is_detected(self):
        self.assertTrue(self.run_engine()["change_impact"]["engineering_change_detected"])

    def test_05_structural_model_change_is_detected(self):
        self.assertIn("structural_model", self.run_engine()["change_impact"]["changed_components"])

    def test_06_drawing_is_downstream_affected(self):
        self.assertIn("drawing_package", self.run_engine()["change_impact"]["affected_components"])

    def test_07_review_scope_generated(self):
        self.assertIn("HUMAN_ENGINEERING_REVIEW", self.run_engine()["change_impact"]["required_validation_scopes"])

    def test_08_exact_release_matches(self):
        self.assertTrue(self.run_engine()["release_binding"]["exact_release_match"])

    def test_09_old_baseline_is_superseded_by_new_ifc(self):
        self.assertEqual(self.run_engine()["baseline"]["control_state"], "SUPERSEDED_BY_NEW_IFC_REVISION")

    def test_10_ifc_manifest_generated(self):
        self.assertEqual(len(self.run_engine()["ifc_package"]["immutable_manifest_sha256"]), 64)

    def test_11_wrong_release_hash_blocks(self):
        self.p["current_v8_11_release_record"]["package_fingerprint_sha256"] = "a" * 64
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("RELEASE_RECORD_FINGERPRINT_MISMATCH", codes)

    def test_12_locked_construction_release_blocks(self):
        self.p["current_v8_11_release_record"]["construction_release"] = "LOCKED"
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("CONSTRUCTION_RELEASE_NOT_RELEASED", codes)

    def test_13_missing_release_record_blocks_ifc(self):
        self.p["current_v8_11_release_record"] = None
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("EXACT_V8_11_RELEASE_RECORD_REQUIRED", codes)

    def test_14_changed_revision_without_release_returns_for_review(self):
        self.p["current_v8_11_release_record"] = None
        self.assertEqual(self.run_engine()["current_revision"]["effective_state"], "FOR_REVIEW")

    def test_15_changed_revision_requires_fresh_qaqc(self):
        self.p["current_v8_11_release_record"] = None
        self.assertTrue(self.run_engine()["required_rework"]["fresh_v8_10_qaqc_required"])

    def test_16_changed_revision_requires_fresh_v811(self):
        self.p["current_v8_11_release_record"] = None
        self.assertTrue(self.run_engine()["required_rework"]["fresh_v8_11_review_release_required"])

    def test_17_incomplete_ifc_document_blocks(self):
        self.p["documents"][0]["status"] = "DRAFT"
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("IFC_DOCUMENTS_INCOMPLETE", codes)

    def test_18_duplicate_document_id_raises(self):
        self.p["documents"].append(copy.deepcopy(self.p["documents"][0]))
        with self.assertRaises(ValueError):
            self.run_engine()

    def test_19_invalid_current_fingerprint_blocks(self):
        self.p["current_revision"]["revision_fingerprint_sha256"] = "b" * 64
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("CURRENT_FINGERPRINT_INVALID", codes)

    def test_20_invalid_baseline_fingerprint_blocks(self):
        self.p["baseline_release"]["revision_fingerprint_sha256"] = "c" * 64
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("BASELINE_FINGERPRINT_INVALID", codes)

    def test_21_same_revision_with_change_blocks(self):
        self.p["current_revision"]["revision_id"] = self.p["baseline_release"]["revision_id"]
        self.p["current_revision"]["revision_fingerprint_sha256"] = v812.compute_revision_fingerprint(
            self.p["project_id"],
            self.p["current_revision"]["revision_id"],
            self.p["current_revision"]["component_fingerprints"],
        )
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("REVISION_ID_NOT_INCREMENTED", codes)

    def test_22_revision_without_engineering_change_warns(self):
        self.p["current_revision"]["component_fingerprints"] = copy.deepcopy(
            self.p["baseline_release"]["component_fingerprints"]
        )
        new_fp = v812.compute_revision_fingerprint(
            self.p["project_id"],
            self.p["current_revision"]["revision_id"],
            self.p["current_revision"]["component_fingerprints"],
        )
        self.p["current_revision"]["revision_fingerprint_sha256"] = new_fp
        self.p["current_v8_11_release_record"]["package_fingerprint_sha256"] = new_fp
        codes = {x["code"] for x in self.run_engine()["warnings"]}
        self.assertIn("REVISION_WITHOUT_ENGINEERING_CHANGE", codes)

    def test_23_wrong_source_engine_raises(self):
        self.p["source_engine"] = "OTHER"
        with self.assertRaises(ValueError):
            self.run_engine()

    def test_24_invalid_component_sha_raises(self):
        self.p["current_revision"]["component_fingerprints"]["structural_model"] = "bad"
        with self.assertRaises(ValueError):
            self.run_engine()

    def test_25_revision_fingerprint_is_deterministic(self):
        c = self.p["current_revision"]["component_fingerprints"]
        a = v812.compute_revision_fingerprint(self.p["project_id"], "C02", c)
        b = v812.compute_revision_fingerprint(self.p["project_id"], "C02", copy.deepcopy(c))
        self.assertEqual(a, b)

    def test_26_manifest_is_deterministic(self):
        self.assertEqual(
            self.run_engine()["ifc_package"]["immutable_manifest_sha256"],
            self.run_engine()["ifc_package"]["immutable_manifest_sha256"],
        )

    def test_27_change_register_has_old_and_new_hashes(self):
        item = self.run_engine()["change_register"][0]
        self.assertEqual(len(item["baseline_sha256"]), 64)
        self.assertEqual(len(item["current_sha256"]), 64)

    def test_28_digital_twin_ifc_state_issued(self):
        self.assertEqual(
            self.run_engine()["digital_twin_writeback"]["structural.revision_control.ifc_package_state"],
            "ISSUED",
        )

    def test_29_safety_flags_disable_automatic_release(self):
        safety = self.run_engine()["safety"]
        self.assertEqual(safety["automatic_release_without_v8_11_authorization"], "DISABLED")
        self.assertEqual(safety["changed_revision_auto_ifc"], "DISABLED")

    def test_30_as_built_without_released_construction_base_blocks(self):
        self.p["current_revision"]["requested_state"] = "AS_BUILT"
        self.p["current_v8_11_release_record"]["construction_release"] = "LOCKED"
        codes = {x["code"] for x in self.run_engine()["blockers"]}
        self.assertIn("AS_BUILT_WITHOUT_RELEASED_CONSTRUCTION_BASE", codes)

if __name__ == "__main__":
    unittest.main()
