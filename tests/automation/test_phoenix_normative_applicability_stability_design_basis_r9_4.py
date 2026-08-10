from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.normative_applicability_stability_design_basis_r9_4 import (
    build_normative_applicability_stability_design_basis,
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


def make_r93():
    evidence = {
        "SECOND_ORDER_AMPLIFICATION": {
            "first_order_max_horizontal_displacement_m": 1.0,
            "second_order_max_horizontal_displacement_m": 1.01,
        },
        "GLOBAL_BUCKLING_FACTOR": {"lowest_positive_buckling_factor": 10.0},
        "STOREY_STABILITY_INDEX": {
            "storey_id": "S1",
            "gravity_load_above_storey_kN": 100.0,
            "mean_interstorey_drift_m": 0.01,
            "storey_shear_kN": 20.0,
            "storey_height_m": 3.0,
        },
        "TORSIONAL_DRIFT_RATIO": {
            "storey_id": "S2",
            "max_nodal_interstorey_drift_m": 0.002,
            "average_nodal_interstorey_drift_m": 0.001,
        },
        "SOFT_STOREY_STIFFNESS_RATIO": {
            "storey_id": "S2",
            "storey_stiffness_kN_per_m": 100.0,
            "reference_stiffness_kN_per_m": 200.0,
        },
        "DIAPHRAGM_CONTINUITY": {"continuity_verified": True},
        "LOAD_PATH_CONTINUITY": {
            "all_loaded_nodes_reach_support": True,
            "loaded_nodes": ["N1"],
            "load_path_edges": [{"from": "N1", "to": "SUP1"}],
        },
        "WEAK_STOREY_STRENGTH_RATIO": {
            "governing_candidate": {
                "storey_id": "S2",
                "storey_strength_proxy_kN": 50.0,
                "reference_strength_proxy_kN": 100.0,
            }
        },
        "ALTERNATE_LOAD_PATH_EVIDENCE": {
            "status": "AVAILABLE",
            "minimum_residual_capacity_proxy_ratio": 0.9,
            "alternate_path_verified": False,
        },
    }
    return {
        "status": "BLOCKED",
        "technical_evidence_available_for": list(CHECKS),
        "analysis_required_for": [],
        "qualification_register": {
            key: {"evidence": evidence[key]} for key in CHECKS
        },
        "required_input_template": {
            "r9_3_stability_design_basis_input": {
                "stability_basis": {
                    "project_jurisdiction": "Suriname / Paramaribo",
                    "engineering_design_methodology": "Eurocode 2 based",
                    "legal_applicability_in_suriname": "NOT_VERIFIED",
                }
            }
        },
    }


class R94Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(__file__).resolve().parents[2]
        self.policy = (
            root
            / "configs"
            / "phoenix"
            / "structural"
            / "normative_applicability_stability_design_basis_policy_r9_4.json"
        )
        self.registry = (
            root
            / "configs"
            / "phoenix"
            / "structural"
            / "normative_applicability_public_source_registry_r9_4.json"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, candidates=None, r93=None):
        return build_normative_applicability_stability_design_basis(
            project_id="P",
            r93_qualification=r93 or make_r93(),
            candidates=candidates or [],
            policy_path=self.policy,
            source_registry_path=self.registry,
        )

    def full_input(self):
        criteria = {
            "SECOND_ORDER_AMPLIFICATION": {"max_amplification_factor": 1.1},
            "GLOBAL_BUCKLING_FACTOR": {"minimum_critical_load_factor": 2.0},
            "STOREY_STABILITY_INDEX": {"max_stability_index": 0.1},
            "TORSIONAL_DRIFT_RATIO": {"max_torsional_drift_ratio": 3.0},
            "SOFT_STOREY_STIFFNESS_RATIO": {"minimum_ratio": 0.4},
            "WEAK_STOREY_STRENGTH_RATIO": {"minimum_ratio": 0.4},
            "ALTERNATE_LOAD_PATH_EVIDENCE": {
                "minimum_residual_capacity_proxy_ratio": 0.8
            },
            "DIAPHRAGM_CONTINUITY": {},
            "LOAD_PATH_CONTINUITY": {},
        }
        rows = {}
        for check in CHECKS:
            rows[check] = {
                "applicability": "SUPPLEMENTAL_ENGINEERING_POLICY",
                "methodology_accepted": True,
                "methodology_acceptance_reference": "TEST-POLICY",
                "reference_type": "PROJECT_ENGINEERING_POLICY",
                "reference": "TEST-POLICY",
                "acceptance_criteria": criteria[check],
            }
        rows["ALTERNATE_LOAD_PATH_EVIDENCE"]["alternate_path_verified"] = True
        rows["ALTERNATE_LOAD_PATH_EVIDENCE"][
            "independent_engineering_evidence_reference"
        ] = "REVIEWED-ALT-PATH-TEST"
        return {
            "r9_4_normative_applicability_input": {
                "jurisdictional_basis": {
                    "legal_applicability_in_suriname": "NOT_VERIFIED"
                },
                "seismic_applicability": {
                    "status": "ENGINEERING_POLICY_APPLIED",
                    "reference_type": "PROJECT_ENGINEERING_POLICY",
                    "reference": "TEST-SEISMIC-POLICY",
                },
                "checks": rows,
            }
        }

    def test_01_r93_technical_completion_detected(self):
        result = self._run()
        self.assertTrue(result["technical_completion"]["complete"])
        self.assertEqual(result["summary"]["technical_evidence_available_count"], 9)

    def test_02_default_blocks_on_qualification_only(self):
        result = self._run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["summary"]["analysis_required_check_type_count"], 0)

    def test_03_default_does_not_invent_limits(self):
        self.assertFalse(self._run()["safety"]["normative_limits_invented"])

    def test_04_public_registry_does_not_complete_checks(self):
        self.assertEqual(self._run()["summary"]["qualified_for_v8_6_count"], 0)

    def test_05_seismic_style_requires_decision(self):
        result = self._run()
        missing = result["applicability_register"]["TORSIONAL_DRIFT_RATIO"][
            "missing_requirements"
        ]
        self.assertIn("seismic_applicability_decision", missing)

    def test_06_not_applicable_does_not_auto_waive(self):
        data = self.full_input()
        data["r9_4_normative_applicability_input"]["checks"][
            "TORSIONAL_DRIFT_RATIO"
        ]["applicability"] = "NOT_APPLICABLE"
        result = self._run([("p.json", data)])
        self.assertEqual(
            result["applicability_register"]["TORSIONAL_DRIFT_RATIO"][
                "qualification_state"
            ],
            "NOT_APPLICABLE_REVIEW_REQUIRED",
        )

    def test_07_generic_example_rejected(self):
        result = self._run(
            [
                (
                    "configs/projects/generic_building_structural_global_stability_v8_6_0.json",
                    self.full_input(),
                )
            ]
        )
        self.assertTrue(result["warnings"])

    def test_08_full_explicit_project_policy_can_build_v86_input(self):
        result = self._run([("project.json", self.full_input())])
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["qualified_for_v8_6_count"], 9)

    def test_09_full_input_preserves_legal_status(self):
        result = self._run([("project.json", self.full_input())])
        self.assertEqual(
            result["project_stability_design_basis"][
                "legal_applicability_in_suriname"
            ],
            "NOT_VERIFIED",
        )

    def test_10_alternate_path_requires_independent_reviewed_evidence(self):
        data = self.full_input()
        data["r9_4_normative_applicability_input"]["checks"][
            "ALTERNATE_LOAD_PATH_EVIDENCE"
        ]["independent_engineering_evidence_reference"] = None
        result = self._run([("p.json", data)])
        self.assertNotIn(
            "ALTERNATE_LOAD_PATH_EVIDENCE",
            result["qualified_check_types"],
        )

    def test_11_weak_storey_screening_remains_candidate(self):
        result = self._run([("p.json", self.full_input())])
        row = next(
            x
            for x in result["global_stability_input"]["stability_checks"]
            if x["check_type"] == "WEAK_STOREY_STRENGTH_RATIO"
        )
        self.assertIn("CANDIDATE", row["candidate_methodology_status"])

    def test_12_source_registry_has_no_exact_limits(self):
        result = self._run()
        self.assertTrue(
            all(
                not row.get("exact_limits_embedded")
                for row in result["public_source_registry"]["sources"].values()
            )
        )

    def test_13_r93_incomplete_blocks_before_qualification(self):
        r93 = make_r93()
        r93["analysis_required_for"] = ["WEAK_STOREY_STRENGTH_RATIO"]
        result = self._run(r93=r93)
        self.assertEqual(
            result["blockers"][0]["reason"],
            "R9_4_R9_3_TECHNICAL_COMPLETION_REQUIRED",
        )

    def test_14_reference_type_required(self):
        data = self.full_input()
        data["r9_4_normative_applicability_input"]["checks"][
            "GLOBAL_BUCKLING_FACTOR"
        ]["reference_type"] = "PUBLIC_METADATA_ONLY"
        result = self._run([("p.json", data)])
        self.assertNotIn("GLOBAL_BUCKLING_FACTOR", result["qualified_check_types"])

    def test_15_production_release_locked(self):
        self.assertEqual(self._run()["safety"]["production_release"], "LOCKED")

    def test_16_no_code_compliance_claim(self):
        self.assertFalse(self._run()["safety"]["automatic_code_compliance_claim"])

    def test_17_required_template_has_all_nine_checks(self):
        result = self._run()
        checks = result["required_input_template"][
            "r9_4_normative_applicability_input"
        ]["checks"]
        self.assertEqual(len(checks), 9)

    def test_18_deterministic_repeat(self):
        self.assertEqual(
            self._run()["applicability_register"],
            self._run()["applicability_register"],
        )


if __name__ == "__main__":
    unittest.main()
