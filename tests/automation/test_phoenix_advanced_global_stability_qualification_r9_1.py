from __future__ import annotations
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy import advanced_global_stability_qualification_r9_1 as r91
from phoenix.autonomy.advanced_global_stability_qualification_r9_1 import (
    CHECK_TYPES,
    build_advanced_stability_qualification,
    derive_alternate_path_topology,
    derive_storey_mechanics,
    make_buckle_deck,
    parse_buckling_factors,
    run_real_global_buckling,
)


class R91Tests(unittest.TestCase):
    def setUp(self):
        self.model = {
            "nodes": [
                {"id":"N1","x":0,"y":0,"z":0},{"id":"N2","x":5,"y":0,"z":0},
                {"id":"N3","x":0,"y":0,"z":3},{"id":"N4","x":5,"y":0,"z":3},
                {"id":"N5","x":0,"y":0,"z":6},{"id":"N6","x":5,"y":0,"z":6},
            ],
            "members": [
                {"id":"M1","node_i":"N1","node_j":"N3"},{"id":"M2","node_i":"N2","node_j":"N4"},
                {"id":"M3","node_i":"N3","node_j":"N4"},{"id":"M4","node_i":"N3","node_j":"N5"},
                {"id":"M5","node_i":"N4","node_j":"N6"},{"id":"M6","node_i":"N5","node_j":"N6"},
            ],
            "shells": [],
            "supports": [{"id":"S1","node_id":"N1"},{"id":"S2","node_id":"N2"}],
        }
        self.arch = {"storeys":[{"storey_id":"L0","elevation_m":0},{"storey_id":"L1","elevation_m":3,"height_m":3},{"storey_id":"L2","elevation_m":6,"height_m":3}]}
        self.solver = {
            "equivalent_nodal_loads_kN": {
                "G": {"N3":[0,0,-50],"N4":[0,0,-50],"N5":[0,0,-40],"N6":[0,0,-40]},
                "WXP": {"N3":[5,0,0],"N4":[5,0,0],"N5":[3,0,0],"N6":[3,0,0]},
            },
            "load_combinations": [
                {"id":"SLS-WXP","terms":[{"case_id":"G","coefficient":1.0},{"case_id":"WXP","coefficient":1.0}]}
            ],
        }
        self.r9 = {
            "status":"BLOCKED",
            "derived_evidence": {
                "topology_load_path":{"loaded_node_count":4,"all_loaded_nodes_reach_support":True,"loaded_nodes":["N3","N4","N5","N6"],"load_path_edges":[{"from":"N3","to":"N1"}]},
                "diaphragm_connectivity":{"assessed_storey_count":2,"continuity_verified":True,"storeys":[]},
                "first_order_floor_response":{"status":"AVAILABLE","combinations":[
                    {"combination_id":"SLS-WXP","storey_id":"L1","mean_interstorey_drift_m":0.002,"max_nodal_interstorey_drift_m":0.0024,"average_nodal_interstorey_drift_m":0.002,"nodal_drift_spread_ratio":1.2},
                    {"combination_id":"SLS-WXP","storey_id":"L2","mean_interstorey_drift_m":0.003,"max_nodal_interstorey_drift_m":0.0033,"average_nodal_interstorey_drift_m":0.003,"nodal_drift_spread_ratio":1.1},
                ]},
                "second_order_calculix_nlgeom":{"status":"PASSED","worst_case":{"case_id":"LC-WXP","status":"PASSED","first_order_max_horizontal_displacement_m":0.01,"second_order_max_horizontal_displacement_m":0.011,"amplification_factor":1.1,"second_order_dat":"evidence/second.dat"}},
            },
            "required_input_template":{"r9_global_stability_evidence_input":{"stability_basis":{"jurisdiction":"TEST","standard_set":"EXPLICIT_TEST","edition":"1","source_reference":"TEST:BASIS"}}},
        }

    def policy(self, root: Path) -> Path:
        p = root/"policy.json"
        source = ROOT/"configs/phoenix/structural/advanced_global_stability_qualification_policy_r9_1.json"
        p.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return p

    def test_buckle_deck_replaces_static_procedure(self):
        deck = "*HEADING\n*STEP\n*STATIC\n*CLOAD\n1,1,10\n*END STEP\n"
        result = make_buckle_deck(deck)
        self.assertIn("*BUCKLE\n1\n*CLOAD", result)
        self.assertNotIn("*STATIC", result)

    def test_buckle_deck_replaces_static_control_line(self):
        deck = "*STEP\n*STATIC\n0.1,1.0\n*CLOAD\n1,1,10\n*END STEP\n"
        result = make_buckle_deck(deck, 2)
        self.assertIn("*BUCKLE\n2\n*CLOAD", result)
        self.assertNotIn("0.1,1.0", result)

    def test_buckling_factor_parser(self):
        text = "     B U C K L I N G   F A C T O R   O U T P U T\n\n MODE NO       BUCKLING\n                FACTOR\n\n      1   0.7250000E+01\n      2   0.2500000E+02\n"
        values = parse_buckling_factors(text)
        self.assertEqual(len(values), 2)
        self.assertAlmostEqual(values[0], 7.25)
        self.assertAlmostEqual(values[1], 25.0)

    def test_storey_mechanics_from_v83_nodal_ledger(self):
        result = derive_storey_mechanics(self.model, self.arch, self.solver, self.r9, 1e-6)
        rows = [r for r in result["rows"] if r["combination_id"] == "SLS-WXP"]
        self.assertEqual(len(rows), 2)
        l1 = next(r for r in rows if r["storey_id"] == "L1")
        self.assertGreater(l1["storey_shear_kN"], 0)
        self.assertGreater(l1["gravity_load_above_storey_kN"], 0)
        self.assertIsNotNone(l1["storey_stability_index_candidate"])
        self.assertIsNotNone(l1["secant_storey_stiffness_kN_per_m"])

    def test_alternate_path_is_topology_only(self):
        result = derive_alternate_path_topology(self.model)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertFalse(result["capacity_verified"])

    def test_partial_evidence_is_granular_not_zero_information(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=self.policy(root)
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_advanced_stability_qualification(repository=root,project_id="P",analytical_model=self.model,architecture=self.arch,solver_package=self.solver,r9_evidence=self.r9,candidates=[],v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertEqual(result["status"],"BLOCKED")
            self.assertGreater(result["summary"]["technical_evidence_available_count"],0)
            self.assertEqual(set(result["missing_check_types"]),set(CHECK_TYPES))
            self.assertEqual(result["qualification_register"]["SECOND_ORDER_AMPLIFICATION"]["qualification_state"],"LIMIT_REFERENCE_REQUIRED")
            self.assertEqual(result["qualification_register"]["WEAK_STOREY_STRENGTH_RATIO"]["qualification_state"],"ANALYSIS_REQUIRED")

    def test_buckling_live_runner_uses_real_dat_factor(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); case=root/"evidence"/"LC-WXP"; case.mkdir(parents=True)
            (case/"phoenix_v8_4_case.inp").write_text("*STEP\n*STATIC\n*CLOAD\n1,1,1\n*END STEP\n",encoding="utf-8")
            fake=root/"ccx.exe"; fake.write_text("fake",encoding="utf-8")
            old=os.environ.pop("PHOENIX_TEST_MODE",None)
            def fake_run(command,cwd,**kwargs):
                job=command[1]
                (Path(cwd)/(job+".dat")).write_text("BUCKLING FACTOR = 6.5\n",encoding="utf-8")
                return subprocess.CompletedProcess(command,0,"ok","")
            try:
                with patch.object(r91,"_find_calculix",return_value=fake), patch.object(r91.subprocess,"run",side_effect=fake_run):
                    result=run_real_global_buckling(root,root/"evidence",root/"out")
            finally:
                if old is not None: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertEqual(result["status"],"PASSED")
            self.assertAlmostEqual(result["governing_case"]["lowest_positive_buckling_factor"],6.5)

    def test_no_limits_are_invented(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=self.policy(root)
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_advanced_stability_qualification(repository=root,project_id="P",analytical_model=self.model,architecture=self.arch,solver_package=self.solver,r9_evidence=self.r9,candidates=[],v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertFalse(result["safety"]["normative_limits_invented"])
            limits=result["required_input_template"]["r9_1_stability_qualification_input"]["normative_limits"]
            for value in limits.values():
                self.assertIsNone(value.get("normative_reference"))

    def test_explicit_nine_checks_can_complete_v86_contract(self):
        checks = [
            {"id":"A","check_type":"SECOND_ORDER_AMPLIFICATION","first_order_displacement_m":0.01,"second_order_displacement_m":0.011,"max_amplification_factor":1.2,"mandatory":True,"normative_reference":"TEST:1"},
            {"id":"B","check_type":"STOREY_STABILITY_INDEX","storey_id":"L1","gravity_load_kN":100,"storey_drift_m":0.001,"storey_shear_kN":20,"storey_height_m":3,"max_stability_index":0.1,"mandatory":True,"normative_reference":"TEST:2"},
            {"id":"C","check_type":"GLOBAL_BUCKLING_FACTOR","critical_load_factor":8,"minimum_critical_load_factor":5,"mandatory":True,"normative_reference":"TEST:3"},
            {"id":"D","check_type":"TORSIONAL_DRIFT_RATIO","storey_id":"L1","max_edge_drift_m":0.002,"average_edge_drift_m":0.0018,"max_torsional_drift_ratio":1.4,"mandatory":True,"normative_reference":"TEST:4"},
            {"id":"E","check_type":"SOFT_STOREY_STIFFNESS_RATIO","storey_id":"L1","storey_stiffness_kN_per_m":100,"reference_stiffness_kN_per_m":110,"minimum_ratio":0.7,"mandatory":True,"normative_reference":"TEST:5"},
            {"id":"F","check_type":"WEAK_STOREY_STRENGTH_RATIO","storey_id":"L1","storey_strength_kN":100,"reference_strength_kN":110,"minimum_ratio":0.8,"mandatory":True,"normative_reference":"TEST:6"},
            {"id":"G","check_type":"DIAPHRAGM_CONTINUITY","continuity_verified":True,"evidence_reference":"TEST:G","mandatory":True,"normative_reference":"TEST:7"},
            {"id":"H","check_type":"LOAD_PATH_CONTINUITY","loaded_nodes":["N3"],"load_path_edges":[{"from":"N3","to":"N1"}],"mandatory":True,"normative_reference":"TEST:8"},
            {"id":"I","check_type":"ALTERNATE_LOAD_PATH_EVIDENCE","alternate_path_verified":True,"evidence_reference":"TEST:I","mandatory":True,"normative_reference":"TEST:9"},
        ]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=self.policy(root)
            candidate=("inputs/r91.json",{"r9_1_stability_qualification_input":{"stability_basis":{"jurisdiction":"TEST","standard_set":"EXPLICIT","edition":"1","source_reference":"TEST:BASIS"},"explicit_stability_checks":checks}})
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_advanced_stability_qualification(repository=root,project_id="P",analytical_model=self.model,architecture=self.arch,solver_package=self.solver,r9_evidence=self.r9,candidates=[candidate],v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertEqual(result["status"],"PASSED")
            self.assertEqual(len(result["global_stability_input"]["stability_checks"]),9)
            self.assertEqual(result["global_stability_input"]["release_policy"]["structural_model_release"],"LOCKED")

    def test_generic_example_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=self.policy(root)
            candidate=("configs/projects/generic_building_structural_global_stability_v8_6_0.json",{"r9_1_stability_qualification_input":{"stability_basis":{"jurisdiction":"BAD"}}})
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_advanced_stability_qualification(repository=root,project_id="P",analytical_model=self.model,architecture=self.arch,solver_package=self.solver,r9_evidence=self.r9,candidates=[candidate],v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertTrue(any(x.get("reason")=="R9_1_GENERIC_EXAMPLE_REJECTED" for x in result["warnings"]))

    def test_chain_patch_present(self):
        chain=(ROOT/"phoenix/autonomy/structural_session_chain.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_R9_1_ADVANCED_STABILITY_QUALIFICATION_V1_0",chain)
        self.assertIn("_phoenix_build_r9_1_stability_qualification",chain)
        self.assertGreater(chain.index("PHOENIX_R9_1_ADVANCED_STABILITY_QUALIFICATION_V1_0"),chain.index("PHOENIX_R9_GLOBAL_STABILITY_EVIDENCE_V1_0"))

    def test_release_safety_contract_is_locked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=self.policy(root)
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_advanced_stability_qualification(repository=root,project_id="P",analytical_model=self.model,architecture=self.arch,solver_package=self.solver,r9_evidence=self.r9,candidates=[],v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertEqual(result["safety"]["production_release"],"LOCKED")
            self.assertFalse(result["safety"]["automatic_structural_approval"])
            self.assertFalse(result["safety"]["automatic_code_compliance_claim"])


if __name__ == "__main__":
    unittest.main()
