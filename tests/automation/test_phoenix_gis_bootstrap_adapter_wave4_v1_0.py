import json
from pathlib import Path
import tempfile
import unittest

from phoenix.adapters import (
    GISBootstrapConfig,
    GISBootstrapError,
    GISBootstrapSource,
    create_gis_bootstrap_adapter,
)
from phoenix.orchestration.pipeline import PhoenixDeliveryPipeline
from phoenix.orchestration.runtime import AdapterRegistry
from phoenix.project_generator import ProjectBrief


class PhoenixGISBootstrapAdapterTests(unittest.TestCase):
    def test_reference_only_artifact_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = create_gis_bootstrap_adapter(
                GISBootstrapConfig(
                    project_id="PHX-GIS-001",
                    location_reference="Bikkersweg 88, Bunschoten",
                    output_directory=directory,
                )
            )
            result = adapter(
                project_id="PHX-GIS-001",
                engine_id="gis",
                plan_fingerprint="abc",
            )
            artifact = Path(result.outputs[0])
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(payload["data_status"], "reference_only")
            self.assertIsNone(payload["centroid"])
            self.assertEqual(len(payload["artifact_sha256"]), 64)

    def test_supplied_geometry_requires_crs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(GISBootstrapError):
                create_gis_bootstrap_adapter(
                    GISBootstrapConfig(
                        project_id="PHX-GIS-002",
                        location_reference="test",
                        output_directory=directory,
                        centroid=(1.0, 2.0),
                    )
                )

    def test_invalid_bounding_box_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(GISBootstrapError):
                create_gis_bootstrap_adapter(
                    GISBootstrapConfig(
                        project_id="PHX-GIS-003",
                        location_reference="test",
                        output_directory=directory,
                        coordinate_reference_system="EPSG:28992",
                        bounding_box=(10.0, 10.0, 5.0, 20.0),
                    )
                )

    def test_source_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = GISBootstrapSource(
                source_id="SRC-001",
                title="User map reference",
                reference="kaart://project",
            )
            adapter = create_gis_bootstrap_adapter(
                GISBootstrapConfig(
                    project_id="PHX-GIS-004",
                    location_reference="kaart://project",
                    output_directory=directory,
                    sources=(source,),
                )
            )
            result = adapter(
                project_id="PHX-GIS-004",
                engine_id="gis",
                plan_fingerprint="fp",
            )
            payload = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertEqual(payload["sources"][0]["source_id"], "SRC-001")

    def test_wrong_engine_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = create_gis_bootstrap_adapter(
                GISBootstrapConfig(
                    project_id="PHX-GIS-005",
                    location_reference="test",
                    output_directory=directory,
                )
            )
            with self.assertRaises(GISBootstrapError):
                adapter(
                    project_id="PHX-GIS-005",
                    engine_id="parking",
                    plan_fingerprint="fp",
                )

    def test_pipeline_executes_real_gis_bootstrap_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AdapterRegistry()
            registry.register(
                "gis",
                create_gis_bootstrap_adapter(
                    GISBootstrapConfig(
                        project_id="PHX-GIS-006",
                        location_reference="kaart://wave4",
                        output_directory=Path(directory) / "artifacts",
                    )
                ),
            )
            pipeline = PhoenixDeliveryPipeline(registry=registry)
            bootstrap = pipeline.bootstrap(
                ProjectBrief(
                    project_id="PHX-GIS-006",
                    instruction="Ontwerp een appartementencomplex.",
                    location_reference="kaart://wave4",
                )
            )
            plan = pipeline.run_next(
                bootstrap,
                checkpoint_directory=Path(directory) / "runtime",
            )
            gis = plan.engine_map()["gis"]
            self.assertEqual(gis.status, "completed")
            self.assertEqual(len(gis.outputs), 1)

    def test_artifact_explicitly_remains_non_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = create_gis_bootstrap_adapter(
                GISBootstrapConfig(
                    project_id="PHX-GIS-007",
                    location_reference="test",
                    output_directory=directory,
                )
            )
            result = adapter(
                project_id="PHX-GIS-007",
                engine_id="gis",
                plan_fingerprint="fp",
            )
            payload = json.loads(
                Path(result.outputs[0]).read_text(encoding="utf-8")
            )
            self.assertTrue(
                payload["claims_policy"]["bootstrap_is_not_authoritative_gis_analysis"]
            )
            self.assertEqual(payload["verified_facts"], [])


if __name__ == "__main__":
    unittest.main()
