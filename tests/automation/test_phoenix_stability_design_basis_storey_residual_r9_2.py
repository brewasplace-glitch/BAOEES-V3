from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.stability_design_basis_storey_residual_r9_2 import (
    assess_storey_model_completeness,
    augmented_architecture_from_completeness,
    build_stability_design_basis_storey_residual,
    corrected_torsional_response,
    expected_structural_levels,
)


class R92Tests(unittest.TestCase):
    def setUp(self):
        self.arch = {
            "storeys": [
                {"storey_id": "L0", "elevation_m": 0, "height_m": 3},
                {"storey_id": "L1", "elevation_m": 3, "height_m": 3},
            ]
        }
        self.complete_model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 5, "y": 0, "z": 0},
                {"id": "N3", "x": 0, "y": 0, "z": 3},
                {"id": "N4", "x": 5, "y": 0, "z": 3},
                {"id": "N5", "x": 0, "y": 0, "z": 6},
                {"id": "N6", "x": 5, "y": 0, "z": 6},
            ],
            "members": [
                {"id": "M1", "node_i": "N1", "node_j": "N3"},
                {"id": "M2", "node_i": "N2", "node_j": "N4"},
                {"id": "M3", "node_i": "N3", "node_j": "N5"},
                {"id": "M4", "node_i": "N4", "node_j": "N6"},
                {"id": "M5", "node_i": "N3", "node_j": "N4"},
                {"id": "M6", "node_i": "N5", "node_j": "N6"},
            ],
            "shells": [],
            "supports": [{"id": "S1", "node_id": "N1"}, {"id": "S2", "node_id": "N2"}],
        }
        self.incomplete_model = json.loads(json.dumps(self.complete_model))
        self.incomplete_model["nodes"] = [n for n in self.incomplete_model["nodes"] if n["z"] < 6]
        self.incomplete_model["members"] = [m for m in self.incomplete_model["members"] if m["id"] not in {"M3", "M4", "M6"}]
        self.solver = {
            "equivalent_nodal_loads_kN": {
                "G": {"N3": [0, 0, -50], "N4": [0, 0, -50], "N5": [0, 0, -40], "N6": [0, 0, -40]},
                "WXP": {"N3": [5, 0, 0], "N4": [5, 0, 0], "N5": [3, 0, 0], "N6": [3, 0, 0]},
            },
            "load_combinations": [
                {"id": "SLS-WXP", "terms": [{"case_id": "G", "coefficient": 1.0}, {"case_id": "WXP", "coefficient": 1.0}]}
            ],
        }
        disp = {
            "N1": {"UX": 0, "UY": 0},
            "N2": {"UX": 0, "UY": 0},
            "N3": {"UX": 0.002, "UY": 0},
            "N4": {"UX": 0.0022, "UY": 0},
            "N5": {"UX": 0.005, "UY": 0},
            "N6": {"UX": 0.0054, "UY": 0},
        }
        self.v84 = {"synthesized_combination_results": {"calculix": {"SLS-WXP": {"node_displacements": disp}}}}
        self.r9 = {"status": "BLOCKED", "derived_evidence": {}}
        self.r91 = {
            "status": "BLOCKED",
            "qualification_register": {
                "SECOND_ORDER_AMPLIFICATION": {"evidence": {"first_order_max_horizontal_displacement_m": 0.01, "second_order_max_horizontal_displacement_m": 0.0101, "amplification_factor": 1.01, "second_order_dat": "so.dat"}},
                "GLOBAL_BUCKLING_FACTOR": {"evidence": {"lowest_positive_buckling_factor": 8.0, "dat": "buck.dat"}},
                "STOREY_STABILITY_INDEX": {"evidence": {"storey_id": "L1", "gravity_load_above_storey_kN": 100, "mean_interstorey_drift_m": 0.002, "storey_shear_kN": 20, "storey_height_m": 3, "storey_stability_index_candidate": 0.0033}},
                "DIAPHRAGM_CONTINUITY": {"evidence": {"continuity_verified": True, "assessed_storey_count": 2}},
                "LOAD_PATH_CONTINUITY": {"evidence": {"all_loaded_nodes_reach_support": True, "loaded_nodes": ["N3"], "load_path_edges": [{"from": "N3", "to": "N1"}]}},
            },
            "required_input_template": {
                "r9_1_stability_qualification_input": {
                    "stability_basis": {"jurisdiction": "TEST", "standard_set": "EXPLICIT_TEST", "edition": "1", "source_reference": "TEST:BASIS"}
                }
            },
        }

    def policy(self, root: Path) -> Path:
        p = root / "policy.json"
        p.write_text((ROOT / "configs/phoenix/structural/stability_design_basis_storey_residual_policy_r9_2.json").read_text(encoding="utf-8"), encoding="utf-8")
        return p

    def build(self, model, candidates=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            return build_stability_design_basis_storey_residual(
                repository=root,
                project_id="P",
                analytical_model=model,
                architecture=self.arch,
                solver_package=self.solver,
                analysis_validation=self.v84,
                r9_evidence=self.r9,
                r91_qualification=self.r91,
                candidates=candidates or [],
                policy_path=self.policy(root),
            )

    def test_expected_levels_include_top_of_top_storey(self):
        value = expected_structural_levels(self.arch, 1e-6)
        self.assertEqual([x["elevation_m"] for x in value["levels"]], [0.0, 3.0, 6.0])
        self.assertTrue(value["top_boundary_known"])

    def test_missing_roof_level_blocks_storey_completeness(self):
        value = assess_storey_model_completeness(self.incomplete_model, self.arch, 1e-6)
        self.assertEqual(value["status"], "BLOCKED")
        self.assertEqual(value["reason"], "EXPECTED_STRUCTURAL_STOREY_LEVEL_MISSING")
        self.assertIn(6.0, value["missing_expected_levels_m"])

    def test_complete_two_storey_model_passes_completeness(self):
        value = assess_storey_model_completeness(self.complete_model, self.arch, 1e-6)
        self.assertEqual(value["status"], "PASSED")
        self.assertEqual(value["expected_storey_interval_count"], 2)
        self.assertTrue(all(x["vertical_load_path_candidate_present"] for x in value["intervals"]))

    def test_augmented_architecture_contains_roof_boundary(self):
        comp = assess_storey_model_completeness(self.complete_model, self.arch, 1e-6)
        aug = augmented_architecture_from_completeness(comp)
        self.assertEqual([x["elevation_m"] for x in aug["storeys"]], [0.0, 3.0, 6.0])

    def test_torsion_filter_excludes_base_near_zero_row(self):
        floor = {"combinations": [
            {"combination_id": "SLS-W", "storey_id": "L0", "elevation_m": 0, "node_count": 10, "mean_interstorey_drift_m": 1e-23, "average_nodal_interstorey_drift_m": 1e-23, "max_nodal_interstorey_drift_m": 8e-23, "nodal_drift_spread_ratio": 8.0},
            {"combination_id": "SLS-W", "storey_id": "L1", "elevation_m": 3, "node_count": 10, "mean_interstorey_drift_m": 0.002, "average_nodal_interstorey_drift_m": 0.002, "max_nodal_interstorey_drift_m": 0.0024, "nodal_drift_spread_ratio": 1.2},
        ]}
        comp = assess_storey_model_completeness(self.complete_model, self.arch, 1e-6)
        value = corrected_torsional_response(floor, comp, 1e-10)
        self.assertEqual(value["status"], "AVAILABLE")
        self.assertEqual(value["governing_candidate"]["storey_id"], "L1")
        self.assertEqual(value["excluded_row_count"], 1)

    def test_incomplete_model_returns_specific_blocker(self):
        result = self.build(self.incomplete_model)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blockers"][0]["reason"], "R9_2_STRUCTURAL_STOREY_MODEL_INCOMPLETE")

    def test_complete_model_derives_soft_storey_candidates(self):
        result = self.build(self.complete_model)
        self.assertEqual(result["storey_model_completeness"]["status"], "PASSED")
        self.assertTrue(result["residual_storey_mechanics"]["adjacent_storey_stiffness_ratio_candidates"])
        self.assertNotEqual(result["qualification_register"]["SOFT_STOREY_STIFFNESS_RATIO"]["qualification_state"], "ANALYSIS_REQUIRED")

    def test_weak_storey_strength_not_invented(self):
        result = self.build(self.complete_model)
        self.assertFalse(result["safety"]["storey_strength_invented"])
        self.assertEqual(result["qualification_register"]["WEAK_STOREY_STRENGTH_RATIO"]["qualification_state"], "ANALYSIS_REQUIRED")

    def test_alternate_path_capacity_not_invented(self):
        result = self.build(self.complete_model)
        self.assertFalse(result["safety"]["alternate_path_capacity_invented"])
        self.assertEqual(result["qualification_register"]["ALTERNATE_LOAD_PATH_EVIDENCE"]["qualification_state"], "ANALYSIS_REQUIRED")

    def test_required_template_has_no_invented_limits(self):
        result = self.build(self.complete_model)
        limits = result["required_input_template"]["r9_2_stability_design_basis_input"]["normative_limits"]
        for value in limits.values():
            self.assertIsNone(value.get("normative_reference"))
        self.assertFalse(result["safety"]["normative_limits_invented"])

    def test_explicit_strength_and_alternate_evidence_are_traceable_only(self):
        candidate = ("inputs/r92.json", {"r9_2_stability_design_basis_input": {
            "storey_strength_evidence": [{"storey_id": "L1", "storey_strength_kN": 100, "reference_strength_kN": 120, "evidence_reference": "ENG:STRENGTH", "methodology_reference": "ENG:METHOD"}],
            "alternate_path_capacity_evidence": {"alternate_path_verified": True, "evidence_reference": "ENG:ALP", "methodology_reference": "ENG:REMOVAL"},
        }})
        result = self.build(self.complete_model, [candidate])
        self.assertEqual(result["residual_storey_strength"]["status"], "AVAILABLE")
        self.assertEqual(result["residual_alternate_path_capacity"]["status"], "AVAILABLE")

    def test_generic_example_input_is_rejected(self):
        candidate = ("configs/projects/generic_building_structural_global_stability_v8_6_0.json", {"r9_2_stability_design_basis_input": {"stability_basis": {"jurisdiction": "BAD"}}})
        result = self.build(self.complete_model, [candidate])
        self.assertTrue(any(x.get("reason") == "R9_2_GENERIC_EXAMPLE_REJECTED" for x in result["warnings"]))

    def test_explicit_nine_checks_can_complete_v86_contract(self):
        checks = [
            {"id": "A", "check_type": "SECOND_ORDER_AMPLIFICATION", "first_order_displacement_m": 0.01, "second_order_displacement_m": 0.011, "max_amplification_factor": 1.2, "mandatory": True, "normative_reference": "TEST:1"},
            {"id": "B", "check_type": "STOREY_STABILITY_INDEX", "storey_id": "L1", "gravity_load_kN": 100, "storey_drift_m": 0.001, "storey_shear_kN": 20, "storey_height_m": 3, "max_stability_index": 0.1, "mandatory": True, "normative_reference": "TEST:2"},
            {"id": "C", "check_type": "GLOBAL_BUCKLING_FACTOR", "critical_load_factor": 8, "minimum_critical_load_factor": 5, "mandatory": True, "normative_reference": "TEST:3"},
            {"id": "D", "check_type": "TORSIONAL_DRIFT_RATIO", "storey_id": "L1", "max_edge_drift_m": 0.002, "average_edge_drift_m": 0.0018, "max_torsional_drift_ratio": 1.4, "mandatory": True, "normative_reference": "TEST:4"},
            {"id": "E", "check_type": "SOFT_STOREY_STIFFNESS_RATIO", "storey_id": "L1", "storey_stiffness_kN_per_m": 100, "reference_stiffness_kN_per_m": 110, "minimum_ratio": 0.7, "mandatory": True, "normative_reference": "TEST:5"},
            {"id": "F", "check_type": "WEAK_STOREY_STRENGTH_RATIO", "storey_id": "L1", "storey_strength_kN": 100, "reference_strength_kN": 110, "minimum_ratio": 0.8, "mandatory": True, "normative_reference": "TEST:6"},
            {"id": "G", "check_type": "DIAPHRAGM_CONTINUITY", "continuity_verified": True, "evidence_reference": "TEST:G", "mandatory": True, "normative_reference": "TEST:7"},
            {"id": "H", "check_type": "LOAD_PATH_CONTINUITY", "loaded_nodes": ["N3"], "load_path_edges": [{"from": "N3", "to": "N1"}], "mandatory": True, "normative_reference": "TEST:8"},
            {"id": "I", "check_type": "ALTERNATE_LOAD_PATH_EVIDENCE", "alternate_path_verified": True, "evidence_reference": "TEST:I", "mandatory": True, "normative_reference": "TEST:9"},
        ]
        candidate = ("inputs/r92.json", {"r9_2_stability_design_basis_input": {"stability_basis": {"jurisdiction": "TEST", "source_reference": "TEST:BASIS"}, "explicit_stability_checks": checks}})
        result = self.build(self.complete_model, [candidate])
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(len(result["global_stability_input"]["stability_checks"]), 9)
        self.assertEqual(result["global_stability_input"]["release_policy"]["structural_model_release"], "LOCKED")

    def test_chain_patch_present(self):
        chain = (ROOT / "phoenix/autonomy/structural_session_chain.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_R9_2_STABILITY_DESIGN_BASIS_STOREY_COMPLETENESS_RESIDUAL_V1_0", chain)
        self.assertIn("_phoenix_build_r9_2_stability_design_basis_storey_residual", chain)
        self.assertGreater(chain.index("PHOENIX_R9_2_STABILITY_DESIGN_BASIS_STOREY_COMPLETENESS_RESIDUAL_V1_0"), chain.index("PHOENIX_R9_1_ADVANCED_STABILITY_QUALIFICATION_V1_0"))

    def test_release_safety_contract_locked(self):
        result = self.build(self.complete_model)
        self.assertEqual(result["safety"]["production_release"], "LOCKED")
        self.assertFalse(result["safety"]["automatic_structural_approval"])
        self.assertFalse(result["safety"]["automatic_code_compliance_claim"])


if __name__ == "__main__":
    unittest.main()
