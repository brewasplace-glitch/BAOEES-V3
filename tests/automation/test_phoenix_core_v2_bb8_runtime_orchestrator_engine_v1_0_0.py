import json
import tempfile
import unittest
from pathlib import Path

from phoenix.runtime_orchestrator import (
    DependencyError,
    RuntimeOrchestrator,
    TaskSpec,
)
from phoenix.runtime_orchestrator.registry import (
    EngineDescriptor,
    EngineRegistry,
)


def ok_task(context):
    context.emit("test_event", value=1)
    return context.task_id


def failing_task(context):
    raise RuntimeError("intentional failure")


class T(unittest.TestCase):
    def test_dependency_order(self):
        orchestrator = RuntimeOrchestrator(
            max_workers=2,
            runtime_id="test-runtime",
        )
        orchestrator.register_many(
            [
                TaskSpec("a", ok_task),
                TaskSpec("b", ok_task, dependencies=("a",)),
            ]
        )
        snapshot = orchestrator.run()
        self.assertEqual(snapshot.status, "completed")
        self.assertEqual(
            snapshot.tasks["a"]["status"],
            "completed",
        )
        self.assertEqual(
            snapshot.tasks["b"]["status"],
            "completed",
        )

    def test_parallel_ready_tasks(self):
        orchestrator = RuntimeOrchestrator(max_workers=2)
        orchestrator.register_many(
            [
                TaskSpec("a", ok_task),
                TaskSpec("b", ok_task),
            ]
        )
        snapshot = orchestrator.run()
        self.assertEqual(snapshot.status, "completed")
        self.assertEqual(len(snapshot.tasks), 2)

    def test_failure_blocks_dependent_task(self):
        orchestrator = RuntimeOrchestrator(max_workers=2)
        orchestrator.register_many(
            [
                TaskSpec("a", failing_task),
                TaskSpec("b", ok_task, dependencies=("a",)),
            ]
        )
        snapshot = orchestrator.run()
        self.assertEqual(snapshot.status, "failed")
        self.assertEqual(snapshot.tasks["a"]["status"], "failed")
        self.assertEqual(snapshot.tasks["b"]["status"], "blocked")

    def test_cycle_detection(self):
        orchestrator = RuntimeOrchestrator()
        orchestrator.register_many(
            [
                TaskSpec("a", ok_task, dependencies=("b",)),
                TaskSpec("b", ok_task, dependencies=("a",)),
            ]
        )
        with self.assertRaises(DependencyError):
            orchestrator.run()

    def test_unknown_dependency_detection(self):
        orchestrator = RuntimeOrchestrator()
        orchestrator.register(
            TaskSpec("a", ok_task, dependencies=("missing",))
        )
        with self.assertRaises(DependencyError):
            orchestrator.run()

    def test_snapshot_write(self):
        with tempfile.TemporaryDirectory() as folder:
            orchestrator = RuntimeOrchestrator()
            orchestrator.register(TaskSpec("a", ok_task))
            snapshot = orchestrator.run()
            output = Path(folder) / "snapshot.json"
            RuntimeOrchestrator.write_snapshot(snapshot, output)
            parsed = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(parsed["status"], "completed")
        self.assertEqual(len(parsed["evidence_sha256"]), 64)

    def test_registry_health(self):
        registry = EngineRegistry()
        registry.register(
            EngineDescriptor(
                "json",
                "1.0",
                "json",
                required=True,
            )
        )
        self.assertTrue(registry.required_engines_available())
        self.assertEqual(
            registry.health()[0].status,
            "healthy",
        )

    def test_retry_success(self):
        attempts = {"count": 0}

        def flaky(context):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("first failure")
            return "ok"

        orchestrator = RuntimeOrchestrator()
        orchestrator.register(
            TaskSpec("a", flaky, retries=1)
        )
        snapshot = orchestrator.run()
        self.assertEqual(snapshot.status, "completed")
        self.assertEqual(snapshot.tasks["a"]["attempts"], 2)


if __name__ == "__main__":
    unittest.main()
