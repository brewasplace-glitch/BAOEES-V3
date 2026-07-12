from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ENGINE_NAME = "Phoenix Autonomous Workflow Engine"
ENGINE_VERSION = "v11.0"


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


PROJECT_ROOT = find_project_root()
REGISTRY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "autonomous_workflow_registry_v11_0.json"
POLICY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "autonomous_workflow_policy_v11_0.json"
STATE_DIR = PROJECT_ROOT / "outputs" / "runtime" / "workflow_state"
REPORT_DIR = PROJECT_ROOT / "outputs" / "runtime"
MAIN_RUNNER = PROJECT_ROOT / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_main_runner_orchestrator.py"


class WorkflowEngineError(RuntimeError):
    pass


class PhoenixAutonomousWorkflowEngine:
    def __init__(self) -> None:
        self.registry = self._read_json(REGISTRY_PATH)
        self.policy = self._read_json(POLICY_PATH)

    def self_test(self) -> Dict[str, Any]:
        workflows = self.registry.get("workflows", {})
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "git_directory_exists": (PROJECT_ROOT / ".git").exists(),
            "registry_exists": REGISTRY_PATH.exists(),
            "policy_exists": POLICY_PATH.exists(),
            "main_runner_exists": MAIN_RUNNER.exists(),
            "state_directory_writable": self._directory_writable(STATE_DIR),
            "workflows_registered": bool(workflows),
            "dependencies_valid": self._dependencies_valid(workflows),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def plan(self, workflow: str, project_id: str) -> Dict[str, Any]:
        ordered = self._resolve_order(self._workflow(workflow)["steps"])
        steps = []
        for name in ordered:
            definition = self._step(name)
            steps.append({
                "name": name,
                "description": definition.get("description", ""),
                "dependencies": definition.get("dependencies", []),
                "required": definition.get("required", True),
                "mode": definition.get("mode", "orchestrator"),
                "orchestrator_workflow": definition.get("orchestrator_workflow", ""),
                "status": "PENDING",
            })
        state = self._new_state(project_id, workflow, steps)
        state_path = self._write_state(state)
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "mode": "PLAN",
            "project_id": project_id,
            "workflow": workflow,
            "state_path": str(state_path),
            "steps": steps,
            "status": "PASS",
            "automatic_commit_push": False,
        })

    def validate(self, workflow: str, project_id: str) -> Dict[str, Any]:
        plan = self.plan(workflow, project_id)
        errors: List[str] = []
        for step in plan["steps"]:
            if step["mode"] == "orchestrator" and not step["orchestrator_workflow"]:
                errors.append(f"Geen orchestrator_workflow voor {step['name']}")
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "mode": "VALIDATE",
            "project_id": project_id,
            "workflow": workflow,
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
            "automatic_commit_push": False,
        })

    def execute(self, workflow: str, project_id: str, approval_token: str, resume: bool = False) -> Dict[str, Any]:
        if approval_token != self.policy["required_approval_token"]:
            return self._report({
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "mode": "RESUME" if resume else "EXECUTE",
                "project_id": project_id,
                "workflow": workflow,
                "status": "BLOCKED_NO_GO",
                "automatic_commit_push": False,
            })

        if not self._repository_clean():
            return self._report({
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "mode": "RESUME" if resume else "EXECUTE",
                "project_id": project_id,
                "workflow": workflow,
                "status": "BLOCKED_REPOSITORY_PREFLIGHT",
                "automatic_commit_push": False,
            })

        state = self._load_state(project_id, workflow) if resume else self._new_state(
            project_id,
            workflow,
            [{"name": name, "status": "PENDING"} for name in self._resolve_order(self._workflow(workflow)["steps"])],
        )
        state["status"] = "RUNNING"
        self._write_state(state)

        for item in state["steps"]:
            if resume and item.get("status") == "PASS":
                continue
            definition = self._step(item["name"])
            if definition.get("mode") == "virtual":
                item["status"] = "PASS"
                item["completed_at"] = datetime.now().isoformat(timespec="seconds")
                self._write_state(state)
                continue

            command = [
                sys.executable,
                str(MAIN_RUNNER),
                "execute",
                "--workflow",
                definition["orchestrator_workflow"],
                "--approval-token",
                approval_token,
            ]
            result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
            item.update({
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "completed_at": datetime.now().isoformat(timespec="seconds"),
            })
            self._write_state(state)
            if result.returncode != 0 and definition.get("required", True):
                state["status"] = "FAILED"
                state["failed_step"] = item["name"]
                self._write_state(state)
                return self._report({
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "project_id": project_id,
                    "workflow": workflow,
                    "status": "FAILED_REQUIRED_STEP",
                    "steps": state["steps"],
                    "automatic_commit_push": False,
                })

        state["status"] = "PASS"
        state["completed_at"] = datetime.now().isoformat(timespec="seconds")
        state_path = self._write_state(state)
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "workflow": workflow,
            "state_path": str(state_path),
            "status": "PASS",
            "steps": state["steps"],
            "automatic_commit_push": False,
        })

    def status(self, workflow: str, project_id: str) -> Dict[str, Any]:
        path = self._state_path(project_id, workflow)
        if not path.exists():
            return self._report({
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "project_id": project_id,
                "workflow": workflow,
                "status": "NOT_FOUND",
            })
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "project_id": project_id,
            "workflow": workflow,
            "state_path": str(path),
            "state": self._read_json(path),
            "status": "PASS",
        })

    def _workflow(self, name: str) -> Dict[str, Any]:
        workflows = self.registry.get("workflows", {})
        if name not in workflows:
            raise WorkflowEngineError(f"Onbekende workflow: {name}")
        return workflows[name]

    def _step(self, name: str) -> Dict[str, Any]:
        steps = self.registry.get("steps", {})
        if name not in steps:
            raise WorkflowEngineError(f"Onbekende stap: {name}")
        return steps[name]

    def _resolve_order(self, requested: Iterable[str]) -> List[str]:
        resolved: List[str] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise WorkflowEngineError(f"Circulaire afhankelijkheid: {name}")
            visiting.add(name)
            for dependency in self._step(name).get("dependencies", []):
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            resolved.append(name)

        for name in requested:
            visit(name)
        return resolved

    def _dependencies_valid(self, workflows: Dict[str, Any]) -> bool:
        try:
            for workflow in workflows.values():
                self._resolve_order(workflow["steps"])
            return True
        except WorkflowEngineError:
            return False

    def _repository_clean(self) -> bool:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        return result.returncode == 0 and not result.stdout.strip()

    def _new_state(self, project_id: str, workflow: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "project_id": project_id,
            "workflow": workflow,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "PLANNED",
            "steps": steps,
        }

    def _load_state(self, project_id: str, workflow: str) -> Dict[str, Any]:
        path = self._state_path(project_id, workflow)
        if not path.exists():
            raise WorkflowEngineError("Geen runtime-state gevonden om te hervatten.")
        return self._read_json(path)

    def _state_path(self, project_id: str, workflow: str) -> Path:
        safe_project = "".join(ch for ch in project_id if ch.isalnum() or ch in "-_").strip()
        safe_workflow = "".join(ch for ch in workflow if ch.isalnum() or ch in "-_").strip()
        if not safe_project or not safe_workflow:
            raise WorkflowEngineError("Ongeldige project-id of workflow.")
        return STATE_DIR / safe_project / f"{safe_workflow}.json"

    def _write_state(self, state: Dict[str, Any]) -> Path:
        path = self._state_path(state["project_id"], state["workflow"])
        path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        return path

    def _report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
        path = REPORT_DIR / f"phoenix_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        report["report_path"] = str(path)
        return report

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _directory_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / f".workflow_probe_{os.getpid()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    for command in ("plan", "validate", "execute", "resume", "status"):
        item = sub.add_parser(command)
        item.add_argument("--workflow", default="platform_foundation")
        item.add_argument("--project-id", default="phoenix-core")
        if command in ("execute", "resume"):
            item.add_argument("--approval-token", default="")
    args = parser.parse_args()
    engine = PhoenixAutonomousWorkflowEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "plan":
        result = engine.plan(args.workflow, args.project_id)
    elif args.command == "validate":
        result = engine.validate(args.workflow, args.project_id)
    elif args.command == "execute":
        result = engine.execute(args.workflow, args.project_id, args.approval_token)
    elif args.command == "resume":
        result = engine.execute(args.workflow, args.project_id, args.approval_token, resume=True)
    else:
        result = engine.status(args.workflow, args.project_id)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {"FAIL", "BLOCKED_NO_GO", "BLOCKED_REPOSITORY_PREFLIGHT", "FAILED_REQUIRED_STEP"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
