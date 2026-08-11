from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.stability_ab_project_policy_integration_r9_5_2_2 import (
    apply_ab_policy_to_r9_5_required_input_document,
    apply_ab_project_policy_to_r9_5_2_result,
    apply_ab_project_policy_to_workspace,
    render_licensed_clause_extract_request,
)

POLICY_PATH = ROOT / "configs/phoenix/structural/stability_ab_project_policy_r9_5_2_2.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

CHECK_IDS = [
    "ALTERNATE_LOAD_PATH_EVIDENCE",
    "DIAPHRAGM_CONTINUITY",
    "GLOBAL_BUCKLING_FACTOR",
    "LOAD_PATH_CONTINUITY",
    "SECOND_ORDER_AMPLIFICATION",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "STOREY_STABILITY_INDEX",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
]


def global_input_fixture():
    checks = {
        check: {
            "applicability": None,
            "methodology_accepted": False,
            "methodology_acceptance_reference": None,
            "primary_source_record_id": None,
            "acceptance_criteria": {},
            "criteria_traceability": {},
        }
        for check in CHECK_IDS
    }
    checks["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"] = {"minimum_critical_load_factor": None}
    checks["SECOND_ORDER_AMPLIFICATION"]["acceptance_criteria"] = {"max_amplification_factor": None}
    checks["STOREY_STABILITY_INDEX"]["acceptance_criteria"] = {"max_stability_index": None}
    return {
        "project_id": "PHOENIX-PAT-001",
        "r9_5_project_stability_design_basis_decision": {
            "jurisdictional_basis": {"project_jurisdiction": "Suriname / Paramaribo"},
            "source_records": {
                "PROJECT_STABILITY_POLICY_REQUIRED": {
                    "reference_type": "PROJECT_ENGINEERING_POLICY",
                    "reference": "PROJECT STABILITY DESIGN BASIS - EXPLICIT APPROVAL REQUIRED",
                    "project_policy_approved": False,
                    "approval_reference": None,
                }
            },
            "checks": checks,
        },
    }


def r952_fixture():
    package_inputs = {
        "PKG-A-STABILITY-METHODOLOGY-DECISION": {
            "status": "INPUT_REQUIRED",
            "inputs": {
                "decision_status": None,
                "methodology_reference_type": None,
                "methodology_reference": None,
                "approval_or_clause_reference": None,
                "scope": None,
            },
        },
        "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA": {
            "status": "INPUT_REQUIRED",
            "inputs": {
                "source_record_id": None,
                "source_file": None,
                "sha256": None,
                "clause_reference": None,
                "licensed_use_confirmed": False,
                "extraction_reviewed": False,
                "criteria": {
                    "GLOBAL_BUCKLING_FACTOR": {"minimum_critical_load_factor": None},
                    "SECOND_ORDER_AMPLIFICATION": {"max_amplification_factor": None},
                    "STOREY_STABILITY_INDEX": {"max_stability_index": None},
                },
            },
        },
    }
    checks = global_input_fixture()["r9_5_project_stability_design_basis_decision"]["checks"]
    return {
        "status": "BLOCKED",
        "project_id": "PHOENIX-PAT-001",
        "evidence_intake": {
            "project_id": "PHOENIX-PAT-001",
            "project_basis": {"project_jurisdiction": "Suriname / Paramaribo"},
            "source_records": {
                "PROJECT_STABILITY_POLICY_REQUIRED": {
                    "reference_type": "PROJECT_ENGINEERING_POLICY",
                    "project_policy_approved": False,
                }
            },
            "checks_snapshot": checks,
            "package_inputs": package_inputs,
            "intake_metadata": {},
        },
        "blockers": [{"reason": "R9_5_2_STABILITY_DESIGN_BASIS_EVIDENCE_INTAKE_REQUIRED"}],
    }


