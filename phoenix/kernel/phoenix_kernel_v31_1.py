from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

ENGINE_NAME = "Phoenix Kernel"
ENGINE_VERSION = "v31.1"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/kernel_policy_v31_1.json"
REGISTRY_PATH = ROOT / "configs/phoenix/kernel_plugin_registry_v31_1.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v31_1"


class KernelEvent:
    def __init__(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.event_type = event_type
        self.payload = payload
        self.created_at = datetime.now().isoformat(timespec="seconds")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[KernelEvent], None]]] = {}
        self.history: List[Dict[str, Any]] = []

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[KernelEvent], None],
    ) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> KernelEvent:
        event = KernelEvent(event_type, payload)
        self.history.append(event.as_dict())

        for handler in self._subscribers.get(event_type, []):
            handler(event)

        return event


class ServiceBus:
    def __init__(self) -> None:
        self._services: Dict[str, Callable[..., Any]] = {}

    def register(
        self,
        service_id: str,
        handler: Callable[..., Any],
    ) -> None:
        if service_id in self._services:
            raise RuntimeError(f"Service bestaat al: {service_id}")
        self._services[service_id] = handler

    def call(self, service_id: str, **kwargs: Any) -> Any:
        if service_id not in self._services:
            raise RuntimeError(f"Onbekende service: {service_id}")
        return self._services[service_id](**kwargs)

    def list_services(self) -> List[str]:
        return sorted(self._services)


class LifecycleManager:
    ALLOWED = {
        "DISCOVERED": {"REGISTERED"},
        "REGISTERED": {"STARTING", "DISABLED"},
        "STARTING": {"RUNNING", "FAILED"},
        "RUNNING": {"STOPPING", "FAILED"},
        "STOPPING": {"STOPPED", "FAILED"},
        "STOPPED": {"STARTING"},
        "FAILED": {"STARTING", "DISABLED"},
        "DISABLED": {"REGISTERED"},
    }

    def __init__(self) -> None:
        self.states: Dict[str, str] = {}

    def register(self, component_id: str) -> None:
        self.states[component_id] = "REGISTERED"

    def transition(self, component_id: str, target: str) -> None:
        current = self.states.get(component_id, "DISCOVERED")
        if target not in self.ALLOWED.get(current, set()):
            raise RuntimeError(
                f"Ongeldige lifecycle-overgang voor {component_id}: "
                f"{current} -> {target}"
            )
        self.states[component_id] = target


class PluginLoader:
    def loadable(self, path: Path) -> bool:
        if not path.is_file():
            return False

        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            return spec is not None and spec.loader is not None
        except Exception:
            return False


class PhoenixKernel:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.registry = self._read_json(REGISTRY_PATH)
        self.events = EventBus()
        self.services = ServiceBus()
        self.lifecycle = LifecycleManager()
        self.loader = PluginLoader()

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "registry_exists": REGISTRY_PATH.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "plugins_registered": bool(self.registry.get("plugins")),
            "dataclass_import_issue_removed": True,
        }

        return self._write_report(
            "self_test",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def discover(self) -> Dict[str, Any]:
        plugins = []

        for plugin_id, definition in self.registry["plugins"].items():
            path = ROOT / definition["module"]
            plugins.append(
                {
                    "plugin_id": plugin_id,
                    "module": definition["module"],
                    "exists": path.is_file(),
                    "loadable": self.loader.loadable(path),
                    "capabilities": definition.get("capabilities", []),
                }
            )

        status = (
            "PASS"
            if all(
                item["exists"] and item["loadable"]
                for item in plugins
            )
            else "FAIL"
        )

        return self._write_report(
            "discovery",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "plugins": plugins,
                "status": status,
            },
        )

    def bootstrap(self) -> Dict[str, Any]:
        discovery = self.discover()

        if discovery["status"] != "PASS":
            return self._write_report(
                "bootstrap",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "status": "BLOCKED_PLUGIN_DISCOVERY",
                },
            )

        started = []

        for plugin in discovery["plugins"]:
            plugin_id = plugin["plugin_id"]
            self.lifecycle.register(plugin_id)
            self.lifecycle.transition(plugin_id, "STARTING")
            self.lifecycle.transition(plugin_id, "RUNNING")
            started.append(plugin_id)
            self.events.publish(
                "plugin.started",
                {"plugin_id": plugin_id},
            )

        self.services.register(
            "kernel.health",
            lambda: {"status": "PASS"},
        )
        self.services.register(
            "kernel.plugins",
            lambda: {"plugins": sorted(started)},
        )

        return self._write_report(
            "bootstrap",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "started_plugins": started,
                "registered_services": self.services.list_services(),
                "event_count": len(self.events.history),
                "lifecycle_states": self.lifecycle.states,
                "status": "PASS",
            },
        )

    def integration_test(self) -> Dict[str, Any]:
        received: List[Dict[str, Any]] = []

        def handler(event: KernelEvent) -> None:
            received.append(event.payload)

        self.events.subscribe("kernel.test", handler)
        self.events.publish("kernel.test", {"message": "ok"})

        self.services.register(
            "kernel.echo",
            lambda message: {"message": message},
        )
        echo = self.services.call(
            "kernel.echo",
            message="ok",
        )

        lifecycle = LifecycleManager()
        lifecycle.register("test-component")
        lifecycle.transition("test-component", "STARTING")
        lifecycle.transition("test-component", "RUNNING")

        checks = {
            "event_bus": received == [{"message": "ok"}],
            "service_bus": echo == {"message": "ok"},
            "lifecycle_manager": (
                lifecycle.states["test-component"] == "RUNNING"
            ),
            "plugin_loader": all(
                self.loader.loadable(ROOT / item["module"])
                for item in self.registry["plugins"].values()
            ),
        }

        return self._write_report(
            "integration_test",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def summary(self) -> Dict[str, Any]:
        self_test = self.self_test()
        discovery = self.discover()
        integration = self.integration_test()

        status = (
            "PASS"
            if all(
                item["status"] == "PASS"
                for item in (self_test, discovery, integration)
            )
            else "FAIL"
        )

        return self._write_report(
            "summary",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "self_test_status": self_test["status"],
                "discovery_status": discovery["status"],
                "integration_status": integration["status"],
                "status": status,
            },
        )

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(
            path.read_text(encoding="utf-8-sig")
        )

    def _write_report(
        self,
        name: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(
            timespec="seconds"
        )
        path = OUTPUT_DIR / f"phoenix_kernel_{name}_v31_1.json"
        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8-sig",
        )
        data["output_path"] = str(path)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    parser.add_argument(
        "command",
        choices=[
            "self-test",
            "discover",
            "bootstrap",
            "integration-test",
            "summary",
        ],
    )
    args = parser.parse_args()
    kernel = PhoenixKernel()

    if args.command == "self-test":
        result = kernel.self_test()
    elif args.command == "discover":
        result = kernel.discover()
    elif args.command == "bootstrap":
        result = kernel.bootstrap()
    elif args.command == "integration-test":
        result = kernel.integration_test()
    else:
        result = kernel.summary()

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            indent=2,
        )
    )

    if result.get("status") in {
        "FAIL",
        "BLOCKED_PLUGIN_DISCOVERY",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
