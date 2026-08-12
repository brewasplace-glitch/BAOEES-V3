from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.phoenix_pat001_real_cde_evidence_intake_preparation import (
    COMBINED_FILENAME,
    PACKAGE_C,
    PACKAGE_D,
    PACKAGE_E,
    prepare,
)


def template():
    return {
        "schema_version": "x",
        "project_id": None,
        "package_inputs": {
            PACKAGE_C: {
                "package_id": PACKAGE_C,
                "seismic_applicability_status": "INPUT_REQUIRED",
                "reference_type": None,
                "reference": None,
                "source_record_id": None,
                "professional_scope_reviewed": False,
                "scope_review_reference": None,
                "criteria_if_applicable": {
                    "SOFT_STOREY_STIFFNESS_RATIO": {"minimum_ratio": None, "source_record_id": None, "clause_reference": None},
                    "TORSIONAL_DRIFT_RATIO": {"max_torsional_drift_ratio": None, "source_record_id": None, "clause_reference": None},
                    "WEAK_STOREY_STRENGTH_RATIO": {"minimum_ratio": None, "source_record_id": None, "clause_reference": None},
                },
            },
            PACKAGE_D: {
                "package_id": PACKAGE_D,
                "screening_proxy_accepted_for_candidate_gate": None,
                "screening_proxy_review_reference": None,
                "reviewer_scope": None,
                "review_status": "INPUT_REQUIRED",
            },
            PACKAGE_E: {
                "package_id": PACKAGE_E,
                "independent_engineering_evidence_reference": None,
                "repository_relative_source_file": None,
                "sha256": None,
                "independent_review_status": "INPUT_REQUIRED",
                "independent_review_reference": None,
                "independently_verified_alternate_path": None,
                "acceptance_criterion_and_traceability": {
                    "minimum_residual_capacity_proxy_ratio": None,
                    "source_record_id": None,
                    "clause_reference": None,
                },
            },
        },
    }


class PAT001RealCDEEvidencePreparationTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "templates" / "structural").mkdir(parents=True)
        (root / "templates" / "structural" / COMBINED_FILENAME).write_text(json.dumps(template()), encoding="utf-8")
        project = root / "projects" / "runtime" / "PHOENIX-PAT-001"
        (project / "inputs" / "structural").mkdir(parents=True)
        result_dir = project / "results" / "session_adapters" / "structural_engineering" / "validated_v8_1_to_v8_12" / "v8_6"
        result_dir.mkdir(parents=True)
        (result_dir / "r9_5_2_4_runtime_input_merge_r9_5_requalification.json").write_text(json.dumps({
            "status": "BLOCKED",
            "summary": {
                "technical_analysis_required_count": 0,
                "package_b_traceability_complete": True,
            },
            "blockers": [{
                "unresolved_check_types": [
                    "ALTERNATE_LOAD_PATH_EVIDENCE",
                    "SOFT_STOREY_STIFFNESS_RATIO",
                    "TORSIONAL_DRIFT_RATIO",
                    "WEAK_STOREY_STRENGTH_RATIO",
                ],
                "unresolved_package_ids": [PACKAGE_C, PACKAGE_D, PACKAGE_E],
            }],
        }), encoding="utf-8")
        (result_dir / "r9_5_project_stability_design_basis_decision.json").write_text(json.dumps({
            "status": "BLOCKED"
        }), encoding="utf-8")
        return temp, root, project

    def test_01_prepare_never_invents_professional_inputs(self):
        temp, root, project = self.make_repo()
        try:
            result = prepare(root, "PHOENIX-PAT-001")
            intake = json.loads(Path(result["combined_intake"]).read_text(encoding="utf-8"))
            c = intake["package_inputs"][PACKAGE_C]
            d = intake["package_inputs"][PACKAGE_D]
            e = intake["package_inputs"][PACKAGE_E]
            self.assertEqual("INPUT_REQUIRED", c["seismic_applicability_status"])
            self.assertFalse(c["professional_scope_reviewed"])
            self.assertIsNone(d["screening_proxy_accepted_for_candidate_gate"])
            self.assertEqual("INPUT_REQUIRED", d["review_status"])
            self.assertIsNone(e["independent_engineering_evidence_reference"])
            self.assertIsNone(e["independently_verified_alternate_path"])
        finally:
            temp.cleanup()

    def test_02_existing_human_values_are_preserved(self):
        temp, root, project = self.make_repo()
        try:
            path = project / "inputs" / "structural" / COMBINED_FILENAME
            existing = template()
            existing["package_inputs"][PACKAGE_D]["reviewer_scope"] = "SIGNED PROFESSIONAL REVIEW REF X"
            path.write_text(json.dumps(existing), encoding="utf-8")
            result = prepare(root, "PHOENIX-PAT-001")
            intake = json.loads(Path(result["combined_intake"]).read_text(encoding="utf-8"))
            self.assertEqual(
                "SIGNED PROFESSIONAL REVIEW REF X",
                intake["package_inputs"][PACKAGE_D]["reviewer_scope"],
            )
        finally:
            temp.cleanup()

    def test_03_gap_register_matches_real_missing_professional_fields(self):
        temp, root, project = self.make_repo()
        try:
            result = prepare(root, "PHOENIX-PAT-001")
            gap = json.loads(Path(result["gap_register"]).read_text(encoding="utf-8"))
            self.assertEqual(0, gap["technical_analysis_required_count"])
            self.assertIn("seismic_applicability_status", gap["packages"][PACKAGE_C]["missing_requirements"])
            self.assertIn("screening_proxy_review_reference", gap["packages"][PACKAGE_D]["missing_requirements"])
            self.assertIn("independent_engineering_evidence_reference", gap["packages"][PACKAGE_E]["missing_requirements"])
            self.assertFalse(gap["all_intake_fields_ready_for_existing_validators"])
        finally:
            temp.cleanup()

    def test_04_release_locks_remain_hard(self):
        temp, root, project = self.make_repo()
        try:
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertEqual("LOCKED", result["production_release"])
            self.assertEqual("LOCKED", result["for_construction_release"])
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
