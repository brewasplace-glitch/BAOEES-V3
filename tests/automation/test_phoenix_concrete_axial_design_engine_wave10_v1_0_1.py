import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters.concrete_axial_design import (
    ConcreteAxialDesignConfig,
    ConcreteAxialDesignError,
    ConcreteMemberDesignInput,
    create_concrete_axial_design_adapter,
)
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
from phoenix.adapters.reference_solver_execution import (
    ReferenceSolverExecutionConfig,
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


class PhoenixConcreteAxialDesignTests(unittest.TestCase):
    def build_solver_results(self, directory, force_n=100000.0):
        project_id = "PHX-W10-001"
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://wave10",
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
                        source_reference="report://wave10",
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
                nodes={
                    "N1": (0.0, 0.0, 0.0),
                    "N2": (2.0, 0.0, 0.0),
                },
                materials=(
                    StructuralMaterial(
                        material_id="C",
                        material_type="concrete",
                        grade="generic",
                        elastic_modulus_pa=30e9,
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="C1",
                        element_type="truss",
                        material_id="C",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="ULS",
                        load_type="dead",
                        description="Axial design action",
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
                        action_id="NED",
                        load_case_id="ULS",
                        node_id="N2",
                        components={"ux": force_n},
                    ),
                ),
            )
        )(
            project_id=project_id,
            engine_id="structural_solver",
            plan_fingerprint="contract-fp",
        )
        solver = create_reference_solver_execution_adapter(
            ReferenceSolverExecutionConfig(
                project_id=project_id,
                solver_contract_artifact=contract.outputs[0],
                output_directory=Path(directory) / "solver",
                section_areas_m2={"C1": 0.09},
            )
        )(
            project_id=project_id,
            engine_id="reference_solver",
            plan_fingerprint="solver-fp",
        )
        return solver.outputs[0]

    def member_input(self, **overrides):
        values = dict(
            element_id="C1",
            gross_area_m2=0.09,
            concrete_strength_pa=30e6,
            reinforcement_yield_strength_pa=500e6,
            minimum_reinforcement_ratio=0.002,
            maximum_reinforcement_ratio=0.04,
            concrete_resistance_factor=0.60,
            steel_resistance_factor=0.87,
            design_action_factor=1.00,
            bar_diameter_m=0.016,
            minimum_bar_count=4,
        )
        values.update(overrides)
        return ConcreteMemberDesignInput(**values)

    def test_tension_member_provides_reinforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=100000.0)
            adapter = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )
            result = adapter(
                project_id="PHX-W10-001",
                engine_id="concrete_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertEqual(member["action_mode"], "tension")
            self.assertGreaterEqual(member["required_bar_count"], 4)
            self.assertTrue(member["checks"]["capacity_passed"])
            self.assertTrue(artifact["summary"]["all_members_passed"])

    def test_compression_uses_concrete_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=-500000.0)
            result = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )(
                project_id="PHX-W10-001",
                engine_id="concrete_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertEqual(member["action_mode"], "compression")
            self.assertGreater(member["nominal_axial_capacity_n"], 0)
            self.assertTrue(member["checks"]["capacity_passed"])

    def test_excessive_reinforcement_ratio_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=20_000_000.0)
            result = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member_input(
                            maximum_reinforcement_ratio=0.005
                        ),
                    ),
                )
            )(
                project_id="PHX-W10-001",
                engine_id="concrete_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertFalse(
                artifact["member_results"][0]["checks"][
                    "maximum_reinforcement_ratio_passed"
                ]
            )
            self.assertFalse(artifact["summary"]["all_members_passed"])

    def test_unknown_element_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            adapter = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member_input(element_id="UNKNOWN"),
                    ),
                )
            )
            with self.assertRaises(ConcreteAxialDesignError):
                adapter(
                    project_id="PHX-W10-001",
                    engine_id="concrete_axial_design",
                    plan_fingerprint="design-fp",
                )

    def test_invalid_member_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            with self.assertRaises(ConcreteAxialDesignError):
                create_concrete_axial_design_adapter(
                    ConcreteAxialDesignConfig(
                        project_id="PHX-W10-001",
                        solver_results_artifact=results,
                        output_directory=Path(directory) / "design",
                        members=(
                            self.member_input(
                                minimum_reinforcement_ratio=0.05,
                                maximum_reinforcement_ratio=0.04,
                            ),
                        ),
                    )
                )

    def test_tampered_solver_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(self.build_solver_results(directory))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["active_load_case"] = "tampered"
            path.write_text(json.dumps(data), encoding="utf-8")
            adapter = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=path,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )
            with self.assertRaises(ConcreteAxialDesignError):
                adapter(
                    project_id="PHX-W10-001",
                    engine_id="concrete_axial_design",
                    plan_fingerprint="design-fp",
                )

    def test_named_code_compliance_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            result = create_concrete_axial_design_adapter(
                ConcreteAxialDesignConfig(
                    project_id="PHX-W10-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )(
                project_id="PHX-W10-001",
                engine_id="concrete_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertIsNone(
                artifact["design_basis"]["named_code_compliance"]
            )
            self.assertTrue(
                artifact["claims_policy"][
                    "named_code_compliance_not_claimed"
                ]
            )
            self.assertTrue(
                artifact["claims_policy"][
                    "competent_structural_engineer_review_required"
                ]
            )


if __name__ == "__main__":
    unittest.main()
