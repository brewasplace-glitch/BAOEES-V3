from __future__ import annotations

import unittest

from phoenix.autonomy.package_c_seismic_scope_criteria_r9_5_2_6 import (
    PACKAGE_ID,
    discover_package_c_input,
    required_template,
    run_package_c_seismic_scope_criteria_r9_5_2_6,
    validate_package_c_input,
)


class PackageCSeismicScopeCriteriaR9526Tests(unittest.TestCase):
    def test_required_template_does_not_invent_scope_or_criteria(self):
        value = required_template()
        self.assertEqual(value["package_id"], PACKAGE_ID)
        self.assertEqual(value["seismic_applicability_status"], "INPUT_REQUIRED")
        self.assertFalse(value["professional_scope_reviewed"])
        criteria = value["criteria_if_applicable"]
        self.assertIsNone(criteria["SOFT_STOREY_STIFFNESS_RATIO"]["minimum_ratio"])
        self.assertIsNone(criteria["TORSIONAL_DRIFT_RATIO"]["max_torsional_drift_ratio"])
        self.assertIsNone(criteria["WEAK_STOREY_STRENGTH_RATIO"]["minimum_ratio"])

    def test_missing_input_remains_input_required(self):
        result = validate_package_c_input(None)
        self.assertEqual(result["status"], "INPUT_REQUIRED")
        self.assertFalse(result["eligible_for_r9_5_promotion"])
        self.assertEqual(result["safety"]["production_release"], "LOCKED")
        self.assertFalse(result["safety"]["automatic_seismic_applicability_decision"])
        self.assertFalse(result["safety"]["automatic_normative_value_insertion"])
        self.assertFalse(result["safety"]["automatic_r9_5_promotion"])

    def test_not_applicable_requires_traceable_professional_scope_review(self):
        value = required_template()
        value.update({
            "seismic_applicability_status": "NOT_APPLICABLE",
            "reference_type": "PROJECT_ENGINEERING_SCOPE_REVIEW",
            "reference": "SEISMIC-SCOPE-REVIEW-001",
            "source_record_id": "SRC-SEISMIC-SCOPE-001",
            "professional_scope_reviewed": True,
            "scope_review_reference": "REVIEW-001",
        })
        result = validate_package_c_input(value)
        self.assertTrue(result["eligible_for_r9_5_promotion"])
        self.assertEqual(result["status"], "ELIGIBLE_FOR_LATER_R9_5_PROMOTION")
        self.assertTrue(result["safety"]["weak_storey_package_d_review_gate_preserved"])

    def test_applicable_without_numerical_traceability_is_incomplete(self):
        value = required_template()
        value.update({
            "seismic_applicability_status": "APPLICABLE",
            "reference_type": "PRIMARY_STANDARD",
            "reference": "SOURCE-REF",
            "source_record_id": "SRC-001",
            "professional_scope_reviewed": True,
            "scope_review_reference": "REVIEW-001",
        })
        result = validate_package_c_input(value)
        self.assertFalse(result["eligible_for_r9_5_promotion"])
        self.assertIn(
            "criteria_if_applicable.SOFT_STOREY_STIFFNESS_RATIO.minimum_ratio",
            result["missing_requirements"],
        )

    def test_complete_applicable_input_is_only_eligible_not_auto_promoted(self):
        value = required_template()
        value.update({
            "seismic_applicability_status": "APPLICABLE",
            "reference_type": "PRIMARY_STANDARD",
            "reference": "TRACEABLE-SEISMIC-REFERENCE",
            "source_record_id": "SRC-SEISMIC-001",
            "professional_scope_reviewed": True,
            "scope_review_reference": "PRO-REVIEW-001",
        })
        value["criteria_if_applicable"] = {
            "SOFT_STOREY_STIFFNESS_RATIO": {
                "minimum_ratio": 0.70,
                "source_record_id": "SRC-SOFT",
                "clause_reference": "CLAUSE-SOFT",
            },
            "TORSIONAL_DRIFT_RATIO": {
                "max_torsional_drift_ratio": 1.20,
                "source_record_id": "SRC-TORSION",
                "clause_reference": "CLAUSE-TORSION",
            },
            "WEAK_STOREY_STRENGTH_RATIO": {
                "minimum_ratio": 0.80,
                "source_record_id": "SRC-WEAK",
                "clause_reference": "CLAUSE-WEAK",
            },
        }
        result = validate_package_c_input(value)
        self.assertTrue(result["eligible_for_r9_5_promotion"])
        self.assertFalse(result["safety"]["automatic_r9_5_promotion"])
        self.assertEqual(result["safety"]["production_release"], "LOCKED")

    def test_discovery_finds_package_in_evidence_intake(self):
        source = {
            "evidence_intake": {
                "package_inputs": {
                    PACKAGE_ID: {
                        "package_id": PACKAGE_ID,
                        "seismic_applicability_status": "INPUT_REQUIRED",
                    }
                }
            }
        }
        result = discover_package_c_input(source)
        self.assertEqual(result["package_id"], PACKAGE_ID)

    def test_chain_entry_accepts_permissive_context(self):
        result = run_package_c_seismic_scope_criteria_r9_5_2_6(
            {"unrelated": True},
            repository="C:/does-not-need-to-exist",
        )
        self.assertEqual(result["package_id"], PACKAGE_ID)
        self.assertEqual(result["status"], "INPUT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
