import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters.foundation_bootstrap import (
    FoundationBootstrapConfig,
    FoundationBootstrapError,
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
from phoenix.orchestration.pipeline import PhoenixDeliveryPipeline
from phoenix.orchestration.runtime import AdapterRegistry
from phoenix.project_generator import ProjectBrief


class PhoenixFoundationBootstrapAdapterTests(unittest.TestCase):
    def create_chain(self, directory, project_id="PHX-FND-001"):
        gis_adapter = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://foundation-test",
                output_directory=Path(directory) / "gis",
            )
        )
        gis_result = gis_adapter(
            project_id=project_id,
            engine_id="gis",
            plan_fingerprint="gis-fingerprint",
        )

        geotechnical_adapter = create_geotechnical_bootstrap_adapter(
            GeotechnicalBootstrapConfig(
                project_id=project_id,
                gis_artifact=gis_result.outputs[0],
                output_directory=Path(directory) / "geotechnical",
                soil_layers=(
                    SoilLayer(
                        layer_id="L1",
                        top_level_m=0.0,
                        bottom_level_m=-1.0,
                        classification="sand",
                        friction_angle_deg=30.0,
                        source_reference="report://ground-investigation",
                    ),
                ),
                allow_assumed_groundwater=True,
            )
        )
        geotechnical_result = geotechnical_adapter(
            project_id=project_id,
            engine_id="geotechnical",
            plan_fingerprint="geotechnical-fingerprint",
        )
        return (
            gis_adapter,
            geotechnical_adapter,
            geotechnical_result.outputs[0],
        )

    def test_standard_strip_concept_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id="PHX-FND-001",
                    geotechnical_artifact=geotechnical_artifact,
                    output_directory=Path(directory) / "foundation",
                    use_phoenix_standard_strip_concept=True,
                )
            )
            result = adapter(
                project_id="PHX-FND-001",
                engine_id="foundation",
                plan_fingerprint="foundation-fingerprint",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(artifact["foundation_type"], "strip")
            self.assertEqual(
                artifact["strip_concept"]["continuous_strip"]["width_m"],
                1.50,
            )
            self.assertEqual(
                artifact["strip_concept"]["centered_foundation_beam"]["height_m"],
                0.60,
            )

    def test_explicit_preference_requires_basis(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            with self.assertRaises(FoundationBootstrapError):
                create_foundation_bootstrap_adapter(
                    FoundationBootstrapConfig(
                        project_id="PHX-FND-001",
                        geotechnical_artifact=geotechnical_artifact,
                        output_directory=Path(directory) / "foundation",
                        preferred_foundation_type="raft",
                    )
                )

    def test_undetermined_type_remains_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id="PHX-FND-001",
                    geotechnical_artifact=geotechnical_artifact,
                    output_directory=Path(directory) / "foundation",
                )
            )
            result = adapter(
                project_id="PHX-FND-001",
                engine_id="foundation",
                plan_fingerprint="foundation-fingerprint",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(artifact["foundation_type"], "undetermined")
            self.assertIsNone(
                artifact["verified_design_checks"]["settlement"]
            )
            self.assertIsNone(artifact["reinforcement"])

    def test_tampered_geotechnical_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            path = Path(geotechnical_artifact)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["data_status"] = "tampered"
            path.write_text(json.dumps(artifact), encoding="utf-8")

            adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id="PHX-FND-001",
                    geotechnical_artifact=path,
                    output_directory=Path(directory) / "foundation",
                )
            )
            with self.assertRaises(FoundationBootstrapError):
                adapter(
                    project_id="PHX-FND-001",
                    engine_id="foundation",
                    plan_fingerprint="foundation-fingerprint",
                )

    def test_wrong_engine_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id="PHX-FND-001",
                    geotechnical_artifact=geotechnical_artifact,
                    output_directory=Path(directory) / "foundation",
                )
            )
            with self.assertRaises(FoundationBootstrapError):
                adapter(
                    project_id="PHX-FND-001",
                    engine_id="structural",
                    plan_fingerprint="foundation-fingerprint",
                )

    def test_pipeline_executes_gis_geotechnical_and_foundation(self):
        with tempfile.TemporaryDirectory() as directory:
            project_id = "PHX-FND-PIPE"
            gis_adapter, geotechnical_adapter, geo_artifact = self.create_chain(
                directory,
                project_id,
            )
            foundation_adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id=project_id,
                    geotechnical_artifact=geo_artifact,
                    output_directory=Path(directory) / "foundation",
                    use_phoenix_standard_strip_concept=True,
                )
            )

            registry = AdapterRegistry()
            registry.register("gis", gis_adapter)
            registry.register("geotechnical", geotechnical_adapter)
            registry.register("foundation", foundation_adapter)

            pipeline = PhoenixDeliveryPipeline(registry=registry)
            bootstrap = pipeline.bootstrap(
                ProjectBrief(
                    project_id=project_id,
                    instruction="Ontwerp een appartementencomplex.",
                    location_reference="kaart://foundation-pipeline",
                )
            )

            checkpoint_directory = Path(directory) / "runtime"
            first_plan = pipeline.run_next(
                bootstrap,
                checkpoint_directory=checkpoint_directory,
            )
            final_plan = pipeline.run_plan_until_blocked_or_complete(
                first_plan,
                checkpoint_directory=checkpoint_directory,
            )

            self.assertEqual(
                final_plan.engine_map()["gis"].status,
                "completed",
            )
            self.assertEqual(
                final_plan.engine_map()["geotechnical"].status,
                "completed",
            )
            self.assertEqual(
                final_plan.engine_map()["foundation"].status,
                "completed",
            )

    def test_artifact_disclaims_verified_design(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, geotechnical_artifact = self.create_chain(directory)
            adapter = create_foundation_bootstrap_adapter(
                FoundationBootstrapConfig(
                    project_id="PHX-FND-001",
                    geotechnical_artifact=geotechnical_artifact,
                    output_directory=Path(directory) / "foundation",
                    use_phoenix_standard_strip_concept=True,
                )
            )
            result = adapter(
                project_id="PHX-FND-001",
                engine_id="foundation",
                plan_fingerprint="foundation-fingerprint",
            )
            artifact = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertTrue(
                artifact["claims_policy"][
                    "bootstrap_is_not_verified_foundation_design"
                ]
            )
            self.assertEqual(artifact["design_actions"], {})


if __name__ == "__main__":
    unittest.main()
