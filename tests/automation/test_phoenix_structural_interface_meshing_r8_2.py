from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.autonomous_structural_interface_meshing_v8_1_r82 import (
    repair_geometry_grounded_interfaces,
)
from phoenix.autonomy.autonomous_structural_topology_support_repair_v8_1_r81 import (
    repair_structural_topology_for_solver,
)


POLICY = {
    "geometry_tolerance_m": 1e-6,
    "interior_face_allowed_shell_types": ["slab_panel"],
    "require_unique_interior_shell_face": True,
}
R81_POLICY = {
    "coordinate_tolerance_m": 1e-6,
    "geometric_interface_detection_tolerance_m": 1e-6,
    "foundation_plane_tolerance_m": 1e-6,
}


def node(nid, x, y, z):
    return {"id": nid, "x": x, "y": y, "z": z}


def member(mid, ni, nj, kind="beam"):
    return {
        "id": mid,
        "type": kind,
        "node_i": ni,
        "node_j": nj,
        "material_id": "MAT",
        "section_id": "BEAM",
    }


def shell(sid, ids):
    return {
        "id": sid,
        "type": "slab_panel",
        "node_ids": ids,
        "material_id": "MAT",
        "section_id": "SHELL",
    }


def support(nid, provisional=True):
    return {
        "id": "SUP-" + nid,
        "node_id": nid,
        "type": "PROVISIONAL_FIXED_BASE" if provisional else "EXPLICIT_TEST_SUPPORT",
        "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"],
    }


