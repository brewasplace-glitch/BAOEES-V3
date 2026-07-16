from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Full Autonomous Project Engine"
ENGINE_VERSION = "v20.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/full_autonomous_project_policy_v20_0.json"
WORKFLOW_PATH = ROOT / "configs/phoenix/full_autonomous_project_workflow_v20_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v20_0"
STATE_DIR = OUTPUT_DIR / "state"

COMPONENTS = {
    "planner": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_ai_planner_v14_0.py",
    "execution": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_execution_engine_v15_0.py",
    "supervisor": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_workflow_supervisor_v16_0.py",
    "learning": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_autonomous_learning_engine_v17_0.py",
    "reasoning": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_knowledge_reasoning_v18_0.py",
    "multi_agent": ROOT / "apps/brewster_engineering_wizard/project_analyzer/phoenix_multi_agent_orchestrator_v19_0.py",
}


class PhoenixFullAutonomousProjectEngine:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.workflow = self._read_json(WORKFLOW_PATH)

    def self_test(self) -> Dict[str, Any]:
        component_checks = {
            name: path.is_file()
            for name, path in COMPONENTS.items()
        }
        checks = {
            "policy_exists": POLICY_PATH.is_file(),
            "workflow_exists": WORKFLOW_PATH.is_file(),
            "python_supported": sys.version_info >= (3, 10),
            "components_available": all(component_checks.values()),
        }
        return self._write_report(
            "self_test",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "checks": checks,
                "component_checks": component_checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            },
        )

    def plan(self, project_id: str, objective: str) -> Dict[str, Any]:
        stages = []
        for sequence, stage in enumerate(self.workflow["stages"], start=1):
            stages.append(
                {
                    "sequence": sequence,
                    "stage_id": stage["stage_id"],
                    "component": stage["component"],
                    "mode": stage["mode"],
                    "dependencies": stage.get("dependencies", []),
                    "status": "PLANNED",
                }
            )

        state = {
            "project_id": project_id,
            "objective": objective,
            "status": "PLANNED",
            "stages": stages,
            "completed_stages": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        state_path = self._write_state(state)

        return self._write_report(
            "plan",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "project_id": project_id,
                "objective": objective,
                "mode": "DRY_RUN",
                "stages": stages,
                "state_path": str(state_path),
                "automatic_execution": False,
                "status": "PASS",
            },
        )

    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        stage_ids = [stage["stage_id"] for stage in self.workflow["stages"]]
        stage_id_set = set(stage_ids)

        if len(stage_ids) != len(stage_id_set):
            errors.append("Dubbele stage_id gevonden.")

        for stage in self.workflow["stages"]:
            component = stage["component"]
            if component not in COMPONENTS:
                errors.append(f"Onbekende component: {component}")
            elif not COMPONENTS[component].is_file():
                errors.append(f"Component ontbreekt: {component}")

            for dependency in stage.get("dependencies", []):
                if dependency not in stage_id_set:
                    errors.append(
                        f"Ontbrekende dependency {dependency} voor {stage['stage_id']}"
                    )

        return self._write_report(
            "validation",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "errors": errors,
                "status": "PASS" if not errors else "FAIL",
            },
        )

    def execute(
        self,
        project_id: str,
        objective: str,
        approval_token: str,
    ) -> Dict[str, Any]:
        if approval_token != self.policy["required_approval_token"]:
            return self._write_report(
                "execution",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "project_id": project_id,
                    "status": "BLOCKED_NO_GO",
                },
            )

        if not self._repository_clean():
            return self._write_report(
                "execution",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "project_id": project_id,
                    "status": "BLOCKED_REPOSITORY_PREFLIGHT",
                },
            )

        validation = self.validate()
        if validation["status"] != "PASS":
            return self._write_report(
                "execution",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "project_id": project_id,
                    "status": "BLOCKED_INVALID_WORKFLOW",
                },
            )

        self.plan(project_id, objective)
        state_path = self._state_path(project_id)
        state = self._read_json(state_path)
        completed = set()
        results = []

        for stage in state["stages"]:
            if not all(dep in completed for dep in stage.get("dependencies", [])):
                state["status"] = "FAILED"
                state["failed_stage"] = stage["stage_id"]
                self._write_state(state)
                return self._write_report(
                    "execution",
                    {
                        "engine": ENGINE_NAME,
                        "version": ENGINE_VERSION,
                        "project_id": project_id,
                        "results": results,
                        "status": "FAILED_DEPENDENCY_GATE",
                    },
                )

            result = self._run_stage(stage)
            results.append(result)
            if result["status"] != "PASS":
                state["status"] = "FAILED"
                state["failed_stage"] = stage["stage_id"]
                self._write_state(state)
                return self._write_report(
                    "execution",
                    {
                        "engine": ENGINE_NAME,
                        "version": ENGINE_VERSION,
                        "project_id": project_id,
                        "results": results,
                        "status": "FAILED_REQUIRED_STAGE",
                    },
                )

            completed.add(stage["stage_id"])
            stage["status"] = "PASS"
            state["completed_stages"] = sorted(completed)
            self._write_state(state)

        state["status"] = "PASS"
        state["completed_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_state(state)

        return self._write_report(
            "execution",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "project_id": project_id,
                "results": results,
                "completed_stages": sorted(completed),
                "status": "PASS",
            },
        )

    def _run_stage(self, stage: Dict[str, Any]) -> Dict[str, Any]:
        component = stage["component"]
        mode = stage["mode"]
        script = COMPONENTS[component]

        commands = {
            ("planner", "self-test"): [sys.executable, str(script), "self-test"],
            ("execution", "self-test"): [sys.executable, str(script), "self-test"],
            ("supervisor", "self-test"): [sys.executable, str(script), "self-test"],
            ("learning", "self-test"): [sys.executable, str(script), "self-test"],
            ("reasoning", "self-test"): [sys.executable, str(script), "self-test"],
            ("multi_agent", "self-test"): [sys.executable, str(script), "self-test"],
        }

        command = commands.get((component, mode))
        if command is None:
            return {
                "stage_id": stage["stage_id"],
                "component": component,
                "mode": mode,
                "status": "FAIL",
                "message": "Niet-ondersteunde stagecombinatie.",
            }

        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "stage_id": stage["stage_id"],
            "component": component,
            "mode": mode,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
        }

    def _repository_clean(self) -> bool:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return completed.returncode == 0 and not completed.stdout.strip()

    def _state_path(self, project_id: str) -> Path:
        safe = "".join(
            char for char in project_id
            if char.isalnum() or char in "-_"
        ).strip()
        if not safe:
            raise RuntimeError("Ongeldige project_id.")
        return STATE_DIR / f"{safe}.json"

    def _write_state(self, state: Dict[str, Any]) -> Path:
        path = self._state_path(state["project_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        return path

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"full_autonomous_{name}_v20_0.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )
        data["report_path"] = str(path)
        return data

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{ENGINE_NAME} {ENGINE_VERSION}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")
    sub.add_parser("validate")

    plan = sub.add_parser("plan")
    plan.add_argument("--project-id", default="phoenix-core-v20")
    plan.add_argument(
        "--objective",
        default="Run the complete Phoenix Core autonomous pipeline safely.",
    )

    execute = sub.add_parser("execute")
    execute.add_argument("--project-id", default="phoenix-core-v20")
    execute.add_argument(
        "--objective",
        default="Run the complete Phoenix Core autonomous pipeline safely.",
    )
    execute.add_argument("--approval-token", default="")

    args = parser.parse_args()
    engine = PhoenixFullAutonomousProjectEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "validate":
        result = engine.validate()
    elif args.command == "plan":
        result = engine.plan(args.project_id, args.objective)
    else:
        result = engine.execute(
            args.project_id,
            args.objective,
            args.approval_token,
        )

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {
        "FAIL",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_INVALID_WORKFLOW",
        "FAILED_DEPENDENCY_GATE",
        "FAILED_REQUIRED_STAGE",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
