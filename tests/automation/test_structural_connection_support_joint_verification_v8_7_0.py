import importlib.util
import math
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_connection_support_joint_verification_v8_7_0.py"
spec = importlib.util.spec_from_file_location("phx_v870", RUNNER_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TestStructuralConnectionSupportJointVerificationV870(unittest.TestCase):
    def setUp(self): self.payload = mod._demo_payload()
    def report(self): return mod.build_connection_report(self.payload)

    def test_engine_identity(self):
        r=self.report(); self.assertEqual(r["engine"]["id"],mod.ENGINE_ID); self.assertEqual(r["engine"]["version"],"8.7.0")
    def test_v86_source_contract_required(self):
        b=deepcopy(self.payload); b["source_engine"]="PHX-OLD"
        with self.assertRaisesRegex(ValueError,"v8.6.0"): mod.build_connection_report(b)
    def test_global_stability_state_gate(self):
        b=deepcopy(self.payload); b["global_stability_state"]="GLOBAL_STABILITY_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError,"not accepted"): mod.build_connection_report(b)
    def test_basis_requires_traceable_source(self):
        b=deepcopy(self.payload); b["connection_basis"]["source_reference"]=""
        with self.assertRaisesRegex(ValueError,"source_reference"): mod.build_connection_report(b)
    def test_capacity_ratio(self):
        r=self.report(); c=next(x for x in r["verification_checks"] if x["check_type"]=="BEAM_COLUMN_CONNECTION")
        self.assertAlmostEqual(c["utilization"],c["demand"]/c["capacity"]); self.assertEqual(c["status"],"PASS")
    def test_failed_capacity_creates_review(self):
        b=deepcopy(self.payload); b["verification_checks"][0]["demand"]=20; b["verification_checks"][0]["capacity"]=10
        r=mod.build_connection_report(b); self.assertEqual(r["verification_state"],"CONNECTION_SUPPORT_JOINT_REVIEW_REQUIRED"); self.assertGreater(r["summary"]["review_item_count"],0)
    def test_unknown_connection_rejected(self):
        b=deepcopy(self.payload); b["verification_checks"][0]["connection_id"]="NOPE"
        with self.assertRaisesRegex(ValueError,"unknown connection"): mod.build_connection_report(b)
    def test_unknown_support_rejected(self):
        b=deepcopy(self.payload); c=next(x for x in b["verification_checks"] if x["check_type"]=="SUPPORT_REACTION_CAPACITY"); c["support_id"]="NOPE"
        with self.assertRaisesRegex(ValueError,"unknown support"): mod.build_connection_report(b)
    def test_unknown_joint_rejected(self):
        b=deepcopy(self.payload); c=next(x for x in b["verification_checks"] if x["check_type"]=="JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE"); c["joint_id"]="NOPE"
        with self.assertRaisesRegex(ValueError,"unknown joint"): mod.build_connection_report(b)
    def test_stiffness_evidence(self):
        r=self.report(); c=next(x for x in r["verification_checks"] if x["check_type"]=="JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE"); self.assertTrue(c["classification_verified"]); self.assertEqual(c["status"],"PASS")
    def test_failed_stiffness_evidence_creates_review(self):
        b=deepcopy(self.payload); c=next(x for x in b["verification_checks"] if x["check_type"]=="JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE"); c["classification_verified"]=False
        r=mod.build_connection_report(b); self.assertEqual(r["verification_state"],"CONNECTION_SUPPORT_JOINT_REVIEW_REQUIRED")
    def test_missing_mandatory_type_detected(self):
        b=deepcopy(self.payload); b["verification_checks"]=[x for x in b["verification_checks"] if x["check_type"]!="ANCHOR_GROUP_CAPACITY"]
        r=mod.build_connection_report(b); self.assertEqual(r["verification_state"],"CONNECTION_SUPPORT_JOINT_VERIFICATION_INCOMPLETE"); self.assertIn("ANCHOR_GROUP_CAPACITY",r["summary"]["missing_mandatory_check_types"])
    def test_missing_normative_reference_rejected(self):
        b=deepcopy(self.payload); b["verification_checks"][0]["normative_reference"]=""
        with self.assertRaisesRegex(ValueError,"missing normative_reference"): mod.build_connection_report(b)
    def test_nonfinite_rejected(self):
        b=deepcopy(self.payload); b["verification_checks"][0]["demand"]=math.inf
        with self.assertRaisesRegex(ValueError,"finite"): mod.build_connection_report(b)
    def test_zero_capacity_rejected(self):
        b=deepcopy(self.payload); b["verification_checks"][0]["capacity"]=0
        with self.assertRaisesRegex(ValueError,"must be > 0"): mod.build_connection_report(b)
    def test_duplicate_check_id_rejected(self):
        b=deepcopy(self.payload); b["verification_checks"].append(deepcopy(b["verification_checks"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"): mod.build_connection_report(b)
    def test_all_supported_types_present_and_pass(self):
        r=self.report(); self.assertEqual({x["check_type"] for x in r["verification_checks"]},mod.SUPPORTED_CHECK_TYPES); self.assertTrue(all(x["status"]=="PASS" for x in r["verification_checks"]))
    def test_release_safety_and_digital_twin(self):
        r=self.report(); self.assertFalse(r["release"]["automatic_code_compliance_claim"]); self.assertFalse(r["release"]["automatic_structural_approval"]); self.assertFalse(r["release"]["automatic_connection_approval"]); self.assertEqual(r["release"]["structural_model_release"],"LOCKED"); self.assertTrue(r["digital_twin_writeback"]["enabled"])


if __name__ == "__main__": unittest.main()
