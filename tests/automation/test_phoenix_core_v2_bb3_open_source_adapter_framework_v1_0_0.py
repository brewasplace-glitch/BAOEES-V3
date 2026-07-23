import json
import tempfile
import unittest
from pathlib import Path

from phoenix.osif import ApplicationDescriptor, Capability
from phoenix.osif.adapters import (
    AdapterContext,
    AdapterError,
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterExecutor,
    AdapterHealth,
    AdapterLifecycleState,
    AdapterRegistry,
    OSIFAdapter,
    register_builtin_adapters,
)


class DemoAdapter(OSIFAdapter):
    def descriptor(self):
        return ApplicationDescriptor(
            application_id="demo",
            name="Demo",
            adapter_id="adapter.demo",
            execution_mode="python",
            capabilities=(Capability("demo.run", "Run demo"),),
        )

    def health_check(self):
        return AdapterHealth("available", "ok")

    def validate_request(self, request):
        if request.capability_id != "demo.run":
            raise AdapterError("unsupported")

    def _execute(self, request):
        payload = {"value": request.inputs.get("value", 0)}
        return AdapterExecutionResult(
            request_id=request.request_id,
            adapter_id="adapter.demo",
            application_id="demo",
            status="completed",
            outputs=payload,
            evidence_sha256=self.evidence_digest(payload),
        )


class BB3AdapterFrameworkTests(unittest.TestCase):
    def test_lifecycle_success(self):
        adapter = DemoAdapter()
        self.assertEqual(adapter.state, AdapterLifecycleState.CREATED)
        adapter.initialize(AdapterContext("PHX", "."))
        self.assertEqual(adapter.state, AdapterLifecycleState.READY)
        result = adapter.execute(
            AdapterExecutionRequest("req", "PHX", "demo.run", {"value": 7})
        )
        self.assertEqual(result.outputs["value"], 7)
        adapter.shutdown()
        self.assertEqual(adapter.state, AdapterLifecycleState.STOPPED)

    def test_execute_before_initialize_rejected(self):
        with self.assertRaisesRegex(AdapterError, "not ready"):
            DemoAdapter().execute(
                AdapterExecutionRequest("req", "PHX", "demo.run")
            )

    def test_registry(self):
        registry = AdapterRegistry()
        registry.register(DemoAdapter)
        self.assertEqual(registry.list_adapter_ids(), ("adapter.demo",))
        self.assertEqual(
            registry.find_by_capability("demo.run"),
            ("adapter.demo",),
        )

    def test_builtin_registration(self):
        registry = AdapterRegistry()
        register_builtin_adapters(registry)
        self.assertEqual(len(registry.list_adapter_ids()), 4)

    def test_executor_and_writeback(self):
        envelope = AdapterExecutor().run(
            adapter=DemoAdapter(),
            context=AdapterContext("PHX", "."),
            request=AdapterExecutionRequest(
                "req",
                "PHX",
                "demo.run",
                {"value": 3},
            ),
        )
        self.assertEqual(envelope["result"]["status"], "completed")
        self.assertEqual(len(envelope["audit_sha256"]), 64)
        self.assertEqual(
            len(envelope["digital_twin_writeback"]["writeback_sha256"]),
            64,
        )

    def test_atomic_envelope_write(self):
        executor = AdapterExecutor()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "envelope.json"
            executor.write_envelope({"ok": True}, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(loaded["ok"])

    def test_unsupported_capability_rejected(self):
        adapter = DemoAdapter()
        adapter.initialize(AdapterContext("PHX", "."))
        with self.assertRaisesRegex(AdapterError, "unsupported"):
            adapter.execute(
                AdapterExecutionRequest("req", "PHX", "other")
            )


if __name__ == "__main__":
    unittest.main()