class R82InterfaceMeshingTests(unittest.TestCase):
    def test_member_intersection_splits_existing_member_at_existing_node(self):
        model = {
            "nodes": [node("N1", 0, 0, 0), node("N2", 2, 0, 0), node("N3", 1, 0, 0), node("N4", 1, 0, 1)],
            "members": [member("M0001", "N1", "N2"), member("M0002", "N3", "N4", "column")],
            "shells": [],
            "supports": [support("N1"), support("N2", False), support("N4", False)],
        }
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        self.assertEqual(r81["status"], "BLOCKED")
        result = repair_geometry_grounded_interfaces(
            project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY
        )
        self.assertEqual(result["status"], "PASSED")
        children = result["register"]["member_parent_to_children"]["M0001"]
        self.assertEqual(len(children), 2)
        endpoints = {(m["node_i"], m["node_j"]) for m in result["analytical_model"]["members"] if m["id"] in children}
        self.assertIn(("N1", "N3"), endpoints)
        self.assertIn(("N3", "N2"), endpoints)

    def test_shell_edge_interface_is_meshed_with_existing_node(self):
        model = {
            "nodes": [node("N1", 0, 0, 0), node("N2", 2, 0, 0), node("N3", 2, 2, 0), node("N4", 0, 2, 0), node("N5", 1, 0, 0), node("N6", 1, 0, 1)],
            "members": [member("M0001", "N5", "N6", "column")],
            "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])],
            "supports": [support("N1"), support("N6", False)],
        }
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(result["status"], "PASSED")
        child_ids = result["register"]["shell_parent_to_children"]["S0001"]
        child_shells = [s for s in result["analytical_model"]["shells"] if s["id"] in child_ids]
        self.assertTrue(any("N5" in s["node_ids"] for s in child_shells))
        self.assertTrue(all(len(s["node_ids"]) == 3 for s in child_shells))

    def test_floating_endpoint_inside_slab_face_is_meshed(self):
        model = {
            "nodes": [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 2, 2, 0), node("N6", 2, 2, 1)],
            "members": [member("M0001", "N5", "N6", "column")],
            "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])],
            "supports": [support("N1"), support("N6", False)],
        }
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        self.assertEqual(r81["register"]["unresolved_member_endpoints"][0]["reason"], "STRUCTURAL_MEMBER_ENDPOINT_FLOATING")
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(result["status"], "PASSED")
        self.assertTrue(any(x["classification"] == "SHELL_FACE_INTERFACE" for x in result["register"]["classified_interfaces"]))

    def test_multiple_interior_points_on_same_quad_are_meshed_and_area_conserved(self):
        nodes = [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 1, 1, 0), node("N6", 1, 1, 1), node("N7", 3, 3, 0), node("N8", 3, 3, 1)]
        model = {"nodes": nodes, "members": [member("M0001", "N5", "N6", "column"), member("M0002", "N7", "N8", "column")], "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])], "supports": [support("N1"), support("N6", False), support("N8", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(result["status"], "PASSED")
        ev = result["register"]["shell_meshing_evidence"][0]
        self.assertAlmostEqual(ev["original_area_m2"], ev["meshed_area_m2"], places=9)
        used = {nid for s in result["analytical_model"]["shells"] for nid in s["node_ids"]}
        self.assertTrue({"N5", "N7"}.issubset(used))

    def test_self_weight_target_list_expands_after_member_split(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 2, 0, 0), node("N3", 1, 0, 0), node("N4", 1, 0, 1)], "members": [member("M0001", "N1", "N2"), member("M0002", "N3", "N4", "column")], "shells": [], "supports": [support("N1"), support("N2", False), support("N4", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        actions = {"load_cases": [{"id": "G"}], "action_assignments": [{"id": "SW", "case_id": "G", "kind": "self_weight", "target_element_ids": ["M0001", "M0002"]}]}
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model=actions, r8_1_register=r81["register"], policy=POLICY)
        children = result["register"]["member_parent_to_children"]["M0001"]
        targets = result["action_load_model"]["action_assignments"][0]["target_element_ids"]
        self.assertTrue(set(children).issubset(set(targets)))

    def test_area_action_is_cloned_to_shell_children(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 2, 2, 0), node("N6", 2, 2, 1)], "members": [member("M0001", "N5", "N6", "column")], "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])], "supports": [support("N1"), support("N6", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        actions = {"load_cases": [{"id": "Q"}], "action_assignments": [{"id": "Q-S1", "case_id": "Q", "kind": "area", "direction": "GLOBAL_Z", "magnitude": -2.0, "target_element_id": "S0001"}]}
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model=actions, r8_1_register=r81["register"], policy=POLICY)
        children = result["register"]["shell_parent_to_children"]["S0001"]
        cloned = [a for a in result["action_load_model"]["action_assignments"] if a["id"].startswith("Q-S1-R82-")]
        self.assertEqual({a["target_element_id"] for a in cloned}, set(children))
        self.assertTrue(all(a["magnitude"] == -2.0 for a in cloned))

    def test_unknown_element_target_action_fails_closed(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 2, 0, 0), node("N3", 1, 0, 0), node("N4", 1, 0, 1)], "members": [member("M0001", "N1", "N2"), member("M0002", "N3", "N4", "column")], "shells": [], "supports": [support("N1"), support("N2", False), support("N4", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        actions = {"load_cases": [{"id": "X"}], "action_assignments": [{"id": "X1", "case_id": "X", "kind": "mystery", "target_element_id": "M0001"}]}
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model=actions, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blockers"][0]["reason"], "STRUCTURAL_REPAIR_ACTION_REMAP_REQUIRED")

    def test_truly_floating_endpoint_remains_blocked(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 8, 8, 0), node("N6", 8, 8, 1)], "members": [member("M0001", "N5", "N6", "column")], "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])], "supports": [support("N1"), support("N6", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blockers"][0]["reason"], "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED")

    def test_no_support_column_or_constraint_invention(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 2, 2, 0), node("N6", 2, 2, 1)], "members": [member("M0001", "N5", "N6", "column")], "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])], "supports": [support("N1"), support("N6", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        result = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        self.assertEqual(len(result["analytical_model"]["supports"]), len(model["supports"]))
        self.assertEqual(sum(1 for m in result["analytical_model"]["members"] if m["type"] == "column"), 1)
        self.assertFalse(result["register"]["safety"]["automatic_solver_constraint_invention"])

    def test_post_r81_validation_passes_after_shell_face_mesh(self):
        model = {"nodes": [node("N1", 0, 0, 0), node("N2", 4, 0, 0), node("N3", 4, 4, 0), node("N4", 0, 4, 0), node("N5", 2, 2, 0), node("N6", 2, 2, 1)], "members": [member("M0001", "N5", "N6", "column")], "shells": [shell("S0001", ["N1", "N2", "N3", "N4"])], "supports": [support("N1"), support("N6", False)]}
        r81 = repair_structural_topology_for_solver(project_id="T", analytical_model=model, policy=R81_POLICY)
        r82 = repair_geometry_grounded_interfaces(project_id="T", analytical_model=r81["analytical_model"], action_load_model={"load_cases": [], "action_assignments": []}, r8_1_register=r81["register"], policy=POLICY)
        post = repair_structural_topology_for_solver(project_id="T", analytical_model=r82["analytical_model"], policy=R81_POLICY)
        self.assertEqual(post["status"], "PASSED")

    def test_v83_runner_contains_triangular_shell_support(self):
        repository = Path(__file__).resolve().parents[2]
        runner = (repository / "runners" / "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py").read_text(encoding="utf-8")
        self.assertIn("ShellDKGT", runner)
        self.assertIn('shell_element_type = "S3" if len(tags) == 3 else "S4"', runner)
        self.assertIn("3 or 4 nodes", runner)

    def test_chain_contains_r82_fallback_and_post_r81_gate(self):
        repository = Path(__file__).resolve().parents[2]
        chain = (repository / "phoenix" / "autonomy" / "structural_session_chain.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_R8_2_GEOMETRY_GROUNDED_INTERFACE_MESHING_V1_0", chain)
        self.assertIn("structural_interface_meshing_r8_2.json", chain)
        self.assertIn("structural_topology_support_repair_r8_1_post_r8_2.json", chain)
        self.assertIn("action_load_for_solver", chain)


if __name__ == "__main__":
    unittest.main()
