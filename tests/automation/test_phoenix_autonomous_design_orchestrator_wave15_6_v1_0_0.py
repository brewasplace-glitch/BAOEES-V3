import json
import tempfile
import unittest
from pathlib import Path

from phoenix.adapters.autonomous_design_orchestrator_adapter import (
    run_autonomous_design_orchestrator,
)
from phoenix.autonomous_orchestrator import (
    AutonomousDesignOrchestrator,
    OrchestrationContext,
    OrchestrationError,
    OrchestrationStep,
)


class Wave156Tests(unittest.TestCase):
    def test_dependency_order(self):
        registry = {
            "engine.a": lambda payload: {"value": 1},
            "engine.b": lambda payload: {"value": 2},
        }
        result = AutonomousDesignOrchestrator(registry).run(
            context=OrchestrationContext("PHX", human_approval_required=False),
            steps=(
                OrchestrationStep("b", "engine.b", ("a",)),
                OrchestrationStep("a", "engine.a"),
            ),
        )
        self.assertEqual(result["execution_order"], ["a", "b"])
        self.assertEqual(result["workflow_status"], "completed")

    def test_cycle_rejected(self):
        with self.assertRaisesRegex(OrchestrationError, "cycle"):
            AutonomousDesignOrchestrator({}).run(
                context=OrchestrationContext("PHX"),
                steps=(
                    OrchestrationStep("a", "engine.a", ("b",)),
                    OrchestrationStep("b", "engine.b", ("a",)),
                ),
            )

    def test_missing_required_engine_fails(self):
        result = AutonomousDesignOrchestrator({}).run(
            context=OrchestrationContext("PHX"),
            steps=(OrchestrationStep("a", "engine.a"),),
        )
        self.assertEqual(result["workflow_status"], "failed")

    def test_missing_optional_engine_skips(self):
        result = AutonomousDesignOrchestrator({}).run(
            context=OrchestrationContext("PHX"),
            steps=(OrchestrationStep("a", "engine.a", required=False),),
        )
        self.assertEqual(result["workflow_status"], "completed")
        self.assertEqual(result["step_results"][0]["status"], "skipped_optional")

    def test_failure_stops_required_workflow(self):
        def fail(_):
            raise RuntimeError("boom")
        registry = {"engine.a": fail, "engine.b": lambda payload: {"ok": True}}
        result = AutonomousDesignOrchestrator(registry).run(
            context=OrchestrationContext("PHX"),
            steps=(
                OrchestrationStep("a", "engine.a"),
                OrchestrationStep("b", "engine.b", ("a",)),
            ),
        )
        self.assertEqual(result["workflow_status"], "failed")
        self.assertIn("b", result["pending_steps"])

    def test_input_output_keys(self):
        registry = {"engine.a": lambda payload: {"doubled": payload["value"] * 2}}
        result = AutonomousDesignOrchestrator(registry).run(
            context=OrchestrationContext("PHX", human_approval_required=False),
            steps=(OrchestrationStep("a", "engine.a", input_key="source", output_key="result"),),
            initial_state={"source": {"value": 4}},
        )
        self.assertEqual(result["state"]["result"]["doubled"], 8)

    def test_evidence_sha256(self):
        result = AutonomousDesignOrchestrator({"engine.a": lambda _: {"ok": True}}).run(
            context=OrchestrationContext("PHX"),
            steps=(OrchestrationStep("a", "engine.a"),),
        )
        self.assertEqual(len(result["evidence"]["payload_sha256"]), 64)

    def test_adapter_writes_output(self):
        request = {
            "context": {"project_id": "PHX"},
            "steps": [{"step_id": "a", "engine_id": "engine.a"}],
            "initial_state": {},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            result = run_autonomous_design_orchestrator(
                request,
                {"engine.a": lambda _: {"ok": True}},
                path,
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result["workflow_status"], "completed")
        self.assertEqual(stored["adapter"]["version"], "1.0.0")

    def test_write_result_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            AutonomousDesignOrchestrator(
                {"engine.a": lambda _: {"ok": True}}
            ).write_result(
                context=OrchestrationContext("PHX"),
                steps=(OrchestrationStep("a", "engine.a"),),
                initial_state={},
                destination=path,
            )
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
