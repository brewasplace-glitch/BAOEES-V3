import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters import (
    GISBootstrapConfig,
    GeotechnicalBootstrapConfig,
    GeotechnicalBootstrapError,
    SoilLayer,
    create_gis_bootstrap_adapter,
    create_geotechnical_bootstrap_adapter,
)
from phoenix.orchestration.pipeline import PhoenixDeliveryPipeline
from phoenix.orchestration.runtime import AdapterRegistry
from phoenix.project_generator import ProjectBrief


class PhoenixGeotechnicalBootstrapAdapterTests(unittest.TestCase):
    def create_gis_artifact(self, directory, project_id="PHX-GEO-001"):
        adapter = create_gis_bootstrap_adapter(
            GISBootstrapConfig(
                project_id=project_id,
                location_reference="kaart://geo-test",
                output_directory=Path(directory) / "gis",
            )
        )
        result = adapter(
            project_id=project_id,
            engine_id="gis",
            plan_fingerprint="gis-fp",
        )
        return result.outputs[0]

    def test_empty_profile_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = self.create_gis_artifact(directory)
            adapter = create_geotechnical_bootstrap_adapter(
                GeotechnicalBootstrapConfig(
                    project_id="PHX-GEO-001",
                    gis_artifact=gis,
                    output_directory=Path(directory) / "geo",
                )
            )
            result = adapter(
                project_id="PHX-GEO-001",
                engine_id="geotechnical",
                plan_fingerprint="geo-fp",
            )
            payload = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertEqual(payload["data_status"], "awaiting_ground_investigation")
            self.assertIsNone(payload["foundation_recommendation"])

    def test_supplied_soil_profile_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = self.create_gis_artifact(directory)
            layer = SoilLayer(
                layer_id="L1",
                top_level_m=0.0,
                bottom_level_m=-1.0,
                classification="sand",
                friction_angle_deg=30.0,
                source_reference="report://soil-001",
            )
            adapter = create_geotechnical_bootstrap_adapter(
                GeotechnicalBootstrapConfig(
                    project_id="PHX-GEO-001",
                    gis_artifact=gis,
                    output_directory=Path(directory) / "geo",
                    soil_layers=(layer,),
                )
            )
            result = adapter(
                project_id="PHX-GEO-001",
                engine_id="geotechnical",
                plan_fingerprint="geo-fp",
            )
            payload = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertEqual(payload["data_status"], "supplied_soil_profile")
            self.assertEqual(payload["soil_layers"][0]["layer_id"], "L1")

    def test_assumed_groundwater_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = self.create_gis_artifact(directory)
            adapter = create_geotechnical_bootstrap_adapter(
                GeotechnicalBootstrapConfig(
                    project_id="PHX-GEO-001",
                    gis_artifact=gis,
                    output_directory=Path(directory) / "geo",
                    allow_assumed_groundwater=True,
                )
            )
            result = adapter(
                project_id="PHX-GEO-001",
                engine_id="geotechnical",
                plan_fingerprint="geo-fp",
            )
            payload = json.loads(Path(result.outputs[0]).read_text(encoding="utf-8"))
            self.assertEqual(payload["groundwater"]["status"], "assumption")
            self.assertEqual(payload["groundwater"]["level_m"], -0.50)

    def test_supplied_groundwater_requires_basis(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = self.create_gis_artifact(directory)
            with self.assertRaises(GeotechnicalBootstrapError):
                create_geotechnical_bootstrap_adapter(
                    GeotechnicalBootstrapConfig(
                        project_id="PHX-GEO-001",
                        gis_artifact=gis,
                        output_directory=Path(directory) / "geo",
                        groundwater_level_m=-0.75,
                    )
                )

    def test_tampered_gis_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = Path(self.create_gis_artifact(directory))
            payload = json.loads(gis.read_text(encoding="utf-8"))
            payload["project_id"] = "TAMPERED"
            gis.write_text(json.dumps(payload), encoding="utf-8")
            adapter = create_geotechnical_bootstrap_adapter(
                GeotechnicalBootstrapConfig(
                    project_id="PHX-GEO-001",
                    gis_artifact=gis,
                    output_directory=Path(directory) / "geo",
                )
            )
            with self.assertRaises(GeotechnicalBootstrapError):
                adapter(
                    project_id="PHX-GEO-001",
                    engine_id="geotechnical",
                    plan_fingerprint="geo-fp",
                )

    def test_pipeline_executes_gis_then_geotechnical(self):
        with tempfile.TemporaryDirectory() as directory:
            project_id = "PHX-GEO-PIPE"
            gis_output = Path(directory) / "artifacts" / "gis"
            geo_output = Path(directory) / "artifacts" / "geo"

            gis_adapter = create_gis_bootstrap_adapter(
                GISBootstrapConfig(
                    project_id=project_id,
                    location_reference="kaart://pipeline",
                    output_directory=gis_output,
                )
            )

            # Create the GIS artifact once so the geotechnical adapter has a
            # verified input path. Runtime execution will deterministically
            # overwrite the same artifact before geotechnical execution.
            gis_result = gis_adapter(
                project_id=project_id,
                engine_id="gis",
                plan_fingerprint="bootstrap-gis",
            )

            geo_adapter = create_geotechnical_bootstrap_adapter(
                GeotechnicalBootstrapConfig(
                    project_id=project_id,
                    gis_artifact=gis_result.outputs[0],
                    output_directory=geo_output,
                    allow_assumed_groundwater=True,
                )
            )

            registry = AdapterRegistry()
            registry.register("gis", gis_adapter)
            registry.register("geotechnical", geo_adapter)

            pipeline = PhoenixDeliveryPipeline(registry=registry)
            bootstrap = pipeline.bootstrap(
                ProjectBrief(
                    project_id=project_id,
                    instruction="Ontwerp een appartementencomplex.",
                    location_reference="kaart://pipeline",
                )
            )

            checkpoint_dir = Path(directory) / "runtime"
            first = pipeline.run_next(
                bootstrap,
                checkpoint_directory=checkpoint_dir,
            )
            second = pipeline.run_plan_until_blocked_or_complete(
                first,
                checkpoint_directory=checkpoint_dir,
            )
            self.assertEqual(second.engine_map()["gis"].status, "completed")
            self.assertEqual(
                second.engine_map()["geotechnical"].status,
                "completed",
            )

    def test_invalid_layer_order_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            gis = self.create_gis_artifact(directory)
            with self.assertRaises(GeotechnicalBootstrapError):
                create_geotechnical_bootstrap_adapter(
                    GeotechnicalBootstrapConfig(
                        project_id="PHX-GEO-001",
                        gis_artifact=gis,
                        output_directory=Path(directory) / "geo",
                        soil_layers=(
                            SoilLayer(
                                layer_id="L1",
                                top_level_m=-1.0,
                                bottom_level_m=0.0,
                                classification="invalid",
                            ),
                        ),
                    )
                )


if __name__ == "__main__":
    unittest.main()
