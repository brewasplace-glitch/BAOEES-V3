import copy
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[2] / "runners" / "PROJECT_PHOENIX_structural_engineering_review_approval_release_control_v8_11_0.py"
spec = importlib.util.spec_from_file_location("v811", RUNNER)
v811 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v811
spec.loader.exec_module(v811)


class TestStructuralEngineeringReviewApprovalReleaseControlV8110(unittest.TestCase):
    def setUp(self):
        self.p = v811.build_demo_payload()

    def run_engine(self, p=None):
        return v811.evaluate_release(self.p if p is None else p)

    def test_01_valid_construction_release(self):
        r=self.run_engine(); self.assertEqual(r["construction_release"], "RELEASED")
    def test_02_valid_structural_model_release(self):
        self.p["release_authorization"]["decision"]="RELEASE_STRUCTURAL_MODEL"; self.p["release_authorization"]["authorized_scopes"]=["STRUCTURAL_MODEL"]
        r=self.run_engine(); self.assertEqual(r["structural_model_release"], "RELEASED"); self.assertEqual(r["construction_release"], "LOCKED")
    def test_03_pending_review_locks(self):
        self.p["human_engineering_review"]["status"]="PENDING"; r=self.run_engine(); self.assertEqual(r["construction_release"], "LOCKED")
    def test_04_rejected_review_locks(self):
        self.p["human_engineering_review"]["status"]="REJECTED"; r=self.run_engine(); self.assertEqual(r["overall_release_state"], "HUMAN_REVIEW_REQUIRED")
    def test_05_returned_review_locks(self):
        self.p["human_engineering_review"]["status"]="RETURNED_FOR_REVISION"; r=self.run_engine(); self.assertEqual(r["structural_model_release"], "LOCKED")
    def test_06_approved_with_resolved_nonblocking_comments(self):
        self.p["human_engineering_review"]["status"]="APPROVED_WITH_COMMENTS"; self.p["human_engineering_review"]["comments"]=[{"id":"C1","text":"note","blocking":False,"resolved":False}]
        self.assertEqual(self.run_engine()["construction_release"], "RELEASED")
    def test_07_unresolved_blocking_comment_locks(self):
        self.p["human_engineering_review"]["status"]="APPROVED_WITH_COMMENTS"; self.p["human_engineering_review"]["comments"]=[{"id":"C1","text":"fix","blocking":True,"resolved":False}]
        self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_08_resolved_blocking_comment_allows(self):
        self.p["human_engineering_review"]["status"]="APPROVED_WITH_COMMENTS"; self.p["human_engineering_review"]["comments"]=[{"id":"C1","text":"fixed","blocking":True,"resolved":True}]
        self.assertEqual(self.run_engine()["construction_release"], "RELEASED")
    def test_09_review_package_hash_mismatch_invalidates(self):
        self.p["human_engineering_review"]["approved_package_fingerprint_sha256"]="0"*64; r=self.run_engine(); self.assertTrue(r["approval_binding"]["approval_invalidated"])
    def test_10_review_model_hash_mismatch_invalidates(self):
        self.p["human_engineering_review"]["approved_structural_model_fingerprint_sha256"]="0"*64; self.assertEqual(self.run_engine()["overall_release_state"], "APPROVAL_INVALIDATED_REVIEW_REQUIRED")
    def test_11_review_calculation_hash_mismatch_invalidates(self):
        self.p["human_engineering_review"]["approved_calculation_package_fingerprint_sha256"]="0"*64; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_12_review_drawing_hash_mismatch_invalidates(self):
        self.p["human_engineering_review"]["approved_drawing_package_fingerprint_sha256"]="0"*64; self.assertEqual(self.run_engine()["structural_model_release"], "LOCKED")
    def test_13_authorization_hash_mismatch_invalidates(self):
        self.p["release_authorization"]["authorized_package_fingerprint_sha256"]="0"*64; self.assertTrue(self.run_engine()["approval_binding"]["approval_invalidated"])
    def test_14_component_change_invalidates_declared_package(self):
        self.p["engineering_package"]["drawing_package_fingerprint_sha256"]=hashlib.sha256(b"new").hexdigest(); r=self.run_engine(); self.assertIn("PACKAGE_FINGERPRINT_INVALID", {b["code"] for b in r["blockers"]})
    def test_15_qaqc_blocker_locks(self):
        self.p["engineering_package"]["qaqc_blockers"]=1; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_16_incomplete_verification_registers_lock(self):
        self.p["engineering_package"]["verification_registers_complete"]=False; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_17_incomplete_documents_block_construction(self):
        self.p["engineering_package"]["required_documents_complete"]=False; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_18_wrong_qaqc_state_locks(self):
        self.p["engineering_package_qaqc_state"]="PENDING"; self.assertEqual(self.run_engine()["structural_model_release"], "LOCKED")
    def test_19_reviewer_role_not_authorized(self):
        self.p["human_engineering_review"]["reviewer_role"]="INTERN"; self.assertIn("REVIEWER_ROLE_NOT_AUTHORIZED", {b["code"] for b in self.run_engine()["blockers"]})
    def test_20_release_authority_role_not_authorized(self):
        self.p["release_authorization"]["authority_role"]="INTERN"; self.assertIn("RELEASE_AUTHORITY_ROLE_NOT_AUTHORIZED", {b["code"] for b in self.run_engine()["blockers"]})
    def test_21_review_signature_must_verify(self):
        self.p["human_engineering_review"]["signature_validation_state"]="NOT_VERIFIED"; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_22_authority_signature_must_verify(self):
        self.p["release_authorization"]["signature_validation_state"]="NOT_VERIFIED"; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_23_professional_responsibility_ack_required(self):
        self.p["human_engineering_review"]["professional_responsibility_acknowledged"]=False; self.assertEqual(self.run_engine()["structural_model_release"], "LOCKED")
    def test_24_separation_of_duties_default(self):
        self.p["release_authorization"]["authority_id"]=self.p["human_engineering_review"]["reviewer_id"]; self.assertIn("SEPARATION_OF_DUTIES_VIOLATION", {b["code"] for b in self.run_engine()["blockers"]})
    def test_25_separation_of_duties_can_be_disabled(self):
        self.p["release_policy"]["require_separation_of_duties"]=False; self.p["release_authorization"]["authority_id"]=self.p["human_engineering_review"]["reviewer_id"]; self.assertEqual(self.run_engine()["construction_release"], "RELEASED")
    def test_26_authorization_cannot_precede_review(self):
        self.p["release_authorization"]["authorization_timestamp"]="2026-08-01T09:59:00+00:00"; self.assertIn("AUTHORIZATION_PRECEDES_REVIEW", {b["code"] for b in self.run_engine()["blockers"]})
    def test_27_structural_scope_required(self):
        self.p["human_engineering_review"]["approved_scopes"]=["CONSTRUCTION_DOCUMENTS"]; self.assertEqual(self.run_engine()["structural_model_release"], "LOCKED")
    def test_28_construction_scope_required(self):
        self.p["human_engineering_review"]["approved_scopes"]=["STRUCTURAL_MODEL"]; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_29_hold_decision_locks(self):
        self.p["release_authorization"]["decision"]="HOLD"; self.assertEqual(self.run_engine()["construction_release"], "LOCKED")
    def test_30_reject_decision_locks(self):
        self.p["release_authorization"]["decision"]="REJECT"; self.assertEqual(self.run_engine()["structural_model_release"], "LOCKED")
    def test_31_unknown_decision_raises(self):
        self.p["release_authorization"]["decision"]="AUTO_RELEASE"; self.assertRaises(ValueError, self.run_engine)
    def test_32_unknown_review_status_raises(self):
        self.p["human_engineering_review"]["status"]="AUTO_APPROVED"; self.assertRaises(ValueError, self.run_engine)
    def test_33_wrong_source_engine_raises(self):
        self.p["source_engine"]="OTHER"; self.assertRaises(ValueError, self.run_engine)
    def test_34_invalid_sha_raises(self):
        self.p["engineering_package"]["package_fingerprint_sha256"]="bad"; self.assertRaises(ValueError, self.run_engine)
    def test_35_package_fingerprint_deterministic(self):
        a=v811.compute_package_fingerprint(self.p["engineering_package"]); b=v811.compute_package_fingerprint(copy.deepcopy(self.p["engineering_package"])); self.assertEqual(a,b)
    def test_36_release_id_deterministic(self):
        self.assertEqual(self.run_engine()["release_record"]["release_id"], self.run_engine()["release_record"]["release_id"])
    def test_37_ledger_previous_hash_supported(self):
        self.p["previous_release_event_hash_sha256"]="a"*64; r=self.run_engine(); self.assertEqual(r["release_ledger_entry"]["previous_event_hash_sha256"], "a"*64)
    def test_38_digital_twin_writeback_contains_release(self):
        r=self.run_engine(); self.assertEqual(r["digital_twin_writeback"]["structural.engineering_release.construction_release"], "RELEASED")
    def test_39_approved_with_comments_requires_comment_register(self):
        self.p["human_engineering_review"]["status"]="APPROVED_WITH_COMMENTS"; self.p["human_engineering_review"]["comments"]=[]; self.assertIn("APPROVAL_COMMENTS_MISSING", {b["code"] for b in self.run_engine()["blockers"]})
    def test_40_default_safety_flags_disable_fabrication(self):
        r=self.run_engine(); self.assertEqual(r["safety"]["automatic_professional_engineering_approval"], "DISABLED"); self.assertEqual(r["safety"]["release_without_explicit_human_authorization"], "DISABLED")


if __name__ == "__main__":
    unittest.main()
