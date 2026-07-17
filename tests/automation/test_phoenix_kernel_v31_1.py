from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


def load_kernel_module():
    path = project_root() / "phoenix/kernel/phoenix_kernel_v31_1.py"
    module_name = "phoenix_kernel_v31_1_test_module"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise RuntimeError("Kernelmodule kon niet worden geladen.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)

    return module


class PhoenixKernelRecoveryTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/kernel_policy_v31_1.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v31.1")
        self.assertTrue(data["remove_dataclass_import_dependency"])

    def test_registry(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/kernel_plugin_registry_v31_1.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["registry_version"], "v31.1")
        self.assertGreaterEqual(len(data["plugins"]), 5)

    def test_import(self) -> None:
        module = load_kernel_module()
        self.assertTrue(hasattr(module, "PhoenixKernel"))
        self.assertTrue(hasattr(module, "KernelEvent"))
        self.assertTrue(hasattr(module, "EventBus"))
        self.assertTrue(hasattr(module, "ServiceBus"))

    def test_event_bus(self) -> None:
        module = load_kernel_module()
        bus = module.EventBus()
        received = []

        bus.subscribe(
            "test.event",
            lambda event: received.append(event.payload),
        )
        bus.publish("test.event", {"ok": True})

        self.assertEqual(received, [{"ok": True}])

    def test_service_bus(self) -> None:
        module = load_kernel_module()
        bus = module.ServiceBus()
        bus.register("echo", lambda value: value)
        self.assertEqual(bus.call("echo", value="ok"), "ok")


if __name__ == "__main__":
    unittest.main()
