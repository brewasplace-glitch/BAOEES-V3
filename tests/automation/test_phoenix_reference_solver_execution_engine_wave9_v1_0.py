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
from phoenix.adapters.gis_bootstrap import GISBootstrapConfig, create_gis_bootstrap_adapter
from phoenix.adapters.reference_solver_execution import (
    ReferenceSolverExecutionConfig,
    ReferenceSolverExecutionError,
    create_reference_solver_execution_adapter,
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
    create_structural_solver_contract_adapter,
)


class PhoenixReferenceSolverExecutionTests(unittest.TestCase):
    def build_contract(self, directory, element_type="truss", load_component="ux"):
        project_id = "PHX-W9-001"
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://wave9",
                output_directory=Path(directory) / "gis",
            )
        )(
            project_id=project_id,
            engine_id="gis",
            plan_fingerprint="gis-fp",
        )
        geo = create_geotechnical_bootstrap_adapter(
            GeotechnicalBootstrapConfig(
                project_id=project_id,
                gis_artifact=gis.outputs[0],
                output_directory=Path(directory) / "geo",
                soil_layers=(
                    SoilLayer(
                        layer_id="L1",
                        top_level_m=0.0,
                        bottom_level_m=-2.0,
                        classification="sand",
                        friction_angle_deg=30.0,
                        source_reference="report://wave9",
                    ),
                ),
                allow_assumed_groundwater=True,
            )
        )(
            project_id=project_id,
            engine_id="geotechnical",
            plan_fingerprint="geo-fp",
        )
        foundation = create_foundation_bootstrap_adapter(
            FoundationBootstrapConfig(
                project_id=project_id,
                geotechnical_artifact=geo.outputs[0],
                output_directory=Path(directory) / "foundation",
                use_phoenix_standard_strip_concept=True,
            )
        )(
            project_id=project_id,
            engine_id="foundation",
            plan_fingerprint="foundation-fp",
        )
        structural = create_structural_analysis_bootstrap_adapter(
            StructuralBootstrapConfig(
                project_id=project_id,
                foundation_artifact=foundation.outputs[0],
                output_directory=Path(directory) / "structural",
                nodes={"N1": (0.0, 0.0, 0.0), "N2": (2.0, 0.0, 0.0)},
                materials=(
                    StructuralMaterial(
                        material_id="S",
                        material_type="steel",
                        grade="S355",
                        elastic_modulus_pa=200e9,
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="E1",
                        element_type=element_type,
                        material_id="S",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Axial test action",
                    ),
                ),
            )
        )(
            project_id=project_id,
            engine_id="structural",
            plan_fingerprint="structural-fp",
        )
        contract = create_structural_solver_contract_adapter(
            StructuralSolverContractConfig(
                project_id=project_id,
                structural_bootstrap_artifact=structural.outputs[0],
                output_directory=Path(directory) / "contract",
                solver_name="Phoenix Reference Axial Solver",
                boundary_conditions=(
                    BoundaryCondition(
                        boundary_id="SUP",
                        node_id="N1",
                        restrained_dof=("ux",),
                    ),
                ),
                nodal_actions=(
                    NodalAction(
                        action_id="P",
                        load_case_id="G",
                        node_id="N2",
                        components={load_component: 100000.0},
                    ),
                ),
            )
        )(
            project_id=project_id,
            engine_id="structural_solver",
            plan_fingerprint="contract-fp",
        )
        return contract.outputs[0]

    def test_axial_bar_solution(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory)
            result = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )(
                project_id="PHX-W9-001",
                engine_id="reference_solver",
                plan_fingerprint="solver-fp",
            )
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertAlmostEqual(
                artifact["nodal_displacements_m"]["N2"]["ux"],
                0.0001,
                places=12,
            )
            self.assertAlmostEqual(
                artifact["element_results"][0]["axial_force_n"],
                100000.0,
                places=6,
            )
            self.assertAlmostEqual(
                artifact["nodal_reactions_n"]["N1"]["fx"],
                -100000.0,
                places=6,
            )

    def test_global_equilibrium_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory)
            result = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )(
                project_id="PHX-W9-001",
                engine_id="reference_solver",
                plan_fingerprint="solver-fp",
            )
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertTrue(
                artifact["verification"]["global_equilibrium_passed"]
            )
            self.assertLessEqual(
                artifact["verification"]["global_equilibrium_residual_n"],
                1e-6,
            )

    def test_unsupported_beam_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory, element_type="beam")
            adapter = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )
            with self.assertRaises(ReferenceSolverExecutionError):
                adapter(
                    project_id="PHX-W9-001",
                    engine_id="reference_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_unsupported_load_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory, load_component="uz")
            adapter = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )
            with self.assertRaises(ReferenceSolverExecutionError):
                adapter(
                    project_id="PHX-W9-001",
                    engine_id="reference_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_missing_section_area_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory)
            with self.assertRaises(ReferenceSolverExecutionError):
                create_reference_solver_execution_adapter(
                    ReferenceSolverExecutionConfig(
                        project_id="PHX-W9-001",
                        solver_contract_artifact=contract,
                        output_directory=Path(directory) / "results",
                        section_areas_m2={},
                    )
                )

    def test_tampered_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(self.build_contract(directory))
            data = json.loads(contract.read_text(encoding="utf-8"))
            data["analysis_type"] = "tampered"
            contract.write_text(json.dumps(data), encoding="utf-8")
            adapter = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )
            with self.assertRaises(ReferenceSolverExecutionError):
                adapter(
                    project_id="PHX-W9-001",
                    engine_id="reference_solver",
                    plan_fingerprint="solver-fp",
                )

    def test_claims_policy_remains_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.build_contract(directory)
            result = create_reference_solver_execution_adapter(
                ReferenceSolverExecutionConfig(
                    project_id="PHX-W9-001",
                    solver_contract_artifact=contract,
                    output_directory=Path(directory) / "results",
                    section_areas_m2={"E1": 0.01},
                )
            )(
                project_id="PHX-W9-001",
                engine_id="reference_solver",
                plan_fingerprint="solver-fp",
            )
            artifact = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertTrue(
                artifact["claims_policy"][
                    "results_apply_only_to_supported_reference_scope"
                ]
            )
            self.assertTrue(
                artifact["claims_policy"]["competent_engineer_review_required"]
            )


if __name__ == "__main__":
    unittest.main()
