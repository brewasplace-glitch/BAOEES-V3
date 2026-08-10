from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.stability_design_basis_decision_dossier_evidence_intake_r9_5_2 import (
    build_stability_design_basis_decision_dossier_evidence_intake,
    render_decision_dossier_markdown,
)

CHECKS = [
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


def r951_fixture():
    matrix = {}
    for check in CHECKS:
        matrix[check] = {
            "technical_evidence_reference": f"R9.3:{check}",
            "r9_5_state": "DECISION_OR_SOURCE_INPUT_REQUIRED",
            "remaining_requirements": ["explicit_applicability_decision", "primary_source_record_id"],
            "suriname_primary_support": [],
            "numerical_acceptance_criterion_still_required": check in {
                "GLOBAL_BUCKLING_FACTOR",
                "SECOND_ORDER_AMPLIFICATION",
                "STOREY_STABILITY_INDEX",
                "SOFT_STOREY_STIFFNESS_RATIO",
                "TORSIONAL_DRIFT_RATIO",
                "WEAK_STOREY_STRENGTH_RATIO",
                "ALTERNATE_LOAD_PATH_EVIDENCE",
            },
            "professional_or_independent_review_required": check in {
                "WEAK_STOREY_STRENGTH_RATIO",
                "ALTERNATE_LOAD_PATH_EVIDENCE",
            },
        }
    matrix["GLOBAL_BUCKLING_FACTOR"]["suriname_primary_support"] = [{
        "status": "AVAILABLE",
        "source_id": "SR-SUR-BB1-1956-001",
        "rule_id": "SUR-BB1-A27-BUCKLING",
        "source_pointer": "Bouwbesluit no. 1, Article 27",
        "support_scope": "CHECK_APPLICABILITY_ONLY",
        "exact_v8_6_acceptance_limit_available": False,
    }]
    checks = {
        check: {
            "applicability": None,
            "methodology_accepted": False,
            "primary_source_record_id": None,
            "supporting_source_record_ids": [],
            "evidence_reference": f"R9.3:{check}",
        }
        for check in CHECKS
    }
    checks["GLOBAL_BUCKLING_FACTOR"]["supporting_source_record_ids"] = [
        "SURINAME_BOUWBESLUIT_A27_BUCKLING"
    ]
    return {
        "status": "BLOCKED",
        "source_states": {
            "r9_5_summary": {
                "r9_3_technical_evidence_count": 9,
            }
        },
        "summary": {
            "remaining_decision_check_count": 9,
            "technical_analysis_required_count": 0,
            "consolidated_input_package_count": 5,
        },
        "evidence_requirement_matrix": matrix,
        "prefilled_project_input": {
            "schema_version": "phoenix.r9-5-project-stability-design-basis-required-input/1.0",
            "r9_5_project_stability_design_basis_decision": {
                "decision_id": "PHOENIX-PAT-001-STABILITY-DESIGN-BASIS-DECISION",
                "jurisdictional_basis": {
                    "project_jurisdiction": "Suriname / Paramaribo",
                    "engineering_design_methodology": "Eurocode 2 based",
                    "current_2026_surinaame_legal_status": "NOT_EXTERNALLY_VERIFIED",
                    "eurocode_2_legal_adoption": "NOT_ESTABLISHED_BY_UPLOADED_PRIMARY_SOURCES",
                    "qualification_scope": "ENGINEERING_DESIGN_CANDIDATE_ONLY",
                    "professional_review": "REQUIRED",
                },
                "seismic_applicability": {
                    "status": None,
                    "professional_scope_reviewed": False,
                    "r9_5_1_status": "EXPLICIT_SCOPE_DECISION_REQUIRED",
                },
                "source_records": {
                    "SURINAME_BOUWBESLUIT_A26_STRENGTH": {
                        "reference_type": "AUTHORITY_APPROVED_PROJECT_BASIS",
                        "bib_source_id": "SR-SUR-BB1-1956-001",
                        "source_pointer": "Bouwbesluit no. 1, Article 26",
                    },
                    "SURINAME_BOUWBESLUIT_A27_BUCKLING": {
                        "reference_type": "AUTHORITY_APPROVED_PROJECT_BASIS",
                        "bib_source_id": "SR-SUR-BB1-1956-001",
                        "source_pointer": "Bouwbesluit no. 1, Article 27",
                    },
                },
                "checks": checks,
            },
        },
        "blockers": [{
            "reason": "R9_5_1_EXPLICIT_SOURCE_REVIEW_AND_DESIGN_BASIS_INPUT_REQUIRED"
        }],
    }


class R952Tests(unittest.TestCase):
    def setUp(self):
        self.policy = ROOT / "configs/phoenix/structural/stability_design_basis_decision_dossier_evidence_intake_policy_r9_5_2.json"

    def execute(self, r951=None, existing=None):
        return build_stability_design_basis_decision_dossier_evidence_intake(
            project_id="PHOENIX-PAT-001",
            r951_result=r951 or r951_fixture(),
            policy_path=self.policy,
            existing_intake=existing,
        )

    def test_01_blocks_only_on_intake(self):
        r = self.execute()
        self.assertEqual("BLOCKED", r["status"])
        self.assertEqual(0, r["summary"]["technical_analysis_required_count"])

    def test_02_five_packages(self):
        self.assertEqual(5, self.execute()["summary"]["package_count"])

    def test_03_all_five_unresolved_initially(self):
        self.assertEqual(5, self.execute()["summary"]["unresolved_package_count"])

    def test_04_surinaame_records_preserved(self):
        intake = self.execute()["evidence_intake"]
        self.assertIn("SURINAME_BOUWBESLUIT_A26_STRENGTH", intake["source_records"])
        self.assertIn("SURINAME_BOUWBESLUIT_A27_BUCKLING", intake["source_records"])

    def test_05_buckling_support_preserved(self):
        row = self.execute()["decision_dossier"]["packages"]["PKG-A-STABILITY-METHODOLOGY-DECISION"]["known_check_state"]["GLOBAL_BUCKLING_FACTOR"]
        self.assertEqual("SUR-BB1-A27-BUCKLING", row["suriname_primary_support"][0]["rule_id"])

    def test_06_no_buckling_limit_invented(self):
        criteria = self.execute()["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]["criteria"]
        self.assertIsNone(criteria["GLOBAL_BUCKLING_FACTOR"]["minimum_critical_load_factor"])

    def test_07_no_second_order_limit_invented(self):
        criteria = self.execute()["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]["criteria"]
        self.assertIsNone(criteria["SECOND_ORDER_AMPLIFICATION"]["max_amplification_factor"])

    def test_08_no_storey_index_limit_invented(self):
        criteria = self.execute()["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]["criteria"]
        self.assertIsNone(criteria["STOREY_STABILITY_INDEX"]["max_stability_index"])

    def test_09_seismic_scope_unresolved(self):
        pkg = self.execute()["evidence_intake"]["package_inputs"]["PKG-C-SEISMIC-SCOPE-AND-CRITERIA"]
        self.assertIsNone(pkg["inputs"]["seismic_applicability_status"])
        self.assertFalse(pkg["inputs"]["professional_scope_reviewed"])

    def test_10_weak_storey_review_false(self):
        pkg = self.execute()["evidence_intake"]["package_inputs"]["PKG-D-WEAK-STOREY-SCREENING-REVIEW"]
        self.assertFalse(pkg["inputs"]["screening_proxy_accepted_for_candidate_gate"])

    def test_11_alt_path_review_false(self):
        pkg = self.execute()["evidence_intake"]["package_inputs"]["PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"]
        self.assertFalse(pkg["inputs"]["independently_verified_alternate_path"])

    def test_12_alt_path_sha_empty(self):
        pkg = self.execute()["evidence_intake"]["package_inputs"]["PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"]
        self.assertIsNone(pkg["inputs"]["sha256"])

    def test_13_preserves_existing_reference(self):
        existing = {
            "package_inputs": {
                "PKG-A-STABILITY-METHODOLOGY-DECISION": {
                    "inputs": {
                        "methodology_reference": "PROJECT-POLICY-001"
                    }
                }
            }
        }
        r = self.execute(existing=existing)
        got = r["evidence_intake"]["package_inputs"]["PKG-A-STABILITY-METHODOLOGY-DECISION"]["inputs"]["methodology_reference"]
        self.assertEqual("PROJECT-POLICY-001", got)

    def test_14_preserved_value_count(self):
        existing = {
            "package_inputs": {
                "PKG-A-STABILITY-METHODOLOGY-DECISION": {
                    "inputs": {
                        "methodology_reference": "A",
                        "scope": "B",
                    }
                }
            }
        }
        self.assertEqual(2, self.execute(existing=existing)["summary"]["preserved_existing_input_value_count"])

    def test_15_dossier_contains_all_checks(self):
        packages = self.execute()["decision_dossier"]["packages"]
        seen = set()
        for pkg in packages.values():
            seen.update(pkg["checks"])
        self.assertEqual(set(CHECKS), seen)

    def test_16_markdown_lists_packages(self):
        md = render_decision_dossier_markdown(self.execute())
        self.assertIn("PKG-A-STABILITY-METHODOLOGY-DECISION", md)
        self.assertIn("PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE", md)

    def test_17_markdown_states_zero_analysis(self):
        md = render_decision_dossier_markdown(self.execute())
        self.assertIn("Technical analyses still required: `0`", md)

    def test_18_background_ai_forbidden(self):
        self.assertFalse(self.execute()["safety"]["background_ai_source_as_normative_input"])

    def test_19_seismic_auto_decision_forbidden(self):
        self.assertFalse(self.execute()["safety"]["automatic_seismic_applicability_decision"])

    def test_20_professional_review_not_automatic(self):
        self.assertFalse(self.execute()["safety"]["automatic_professional_review"])

    def test_21_production_locked(self):
        self.assertEqual("LOCKED", self.execute()["safety"]["production_release"])

    def test_22_missing_scaffold_fails_closed(self):
        r951 = r951_fixture()
        r951["prefilled_project_input"] = {}
        r = self.execute(r951=r951)
        self.assertEqual("R9_5_2_R9_5_1_SCAFFOLD_REQUIRED", r["blockers"][0]["reason"])

    def test_23_r951_passed_noop(self):
        r = self.execute(r951={"status": "PASSED"})
        self.assertEqual("PASSED", r["status"])
        self.assertEqual([], r["blockers"])

    def test_24_qualification_gate_message_preserved(self):
        pkg = self.execute()["evidence_intake"]["package_inputs"]["PKG-A-STABILITY-METHODOLOGY-DECISION"]
        self.assertIn("R9.5/R9.4/v8.6", pkg["validation"]["qualification_message"])


if __name__ == "__main__":
    unittest.main()
