from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.combined_cde_evidence_intake_r9_5_2_9 import (
    DEFAULT_WORKSPACE_FILENAME,
    INPUT_REQUIRED,
    PACKAGE_C_ID,
    PACKAGE_D_ID,
    PACKAGE_E_ID,
    READY_FOR_PACKAGE_VALIDATION,
    discover_combined_intake,
    required_combined_intake_template,
    run_combined_cde_evidence_intake_r9_5_2_9,
    validate_combined_intake_structure,
)


class CombinedCDEEvidenceIntakeR9529Tests(unittest.TestCase):
    def test_01_template_contains_exact_c_d_e_package_ids(self):
        value = required_combined_intake_template()
        self.assertEqual(
            {PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID},
            set(value["package_inputs"]),
        )

    def test_02_template_preserves_package_c_required_shape(self):
        c = required_combined_intake_template()["package_inputs"][PACKAGE_C_ID]
        self.assertIn("seismic_applicability_status", c)
        self.assertIn("professional_scope_reviewed", c)
        self.assertIn("criteria_if_applicable", c)
        self.assertIn("SOFT_STOREY_STIFFNESS_RATIO", c["criteria_if_applicable"])
        self.assertIn("TORSIONAL_DRIFT_RATIO", c["criteria_if_applicable"])
        self.assertIn("WEAK_STOREY_STRENGTH_RATIO", c["criteria_if_applicable"])

    def test_03_template_preserves_package_d_required_shape(self):
        d = required_combined_intake_template()["package_inputs"][PACKAGE_D_ID]
        self.assertIn("screening_proxy_accepted_for_candidate_gate", d)
        self.assertIn("screening_proxy_review_reference", d)
        self.assertIn("reviewer_scope", d)
        self.assertIn("review_status", d)

    def test_04_template_preserves_package_e_required_shape(self):
        e = required_combined_intake_template()["package_inputs"][PACKAGE_E_ID]
        for key in (
            "independent_engineering_evidence_reference",
            "repository_relative_source_file",
            "sha256",
            "independent_review_status",
            "independent_review_reference",
            "independently_verified_alternate_path",
            "acceptance_criterion_and_traceability",
        ):
            self.assertIn(key, e)

    def test_05_missing_input_is_input_required_not_auto_complete(self):
        value = run_combined_cde_evidence_intake_r9_5_2_9({})
        self.assertEqual(INPUT_REQUIRED, value["status"])
        self.assertIsNone(value["intake_source"])
        self.assertFalse(value["controlled_requalification_trigger"]["performed_by_r9_5_2_9"])

    def test_06_workspace_file_is_discovered(self):
        template = required_combined_intake_template()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            path = workspace / "inputs" / "structural" / DEFAULT_WORKSPACE_FILENAME
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(template), encoding="utf-8")
            discovered, source = discover_combined_intake({"workspace": workspace})
            self.assertIsInstance(discovered, dict)
            self.assertEqual(str(path), source)

    def test_07_structurally_complete_bundle_only_becomes_ready_for_package_validation(self):
        template = required_combined_intake_template()
        result = validate_combined_intake_structure(template)
        self.assertEqual(READY_FOR_PACKAGE_VALIDATION, result["status"])
        self.assertTrue(
            result["intake_validation"]["package_specific_validation_delegated_to_existing_engines"]
        )
        self.assertNotEqual("ELIGIBLE_FOR_LATER_R9_5_PROMOTION", result["status"])

    def test_08_nested_package_inputs_are_discovered_for_existing_chain_context(self):
        template = required_combined_intake_template()
        context = {"nested": {"package_inputs": template["package_inputs"]}}
        discovered, source = discover_combined_intake(context)
        self.assertEqual("context:recursive-package-inputs", source)
        self.assertEqual(
            {PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID},
            set(discovered["package_inputs"]),
        )

    def test_09_package_ids_are_forced_to_authoritative_ids(self):
        template = required_combined_intake_template()
        template["package_inputs"][PACKAGE_C_ID]["package_id"] = "WRONG"
        result = validate_combined_intake_structure(template)
        self.assertEqual(PACKAGE_C_ID, result["package_inputs"][PACKAGE_C_ID]["package_id"])

    def test_10_safety_locks_are_never_relaxed(self):
        value = run_combined_cde_evidence_intake_r9_5_2_9({})
        safety = value["safety"]
        self.assertFalse(safety["automatic_professional_approval"])
        self.assertFalse(safety["automatic_code_compliance_claim"])
        self.assertFalse(safety["automatic_seismic_applicability_decision"])
        self.assertFalse(safety["automatic_numerical_criteria_generation"])
        self.assertFalse(safety["automatic_screening_proxy_acceptance"])
        self.assertFalse(safety["automatic_independent_evidence_generation"])
        self.assertFalse(safety["automatic_r9_5_success_claim"])
        self.assertEqual("LOCKED", safety["production_release"])
        self.assertEqual("LOCKED", safety["for_construction_release"])


if __name__ == "__main__":
    unittest.main()
