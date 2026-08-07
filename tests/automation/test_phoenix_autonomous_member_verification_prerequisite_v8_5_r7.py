import json
import unittest
from pathlib import Path

from phoenix.autonomy.autonomous_member_verification_prerequisite_v8_5 import (
    derive_member_verification_prerequisite,
)


class TestAutonomousMemberVerificationPrerequisiteV85R7(unittest.TestCase):
    def test_rc_members_get_specific_fail_closed_reason(self):
        model = {
            "members": [
                {
                    "id": "M0001",
                    "material_id": "MAT-RC-C20-25-REFERENCE",
                    "section_id": "SEC-COLUMN-250x250-REF-REINFORCED-CONCRETE",
                },
                {
                    "id": "M0002",
                    "material_id": "MAT-RC-C20-25-REFERENCE",
                    "section_id": "SEC-BEAM-250x400-REF-REINFORCED-CONCRETE",
                },
            ]
        }
        result = derive_member_verification_prerequisite(
            project_id="PHOENIX-PAT-001",
            analytical_model=model,
        )
        self.assertEqual(result["reason"], "RC_MEMBER_DESIGN_RESISTANCE_EVIDENCE_REQUIRED")
        self.assertEqual(result["model_summary"]["member_count"], 2)
        self.assertEqual(result["model_summary"]["rc_member_count"], 2)
        self.assertFalse(result["automatic_member_capacity_invention"])
        self.assertEqual(result["production_release"], "LOCKED")

    def test_required_rc_evidence_is_explicit(self):
        result = derive_member_verification_prerequisite(
            project_id="P",
            analytical_model={
                "members": [
                    {
                        "id": "M1",
                        "material_id": "MAT-RC-C20-25-REFERENCE",
                        "section_id": "SEC-COLUMN-250x250-REF-REINFORCED-CONCRETE",
                    }
                ]
            },
        )
        ids = {item["id"] for item in result["required_evidence"]}
        self.assertIn("RC_DESIGN_CODE_BASIS", ids)
        self.assertIn("RC_MATERIAL_DESIGN_PROPERTIES", ids)
        self.assertIn("RC_REINFORCEMENT_LAYOUT_PER_MEMBER_OR_GROUP", ids)
        self.assertIn("RC_MEMBER_RESISTANCE_DERIVATION", ids)
        self.assertIn("RC_SLS_VERIFICATION_LIMITS", ids)

    def test_no_capacity_values_are_fabricated(self):
        result = derive_member_verification_prerequisite(
            project_id="P",
            analytical_model={
                "members": [
                    {
                        "id": "M1",
                        "material_id": "MAT-RC-C20-25-REFERENCE",
                        "section_id": "SEC-BEAM-250x400-REF-REINFORCED-CONCRETE",
                    }
                ]
            },
        )
        payload = json.dumps(result).lower()
        self.assertNotIn('"capacity":', payload)
        self.assertNotIn('"design_resistance":', payload)
        self.assertNotIn('"fck":', payload)
        self.assertNotIn('"fyk":', payload)

    def test_non_rc_keeps_generic_gate(self):
        result = derive_member_verification_prerequisite(
            project_id="P",
            analytical_model={
                "members": [
                    {
                        "id": "M1",
                        "material_id": "MAT-STEEL-REFERENCE",
                        "section_id": "IPE200",
                    }
                ]
            },
        )
        self.assertEqual(
            result["reason"],
            "STRUCTURAL_CODE_BASIS_AND_MEMBER_VERIFICATION_RULES_REQUIRED",
        )

    def test_chain_contains_r7_integration(self):
        repository = Path(__file__).resolve().parents[2]
        chain = (
            repository / "phoenix" / "autonomy" / "structural_session_chain.py"
        ).read_text(encoding="utf-8")
        self.assertIn("autonomous_member_verification_prerequisite_v8_5", chain)
        self.assertIn("member_verification_input_requirement.json", chain)
        self.assertIn("derive_member_verification_prerequisite", chain)


if __name__ == "__main__":
    unittest.main()