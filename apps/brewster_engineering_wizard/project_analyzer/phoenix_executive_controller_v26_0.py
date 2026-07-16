from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME = "Phoenix Executive Controller"
ENGINE_VERSION = "v26.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/executive_controller_policy_v26_0.json"
REGISTRY_PATH = ROOT / "configs/phoenix/executive_controller_registry_v26_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v26_0"
STATE_DIR = OUTPUT_DIR / "state"


class ExecutiveControllerError(RuntimeError):
    pass


class PhoenixExecutiveController:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.registry = self._read_json(REGISTRY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "registry_exists": REGISTRY_PATH.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "components_registered": bool(self.registry.get("components")),
            "workflows_registered": bool(self.registry.get("workflows")),
            "registry_valid": self._registry_valid(),
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
        components = []
        for component_id, definition in self.registry["components"].items():
            module_path = ROOT / definition["module"]
            components.append(
                {
                    "component_id": component_id,
                    "module": definition["module"],
                    "exists": module_path.is_file(),
                    "dependencies": definition.get("dependencies", []),
                    "priority": definition.get("priority", 100),
                    "role": definition.get("role", "UNKNOWN"),
                }
            )

        return self._write_report(
            "discovery",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "components": components,
                "status": (
                    "PASS"
                    if all(item["exists"] for item in components)
                    else "FAIL"
                ),
            },
        )

    def validate(self, workflow_id: str) -> Dict[str, Any]:
        errors: List[str] = []
        components = self.registry["components"]

        if workflow_id not in self.registry["workflows"]:
            errors.append(f"Onbekende workflow: {workflow_id}")
        else:
            workflow = self.registry["workflows"][workflow_id]
            for component_id in workflow["components"]:
                if component_id not in components:
                    errors.append(
                        f"Niet-geregistreerd component in workflow: {component_id}"
                    )

        for component_id, definition in components.items():
            module_path = ROOT / definition["module"]
            if not module_path.is_file():
                errors.append(
                    f"Module ontbreekt voor {component_id}: {definition['module']}"
                )
            for dependency in definition.get("dependencies", []):
                if dependency not in components:
                    errors.append(
                        f"Ontbrekende dependency {dependency} voor {component_id}"
                    )

        try:
            if workflow_id in self.registry["workflows"]:
                self._resolve_order(
                    self.registry["workflows"][workflow_id]["components"]
                )
        except ExecutiveControllerError as exc:
            errors.append(str(exc))

        return self._write_report(
            "validation",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "workflow_id": workflow_id,
                "errors": errors,
                "status": "PASS" if not errors else "FAIL",
            },
        )

    def plan(self, workflow_id: str, run_id: str) -> Dict[str, Any]:
        validation = self.validate(workflow_id)
        if validation["status"] != "PASS":
            return self._write_report(
                "plan",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "workflow_id": workflow_id,
                    "run_id": run_id,
                    "status": "BLOCKED_INVALID_WORKFLOW",
                },
            )

        requested = self.registry["workflows"][workflow_id]["components"]
        ordered = self._resolve_order(requested)
        stages = []

        for sequence, component_id in enumerate(ordered, start=1):
            definition = self.registry["components"][component_id]
            stages.append(
                {
                    "sequence": sequence,
                    "component_id": component_id,
                    "role": definition["role"],
                    "priority": definition["priority"],
                    "dependencies": definition.get("dependencies", []),
                    "mode": "SELF_TEST",
                    "status": "PLANNED",
                }
            )

        state = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "status": "PLANNED",
            "stages": stages,
            "completed_components": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        state_path = self._write_state(state)

        return self._write_report(
            "plan",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "stages": stages,
                "state_path": str(state_path),
                "automatic_execution": False,
                "status": "PASS",
            },
        )

    def health(self) -> Dict[str, Any]:
        results = []
        overall = True

        for component_id in self._resolve_order(
            list(self.registry["components"].keys())
        ):
            definition = self.registry["components"][component_id]
            module_path = ROOT / definition["module"]
            healthy = module_path.is_file()
            overall = overall and healthy
            results.append(
                {
                    "component_id": component_id,
                    "module_exists": healthy,
                    "status": "HEALTHY" if healthy else "UNHEALTHY",
                }
            )

        return self._write_report(
            "health",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "components": results,
                "status": "PASS" if overall else "FAIL",
            },
        )

    def executive_summary(self, workflow_id: str) -> Dict[str, Any]:
        discovery = self.discover()
        validation = self.validate(workflow_id)
        health = self.health()

        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "workflow_id": workflow_id,
            "discovery_status": discovery["status"],
            "validation_status": validation["status"],
            "health_status": health["status"],
            "safe_to_plan": all(
                status == "PASS"
                for status in (
                    discovery["status"],
                    validation["status"],
                    health["status"],
                )
            ),
            "automatic_execution": False,
            "status": "PASS",
        }
        return self._write_report("executive_summary", result)

    def _resolve_order(self, requested: List[str]) -> List[str]:
        components = self.registry["components"]
        visiting: Set[str] = set()
        visited: Set[str] = set()
        ordered: List[str] = []

        def visit(component_id: str) -> None:
            if component_id in visited:
                return
            if component_id in visiting:
                raise ExecutiveControllerError(
                    f"Circulaire dependency bij {component_id}"
                )
            if component_id not in components:
                raise ExecutiveControllerError(
                    f"Onbekend component: {component_id}"
                )

            visiting.add(component_id)
            dependencies = components[component_id].get("dependencies", [])
            for dependency in dependencies:
                visit(dependency)
            visiting.remove(component_id)
            visited.add(component_id)
            ordered.append(component_id)

        for component_id in sorted(
            requested,
            key=lambda item: components[item].get("priority", 100),
        ):
            visit(component_id)

        return ordered

    def _registry_valid(self) -> bool:
        try:
            for workflow in self.registry.get("workflows", {}).values():
                self._resolve_order(workflow.get("components", []))
            return True
        except ExecutiveControllerError:
            return False

    def _state_path(self, run_id: str) -> Path:
        safe = "".join(
            character
            for character in run_id
            if character.isalnum() or character in "-_"
        ).strip()
        if not safe:
            raise ExecutiveControllerError("Ongeldige run_id.")
        return STATE_DIR / f"{safe}.json"

    def _write_state(self, state: Dict[str, Any]) -> Path:
        path = self._state_path(state["run_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        return path

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"executive_controller_{name}_v26_0.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["report_path"] = str(path)
        return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")
    sub.add_parser("discover")
    sub.add_parser("health")

    validate = sub.add_parser("validate")
    validate.add_argument(
        "--workflow-id",
        default="phoenix_executive_core",
    )

    plan = sub.add_parser("plan")
    plan.add_argument(
        "--workflow-id",
        default="phoenix_executive_core",
    )
    plan.add_argument(
        "--run-id",
        default="phoenix-core-v26",
    )

    summary = sub.add_parser("summary")
    summary.add_argument(
        "--workflow-id",
        default="phoenix_executive_core",
    )

    args = parser.parse_args()
    engine = PhoenixExecutiveController()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "discover":
        result = engine.discover()
    elif args.command == "health":
        result = engine.health()
    elif args.command == "validate":
        result = engine.validate(args.workflow_id)
    elif args.command == "plan":
        result = engine.plan(args.workflow_id, args.run_id)
    else:
        result = engine.executive_summary(args.workflow_id)

    print(json.dumps(result, ensure_ascii=True, indent=2))

    if result.get("status") in {
        "FAIL",
        "BLOCKED_INVALID_WORKFLOW",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
