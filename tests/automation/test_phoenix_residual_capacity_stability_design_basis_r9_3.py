from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.residual_capacity_stability_design_basis_r9_3 import (
    build_residual_capacity_stability_design_basis,
    derive_alternate_path_capacity_screening,
    derive_weak_storey_capacity_screening,
)


def _r92():
    return {
        "status": "BLOCKED",
        "storey_model_completeness": {
            "status": "PASSED",
            "intervals": [
                {
                    "interval_id": "L0->L1",
                    "lower_elevation_m": 0.0,
                    "upper_elevation_m": 3.0,
                    "height_m": 3.0,
                    "vertical_member_ids": ["M1", "M2"],
                },
                {
                    "interval_id": "L1->TOP",
                    "lower_elevation_m": 3.0,
                    "upper_elevation_m": 6.0,
                    "height_m": 3.0,
                    "vertical_member_ids": ["M3", "M4"],
                },
            ],
        },
        "qualification_register": {
            "SECOND_ORDER_AMPLIFICATION": {
                "qualification_state": "LIMIT_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {
                    "first_order_max_horizontal_displacement_m": 1.0,
                    "second_order_max_horizontal_displacement_m": 1.01,
                    "second_order_dat": "a.dat",
                },
            },
            "GLOBAL_BUCKLING_FACTOR": {
                "qualification_state": "LIMIT_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {"lowest_positive_buckling_factor": 10.0, "dat": "b.dat"},
            },
            "STOREY_STABILITY_INDEX": {
                "qualification_state": "LIMIT_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {
                    "storey_id": "L1",
                    "gravity_load_above_storey_kN": 100.0,
                    "mean_interstorey_drift_m": 0.001,
                    "storey_shear_kN": 10.0,
                    "storey_height_m": 3.0,
                },
            },
            "TORSIONAL_DRIFT_RATIO": {
                "qualification_state": "LIMIT_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {
                    "storey_id": "TOP",
                    "max_nodal_interstorey_drift_m": 0.002,
                    "average_nodal_interstorey_drift_m": 0.001,
                },
            },
            "SOFT_STOREY_STIFFNESS_RATIO": {
                "qualification_state": "REFERENCE_METHOD_AND_LIMIT_REQUIRED",
                "missing_requirements": [],
                "evidence": {
                    "storey_id": "TOP",
                    "storey_stiffness_kN_per_m": 100.0,
                    "reference_stiffness_kN_per_m": 200.0,
                },
            },
            "DIAPHRAGM_CONTINUITY": {
                "qualification_state": "ENGINEERING_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {"continuity_verified": True},
            },
            "LOAD_PATH_CONTINUITY": {
                "qualification_state": "ENGINEERING_REFERENCE_REQUIRED",
                "missing_requirements": [],
                "evidence": {
                    "all_loaded_nodes_reach_support": True,
                    "loaded_nodes": ["N1"],
                    "load_path_edges": [{"from": "N1", "to": "S1"}],
                },
            },
        },
        "required_input_template": {
            "r9_2_stability_design_basis_input": {
                "stability_basis": {
                    "jurisdiction": "TEST",
                    "methodology": "ENGINEERING CANDIDATE",
                }
            }
        },
    }


def _r91():
    return {
        "status": "BLOCKED",
        "qualification_register": {
            "ALTERNATE_LOAD_PATH_EVIDENCE": {
                "evidence": {
                    "cases": [
                        {"removed_member_id": "M1", "all_loaded_nodes_reach_support": True},
                        {"removed_member_id": "M2", "all_loaded_nodes_reach_support": True},
                        {"removed_member_id": "M3", "all_loaded_nodes_reach_support": True},
                        {"removed_member_id": "M4", "all_loaded_nodes_reach_support": True},
                    ]
                }
            }
        },
    }


def _rc():
    rows = []
    for mid, shear, moment in (
        ("M1", 100.0, 90.0),
        ("M2", 100.0, 90.0),
        ("M3", 60.0, 45.0),
        ("M4", 60.0, 45.0),
    ):
        rows.append({
            "member_id": mid,
            "member_role": "COLUMN",
            "section_id": f"S-{mid}",
            "material_id": "MAT-RC",
            "candidate_status": "ENGINEERING_CANDIDATE_REQUIRING_REVIEW",
            "normative_parameter_status": "INTERIM_NON_NDP_CANDIDATE_ASSUMPTIONS",
            "screening_resistances": {
                "VY_Rd_kN": shear,
                "VZ_Rd_kN": shear,
                "MY_Rd_kNm": moment,
                "MZ_Rd_kNm": moment,
            },
        })
    return {"status": "CANDIDATE_GENERATED", "member_count": 4, "candidate_members": rows}


