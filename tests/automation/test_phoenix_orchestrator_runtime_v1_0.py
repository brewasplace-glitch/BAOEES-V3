import json
from pathlib import Path
import tempfile
import unittest

from phoenix.orchestration.phoenix_orchestrator import (
    OrchestrationState,
    PhoenixOrchestrator,
    ProjectContext,
)
from phoenix.orchestration.runtime import (
    AdapterRegistry,
    AdapterResult,
    PhoenixRuntime,
    RuntimeErrorContract,
    deterministic_test_adapter,
)


class PhoenixOrchestratorRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = PhoenixOrchestrator()
        self.plan = self.orchestrator.create_plan(
            ProjectContext(
                project_id="PHX-RUNTIME-001",
                instruction="Ontwerp een appartementencomplex.",
                location_reference="kaart://runtime-test",
                selected_variant_id="V01",
                selected_variant_fingerprint="fp-runtime",
            )
        )

    def test_registered_adapter_completes_first_ready_engine(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        runtime = PhoenixRuntime(
            orchestrator=self.orchestrator,
            registry=registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            result = runtime.run_next(
                self.plan,
                checkpoint_directory=directory,
            )
            self.assertEqual(result.engine_map()["gis"].status, "completed")
            self.assertTrue(
                Path(directory, "pxo_runtime_checkpoint.json").exists()
            )

    def test_missing_adapter_fails_and_stops(self):
        runtime = PhoenixRuntime(orchestrator=self.orchestrator)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeErrorContract):
                runtime.run_next(
                    self.plan,
                    checkpoint_directory=directory,
                )
            payload = json.loads(
                Path(directory, "pxo_runtime_checkpoint.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["state"], "failed")

    def test_adapter_without_outputs_is_rejected(self):
        def invalid_adapter(**kwargs):
            return AdapterResult(outputs=(), evidence=("e",))

        registry = AdapterRegistry()
        registry.register("gis", invalid_adapter)
        runtime = PhoenixRuntime(
            orchestrator=self.orchestrator,
            registry=registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeErrorContract):
                runtime.run_next(
                    self.plan,
                    checkpoint_directory=directory,
                )

    def test_checkpoint_contains_integrity_hash(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        runtime = PhoenixRuntime(
            orchestrator=self.orchestrator,
            registry=registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            runtime.run_next(
                self.plan,
                checkpoint_directory=directory,
            )
            payload = json.loads(
                Path(directory, "pxo_runtime_checkpoint.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(payload["checkpoint_sha256"]), 64)
            self.assertEqual(
                payload["schema"],
                "phoenix-pxo-runtime-checkpoint-v1.0",
            )

    def test_registry_rejects_duplicate_adapter(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        with self.assertRaises(RuntimeErrorContract):
            registry.register("gis", deterministic_test_adapter)

    def test_run_until_no_ready_engine(self):
        registry = AdapterRegistry()
        registry.register("gis", deterministic_test_adapter)
        runtime = PhoenixRuntime(
            orchestrator=self.orchestrator,
            registry=registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeErrorContract):
                runtime.run_until_blocked_or_complete(
                    self.plan,
                    checkpoint_directory=directory,
                )

    def test_initial_plan_is_ready(self):
        self.assertEqual(self.plan.state, OrchestrationState.READY)


if __name__ == "__main__":
    unittest.main()
