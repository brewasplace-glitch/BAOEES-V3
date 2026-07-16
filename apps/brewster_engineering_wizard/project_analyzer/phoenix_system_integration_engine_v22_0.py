from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME = "Phoenix Autonomous System Integration Engine"
ENGINE_VERSION = "v22.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/system_integration_policy_v22_0.json"
REGISTRY_PATH = ROOT / "configs/phoenix/system_integration_registry_v22_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v22_0"


class SystemIntegrationError(RuntimeError):
    pass


class PhoenixSystemIntegrationEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.registry = self._read_json(REGISTRY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "registry_exists": REGISTRY_PATH.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "registry_has_components": bool(self.registry.get("components")),
            "lifecycle_defined": bool(self.registry.get("lifecycle")),
            "output_writable": self._writable(OUTPUT_DIR),
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
        discovered: List[Dict[str, Any]] = []
        for component_id, definition in self.registry["components"].items():
            module_path = ROOT / definition["module"]
            discovered.append(
                {
                    "component_id": component_id,
                    "module": definition["module"],
                    "exists": module_path.is_file(),
                    "loadable": self._loadable(module_path),
                    "capabilities": definition.get("capabilities", []),
                    "lifecycle_state": definition.get("lifecycle_state", "UNKNOWN"),
                }
            )

        status = "PASS" if all(
            item["exists"] and item["loadable"] for item in discovered
        ) else "FAIL"

        return self._write_report(
            "discovery",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "components": discovered,
                "status": status,
            },
        )

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        components = self.registry.get("components", {})
        component_ids = set(components.keys())

        for component_id, definition in components.items():
            module_path = ROOT / definition["module"]
            if not module_path.is_file():
                errors.append(
                    f"Module ontbreekt voor {component_id}: {definition['module']}"
                )

            for dependency in definition.get("dependencies", []):
                if dependency not in component_ids:
                    errors.append(
                        f"Ontbrekende dependency {dependency} voor {component_id}"
                    )

            state = definition.get("lifecycle_state")
            if state not in self.registry["lifecycle"]["allowed_states"]:
                errors.append(
                    f"Ongeldige lifecycle_state {state} voor {component_id}"
                )

        try:
            self._resolve_order(list(components.keys()))
        except SystemIntegrationError as exc:
            errors.append(str(exc))

        return self._write_report(
            "validation",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "component_count": len(components),
                "errors": errors,
                "status": "PASS" if not errors else "FAIL",
            },
        )

    def health(self) -> Dict[str, Any]:
        rows = []
        overall = True

        for component_id in self._resolve_order(
            list(self.registry["components"].keys())
        ):
            definition = self.registry["components"][component_id]
            module_path = ROOT / definition["module"]

            checks = {
                "exists": module_path.is_file(),
                "loadable": self._loadable(module_path),
                "dependencies_registered": all(
                    dependency in self.registry["components"]
                    for dependency in definition.get("dependencies", [])
                ),
                "lifecycle_active": definition.get("lifecycle_state")
                in {"ACTIVE", "STABLE"},
            }
            healthy = all(checks.values())
            overall = overall and healthy

            rows.append(
                {
                    "component_id": component_id,
                    "checks": checks,
                    "status": "HEALTHY" if healthy else "UNHEALTHY",
                }
            )

        return self._write_report(
            "health",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "components": rows,
                "status": "PASS" if overall else "FAIL",
            },
        )

    def integration_plan(self) -> Dict[str, Any]:
        validation = self.validate()
        if validation["status"] != "PASS":
            return self._write_report(
                "integration_plan",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "validation": validation,
                    "status": "BLOCKED_INVALID_REGISTRY",
                },
            )

        ordered = self._resolve_order(
            list(self.registry["components"].keys())
        )
        stages = []
        for sequence, component_id in enumerate(ordered, start=1):
            definition = self.registry["components"][component_id]
            stages.append(
                {
                    "sequence": sequence,
                    "component_id": component_id,
                    "dependencies": definition.get("dependencies", []),
                    "capabilities": definition.get("capabilities", []),
                    "lifecycle_state": definition.get("lifecycle_state"),
                    "status": "PLANNED",
                }
            )

        return self._write_report(
            "integration_plan",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "mode": "DRY_RUN",
                "stages": stages,
                "automatic_execution": False,
                "status": "PASS",
            },
        )

    def _resolve_order(self, requested: List[str]) -> List[str]:
        components = self.registry["components"]
        visiting: Set[str] = set()
        visited: Set[str] = set()
        ordered: List[str] = []

        def visit(component_id: str) -> None:
            if component_id in visited:
                return
            if component_id in visiting:
                raise SystemIntegrationError(
                    f"Circulaire dependency bij {component_id}"
                )
            if component_id not in components:
                raise SystemIntegrationError(
                    f"Onbekend component: {component_id}"
                )

            visiting.add(component_id)
            for dependency in components[component_id].get(
                "dependencies", []
            ):
                visit(dependency)
            visiting.remove(component_id)
            visited.add(component_id)
            ordered.append(component_id)

        for component_id in requested:
            visit(component_id)
        return ordered

    def _loadable(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            return spec is not None and spec.loader is not None
        except Exception:
            return False

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(
        self,
        name: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"system_integration_{name}_v22_0.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["report_path"] = str(path)
        return data

    def _writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    parser.add_argument(
        "command",
        choices=[
            "self-test",
            "discover",
            "validate",
            "health",
            "plan",
        ],
    )
    args = parser.parse_args()

    engine = PhoenixSystemIntegrationEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "discover":
        result = engine.discover()
    elif args.command == "validate":
        result = engine.validate()
    elif args.command == "health":
        result = engine.health()
    else:
        result = engine.integration_plan()

    print(json.dumps(result, ensure_ascii=True, indent=2))

    if result.get("status") in {
        "FAIL",
        "BLOCKED_INVALID_REGISTRY",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
