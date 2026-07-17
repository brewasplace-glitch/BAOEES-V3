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


def load_kernel():
    path = project_root() / "phoenix/kernel/phoenix_kernel_v31_1.py"
    name = "phoenix_kernel_v31_1_test"
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise RuntimeError("Kernelmodule kon niet worden geladen.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


class PhoenixKernelTests(unittest.TestCase):
    def test_policy(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/kernel_policy_v31_1.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(data["policy_version"], "v31.1")
        self.assertTrue(data["require_event_bus"])
        self.assertTrue(data["require_service_bus"])

    def test_registry(self) -> None:
        data = json.loads(
            (
                project_root()
                / "configs/phoenix/kernel_plugin_registry_v31_1.json"
            ).read_text(encoding="utf-8-sig")
        )
        self.assertGreaterEqual(len(data["plugins"]), 5)

    def test_import(self) -> None:
        module = load_kernel()
        self.assertTrue(hasattr(module, "PhoenixKernel"))

    def test_event_bus(self) -> None:
        module = load_kernel()
        bus = module.EventBus()
        received = []
        bus.subscribe("test", lambda event: received.append(event.payload))
        bus.publish("test", {"ok": True})
        self.assertEqual(received, [{"ok": True}])

    def test_service_bus(self) -> None:
        module = load_kernel()
        bus = module.ServiceBus()
        bus.register("echo", lambda value: value)
        self.assertEqual(bus.call("echo", value="ok"), "ok")


if __name__ == "__main__":
    unittest.main()
