import json
import unittest
from pathlib import Path

from phoenix.autonomy.autonomous_rc_design_candidate_v8_5_r8 import (
    AutonomousRCDesignBlocked,
    derive_rc_design_candidate,
)


def _policy():
    repository = Path(__file__).resolve().parents[2]
    return json.loads(
        (
            repository
            / "configs"
            / "phoenix"
            / "structural"
            / "autonomous_rc_design_candidate_policy_v8_5_r8.json"
        ).read_text(encoding="utf-8")
    )


class TestAutonomousRCDesignCandidateV85R8(unittest.TestCase):
    def _model(self):
        return {
            "nodes": [
                {"id": "N1", "x_m": 0.0, "y_m": 0.0, "z_m": 0.0},
                {"id": "N2", "x_m": 0.0, "y_m": 0.0, "z_m": 3.0},
                {"id": "N3", "x_m": 0.0, "y_m": 0.0, "z_m": 3.0},
                {"id": "N4", "x_m": 4.0, "y_m": 0.0, "z_m": 3.0},
            ],
            "members": [
                {
                    "id": "M1",
                    "node_i": "N1",
                    "node_j": "N2",
                    "material_id": "MAT-RC-C20-25-REFERENCE",
                    "section_id": "SEC-COLUMN-250x250-REF-REINFORCED-CONCRETE",
                },
                {
                    "id": "M2",
                    "node_i": "N3",
                    "node_j": "N4",
                    "material_id": "MAT-RC-C20-25-REFERENCE",
                    "section_id": "SEC-BEAM-250x400-REF-REINFORCED-CONCRETE",
                },
            ],
        }

    def _basis(self):
        return {
            "materials": {
                "MAT-RC-C20-25-REFERENCE": {"analysis_reference_class": "C20/25"}
            },
            "sections": {
                "SEC-COLUMN-250x250-REF-REINFORCED-CONCRETE": {
                    "width_m": 0.25,
                    "height_m": 0.25,
                },
                "SEC-BEAM-250x400-REF-REINFORCED-CONCRETE": {
                    "width_m": 0.25,
                    "height_m": 0.40,
                },
            },
        }

    def _results(self):
        return {
            "calculix": {
                "SR-ULS-LC-Q": {
                    "element_forces": {
                        "M1": {"N": -180.0, "VY": 10.0, "VZ": 5.0, "MY": 35.0, "MZ": 12.0},
                        "M2": {"N": -10.0, "VY": 45.0, "VZ": 4.0, "MY": 80.0, "MZ": 6.0},
                    },
                    "node_displacements": {
                        "N2": {"UX": 0.003, "UZ": -0.002},
                        "N4": {"UX": 0.001, "UZ": -0.009},
                    },
                },
                "SR-SLS-LC-Q": {
                    "element_forces": {
                        "M1": {"N": -100.0, "VY": 5.0, "VZ": 2.0, "MY": 15.0, "MZ": 5.0},
                        "M2": {"N": -5.0, "VY": 20.0, "VZ": 2.0, "MY": 35.0, "MZ": 3.0},
                    },
                    "node_displacements": {
                        "N2": {"UX": 0.002, "UZ": -0.001},
                        "N4": {"UX": 0.001, "UZ": -0.006},
                    },
                },
            }
        }

    def test_generates_candidate_for_rc_members(self):
        result = derive_rc_design_candidate(
            project_id="PHOENIX-PAT-001",
            analytical_model=self._model(),
            solver_basis=self._basis(),
            combination_results=self._results(),
            analysis_validation_state="ENGINEERING_REVIEW_REQUIRED",
            policy=_policy(),
        )
        self.assertEqual(result["status"], "CANDIDATE_GENERATED")
        self.assertEqual(result["member_count"], 2)
        self.assertGreater(result["verification_rule_count"], 0)
        self.assertEqual(result["solver"], "calculix")
        self.assertEqual(result["release"]["production_release"], "LOCKED")

    def test_candidate_contains_reinforcement_and_resistance(self):
        result = derive_rc_design_candidate(
            project_id="P",
            analytical_model=self._model(),
            solver_basis=self._basis(),
            combination_results=self._results(),
            analysis_validation_state="ENGINEERING_REVIEW_REQUIRED",
            policy=_policy(),
        )
        first = result["candidate_members"][0]
        self.assertGreater(first["reinforcement_candidate"]["area_provided_mm2"], 0.0)
        self.assertGreater(first["screening_resistances"]["N_Rd_compression_kN"], 0.0)
        self.assertGreater(first["screening_resistances"]["MY_Rd_kNm"], 0.0)

    def test_v85_input_is_traceable_and_accepts_real_v84_state(self):
        result = derive_rc_design_candidate(
            project_id="P",
            analytical_model=self._model(),
            solver_basis=self._basis(),
            combination_results=self._results(),
            analysis_validation_state="ENGINEERING_REVIEW_REQUIRED",
            policy=_policy(),
        )
        mi = result["member_verification_input"]
        self.assertTrue(mi["verification_rules"])
        self.assertTrue(all(r.get("normative_reference") for r in mi["verification_rules"]))
        self.assertEqual(
            mi["verification_policy"]["acceptable_analysis_validation_states"],
            ["ENGINEERING_REVIEW_REQUIRED"],
        )

    def test_policy_denies_nen_ndp_and_release_claims(self):
        policy = _policy()
        self.assertIn("NOT_CLAIMED_AS_DUTCH_NDP_VALUES", policy["numerical_parameter_status"])
        self.assertFalse(policy["safety"]["automatic_code_compliance_claim"])
        self.assertFalse(policy["safety"]["automatic_structural_approval"])
        self.assertEqual(policy["safety"]["production_release"], "LOCKED")

    def test_missing_results_blocks(self):
        with self.assertRaises(AutonomousRCDesignBlocked):
            derive_rc_design_candidate(
                project_id="P",
                analytical_model=self._model(),
                solver_basis=self._basis(),
                combination_results={},
                analysis_validation_state="ENGINEERING_REVIEW_REQUIRED",
                policy=_policy(),
            )

    def test_chain_contains_r8_integration(self):
        repository = Path(__file__).resolve().parents[2]
        chain = (
            repository / "phoenix" / "autonomy" / "structural_session_chain.py"
        ).read_text(encoding="utf-8")
        self.assertIn("autonomous_rc_design_candidate_v8_5_r8", chain)
        self.assertIn("rc_design_candidate.json", chain)
        self.assertIn("autonomous_rc_design_candidate_policy_v8_5_r8.json", chain)


if __name__ == "__main__":
    unittest.main()
