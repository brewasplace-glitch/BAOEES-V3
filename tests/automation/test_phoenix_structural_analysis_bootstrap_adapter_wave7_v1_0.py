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
    StructuralBootstrapError,
    StructuralElement,
    StructuralLoadCase,
    StructuralLoadCombination,
    StructuralMaterial,
    create_structural_analysis_bootstrap_adapter,
)


class PhoenixStructuralAnalysisBootstrapTests(unittest.TestCase):
    def create_foundation_artifact(self, directory, project_id="PHX-STR-001"):
        gis = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://structural-test",
                output_directory=Path(directory) / "gis",
            )
        )
        gis_result = gis(
            project_id=project_id,
            engine_id="gis",
            plan_fingerprint="gis-fp",
        )

        geotechnical = create_geotechnical_bootstrap_adapter(
            GeotechnicalBootstrapConfig(
                project_id=project_id,
                gis_artifact=gis_result.outputs[0],
                output_directory=Path(directory) / "geotechnical",
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
        geo_result = geotechnical(
            project_id=project_id,
            engine_id="geotechnical",
            plan_fingerprint="geo-fp",
        )

        foundation = create_foundation_bootstrap_adapter(
            FoundationBootstrapConfig(
                project_id=project_id,
                geotechnical_artifact=geo_result.outputs[0],
                output_directory=Path(directory) / "foundation",
                use_phoenix_standard_strip_concept=True,
            )
        )
        foundation_result = foundation(
            project_id=project_id,
            engine_id="foundation",
            plan_fingerprint="foundation-fp",
        )
        return foundation_result.outputs[0]

    def valid_config(self, directory, artifact):
        return StructuralBootstrapConfig(
            project_id="PHX-STR-001",
            foundation_artifact=artifact,
            output_directory=Path(directory) / "structural",
            analysis_engine="unassigned",
            nodes={
                "N1": (0.0, 0.0, 0.0),
                "N2": (5.0, 0.0, 0.0),
            },
            materials=(
                StructuralMaterial(
                    material_id="S355",
                    material_type="steel",
                    grade="S355",
                    elastic_modulus_pa=210e9,
                    density_kg_m3=7850.0,
                    source_reference="project://material-register",
                ),
            ),
            elements=(
                StructuralElement(
                    element_id="B1",
                    element_type="beam",
                    material_id="S355",
                    node_ids=("N1", "N2"),
                    section_reference="section://unverified",
                ),
            ),
            load_cases=(
                StructuralLoadCase(
                    load_case_id="G",
                    load_type="dead",
                    description="Permanent actions",
                ),
                StructuralLoadCase(
                    load_case_id="Q",
                    load_type="imposed",
                    description="Imposed actions",
                ),
            ),
            load_combinations=(
                StructuralLoadCombination(
                    combination_id="ULS-UNVERIFIED",
                    factors={"G": 1.0, "Q": 1.0},
                    design_situation="placeholder_pending_code_policy",
                ),
            ),
        )

    def test_complete_registry_creates_bootstrap_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            adapter = create_structural_analysis_bootstrap_adapter(
                self.valid_config(directory, foundation)
            )
            result = adapter(
                project_id="PHX-STR-001",
                engine_id="structural",
                plan_fingerprint="structural-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(artifact["analysis_graph"]["node_count"], 2)
            self.assertEqual(artifact["analysis_graph"]["element_count"], 1)
            self.assertEqual(
                artifact["analysis_graph"][
                    "global_dof_count_assuming_6_per_node"
                ],
                12,
            )

    def test_unknown_material_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            config = StructuralBootstrapConfig(
                project_id="PHX-STR-001",
                foundation_artifact=foundation,
                output_directory=Path(directory) / "structural",
                nodes={"N1": (0, 0, 0), "N2": (1, 0, 0)},
                elements=(
                    StructuralElement(
                        element_id="B1",
                        element_type="beam",
                        material_id="UNKNOWN",
                        node_ids=("N1", "N2"),
                    ),
                ),
            )
            with self.assertRaises(StructuralBootstrapError):
                create_structural_analysis_bootstrap_adapter(config)

    def test_unknown_node_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            config = self.valid_config(directory, foundation)
            bad = StructuralBootstrapConfig(
                project_id=config.project_id,
                foundation_artifact=config.foundation_artifact,
                output_directory=config.output_directory,
                nodes=config.nodes,
                materials=config.materials,
                elements=(
                    StructuralElement(
                        element_id="B1",
                        element_type="beam",
                        material_id="S355",
                        node_ids=("N1", "N3"),
                    ),
                ),
                load_cases=config.load_cases,
                load_combinations=config.load_combinations,
            )
            with self.assertRaises(StructuralBootstrapError):
                create_structural_analysis_bootstrap_adapter(bad)

    def test_unknown_load_case_in_combination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            config = StructuralBootstrapConfig(
                project_id="PHX-STR-001",
                foundation_artifact=foundation,
                output_directory=Path(directory) / "structural",
                load_cases=(
                    StructuralLoadCase(
                        load_case_id="G",
                        load_type="dead",
                        description="Permanent actions",
                    ),
                ),
                load_combinations=(
                    StructuralLoadCombination(
                        combination_id="C1",
                        factors={"Q": 1.0},
                        design_situation="test",
                    ),
                ),
            )
            with self.assertRaises(StructuralBootstrapError):
                create_structural_analysis_bootstrap_adapter(config)

    def test_tampered_foundation_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = Path(self.create_foundation_artifact(directory))
            artifact = json.loads(foundation.read_text(encoding="utf-8"))
            artifact["foundation_type"] = "tampered"
            foundation.write_text(json.dumps(artifact), encoding="utf-8")
            adapter = create_structural_analysis_bootstrap_adapter(
                StructuralBootstrapConfig(
                    project_id="PHX-STR-001",
                    foundation_artifact=foundation,
                    output_directory=Path(directory) / "structural",
                )
            )
            with self.assertRaises(StructuralBootstrapError):
                adapter(
                    project_id="PHX-STR-001",
                    engine_id="structural",
                    plan_fingerprint="structural-fp",
                )

    def test_empty_model_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            adapter = create_structural_analysis_bootstrap_adapter(
                StructuralBootstrapConfig(
                    project_id="PHX-STR-001",
                    foundation_artifact=foundation,
                    output_directory=Path(directory) / "structural",
                )
            )
            result = adapter(
                project_id="PHX-STR-001",
                engine_id="structural",
                plan_fingerprint="structural-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                artifact["analysis_graph"]["model_status"],
                "bootstrap_model_incomplete",
            )
            self.assertIsNone(artifact["solver_results"])

    def test_artifact_disclaims_completed_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            foundation = self.create_foundation_artifact(directory)
            adapter = create_structural_analysis_bootstrap_adapter(
                self.valid_config(directory, foundation)
            )
            result = adapter(
                project_id="PHX-STR-001",
                engine_id="structural",
                plan_fingerprint="structural-fp",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertTrue(
                artifact["claims_policy"][
                    "bootstrap_is_not_completed_structural_analysis"
                ]
            )
            self.assertIsNone(artifact["member_forces"])
            self.assertIsNone(artifact["displacements"])


if __name__ == "__main__":
    unittest.main()
