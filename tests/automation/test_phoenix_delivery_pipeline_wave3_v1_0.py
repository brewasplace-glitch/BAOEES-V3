import json
from pathlib import Path
import tempfile
import unittest

from phoenix.project_generator import ProjectBrief
from phoenix.orchestration.pipeline import (
    PhoenixDeliveryPipeline,
    PipelineError,
)
from phoenix.orchestration.runtime import (
    AdapterRegistry,
    deterministic_test_adapter,
)


class PhoenixDeliveryPipelineWave3Tests(unittest.TestCase):
    def brief(self):
        return ProjectBrief(
            project_id="PHX-W3-001",
            instruction="Ontwerp een appartementencomplex op deze locatie.",
            location_reference="kaart://wave3-test",
            target_units=120,
            maximum_floors=10,
        )

    def test_bootstrap_generates_ten_variants_and_plan(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        pipeline = PhoenixDeliveryPipeline(registry=registry)
        bootstrap = pipeline.bootstrap(self.brief())
        self.assertEqual(bootstrap.variant_count, 10)
        self.assertEqual(len(bootstrap.presentation_queue), 10)
        self.assertEqual(len(bootstrap.bootstrap_fingerprint), 64)
        self.assertEqual(bootstrap.plan.selected_variant_id, bootstrap.selected_variant_id)

    def test_manual_variant_selection_is_preserved(self):
        pipeline = PhoenixDeliveryPipeline()
        bootstrap = pipeline.bootstrap(
            self.brief(),
            selected_variant_id="V07",
        )
        self.assertEqual(bootstrap.selected_variant_id, "V07")
        self.assertEqual(bootstrap.plan.selected_variant_id, "V07")

    def test_bootstrap_manifest_contains_integrity_hash(self):
        pipeline = PhoenixDeliveryPipeline()
        bootstrap = pipeline.bootstrap(self.brief())
        with tempfile.TemporaryDirectory() as directory:
            path = pipeline.write_bootstrap_manifest(
                bootstrap,
                Path(directory) / "bootstrap.json",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["variant_count"], 10)
            self.assertEqual(len(payload["manifest_sha256"]), 64)

    def test_runtime_executes_registered_gis_adapter(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        pipeline = PhoenixDeliveryPipeline(registry=registry)
        bootstrap = pipeline.bootstrap(self.brief())
        with tempfile.TemporaryDirectory() as directory:
            plan = pipeline.run_next(
                bootstrap,
                checkpoint_directory=directory,
            )
            self.assertEqual(plan.engine_map()["gis"].status, "completed")

    def test_resume_verifies_checkpoint_integrity(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        pipeline = PhoenixDeliveryPipeline(registry=registry)
        bootstrap = pipeline.bootstrap(self.brief())

        with tempfile.TemporaryDirectory() as directory:
            pipeline.run_next(
                bootstrap,
                checkpoint_directory=directory,
            )
            checkpoint = Path(directory) / "pxo_runtime_checkpoint.json"
            resumed = pipeline.resume_from_checkpoint(checkpoint)
            self.assertEqual(resumed.plan.engine_map()["gis"].status, "completed")
            self.assertEqual(len(resumed.checkpoint_sha256), 64)

    def test_tampered_checkpoint_is_rejected(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        pipeline = PhoenixDeliveryPipeline(registry=registry)
        bootstrap = pipeline.bootstrap(self.brief())

        with tempfile.TemporaryDirectory() as directory:
            pipeline.run_next(
                bootstrap,
                checkpoint_directory=directory,
            )
            checkpoint = Path(directory) / "pxo_runtime_checkpoint.json"
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            payload["project_id"] = "TAMPERED"
            checkpoint.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PipelineError):
                pipeline.resume_from_checkpoint(checkpoint)

    def test_bootstrap_is_deterministic(self):
        pipeline = PhoenixDeliveryPipeline()
        first = pipeline.bootstrap(self.brief())
        second = pipeline.bootstrap(self.brief())
        self.assertEqual(
            first.bootstrap_fingerprint,
            second.bootstrap_fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
