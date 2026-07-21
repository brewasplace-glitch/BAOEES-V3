import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters.foundation_bootstrap import (
    FoundationBootstrapConfig,
    create_foundation_bootstrap_adapter,
)
from phoenix.adapters.geotechnical_bootstrap import (
    GeotechnicalBootstrapConfig,
    SoilLayer,
    create_geotechnical_bootstrap_adapter,
)
from phoenix.adapters.gis_bootstrap import (
    GISBootstrapConfig,
    create_gis_bootstrap_adapter,
)
from phoenix.adapters.structural_analysis_bootstrap import (
    StructuralBootstrapConfig,
    StructuralElement,
    StructuralLoadCase,
    StructuralMaterial,
    create_structural_analysis_bootstrap_adapter,
)
from phoenix.adapters.structural_solver_contract import (
    BoundaryCondition,
    NodalAction,
    StructuralSolverContractConfig,
    StructuralSolverContractError,
    create_structural_solver_contract_adapter,
)


class PhoenixStructuralSolverContractTests(unittest.TestCase):
    def create_structural_artifact(
        self,
        directory,
        project_id="PHX-SOLVER-001",
    ):
        gis_adapter = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://solver-test",
                output_directory=Path(directory) / "gis",
            )
        )
        gis_result = gis_adapter(
            project_id=project_id,
            engine_id="gis",
            plan_fingerprint="gis-fp",
        )

        geo_adapter = create_geotechnical_bootstrap_adapter(
            GeotechnicalBootstrapConfig(
                project_id=project_id,
                gis_artifact=gis_result.outputs[0],
                output_directory=Path(directory) / "geo",
                soil_layers=(
                    SoilLayer(
                        layer_id="L1",
                        top_level_m=0.0,
                        bottom_level_m=-2.0,
                        classification="sand",
                        friction_angle_deg=30.0,
                        source_reference="report://ground",
                    ),
                ),
                allow_assumed_groundwater=True,
            )
        )
        geo_result = geo_adapter(
            project_id=project_id,
            engine_id="geotechnical",
            plan_fingerprint="geo-fp",
        )

        foundation_adapter = create_foundation_bootstrap_adapter(
            FoundationBootstrapConfig(
                project_id=project_id,
                geotechnical_artifact=geo_result.outputs[0],
                output_directory=Path(directory) / "foundation",
                use_phoenix_standard_strip_concept=True,
            )
        )
        foundation_result = foundation_adapter(
            project_id=project_id,
            engine_id="foundation",
            plan_fingerprint="foundation-fp",
        )

        structural_adapter = create_structural_analysis_bootstrap_adapter(
            StructuralBootstrapConfig(
                project_id=project_id,
                foundation_artifact=foundation_result.outputs[0],
                output_directory=Path(directory) / "structural",
                nodes={
                    "N1": (0.0, 0.0, 0.0),
                    "N2": (5.0, 0.0, 0.0),
                },
                materials=(
                    StructuralMaterial(
                        material_id="S355",
                        material_type="steel",
                        grade="S355",
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="B1",
                        element_type="beam",
                        material_id="S355",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Permanent action",
                    ),
                ),
            )
        )
        result = structural_adapter(
            project_id=project_id,
            engine_id="structural",
            plan_fingerprint="structural-fp",
        )
        return result.outputs[0]

    def valid_config(self, directory, artifact):
        return StructuralSolverContractConfig(
            project_id="PHX-SOLVER-001",
            structural_bootstrap_artifact=artifact,
            output_directory=Path(directory) / "solver",
            solver_name="CalculiX",
            solver_version="unverified",
            boundary_conditions=(
                BoundaryCondition(
                    boundary_id="SUP-N1",
                    node_id="N1",
                    restrained_dof=("ux", "uy", "uz", "rx", "ry", "rz"),
                ),
            ),
            nodal_actions=(
                NodalAction(
                    action_id="LOAD-N2-G",
                    load_case_id="G",
                    node_id="N2",
                    components={"uz": -10000.0},
                ),
            ),
        )

    def test_ready_contract_counts_degrees_of_freedom(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            adapter = create_structural_solver_contract_adapter(
                self.valid_config(directory, artifact)
            )
            result = adapter(
                project_id="PHX-SOLVER-001",
                engine_id="structural_solver",
                plan_fingerprint="solver-fp",
            )
            contract = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(contract["contract_status"], "solver_contract_ready")
            self.assertEqual(
                contract["degree_of_freedom_summary"]["total_dof"],
                12,
            )
            self.assertEqual(
                contract["degree_of_freedom_summary"]["restrained_dof"],
                6,
            )
            self.assertEqual(
                contract["degree_of_freedom_summary"]["free_dof"],
                6,
            )

    def test_unknown_boundary_node_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            adapter = create_structural_solver_contract_adapter(
                StructuralSolverContractConfig(
                    project_id="PHX-SOLVER-001",
                    structural_bootstrap_artifact=artifact,
                    output_directory=Path(directory) / "solver",
                    boundary_conditions=(
                        BoundaryCondition(
                            boundary_id="BAD",
                            node_id="N9",
                            restrained_dof=("ux",),
                        ),
                    ),
                )
            )
            with self.assertRaises(StructuralSolverContractError):
                adapter(
                    project_id="PHX-SOLVER-001",
                    engine_id="structural_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_unknown_action_load_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            adapter = create_structural_solver_contract_adapter(
                StructuralSolverContractConfig(
                    project_id="PHX-SOLVER-001",
                    structural_bootstrap_artifact=artifact,
                    output_directory=Path(directory) / "solver",
                    nodal_actions=(
                        NodalAction(
                            action_id="BAD",
                            load_case_id="Q",
                            node_id="N2",
                            components={"uz": -1.0},
                        ),
                    ),
                )
            )
            with self.assertRaises(StructuralSolverContractError):
                adapter(
                    project_id="PHX-SOLVER-001",
                    engine_id="structural_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_invalid_degree_of_freedom_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            with self.assertRaises(StructuralSolverContractError):
                create_structural_solver_contract_adapter(
                    StructuralSolverContractConfig(
                        project_id="PHX-SOLVER-001",
                        structural_bootstrap_artifact=artifact,
                        output_directory=Path(directory) / "solver",
                        boundary_conditions=(
                            BoundaryCondition(
                                boundary_id="BAD",
                                node_id="N1",
                                restrained_dof=("invalid",),
                            ),
                        ),
                    )
                )

    def test_tampered_structural_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(self.create_structural_artifact(directory))
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["analysis_engine"] = "tampered"
            path.write_text(json.dumps(artifact), encoding="utf-8")

            adapter = create_structural_solver_contract_adapter(
                StructuralSolverContractConfig(
                    project_id="PHX-SOLVER-001",
                    structural_bootstrap_artifact=path,
                    output_directory=Path(directory) / "solver",
                )
            )
            with self.assertRaises(StructuralSolverContractError):
                adapter(
                    project_id="PHX-SOLVER-001",
                    engine_id="structural_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_incomplete_contract_remains_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            adapter = create_structural_solver_contract_adapter(
                StructuralSolverContractConfig(
                    project_id="PHX-SOLVER-001",
                    structural_bootstrap_artifact=artifact,
                    output_directory=Path(directory) / "solver",
                )
            )
            result = adapter(
                project_id="PHX-SOLVER-001",
                engine_id="structural_solver",
                plan_fingerprint="solver-fp",
            )
            contract = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                contract["contract_status"],
                "solver_contract_incomplete",
            )
            self.assertIsNone(contract["solver_results"])

    def test_contract_disclaims_solver_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.create_structural_artifact(directory)
            adapter = create_structural_solver_contract_adapter(
                self.valid_config(directory, artifact)
            )
            result = adapter(
                project_id="PHX-SOLVER-001",
                engine_id="structural_solver",
                plan_fingerprint="solver-fp",
            )
            contract = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertTrue(
                contract["claims_policy"]["contract_is_not_solver_execution"]
            )
            self.assertEqual(
                contract["solver"]["execution_status"],
                "not_executed",
            )
            self.assertIsNone(contract["reactions"])
            self.assertIsNone(contract["member_forces"])


if __name__ == "__main__":
    unittest.main()
