from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.autonomous_solver_basis_v8_3 import (
    apply_solver_basis_to_analytical_model,
    build_autonomous_solver_basis,
    normalize_support_candidates_for_solver,
)


class AutonomousSolverBasisV83Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[2]
        self.model = {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
                {"id": "N3", "x": 4, "y": 0, "z": 3},
                {"id": "N4", "x": 4, "y": 4, "z": 3},
                {"id": "N5", "x": 0, "y": 4, "z": 3},
            ],
            "members": [
                {
                    "id": "M1",
                    "type": "column",
                    "node_i": "N1",
                    "node_j": "N2",
                    "material_candidate": "reinforced_concrete_candidate",
                    "section_candidate": "AUTO_PRELIMINARY_COLUMN",
                },
                {
                    "id": "M2",
                    "type": "beam",
                    "node_i": "N2",
                    "node_j": "N3",
                    "material_candidate": "reinforced_concrete_candidate",
                    "section_candidate": "AUTO_PRELIMINARY_BEAM",
                },
            ],
            "shells": [
                {
                    "id": "S1",
                    "type": "slab_panel",
                    "node_ids": ["N2", "N3", "N4", "N5"],
                    "material_candidate": "reinforced_concrete_candidate",
                    "thickness_candidate": "EXPLICIT_SOLVER_BASIS_REQUIRED",
                }
            ],
            "support_candidates": [
                {
                    "id": "SUP1",
                    "node_id": "N1",
                    "type": "PROVISIONAL_FIXED_BASE",
                    "approval_state": "CANDIDATE_ONLY",
                }
            ],
        }
        self.action = {
            "load_cases": [{"id": "G", "category": "permanent"}],
            "action_assignments": [
                {
                    "id": "A1",
                    "case_id": "G",
                    "kind": "self_weight",
                    "direction": "GRAVITY",
                    "factor": 1.0,
                    "target_element_ids": ["M1", "M2", "S1"],
                }
            ],
            "load_combinations": [],
        }

    def _workspace(self, tmp: str) -> Path:
        ws = Path(tmp)
        profile = ws / "results" / "session_adapters" / "architecture" / "structural_project_profile.json"
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text(
            json.dumps({"assumptions": {"minimum_loadbearing_wall_thickness_m": 0.2}}),
            encoding="utf-8",
        )
        return ws

    def test_relaxed_mode_generates_complete_reference_grounded_basis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=self.model,
                action_load_model=self.action,
                material_selection={},
            )
        self.assertEqual(result["status"], "PASSED")
        basis = result["structural_analysis_basis"]
        self.assertEqual(len(basis["element_assignments"]["by_id"]), 3)
        self.assertIn("MAT-RC-C20-25-REFERENCE", basis["solver_basis"]["materials"])
        mat = basis["solver_basis"]["materials"]["MAT-RC-C20-25-REFERENCE"]
        self.assertIsNone(mat["required_design_class"])
        self.assertFalse(mat["product_properties_verified"])
        self.assertFalse(basis["solver_basis"]["supplier_capability_may_define_design_class"])
        self.assertFalse(basis["execution_policy"]["allow_execution"])

    def test_strict_mode_does_not_use_reference_material_to_bypass_certification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "CERTIFIED_STRICT"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=self.model,
                action_load_model=self.action,
                material_selection={},
            )
        self.assertEqual(result["status"], "BLOCKED_INPUT")
        self.assertTrue(any(b["reason"] == "STRUCTURAL_SOLVER_REFERENCE_MATERIAL_PROPERTIES_REQUIRED" for b in result["blockers"]))

    def test_supplier_catalog_range_cannot_become_solver_material_properties(self) -> None:
        selection = {
            "selections": [
                {
                    "material_family": "structural_concrete",
                    "selected_product": {
                        "product_id": "P1",
                        "description": "Concrete C8/10 through C53/65",
                        "technical_properties": {},
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=self.model,
                action_load_model=self.action,
                material_selection=selection,
            )
        mat = result["structural_analysis_basis"]["solver_basis"]["materials"]["MAT-RC-C20-25-REFERENCE"]
        self.assertNotIn("C8/10", json.dumps(mat))
        self.assertIsNone(mat["required_design_class"])


    def test_shell_section_ids_are_material_family_specific(self) -> None:
        model = json.loads(json.dumps(self.model))
        model["shells"].append({
            "id": "S2",
            "type": "wall_panel",
            "node_ids": ["N1", "N2", "N3", "N4"],
            "material_candidate": "masonry_candidate",
            "thickness_candidate": 0.2,
        })
        model["shells"][0]["thickness_candidate"] = 0.2
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=model,
                action_load_model=self.action,
                material_selection={},
            )
        self.assertEqual(result["status"], "PASSED")
        by_id = result["structural_analysis_basis"]["element_assignments"]["by_id"]
        self.assertNotEqual(by_id["S1"]["section_id"], by_id["S2"]["section_id"])
        self.assertNotEqual(by_id["S1"]["material_id"], by_id["S2"]["material_id"])

    def test_unsupported_timber_properties_remain_a_real_blocker(self) -> None:
        model = json.loads(json.dumps(self.model))
        model["members"][0]["material_candidate"] = "timber_candidate"
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=model,
                action_load_model=self.action,
                material_selection={},
            )
        self.assertEqual(result["status"], "BLOCKED_INPUT")
        self.assertTrue(any(b.get("material_family") == "timber" for b in result["blockers"]))

    def test_assignment_application_and_support_normalization(self) -> None:
        solver_input = {
            "element_assignments": {
                "by_id": {
                    "M1": {"material_id": "MAT", "section_id": "SEC1"},
                    "M2": {"material_id": "MAT", "section_id": "SEC2"},
                    "S1": {"material_id": "MAT", "section_id": "SEC3"},
                },
                "by_type": {},
            }
        }
        model, missing = apply_solver_basis_to_analytical_model(self.model, solver_input)
        self.assertEqual(missing, [])
        self.assertEqual(model["members"][0]["material_id"], "MAT")
        normalized = normalize_support_candidates_for_solver(model)
        self.assertEqual(len(normalized["supports"]), 1)
        self.assertEqual(normalized["supports"][0]["dofs"], ["UX", "UY", "UZ", "RX", "RY", "RZ"])
        self.assertTrue(normalized["supports"][0]["review_required"])

    def test_generated_basis_is_accepted_by_real_v83_package_builder(self) -> None:
        runner_path = self.repo / "runners" / "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"
        if not runner_path.is_file():
            self.skipTest("v8.3 runner not present")
        spec = importlib.util.spec_from_file_location("phoenix_v83_runner_test", runner_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PHOENIX_MATERIAL_CERTIFICATION_MODE": "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"},
            clear=False,
        ):
            result = build_autonomous_solver_basis(
                repository=self.repo,
                workspace=self._workspace(tmp),
                project_id="TEST",
                analytical_model=self.model,
                action_load_model=self.action,
                material_selection={},
            )
        self.assertEqual(result["status"], "PASSED")
        analytical, missing = apply_solver_basis_to_analytical_model(
            self.model,
            result["structural_analysis_basis"],
        )
        self.assertEqual(missing, [])
        analytical = normalize_support_candidates_for_solver(analytical)
        payload = {
            "project_id": "TEST",
            "analytical_model": analytical,
            "solver_basis": result["structural_analysis_basis"]["solver_basis"],
            "action_load_model": self.action,
            "solver_adapters": result["structural_analysis_basis"]["solver_adapters"],
            "execution_policy": result["structural_analysis_basis"]["execution_policy"],
        }
        package = module.build_solver_package(payload)
        self.assertEqual(package["summary"]["member_count"], 2)
        self.assertEqual(package["summary"]["shell_count"], 1)
        self.assertIn("opensees", package["solver_files"])
        self.assertIn("calculix", package["solver_files"])
        self.assertEqual(package["release"]["structural_model_release"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
