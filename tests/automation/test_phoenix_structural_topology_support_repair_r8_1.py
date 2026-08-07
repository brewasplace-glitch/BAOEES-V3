from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from phoenix.autonomy.autonomous_structural_topology_support_repair_v8_1_r81 import (
    repair_structural_topology_for_solver,
)


def _load_runner(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R81TopologySupportRepairTests(unittest.TestCase):
    def test_connected_frame_passes(self):
        model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
                {"id": "N3", "x": 5, "y": 0, "z": 3},
                {"id": "N4", "x": 5, "y": 0, "z": 0},
            ],
            "members": [
                {"id": "M1", "type": "column", "node_i": "N1", "node_j": "N2"},
                {"id": "M2", "type": "beam", "node_i": "N2", "node_j": "N3"},
                {"id": "M3", "type": "column", "node_i": "N4", "node_j": "N3"},
            ],
            "shells": [],
            "supports": [
                {"id": "S1", "node_id": "N1", "source_support_type": "PROVISIONAL_FIXED_BASE"},
                {"id": "S2", "node_id": "N4", "source_support_type": "PROVISIONAL_FIXED_BASE"},
            ],
        }
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        self.assertEqual("PASSED", out["status"])
        self.assertEqual(
            0,
            out["register"]["final_model_summary"]["unresolved_member_endpoint_count"],
        )

    def test_upper_provisional_support_is_removed(self):
        model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
            ],
            "members": [
                {"id": "M1", "type": "column", "node_i": "N1", "node_j": "N2"}
            ],
            "shells": [],
            "supports": [
                {"id": "S1", "node_id": "N1", "source_support_type": "PROVISIONAL_FIXED_BASE"},
                {"id": "S2", "node_id": "N2", "source_support_type": "PROVISIONAL_FIXED_BASE"},
            ],
        }
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        self.assertEqual(["S1"], [s["id"] for s in out["analytical_model"]["supports"]])
        self.assertEqual(
            ["S2"],
            out["register"]["support_repair"]["removed_provisional_support_ids"],
        )

    def test_explicit_upper_support_is_preserved(self):
        model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
            ],
            "members": [
                {"id": "M1", "type": "column", "node_i": "N1", "node_j": "N2"}
            ],
            "shells": [],
            "supports": [
                {"id": "S1", "node_id": "N1", "source_support_type": "PROVISIONAL_FIXED_BASE"},
                {"id": "S2", "node_id": "N2", "type": "PROJECT_EXPLICIT_SUPPORT"},
            ],
        }
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        self.assertEqual(
            {"S1", "S2"},
            {s["id"] for s in out["analytical_model"]["supports"]},
        )

    def test_floating_member_blocks(self):
        model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
                {"id": "N3", "x": 5, "y": 2, "z": 3},
                {"id": "N4", "x": 8, "y": 2, "z": 3},
            ],
            "members": [
                {"id": "C1", "type": "column", "node_i": "N1", "node_j": "N2"},
                {"id": "B1", "type": "beam", "node_i": "N3", "node_j": "N4"},
            ],
            "shells": [],
            "supports": [
                {"id": "S1", "node_id": "N1", "source_support_type": "PROVISIONAL_FIXED_BASE"}
            ],
        }
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        self.assertEqual("BLOCKED", out["status"])
        reasons = {b["reason"] for b in out["blockers"]}
        self.assertIn("STRUCTURAL_LOAD_PATH_UNRESOLVED", reasons)
        self.assertIn("STRUCTURAL_UNANCHORED_COMPONENTS", reasons)

    def test_geometric_shell_edge_is_reported_not_auto_tied(self):
        model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
                {"id": "N3", "x": 0, "y": 2, "z": 3},
                {"id": "N4", "x": 5, "y": 2, "z": 3},
                {"id": "N5", "x": 0, "y": 4, "z": 3},
                {"id": "N6", "x": 5, "y": 4, "z": 3},
                {"id": "N7", "x": 5, "y": 0, "z": 3},
            ],
            "members": [
                {"id": "C1", "type": "column", "node_i": "N1", "node_j": "N2"},
                {"id": "B1", "type": "beam", "node_i": "N3", "node_j": "N4"},
            ],
            "shells": [
                {"id": "SH1", "node_ids": ["N2", "N7", "N6", "N5"]}
            ],
            "supports": [
                {"id": "S1", "node_id": "N1", "source_support_type": "PROVISIONAL_FIXED_BASE"}
            ],
        }
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        issues = out["register"]["unresolved_member_endpoints"]
        n3 = [x for x in issues if x.get("node_id") == "N3"][0]
        self.assertEqual("UNMESHED_SHELL_EDGE_INTERFACE", n3["reason"])
        self.assertEqual(["SH1"], n3["candidate_shell_edge_interfaces"])
        self.assertFalse(out["register"]["policy"]["automatic_shell_mesh_rewrite"])

    def test_safety_flags_remain_locked(self):
        model = {"nodes": [], "members": [], "shells": [], "supports": []}
        out = repair_structural_topology_for_solver(project_id="T", analytical_model=model)
        safety = out["register"]["safety"]
        self.assertFalse(safety["automatic_code_compliance_claim"])
        self.assertFalse(safety["automatic_structural_approval"])
        self.assertEqual("LOCKED", safety["production_release"])

    def test_v80_beam_derivation_uses_space_edges(self):
        runner = _load_runner(
            REPO
            / "runners"
            / "PROJECT_PHOENIX_architectural_to_structural_model_derivation_v8_0_0.py",
            "phx_v80_runner_r81_test",
        )
        arch = {
            "storeys": [
                {
                    "storey_id": "L1",
                    "spaces": [
                        {
                            "space_id": "R1",
                            "x_m": 0,
                            "y_m": 0,
                            "width_m": 6,
                            "depth_m": 4,
                        }
                    ],
                }
            ]
        }
        profile = {
            "assumptions": {
                "default_beam_material": "reinforced_concrete"
            }
        }
        beams = runner.beams_from_spaces(arch, profile)
        self.assertEqual(2, len(beams))
        endpoints = {
            (
                b["start_x_m"],
                b["start_y_m"],
                b["end_x_m"],
                b["end_y_m"],
            )
            for b in beams
        }
        self.assertEqual(
            {(0.0, 0.0, 6.0, 0.0), (0.0, 4.0, 6.0, 4.0)},
            endpoints,
        )

    def test_v81_generator_keeps_only_lowest_provisional_base_plane(self):
        runner = _load_runner(
            REPO
            / "runners"
            / "PROJECT_PHOENIX_structural_analytical_model_generation_v8_1_0.py",
            "phx_v81_runner_r81_test",
        )
        payload = {
            "structural_candidates": {
                "columns": [
                    {"id": "C1", "base": [0, 0, 0], "top": [0, 0, 3]},
                    {"id": "C2", "base": [0, 0, 3], "top": [0, 0, 6]},
                ]
            },
            "analytical_model_policy": {
                "auto_generate_column_base_support_candidates": True,
                "coordinate_tolerance_m": 1e-6,
            },
        }
        model = runner.build_analytical_model(payload)
        supports = model["support_candidates"]
        self.assertEqual(1, len(supports))
        self.assertEqual("N0001", supports[0]["node_id"])
        self.assertEqual(
            1,
            model["support_filter"]["removed_provisional_support_count"],
        )


if __name__ == "__main__":
    unittest.main()
