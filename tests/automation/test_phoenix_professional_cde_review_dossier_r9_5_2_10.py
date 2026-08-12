from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.professional_cde_review_dossier_r9_5_2_10 import (
    C_RETURN,
    D_RETURN,
    E_RETURN,
    PACKAGE_C,
    PACKAGE_D,
    PACKAGE_E,
    REVIEW_DIRNAME,
    prepare_review_pack,
)


def combined_template():
    return {
        "schema_version": "phoenix.r9-5-cde-combined-evidence-intake/1.0",
        "engine_version": "R9.5.2.9",
        "project_id": "PHOENIX-PAT-001",
        "package_inputs": {
            PACKAGE_C: {
                "package_id": PACKAGE_C,
                "status": "INPUT_REQUIRED",
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
                "status": "INPUT_REQUIRED",
                "screening_proxy_accepted_for_candidate_gate": None,
                "screening_proxy_review_reference": None,
                "reviewer_scope": None,
                "review_status": "INPUT_REQUIRED",
            },
            PACKAGE_E: {
                "package_id": PACKAGE_E,
                "status": "INPUT_REQUIRED",
                "independent_engineering_evidence_reference": None,
                "repository_relative_source_file": None,
                "sha256": None,
                "independent_review_status": "INPUT_REQUIRED",
                "independent_review_reference": None,
                "independently_verified_alternate_path": None,
                "acceptance_criterion_and_traceability": None,
            },
        },
        "evidence_context": {
            "existing_r9_3_evidence_references": {
                "R9.3:ALTERNATE_LOAD_PATH_EVIDENCE": True,
                "R9.3:SOFT_STOREY_STIFFNESS_RATIO": True,
                "R9.3:TORSIONAL_DRIFT_RATIO": True,
                "R9.3:WEAK_STOREY_STRENGTH_RATIO": True,
            },
            "source_files": {},
        },
    }


