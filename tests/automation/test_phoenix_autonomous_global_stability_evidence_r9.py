from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.autonomous_global_stability_evidence_r9 import (
    CHECK_TYPES,
    build_autonomous_global_stability_evidence,
    derive_diaphragm_evidence,
    derive_topology_evidence,
    make_nlgeom_deck,
    run_real_second_order,
)
import phoenix.autonomy.autonomous_global_stability_evidence_r9 as r9


class R9Tests(unittest.TestCase):
    def setUp(self):
        self.model = {
            "nodes": [
                {"id":"N1","coords":[0,0,0]}, {"id":"N2","coords":[4,0,0]},
                {"id":"N3","coords":[0,0,3]}, {"id":"N4","coords":[4,0,3]},
                {"id":"N5","coords":[4,4,3]}, {"id":"N6","coords":[0,4,3]},
            ],
            "members": [
                {"id":"M1","node_i":"N1","node_j":"N3"}, {"id":"M2","node_i":"N2","node_j":"N4"},
                {"id":"M3","node_i":"N3","node_j":"N4"}, {"id":"M4","node_i":"N4","node_j":"N5"},
                {"id":"M5","node_i":"N5","node_j":"N6"}, {"id":"M6","node_i":"N6","node_j":"N3"},
            ],
            "shells": [{"id":"S1","node_ids":["N3","N4","N5","N6"]}],
            "supports": [{"id":"SUP1","node_id":"N1"},{"id":"SUP2","node_id":"N2"}],
        }
        self.arch = {"storeys":[{"storey_id":"L1","elevation_m":3.0,"height_m":3.0}]}

    def test_nlgeom_transform(self):
        deck = "*HEADING\n*STEP\n*STATIC\n*END STEP\n"
        value = make_nlgeom_deck(deck)
        self.assertIn("*STEP, NLGEOM", value)
        self.assertEqual(value.upper().count("NLGEOM"), 1)

    def test_topology_reaches_support(self):
        ev = derive_topology_evidence(self.model)
        self.assertTrue(ev["all_loaded_nodes_reach_support"])
        self.assertEqual(ev["unreachable_node_ids"], [])

    def test_diaphragm_connectivity(self):
        ev = derive_diaphragm_evidence(self.model, self.arch, 1e-6)
        self.assertTrue(ev["continuity_verified"])
        self.assertEqual(ev["assessed_storey_count"], 1)

    def test_test_mode_prevents_live_solver(self):
        old = os.environ.get("PHOENIX_TEST_MODE")
        os.environ["PHOENIX_TEST_MODE"] = "1"
        try:
            with tempfile.TemporaryDirectory() as td:
                ev = run_real_second_order(Path(td), Path(td)/"missing", Path(td)/"out")
            self.assertEqual(ev["status"], "SKIPPED_TEST_MODE")
        finally:
            if old is None: os.environ.pop("PHOENIX_TEST_MODE", None)
            else: os.environ["PHOENIX_TEST_MODE"] = old

    def test_incomplete_without_normative_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); policy = root/"policy.json"
            source = Path(__file__).resolve().parents[2]/"configs/phoenix/structural/autonomous_global_stability_evidence_policy_r9.json"
            policy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            old = os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result = build_autonomous_global_stability_evidence(repository=root, project_id="P", analytical_model=self.model, action_load_model={}, analysis_validation={"validation_state":"PASSED","synthesized_combination_results":{}}, member_verification={"verification_state":"MEMBER_VERIFICATION_CANDIDATE_PASSED","code_basis":{"jurisdiction":"TEST","standard_set":"EXPLICIT_TEST","edition":"1"}}, architecture=self.arch, candidates=[], v84_evidence_dir=root/"none", output_dir=root/"out", policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE", None)
                else: os.environ["PHOENIX_TEST_MODE"] = old
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(set(result["missing_check_types"]), set(CHECK_TYPES))
            self.assertFalse(result["safety"]["normative_limits_invented"])

    def test_complete_explicit_nine_check_contract_passes_to_v86_input(self):
        checks = [
            {"id":"A","check_type":"SECOND_ORDER_AMPLIFICATION","first_order_displacement_m":0.01,"second_order_displacement_m":0.011,"max_amplification_factor":1.2,"mandatory":True,"normative_reference":"TEST:1"},
            {"id":"B","check_type":"STOREY_STABILITY_INDEX","storey_id":"L1","gravity_load_kN":100,"storey_drift_m":0.001,"storey_shear_kN":20,"storey_height_m":3,"max_stability_index":0.1,"mandatory":True,"normative_reference":"TEST:2"},
            {"id":"C","check_type":"GLOBAL_BUCKLING_FACTOR","critical_load_factor":8,"minimum_critical_load_factor":5,"mandatory":True,"normative_reference":"TEST:3"},
            {"id":"D","check_type":"TORSIONAL_DRIFT_RATIO","storey_id":"L1","max_edge_drift_m":0.002,"average_edge_drift_m":0.0018,"max_torsional_drift_ratio":1.4,"mandatory":True,"normative_reference":"TEST:4"},
            {"id":"E","check_type":"SOFT_STOREY_STIFFNESS_RATIO","storey_id":"L1","storey_stiffness_kN_per_m":100,"reference_stiffness_kN_per_m":110,"minimum_ratio":0.7,"mandatory":True,"normative_reference":"TEST:5"},
            {"id":"F","check_type":"WEAK_STOREY_STRENGTH_RATIO","storey_id":"L1","storey_strength_kN":100,"reference_strength_kN":110,"minimum_ratio":0.8,"mandatory":True,"normative_reference":"TEST:6"},
            {"id":"G","check_type":"DIAPHRAGM_CONTINUITY","continuity_verified":True,"evidence_reference":"TEST:G","mandatory":True,"normative_reference":"TEST:7"},
            {"id":"H","check_type":"LOAD_PATH_CONTINUITY","loaded_nodes":["N3"],"load_path_edges":[{"from":"N3","to":"N1"},{"from":"N1","to":"SUP1"}],"mandatory":True,"normative_reference":"TEST:8"},
            {"id":"I","check_type":"ALTERNATE_LOAD_PATH_EVIDENCE","alternate_path_verified":True,"evidence_reference":"TEST:I","mandatory":True,"normative_reference":"TEST:9"},
        ]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); policy=root/"policy.json"
            source=Path(__file__).resolve().parents[2]/"configs/phoenix/structural/autonomous_global_stability_evidence_policy_r9.json"
            policy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            candidates=[("inputs/r9.json", {"r9_global_stability_evidence_input":{"stability_basis":{"jurisdiction":"TEST","standard_set":"EXPLICIT","edition":"1","source_reference":"TEST:BASIS","status":"ENGINEER_INPUT"},"explicit_stability_checks":checks}})]
            old=os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"]="1"
            try:
                result=build_autonomous_global_stability_evidence(repository=root,project_id="P",analytical_model=self.model,action_load_model={},analysis_validation={"validation_state":"PASSED","synthesized_combination_results":{}},member_verification={"verification_state":"MEMBER_VERIFICATION_CANDIDATE_PASSED"},architecture=self.arch,candidates=candidates,v84_evidence_dir=root/"none",output_dir=root/"out",policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE",None)
                else: os.environ["PHOENIX_TEST_MODE"]=old
            self.assertEqual(result["status"],"PASSED")
            self.assertEqual(len(result["global_stability_input"]["stability_checks"]),9)
            self.assertEqual(result["global_stability_input"]["release_policy"]["structural_model_release"],"LOCKED")

    def test_real_second_order_uses_native_node_displacements(self):
        import sys
        import types
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            case = root / "evidence" / "LC-WXP"
            case.mkdir(parents=True)
            (case / "phoenix_v8_4_case.inp").write_text("*HEADING\n*STEP\n*STATIC\n*END STEP\n", encoding="utf-8")
            (case / "phoenix_v8_4_case.dat").write_text("FIRST", encoding="utf-8")
            fake_exe = root / "ccx.exe"
            fake_exe.write_text("fake", encoding="utf-8")
            fake_module = types.ModuleType("phoenix.autonomy.autonomous_calculix_results_v8_4")
            def fake_parse(text):
                value = 0.01 if "FIRST" in text else 0.012
                return {"node_displacements": {1: [value, 0.0, 0.0]}}
            fake_module.parse_calculix_dat = fake_parse
            old_module = sys.modules.get(fake_module.__name__)
            sys.modules[fake_module.__name__] = fake_module
            old_mode = os.environ.pop("PHOENIX_TEST_MODE", None)
            def fake_run(command, cwd, **kwargs):
                job = command[1]
                (Path(cwd) / f"{job}.dat").write_text("SECOND", encoding="utf-8")
                return r9.subprocess.CompletedProcess(command, 0, "ok", "")
            try:
                with patch.object(r9, "_find_calculix", return_value=fake_exe), patch.object(r9.subprocess, "run", side_effect=fake_run):
                    result = run_real_second_order(root, root / "evidence", root / "out")
            finally:
                if old_mode is not None:
                    os.environ["PHOENIX_TEST_MODE"] = old_mode
                if old_module is None:
                    sys.modules.pop(fake_module.__name__, None)
                else:
                    sys.modules[fake_module.__name__] = old_module
            self.assertEqual(result["status"], "PASSED")
            self.assertAlmostEqual(result["worst_case"]["amplification_factor"], 1.2)

    def test_wrong_member_state_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); policy = root / "policy.json"
            source = Path(__file__).resolve().parents[2] / "configs/phoenix/structural/autonomous_global_stability_evidence_policy_r9.json"
            policy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            old = os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"] = "1"
            try:
                result = build_autonomous_global_stability_evidence(repository=root, project_id="P", analytical_model=self.model, action_load_model={}, analysis_validation={"synthesized_combination_results":{}}, member_verification={"verification_state":"MEMBER_VERIFICATION_FAILED_REVIEW_REQUIRED"}, architecture=self.arch, candidates=[], v84_evidence_dir=root/"none", output_dir=root/"out", policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE", None)
                else: os.environ["PHOENIX_TEST_MODE"] = old
            reasons = {x.get("reason") for x in result["blockers"]}
            self.assertIn("R9_MEMBER_VERIFICATION_CANDIDATE_PASSED_REQUIRED", reasons)

    def test_generic_example_is_rejected_and_better_input_ranked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); policy = root / "policy.json"
            source = Path(__file__).resolve().parents[2] / "configs/phoenix/structural/autonomous_global_stability_evidence_policy_r9.json"
            policy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            candidates = [
                ("configs/projects/generic_building_structural_global_stability_v8_6_0.json", {"r9_global_stability_evidence_input":{"stability_basis":{"jurisdiction":"BAD"}}}),
                ("inputs/structural/project_r9.json", {"r9_global_stability_evidence_input":{"stability_basis":{"jurisdiction":"TEST","standard_set":"EXPLICIT","edition":"1"}}}),
            ]
            old = os.environ.get("PHOENIX_TEST_MODE"); os.environ["PHOENIX_TEST_MODE"] = "1"
            try:
                result = build_autonomous_global_stability_evidence(repository=root, project_id="P", analytical_model=self.model, action_load_model={}, analysis_validation={"synthesized_combination_results":{}}, member_verification={"verification_state":"MEMBER_VERIFICATION_CANDIDATE_PASSED"}, architecture=self.arch, candidates=candidates, v84_evidence_dir=root/"none", output_dir=root/"out", policy_path=policy)
            finally:
                if old is None: os.environ.pop("PHOENIX_TEST_MODE", None)
                else: os.environ["PHOENIX_TEST_MODE"] = old
            self.assertEqual(result["source_states"]["r9_explicit_input_source"], "inputs/structural/project_r9.json")
            self.assertTrue(any(x.get("reason") == "R9_GENERIC_EXAMPLE_REJECTED" for x in result["warnings"]))

    def test_chain_patch_present(self):
        chain=(Path(__file__).resolve().parents[2]/"phoenix/autonomy/structural_session_chain.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_R9_GLOBAL_STABILITY_EVIDENCE_V1_0",chain)
        self.assertIn("_phoenix_build_r9_global_stability_evidence",chain)
        self.assertLess(chain.index("completed=\"8.5.0\""), chain.index("PHOENIX_R9_GLOBAL_STABILITY_EVIDENCE_V1_0"))


if __name__ == "__main__":
    unittest.main()