def _member_verification():
    return {"verification_state": "MEMBER_VERIFICATION_CANDIDATE_PASSED"}


class R93Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.policy = Path(self.tmp.name) / "policy.json"
        self.policy.write_text(json.dumps({
            "required_check_types": [
                "ALTERNATE_LOAD_PATH_EVIDENCE",
                "DIAPHRAGM_CONTINUITY",
                "GLOBAL_BUCKLING_FACTOR",
                "LOAD_PATH_CONTINUITY",
                "SECOND_ORDER_AMPLIFICATION",
                "SOFT_STOREY_STIFFNESS_RATIO",
                "STOREY_STABILITY_INDEX",
                "TORSIONAL_DRIFT_RATIO",
                "WEAK_STOREY_STRENGTH_RATIO",
            ],
            "v8_6_policy": {
                "acceptable_member_verification_states": ["MEMBER_VERIFICATION_CANDIDATE_PASSED"],
                "require_normative_reference": True,
                "mandatory_check_types": [
                    "ALTERNATE_LOAD_PATH_EVIDENCE",
                    "DIAPHRAGM_CONTINUITY",
                    "GLOBAL_BUCKLING_FACTOR",
                    "LOAD_PATH_CONTINUITY",
                    "SECOND_ORDER_AMPLIFICATION",
                    "SOFT_STOREY_STIFFNESS_RATIO",
                    "STOREY_STABILITY_INDEX",
                    "TORSIONAL_DRIFT_RATIO",
                    "WEAK_STOREY_STRENGTH_RATIO",
                ],
                "pass_tolerance": 1e-12,
            },
            "forbidden_project_evidence_paths": [
                "configs/projects/generic_building_structural_global_stability_v8_6_0.json"
            ],
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, candidates=None):
        return build_residual_capacity_stability_design_basis(
            project_id="P",
            r91_qualification=_r91(),
            r92_qualification=_r92(),
            rc_design_candidate=_rc(),
            member_verification=_member_verification(),
            candidates=candidates or [],
            policy_path=self.policy,
        )

    def test_01_weak_storey_screening_available(self):
        result = derive_weak_storey_capacity_screening(_r92(), _rc())
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertIsNotNone(result["governing_candidate"])

    def test_02_weak_ratio_is_traceable(self):
        result = derive_weak_storey_capacity_screening(_r92(), _rc())
        self.assertAlmostEqual(result["governing_candidate"]["ratio"], 0.5)

    def test_03_missing_candidate_member_blocks_weak_screening(self):
        rc = _rc()
        rc["candidate_members"] = rc["candidate_members"][:-1]
        result = derive_weak_storey_capacity_screening(_r92(), rc)
        self.assertEqual(result["status"], "ANALYSIS_REQUIRED")

    def test_04_alternate_screening_available(self):
        weak = derive_weak_storey_capacity_screening(_r92(), _rc())
        result = derive_alternate_path_capacity_screening(_r91(), weak)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertFalse(result["alternate_path_verified"])

    def test_05_alternate_screening_requires_topology(self):
        weak = derive_weak_storey_capacity_screening(_r92(), _rc())
        r91 = _r91()
        r91["qualification_register"]["ALTERNATE_LOAD_PATH_EVIDENCE"]["evidence"]["cases"] = []
        result = derive_alternate_path_capacity_screening(r91, weak)
        self.assertEqual(result["status"], "ANALYSIS_REQUIRED")

    def test_06_default_run_has_nine_technical_evidence_types(self):
        result = self._run()
        self.assertEqual(result["summary"]["technical_evidence_available_count"], 9)
        self.assertEqual(result["summary"]["analysis_required_check_type_count"], 0)

    def test_07_default_run_does_not_invent_limits(self):
        result = self._run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["safety"]["normative_limits_invented"])

    def test_08_generic_example_input_is_rejected(self):
        generic = {
            "r9_3_stability_design_basis_input": {
                "normative_limits": {
                    "GLOBAL_BUCKLING_FACTOR": {
                        "minimum_critical_load_factor": 1.0,
                        "normative_reference": "EXAMPLE",
                    }
                }
            }
        }
        result = self._run([
            ("configs/projects/generic_building_structural_global_stability_v8_6_0.json", generic)
        ])
        self.assertTrue(result["warnings"])

    def test_09_direct_input_precedence_is_supported(self):
        direct = {"r9_3_stability_design_basis_input": {"stability_basis": {"jurisdiction": "DIRECT"}}}
        inherited = {"r9_2_stability_design_basis_input": {"stability_basis": {"jurisdiction": "OLD"}}}
        result = self._run([("a.json", inherited), ("b.json", direct)])
        self.assertEqual(
            result["required_input_template"]["r9_3_stability_design_basis_input"]["stability_basis"]["jurisdiction"],
            "DIRECT",
        )

    def test_10_explicit_nine_checks_can_pass_without_engine_invention(self):
        check_types = [
            ("ALTERNATE_LOAD_PATH_EVIDENCE", {"alternate_path_verified": True, "evidence_reference": "E"}),
            ("DIAPHRAGM_CONTINUITY", {"continuity_verified": True}),
            ("GLOBAL_BUCKLING_FACTOR", {"critical_load_factor": 10.0, "minimum_critical_load_factor": 2.0}),
            ("LOAD_PATH_CONTINUITY", {"loaded_nodes": ["N1"], "load_path_edges": [{"from": "N1", "to": "S1"}]}),
            ("SECOND_ORDER_AMPLIFICATION", {"first_order_displacement_m": 1.0, "second_order_displacement_m": 1.01, "max_amplification_factor": 1.1}),
            ("SOFT_STOREY_STIFFNESS_RATIO", {"storey_id": "S2", "storey_stiffness_kN_per_m": 100.0, "reference_stiffness_kN_per_m": 200.0, "minimum_ratio": 0.4}),
            ("STOREY_STABILITY_INDEX", {"storey_id": "S1", "gravity_load_kN": 100.0, "storey_drift_m": 0.01, "storey_shear_kN": 20.0, "storey_height_m": 3.0, "max_stability_index": 0.1}),
            ("TORSIONAL_DRIFT_RATIO", {"storey_id": "S1", "max_edge_drift_m": 0.002, "average_edge_drift_m": 0.001, "max_torsional_drift_ratio": 3.0}),
            ("WEAK_STOREY_STRENGTH_RATIO", {"storey_id": "S2", "storey_strength_kN": 50.0, "reference_strength_kN": 100.0, "minimum_ratio": 0.4}),
        ]
        rows = []
        for ctype, extra in check_types:
            rows.append({
                "id": ctype,
                "check_type": ctype,
                "normative_reference": "TRACEABLE-REF",
                "mandatory": True,
                **extra,
            })
        data = {
            "r9_3_stability_design_basis_input": {
                "stability_basis": {"jurisdiction": "TEST"},
                "explicit_stability_checks": rows,
            }
        }
        result = self._run([("project.json", data)])
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(len(result["completed_check_types"]), 9)

    def test_11_weak_proxy_is_not_promoted_without_acceptance(self):
        result = self._run()
        self.assertNotIn("WEAK_STOREY_STRENGTH_RATIO", result["completed_check_types"])

    def test_12_alternate_proxy_is_not_promoted_without_acceptance(self):
        result = self._run()
        self.assertNotIn("ALTERNATE_LOAD_PATH_EVIDENCE", result["completed_check_types"])

    def test_13_release_is_locked(self):
        result = self._run()
        self.assertEqual(result["safety"]["production_release"], "LOCKED")

    def test_14_no_load_redistribution_is_fabricated(self):
        result = self._run()
        self.assertFalse(result["safety"]["load_redistribution_after_member_removal_invented"])

    def test_15_template_keeps_method_acceptance_false(self):
        result = self._run()
        acceptance = result["required_input_template"]["r9_3_stability_design_basis_input"]["engineering_scope_acceptance"]
        self.assertFalse(acceptance["rc_screening_storey_capacity_proxy_method"])
        self.assertFalse(acceptance["topology_capacity_reserve_screening_as_alternate_path_method"])

    def test_16_deterministic_repeat(self):
        a = self._run()
        b = self._run()
        self.assertEqual(a["weak_storey_capacity_screening"], b["weak_storey_capacity_screening"])


if __name__ == "__main__":
    unittest.main()