class R95210Tests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        project = root / "projects" / "runtime" / "PHOENIX-PAT-001"
        input_root = project / "inputs" / "structural"
        input_root.mkdir(parents=True)
        (input_root / "r9_5_remaining_evidence_combined_intake_REQUIRED.json").write_text(
            json.dumps(combined_template()), encoding="utf-8"
        )
        evidence_dir = project / "results" / "session_adapters" / "structural_engineering" / "validated_v8_1_to_v8_12" / "v8_6"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "technical.json").write_text(json.dumps({
            "checks": {
                "soft": {"evidence_reference": "R9.3:SOFT_STOREY_STIFFNESS_RATIO", "ratio": 0.91},
                "torsion": {"evidence_reference": "R9.3:TORSIONAL_DRIFT_RATIO", "ratio": 1.04},
                "weak": {"evidence_reference": "R9.3:WEAK_STOREY_STRENGTH_RATIO", "ratio": 0.89},
                "alt": {"evidence_reference": "R9.3:ALTERNATE_LOAD_PATH_EVIDENCE", "status": "SCREENING"},
            }
        }), encoding="utf-8")
        return temp, root, project

    def test_01_generates_dossier_request_and_blank_returns(self):
        temp, root, project = self.make_repo()
        try:
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            self.assertTrue((review / "professional_C_D_review_dossier.json").is_file())
            self.assertTrue((review / "package_E_independent_evidence_request.json").is_file())
            self.assertTrue((review / C_RETURN).is_file())
            self.assertTrue((review / D_RETURN).is_file())
            self.assertTrue((review / E_RETURN).is_file())
            self.assertEqual([], result["merged_package_ids"])
            self.assertFalse(result["combined_intake_changed"])
        finally:
            temp.cleanup()

    def test_02_existing_r93_evidence_is_inventoried_not_promoted(self):
        temp, root, project = self.make_repo()
        try:
            prepare_review_pack(root, "PHOENIX-PAT-001")
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            manifest = json.loads((review / "existing_evidence_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(1, manifest["check_evidence"]["SOFT_STOREY_STIFFNESS_RATIO"]["located_source_count"])
            self.assertEqual(
                "INTERNAL_SCREENING_ONLY",
                manifest["check_evidence"]["ALTERNATE_LOAD_PATH_EVIDENCE"]["interpretation"],
            )
            self.assertTrue(manifest["safety"]["alternate_path_screening_is_not_independent_evidence"])
        finally:
            temp.cleanup()

    def test_03_complete_confirmed_d_review_is_mechanically_merged_only(self):
        temp, root, project = self.make_repo()
        try:
            prepare_review_pack(root, "PHOENIX-PAT-001")
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            d = json.loads((review / D_RETURN).read_text(encoding="utf-8"))
            d["submission_confirmed"] = True
            d["review_record"] = {
                "reviewer_name": "Reviewer",
                "reviewer_organization": "Org",
                "reviewer_role": "Structural reviewer",
                "review_date": "2026-08-13",
                "signature_reference": "SIG-D-001",
            }
            d["package_input"].update({
                "screening_proxy_accepted_for_candidate_gate": False,
                "screening_proxy_review_reference": "D-REVIEW-001",
                "reviewer_scope": "Candidate gate review only",
                "review_status": "REVIEWED_NOT_ACCEPTED_FOR_CANDIDATE_GATE",
            })
            (review / D_RETURN).write_text(json.dumps(d), encoding="utf-8")
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            self.assertEqual([PACKAGE_D], result["merged_package_ids"])
            combined = json.loads(
                (project / "inputs" / "structural" / "r9_5_remaining_evidence_combined_intake_REQUIRED.json").read_text(encoding="utf-8")
            )
            self.assertFalse(combined["package_inputs"][PACKAGE_D]["screening_proxy_accepted_for_candidate_gate"])
            self.assertFalse(combined["r9_5_2_10_review_return_processing"]["automatic_gate_promotion"])
        finally:
            temp.cleanup()

    def test_04_package_e_sha_mismatch_blocks_merge(self):
        temp, root, project = self.make_repo()
        try:
            prepare_review_pack(root, "PHOENIX-PAT-001")
            source = project / "inputs" / "structural" / "external_evidence" / "alt.txt"
            source.parent.mkdir(parents=True)
            source.write_text("independent evidence", encoding="utf-8")
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            e = json.loads((review / E_RETURN).read_text(encoding="utf-8"))
            e["submission_confirmed"] = True
            e["review_record"] = {
                "reviewer_name": "Independent Reviewer",
                "reviewer_organization": "Independent Org",
                "reviewer_role": "Independent structural reviewer",
                "review_date": "2026-08-13",
                "signature_reference": "SIG-E-001",
                "independence_confirmed": True,
                "independence_basis": "Independent organization and analysis path",
            }
            e["package_input"] = {
                "package_id": PACKAGE_E,
                "status": "INPUT_REQUIRED",
                "independent_engineering_evidence_reference": "ALT-INDEP-001",
                "repository_relative_source_file": source.relative_to(root).as_posix(),
                "sha256": "0" * 64,
                "independent_review_status": "REVIEWED",
                "independent_review_reference": "E-REVIEW-001",
                "independently_verified_alternate_path": True,
                "acceptance_criterion_and_traceability": {
                    "minimum_residual_capacity_proxy_ratio": 0.75,
                    "source_record_id": "INDEPENDENT-SOURCE-001",
                    "clause_reference": "Independent engineering criterion reference",
                },
            }
            (review / E_RETURN).write_text(json.dumps(e), encoding="utf-8")
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            self.assertEqual([], result["merged_package_ids"])
            validation = json.loads((review / "review_return_validation.json").read_text(encoding="utf-8"))
            self.assertIn(
                "package_input.sha256:MISMATCH",
                validation["submissions"][PACKAGE_E]["invalid_requirements"],
            )
        finally:
            temp.cleanup()

    def test_05_package_e_matching_sha_can_merge_but_not_approve(self):
        temp, root, project = self.make_repo()
        try:
            prepare_review_pack(root, "PHOENIX-PAT-001")
            source = project / "inputs" / "structural" / "external_evidence" / "alt.txt"
            source.parent.mkdir(parents=True)
            source.write_text("independent evidence", encoding="utf-8")
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            e = json.loads((review / E_RETURN).read_text(encoding="utf-8"))
            e["submission_confirmed"] = True
            e["review_record"] = {
                "reviewer_name": "Independent Reviewer",
                "reviewer_organization": "Independent Org",
                "reviewer_role": "Independent structural reviewer",
                "review_date": "2026-08-13",
                "signature_reference": "SIG-E-001",
                "independence_confirmed": True,
                "independence_basis": "Independent organization and analysis path",
            }
            e["package_input"] = {
                "package_id": PACKAGE_E,
                "status": "INPUT_REQUIRED",
                "independent_engineering_evidence_reference": "ALT-INDEP-001",
                "repository_relative_source_file": source.relative_to(root).as_posix(),
                "sha256": sha,
                "independent_review_status": "REVIEWED",
                "independent_review_reference": "E-REVIEW-001",
                "independently_verified_alternate_path": True,
                "acceptance_criterion_and_traceability": {
                    "minimum_residual_capacity_proxy_ratio": 0.75,
                    "source_record_id": "INDEPENDENT-SOURCE-001",
                    "clause_reference": "Independent engineering criterion reference",
                },
            }
            (review / E_RETURN).write_text(json.dumps(e), encoding="utf-8")
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            self.assertEqual([PACKAGE_E], result["merged_package_ids"])
            validation = json.loads((review / "review_return_validation.json").read_text(encoding="utf-8"))
            self.assertFalse(validation["automatic_gate_promotion"])
            self.assertFalse(validation["automatic_r9_5_requalification_started"])
            self.assertEqual("LOCKED", validation["safety"]["production_release"])
        finally:
            temp.cleanup()

    def test_06_blank_or_incomplete_c_never_becomes_applicable(self):
        temp, root, project = self.make_repo()
        try:
            prepare_review_pack(root, "PHOENIX-PAT-001")
            review = project / "inputs" / "structural" / REVIEW_DIRNAME
            c = json.loads((review / C_RETURN).read_text(encoding="utf-8"))
            c["submission_confirmed"] = True
            (review / C_RETURN).write_text(json.dumps(c), encoding="utf-8")
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            self.assertEqual([], result["merged_package_ids"])
            combined = json.loads(
                (project / "inputs" / "structural" / "r9_5_remaining_evidence_combined_intake_REQUIRED.json").read_text(encoding="utf-8")
            )
            self.assertEqual("INPUT_REQUIRED", combined["package_inputs"][PACKAGE_C]["seismic_applicability_status"])
        finally:
            temp.cleanup()

    def test_07_release_locks_remain_hard(self):
        temp, root, project = self.make_repo()
        try:
            result = prepare_review_pack(root, "PHOENIX-PAT-001")
            self.assertEqual("LOCKED", result["production_release"])
            self.assertEqual("LOCKED", result["for_construction_release"])
            self.assertFalse(result["automatic_r9_5_requalification_started"])
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
