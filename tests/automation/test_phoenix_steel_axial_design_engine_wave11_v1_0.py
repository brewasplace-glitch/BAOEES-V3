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
from phoenix.adapters.reference_solver_execution import (
    ReferenceSolverExecutionConfig,
    create_reference_solver_execution_adapter,
)
from phoenix.adapters.steel_axial_design import (
    SteelAxialDesignConfig,
    SteelAxialDesignError,
    SteelMemberDesignInput,
    create_steel_axial_design_adapter,
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


class PhoenixSteelAxialDesignTests(unittest.TestCase):
    def build_solver_results(self, directory, force_n=100000.0):
        project_id = "PHX-W11-001"
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://wave11",
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
                        source_reference="report://wave11",
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
                        material_id="S",
                        material_type="steel",
                        grade="S355",
                        elastic_modulus_pa=200e9,
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="S1",
                        element_type="truss",
                        material_id="S",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Axial steel action",
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
                        load_case_id="G",
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
                section_areas_m2={"S1": 0.002},
            )
        )(
            project_id=project_id,
            engine_id="reference_solver",
            plan_fingerprint="solver-fp",
        )
        return solver.outputs[0]

    def member_input(self, **overrides):
        values = dict(
            element_id="S1",
            gross_area_m2=0.002,
            yield_strength_pa=355e6,
            ultimate_strength_pa=510e6,
            resistance_factor_yield=0.90,
            resistance_factor_ultimate=0.75,
            design_action_factor=1.00,
        )
        values.update(overrides)
        return SteelMemberDesignInput(**values)

    def test_tension_member_strength_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=100000.0)
            result = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )(
                project_id="PHX-W11-001",
                engine_id="steel_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertEqual(member["action_mode"], "tension")
            self.assertTrue(member["checks"]["axial_strength_passed"])
            self.assertTrue(artifact["summary"]["all_members_passed"])

    def test_overloaded_member_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=2_000_000.0)
            result = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )(
                project_id="PHX-W11-001",
                engine_id="steel_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertFalse(
                artifact["member_results"][0]["checks"][
                    "axial_strength_passed"
                ]
            )
            self.assertFalse(artifact["summary"]["all_members_passed"])

    def test_slenderness_screen(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=-100000.0)
            result = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member_input(
                            effective_length_m=3.0,
                            radius_of_gyration_m=0.02,
                            slenderness_limit=120.0,
                        ),
                    ),
                )
            )(
                project_id="PHX-W11-001",
                engine_id="steel_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertEqual(member["action_mode"], "compression")
            self.assertAlmostEqual(
                member["slenderness"]["value"],
                150.0,
            )
            self.assertFalse(
                member["checks"]["slenderness_screen_passed"]
            )
            self.assertFalse(
                member["slenderness"]["buckling_resistance_verified"]
            )

    def test_incomplete_slenderness_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            with self.assertRaises(SteelAxialDesignError):
                create_steel_axial_design_adapter(
                    SteelAxialDesignConfig(
                        project_id="PHX-W11-001",
                        solver_results_artifact=results,
                        output_directory=Path(directory) / "design",
                        members=(
                            self.member_input(
                                effective_length_m=3.0,
                            ),
                        ),
                    )
                )

    def test_unknown_element_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            adapter = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member_input(element_id="UNKNOWN"),
                    ),
                )
            )
            with self.assertRaises(SteelAxialDesignError):
                adapter(
                    project_id="PHX-W11-001",
                    engine_id="steel_axial_design",
                    plan_fingerprint="design-fp",
                )

    def test_tampered_solver_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(self.build_solver_results(directory))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["active_load_case"] = "tampered"
            path.write_text(json.dumps(data), encoding="utf-8")
            adapter = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=path,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )
            with self.assertRaises(SteelAxialDesignError):
                adapter(
                    project_id="PHX-W11-001",
                    engine_id="steel_axial_design",
                    plan_fingerprint="design-fp",
                )

    def test_named_code_and_buckling_are_not_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            result = create_steel_axial_design_adapter(
                SteelAxialDesignConfig(
                    project_id="PHX-W11-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member_input(),),
                )
            )(
                project_id="PHX-W11-001",
                engine_id="steel_axial_design",
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
                    "buckling_resistance_not_verified"
                ]
            )


if __name__ == "__main__":
    unittest.main()
