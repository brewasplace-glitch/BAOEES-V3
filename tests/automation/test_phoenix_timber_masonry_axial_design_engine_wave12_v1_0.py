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
from phoenix.adapters.timber_masonry_axial_design import (
    TimberMasonryAxialDesignConfig,
    TimberMasonryAxialDesignError,
    TimberMasonryMemberDesignInput,
    create_timber_masonry_axial_design_adapter,
)


class PhoenixTimberMasonryAxialDesignTests(unittest.TestCase):
    def build_solver_results(self, directory, force_n=100000.0):
        project_id = "PHX-W12-001"
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://wave12",
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
                        source_reference="report://wave12",
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
                        material_id="T",
                        material_type="timber",
                        grade="generic",
                        elastic_modulus_pa=11e9,
                    ),
                ),
                elements=(
                    StructuralElement(
                        element_id="M1",
                        element_type="truss",
                        material_id="T",
                        node_ids=("N1", "N2"),
                    ),
                ),
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Wave 12 axial action",
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
                section_areas_m2={"M1": 0.02},
            )
        )(
            project_id=project_id,
            engine_id="reference_solver",
            plan_fingerprint="solver-fp",
        )
        return solver.outputs[0]

    def member(self, material_system="timber", **overrides):
        values = dict(
            element_id="M1",
            material_system=material_system,
            gross_area_m2=0.02,
            characteristic_compressive_strength_pa=24e6,
            characteristic_tensile_strength_pa=14e6,
            compression_resistance_factor=0.60,
            tension_resistance_factor=0.60,
            modification_factor=0.80,
        )
        values.update(overrides)
        return TimberMasonryMemberDesignInput(**values)

    def test_timber_tension_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=100000.0)
            result = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member("timber"),),
                )
            )(
                project_id="PHX-W12-001",
                engine_id="timber_masonry_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertEqual(member["material_system"], "timber")
            self.assertEqual(member["action_mode"], "tension")
            self.assertTrue(member["checks"]["member_passed"])

    def test_masonry_compression_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=-100000.0)
            result = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member(
                            "masonry",
                            characteristic_compressive_strength_pa=12e6,
                            characteristic_tensile_strength_pa=0.4e6,
                        ),
                    ),
                )
            )(
                project_id="PHX-W12-001",
                engine_id="timber_masonry_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                artifact["summary"]["masonry_member_count"],
                1,
            )
            self.assertTrue(
                artifact["member_results"][0]["checks"][
                    "axial_strength_passed"
                ]
            )

    def test_overloaded_member_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=2_000_000.0)
            result = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member("timber"),),
                )
            )(
                project_id="PHX-W12-001",
                engine_id="timber_masonry_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertFalse(artifact["summary"]["all_members_passed"])

    def test_slenderness_screen_fails_without_claiming_stability(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory, force_n=-100000.0)
            result = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(
                        self.member(
                            "timber",
                            effective_length_m=3.0,
                            least_dimension_m=0.08,
                            slenderness_limit=30.0,
                        ),
                    ),
                )
            )(
                project_id="PHX-W12-001",
                engine_id="timber_masonry_axial_design",
                plan_fingerprint="design-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            member = artifact["member_results"][0]
            self.assertAlmostEqual(member["slenderness"]["value"], 37.5)
            self.assertFalse(
                member["checks"]["slenderness_screen_passed"]
            )
            self.assertFalse(
                member["slenderness"]["stability_resistance_verified"]
            )

    def test_incomplete_slenderness_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            with self.assertRaises(TimberMasonryAxialDesignError):
                create_timber_masonry_axial_design_adapter(
                    TimberMasonryAxialDesignConfig(
                        project_id="PHX-W12-001",
                        solver_results_artifact=results,
                        output_directory=Path(directory) / "design",
                        members=(
                            self.member(
                                "timber",
                                effective_length_m=3.0,
                            ),
                        ),
                    )
                )

    def test_tampered_solver_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(self.build_solver_results(directory))
            data = json.loads(path.read_text(encoding="utf-8"))
            data["active_load_case"] = "tampered"
            path.write_text(json.dumps(data), encoding="utf-8")
            adapter = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=path,
                    output_directory=Path(directory) / "design",
                    members=(self.member("timber"),),
                )
            )
            with self.assertRaises(TimberMasonryAxialDesignError):
                adapter(
                    project_id="PHX-W12-001",
                    engine_id="timber_masonry_axial_design",
                    plan_fingerprint="design-fp",
                )

    def test_named_code_compliance_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.build_solver_results(directory)
            result = create_timber_masonry_axial_design_adapter(
                TimberMasonryAxialDesignConfig(
                    project_id="PHX-W12-001",
                    solver_results_artifact=results,
                    output_directory=Path(directory) / "design",
                    members=(self.member("timber"),),
                )
            )(
                project_id="PHX-W12-001",
                engine_id="timber_masonry_axial_design",
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


if __name__ == "__main__":
    unittest.main()