class Tests(unittest.TestCase):
    def test_01_project_policy_approved_in_global_input(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        rec = out["r9_5_project_stability_design_basis_decision"]["source_records"]["PROJECT_STABILITY_POLICY_REQUIRED"]
        self.assertTrue(rec["project_policy_approved"])

    def test_02_a_checks_methodology_accepted(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        checks = out["r9_5_project_stability_design_basis_decision"]["checks"]
        for check in ("DIAPHRAGM_CONTINUITY", "GLOBAL_BUCKLING_FACTOR", "LOAD_PATH_CONTINUITY", "SECOND_ORDER_AMPLIFICATION", "STOREY_STABILITY_INDEX"):
            self.assertTrue(checks[check]["methodology_accepted"])

    def test_03_a_checks_applicable(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        checks = out["r9_5_project_stability_design_basis_decision"]["checks"]
        for check in ("DIAPHRAGM_CONTINUITY", "GLOBAL_BUCKLING_FACTOR", "LOAD_PATH_CONTINUITY", "SECOND_ORDER_AMPLIFICATION", "STOREY_STABILITY_INDEX"):
            self.assertTrue(checks[check]["applicability"])

    def test_04_candidate_buckling_11_recorded(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        row = out["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]
        self.assertEqual(11.0, row["r9_5_2_2_candidate_project_policy_criteria"]["minimum_critical_load_factor"])

    def test_05_candidate_amplification_1_10_recorded(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        row = out["r9_5_project_stability_design_basis_decision"]["checks"]["SECOND_ORDER_AMPLIFICATION"]
        self.assertEqual(1.10, row["r9_5_2_2_candidate_project_policy_criteria"]["max_amplification_factor"])

    def test_06_candidate_storey_index_0_10_recorded(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        row = out["r9_5_project_stability_design_basis_decision"]["checks"]["STOREY_STABILITY_INDEX"]
        self.assertEqual(0.10, row["r9_5_2_2_candidate_project_policy_criteria"]["max_stability_index"])

    def test_07_buckling_actual_r95_limit_not_promoted(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        self.assertIsNone(out["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"])

    def test_08_amplification_actual_r95_limit_not_promoted(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        self.assertIsNone(out["r9_5_project_stability_design_basis_decision"]["checks"]["SECOND_ORDER_AMPLIFICATION"]["acceptance_criteria"]["max_amplification_factor"])

    def test_09_storey_index_actual_r95_limit_not_promoted(self):
        out = apply_ab_policy_to_r9_5_required_input_document(global_input_fixture(), POLICY)
        self.assertIsNone(out["r9_5_project_stability_design_basis_decision"]["checks"]["STOREY_STABILITY_INDEX"]["acceptance_criteria"]["max_stability_index"])

    def test_10_r952_package_a_filled(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        a = out["evidence_intake"]["package_inputs"]["PKG-A-STABILITY-METHODOLOGY-DECISION"]
        self.assertEqual("PROJECT_ENGINEERING_POLICY", a["inputs"]["methodology_reference_type"])

    def test_11_r952_package_b_values_filled(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        b = out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]
        self.assertEqual(11.0, b["inputs"]["criteria"]["GLOBAL_BUCKLING_FACTOR"]["minimum_critical_load_factor"])
        self.assertEqual(1.10, b["inputs"]["criteria"]["SECOND_ORDER_AMPLIFICATION"]["max_amplification_factor"])
        self.assertEqual(0.10, b["inputs"]["criteria"]["STOREY_STABILITY_INDEX"]["max_stability_index"])

    def test_12_r952_package_b_not_qualified(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        b = out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]
        self.assertFalse(b["validation"]["qualified"])
        self.assertFalse(b["validation"]["licensed_source_traceability_complete"])

    def test_13_licensed_fields_remain_empty(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        inputs = out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]
        self.assertIsNone(inputs["source_file"])
        self.assertIsNone(inputs["sha256"])
        self.assertIsNone(inputs["clause_reference"])
        self.assertFalse(inputs["licensed_use_confirmed"])
        self.assertFalse(inputs["extraction_reviewed"])

    def test_14_other_jurisdiction_noop(self):
        doc = global_input_fixture()
        doc["r9_5_project_stability_design_basis_decision"]["jurisdictional_basis"]["project_jurisdiction"] = "Netherlands"
        out = apply_ab_policy_to_r9_5_required_input_document(doc, POLICY)
        rec = out["r9_5_project_stability_design_basis_decision"]["source_records"]["PROJECT_STABILITY_POLICY_REQUIRED"]
        self.assertFalse(rec["project_policy_approved"])

    def test_15_existing_real_limit_preserved(self):
        doc = global_input_fixture()
        doc["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"] = 7.25
        out = apply_ab_policy_to_r9_5_required_input_document(doc, POLICY)
        self.assertEqual(
            7.25,
            out["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"],
        )

    def test_16_workspace_applies_existing_scaffold(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            path = workspace / "inputs/structural/global_stability_engineering_input_REQUIRED.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(global_input_fixture()), encoding="utf-8")
            state = apply_ab_project_policy_to_workspace(workspace=workspace, policy_path=POLICY_PATH)
            self.assertEqual("PROJECT_POLICY_APPLIED_TO_R9_5_INPUT", state["status"])
            saved = json.loads(path.read_text(encoding="utf-8"))
            rec = saved["r9_5_project_stability_design_basis_decision"]["source_records"]["PROJECT_STABILITY_POLICY_REQUIRED"]
            self.assertTrue(rec["project_policy_approved"])

    def test_17_workspace_missing_scaffold_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            state = apply_ab_project_policy_to_workspace(workspace=Path(td), policy_path=POLICY_PATH)
            self.assertEqual("SCAFFOLD_NOT_FOUND_NO_CHANGE", state["status"])

    def test_18_no_auto_code_compliance(self):
        self.assertFalse(POLICY["safety"]["automatic_code_compliance_claim"])

    def test_19_professional_review_required(self):
        self.assertTrue(POLICY["safety"]["professional_structural_review_required"])

    def test_20_production_locked(self):
        self.assertEqual("LOCKED", POLICY["safety"]["production_release"])

    def test_21_request_markdown_mentions_all_three(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        md = render_licensed_clause_extract_request(out)
        self.assertIn("1.10", md)
        self.assertIn("11.0", md)
        self.assertIn("0.10", md)

    def test_22_request_markdown_preserves_proxy_warning(self):
        out = apply_ab_project_policy_to_r9_5_2_result(r952_result=r952_fixture(), policy_path=POLICY_PATH)
        md = render_licensed_clause_extract_request(out)
        self.assertIn("not a literal EC2 alpha_cr limit", md)
        self.assertIn("not a literal EC2 storey-index clause", md)


if __name__ == "__main__":
    unittest.main()
