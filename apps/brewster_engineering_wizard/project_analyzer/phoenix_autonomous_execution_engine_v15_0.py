from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME = "Phoenix Autonomous Execution Engine"
ENGINE_VERSION = "v15.0"

def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT = find_root()
POLICY = ROOT / "configs/phoenix/autonomous_execution_policy_v15_0.json"
DEFAULT_PLAN = ROOT / "outputs/runtime/v14_0/ai_planner_plan_v14_0.json"
OUT = ROOT / "outputs/runtime/v15_0"
STATE = OUT / "state"
EVIDENCE = OUT / "evidence"
EVENTS = OUT / "events"

class ExecutionError(RuntimeError):
    pass

class ExecutionEngine:
    def __init__(self) -> None:
        self.policy = self.read(POLICY)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY.exists(),
            "python_supported": sys.version_info >= (3, 10),
            "output_writable": self.writable(OUT),
            "state_writable": self.writable(STATE),
            "evidence_writable": self.writable(EVIDENCE),
        }
        return self.save("self_test", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def validate(self, plan_path: Path) -> Dict[str, Any]:
        errors: List[str] = []
        if not plan_path.is_file():
            errors.append(f"Plan ontbreekt: {plan_path}")
            return self.validation_result(plan_path, errors)

        plan = self.read(plan_path)
        tasks = plan.get("tasks", [])
        ids = [task.get("task_id", "") for task in tasks]
        id_set = set(ids)

        if not tasks:
            errors.append("Plan bevat geen taken.")
        if len(ids) != len(id_set):
            errors.append("Dubbele task_id gevonden.")
        if plan.get("status") not in {"PASS", "PARTIAL"}:
            errors.append("Planstatus is niet uitvoerbaar.")
        if plan.get("automatic_execution") is not False:
            errors.append("Plan mist automatic_execution=false.")

        for task in tasks:
            for dependency in task.get("dependencies", []):
                if dependency not in id_set:
                    errors.append(
                        f"Ontbrekende dependency {dependency} voor {task.get('task_id')}"
                    )

        try:
            self.resolve(tasks)
        except ExecutionError as exc:
            errors.append(str(exc))

        return self.validation_result(plan_path, errors)

    def dry_run(self, plan_path: Path, execution_id: str) -> Dict[str, Any]:
        validation = self.validate(plan_path)
        if validation["status"] != "PASS":
            return self.save("dry_run", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "execution_id": execution_id,
                "validation": validation,
                "status": "BLOCKED_INVALID_PLAN",
            })

        plan = self.read(plan_path)
        ordered = self.resolve(plan["tasks"])
        queue = []
        for index, task in enumerate(ordered, start=1):
            queue.append({
                "task_id": task["task_id"],
                "description": task.get("description", ""),
                "dependencies": task.get("dependencies", []),
                "sequence": index,
                "status": "PENDING",
                "execution_mode": task.get("execution_mode", "virtual"),
            })

        state = {
            "execution_id": execution_id,
            "plan_path": str(plan_path),
            "plan_sha256": self.sha256(plan_path),
            "mode": "DRY_RUN",
            "status": "PLANNED",
            "queue": queue,
            "completed_tasks": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        state_path = self.write_state(state)

        return self.save("dry_run", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "queue": queue,
            "state_path": str(state_path),
            "status": "PASS",
            "automatic_commit_push": False,
        })

    def execute(self, plan_path: Path, execution_id: str, token: str, resume: bool = False) -> Dict[str, Any]:
        if token != self.policy["required_approval_token"]:
            return self.blocked(execution_id, "BLOCKED_NO_GO", resume)
        if not self.repository_clean():
            return self.blocked(execution_id, "BLOCKED_REPOSITORY_PREFLIGHT", resume)

        validation = self.validate(plan_path)
        if validation["status"] != "PASS":
            return self.blocked(execution_id, "BLOCKED_INVALID_PLAN", resume)

        state_path = self.state_path(execution_id)
        if resume:
            if not state_path.is_file():
                return self.blocked(execution_id, "BLOCKED_NO_CHECKPOINT", True)
            state = self.read(state_path)
        else:
            self.dry_run(plan_path, execution_id)
            state = self.read(state_path)
            state["mode"] = "EXECUTE"

        completed: Set[str] = set(state.get("completed_tasks", []))
        results: List[Dict[str, Any]] = []
        state["status"] = "RUNNING"
        self.write_state(state)

        for task in state["queue"]:
            task_id = task["task_id"]
            if task_id in completed:
                continue
            if not all(dep in completed for dep in task.get("dependencies", [])):
                state["status"] = "FAILED"
                state["failed_task"] = task_id
                self.write_state(state)
                return self.save("execution", {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "execution_id": execution_id,
                    "results": results,
                    "status": "FAILED_DEPENDENCY_GATE",
                })

            result = self.execute_task(task)
            results.append(result)
            self.write_event(execution_id, result)
            if result["status"] != "PASS":
                state["status"] = "FAILED"
                state["failed_task"] = task_id
                self.write_state(state)
                return self.save("execution", {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "execution_id": execution_id,
                    "results": results,
                    "status": "FAILED_REQUIRED_TASK",
                })

            completed.add(task_id)
            task["status"] = "PASS"
            state["completed_tasks"] = sorted(completed)
            state["last_checkpoint"] = task_id
            self.write_state(state)
            self.write_evidence(execution_id, task, result)

        state["status"] = "PASS"
        state["completed_at"] = datetime.now().isoformat(timespec="seconds")
        self.write_state(state)

        return self.save("execution", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "mode": "RESUME" if resume else "EXECUTE",
            "completed_tasks": sorted(completed),
            "results": results,
            "status": "PASS",
            "automatic_commit_push": False,
        })

    def status(self, execution_id: str) -> Dict[str, Any]:
        path = self.state_path(execution_id)
        if not path.is_file():
            return self.save("status", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "execution_id": execution_id,
                "status": "NOT_FOUND",
            })
        return self.save("status", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "state": self.read(path),
            "status": "PASS",
        })

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        mode = task.get("execution_mode", "virtual")
        if mode == "virtual":
            return {
                "task_id": task["task_id"],
                "mode": mode,
                "status": "PASS",
                "message": "Virtuele taak gecontroleerd voltooid.",
            }
        return {
            "task_id": task["task_id"],
            "mode": mode,
            "status": "FAIL",
            "message": "Alleen virtual execution is in v15.0 standaard toegestaan.",
        }

    def resolve(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id = {task["task_id"]: task for task in tasks}
        visiting: Set[str] = set()
        visited: Set[str] = set()
        ordered: List[Dict[str, Any]] = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            if task_id in visiting:
                raise ExecutionError(f"Circulaire taakafhankelijkheid: {task_id}")
            if task_id not in by_id:
                raise ExecutionError(f"Onbekende task_id: {task_id}")
            visiting.add(task_id)
            for dependency in by_id[task_id].get("dependencies", []):
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)
            ordered.append(by_id[task_id])

        for task_id in by_id:
            visit(task_id)
        return ordered

    def validation_result(self, plan_path: Path, errors: List[str]) -> Dict[str, Any]:
        return self.save("validation", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "plan_path": str(plan_path),
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
        })

    def blocked(self, execution_id: str, status: str, resume: bool) -> Dict[str, Any]:
        return self.save("execution", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "mode": "RESUME" if resume else "EXECUTE",
            "status": status,
            "automatic_commit_push": False,
        })

    def repository_clean(self) -> bool:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0 and not result.stdout.strip()

    def state_path(self, execution_id: str) -> Path:
        safe = "".join(c for c in execution_id if c.isalnum() or c in "-_").strip()
        if not safe:
            raise ExecutionError("Ongeldige execution_id.")
        return STATE / f"{safe}.json"

    def write_state(self, state: Dict[str, Any]) -> Path:
        path = self.state_path(state["execution_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        return path

    def write_event(self, execution_id: str, event: Dict[str, Any]) -> None:
        directory = EVENTS / execution_id
        directory.mkdir(parents=True, exist_ok=True)
        index = len(list(directory.glob("*.json"))) + 1
        (directory / f"{index:04d}_{event['task_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )

    def write_evidence(self, execution_id: str, task: Dict[str, Any], result: Dict[str, Any]) -> None:
        directory = EVIDENCE / execution_id
        directory.mkdir(parents=True, exist_ok=True)
        evidence = {
            "execution_id": execution_id,
            "task": task,
            "result": result,
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }
        (directory / f"{task['task_id']}.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )

    def save(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUT.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUT / f"autonomous_execution_{name}_v15_0.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["report_path"] = str(path)
        return data

    def read(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False

def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")

    for name in ("validate", "dry-run", "execute", "resume"):
        item = sub.add_parser(name)
        item.add_argument("--plan-path", default=str(DEFAULT_PLAN))
        if name != "validate":
            item.add_argument("--execution-id", default="phoenix-core-v15")
        if name in {"execute", "resume"}:
            item.add_argument("--approval-token", default="")

    status = sub.add_parser("status")
    status.add_argument("--execution-id", default="phoenix-core-v15")

    args = parser.parse_args()
    engine = ExecutionEngine()

    if args.command == "self-test":
        result = engine.self_test()
    elif args.command == "validate":
        result = engine.validate(Path(args.plan_path))
    elif args.command == "dry-run":
        result = engine.dry_run(Path(args.plan_path), args.execution_id)
    elif args.command == "execute":
        result = engine.execute(Path(args.plan_path), args.execution_id, args.approval_token)
    elif args.command == "resume":
        result = engine.execute(Path(args.plan_path), args.execution_id, args.approval_token, True)
    else:
        result = engine.status(args.execution_id)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {
        "FAIL",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_INVALID_PLAN",
        "BLOCKED_NO_CHECKPOINT",
        "FAILED_DEPENDENCY_GATE",
        "FAILED_REQUIRED_TASK",
    }:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
