from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Workflow Supervisor & Recovery Manager"
ENGINE_VERSION = "v16.0"


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


PROJECT_ROOT = find_project_root()
POLICY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "workflow_supervisor_policy_v16_0.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "runtime" / "v16_0"
EXECUTION_STATE_DIR = PROJECT_ROOT / "outputs" / "runtime" / "v15_0" / "state"
EXECUTION_ENGINE = PROJECT_ROOT / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_autonomous_execution_engine_v15_0.py"
DEFAULT_PLAN = PROJECT_ROOT / "outputs" / "runtime" / "v14_0" / "ai_planner_plan_v14_0.json"


class PhoenixWorkflowSupervisor:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "policy_exists": POLICY_PATH.exists(),
            "execution_engine_exists": EXECUTION_ENGINE.exists(),
            "python_version_supported": sys.version_info >= (3, 10),
            "output_directory_writable": self._writable(OUTPUT_DIR),
        }
        return self._write_report("self_test", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })

    def health(self) -> Dict[str, Any]:
        checks = {
            "repository_clean": self._repository_clean(),
            "execution_engine_available": EXECUTION_ENGINE.is_file(),
            "default_plan_available": DEFAULT_PLAN.is_file(),
            "execution_state_directory_exists": EXECUTION_STATE_DIR.exists(),
        }
        status = "PASS" if checks["execution_engine_available"] and checks["default_plan_available"] else "FAIL"
        return self._write_report("health", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": status,
        })

    def inspect(self, execution_id: str) -> Dict[str, Any]:
        state_path = self._state_path(execution_id)
        if not state_path.is_file():
            incident = self._incident(execution_id, "STATE_NOT_FOUND", "MEDIUM", "Geen v15-checkpoint gevonden.", {})
            return self._write_report("inspection", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "execution_id": execution_id,
                "incident": incident,
                "status": "NOT_FOUND",
            })

        state = self._read_json(state_path)
        incidents = self._diagnose(execution_id, state)
        return self._write_report("inspection", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "state_path": str(state_path),
            "state": state,
            "incidents": incidents,
            "status": "PASS" if not incidents else "ATTENTION_REQUIRED",
        })

    def recovery_plan(self, execution_id: str) -> Dict[str, Any]:
        state_path = self._state_path(execution_id)
        if not state_path.is_file():
            return self._write_report("recovery_plan", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "execution_id": execution_id,
                "status": "BLOCKED_NO_CHECKPOINT",
            })

        state = self._read_json(state_path)
        incidents = self._diagnose(execution_id, state)
        strategy = self._select_strategy(state)
        return self._write_report("recovery_plan", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "state_status": state.get("status", "UNKNOWN"),
            "last_checkpoint": state.get("last_checkpoint"),
            "completed_tasks": state.get("completed_tasks", []),
            "incidents": incidents,
            "strategy": strategy,
            "mode": "DRY_RUN",
            "automatic_execution": False,
            "automatic_commit_push": False,
            "status": "PASS",
        })

    def recover(self, execution_id: str, plan_path: Path, approval_token: str) -> Dict[str, Any]:
        if approval_token != self.policy["required_approval_token"]:
            return self._blocked(execution_id, "BLOCKED_NO_GO")
        if not self._repository_clean():
            return self._blocked(execution_id, "BLOCKED_REPOSITORY_PREFLIGHT")

        recovery = self.recovery_plan(execution_id)
        if recovery.get("status") != "PASS":
            return self._blocked(execution_id, recovery.get("status", "BLOCKED_RECOVERY_PLAN"))

        action = recovery["strategy"]["action"]
        if action == "NO_ACTION":
            return self._write_report("recovery", {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "execution_id": execution_id,
                "strategy": action,
                "status": "PASS",
                "message": "Geen herstelactie nodig.",
            })
        if action != "RESUME_FROM_CHECKPOINT":
            return self._blocked(execution_id, "BLOCKED_UNSUPPORTED_RECOVERY_STRATEGY")

        command = [
            sys.executable,
            str(EXECUTION_ENGINE),
            "resume",
            "--plan-path",
            str(plan_path),
            "--execution-id",
            execution_id,
            "--approval-token",
            approval_token,
        ]
        completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        return self._write_report("recovery", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "strategy": action,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "automatic_commit_push": False,
        })

    def _diagnose(self, execution_id: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        incidents: List[Dict[str, Any]] = []
        status = state.get("status", "UNKNOWN")
        if status == "FAILED":
            incidents.append(self._incident(execution_id, "WORKFLOW_FAILED", "HIGH", f"Workflow faalde bij taak {state.get('failed_task', 'onbekend')}.", state))
        elif status == "RUNNING":
            incidents.append(self._incident(execution_id, "WORKFLOW_INCOMPLETE", "MEDIUM", "Workflow staat nog op RUNNING.", state))
        elif status == "PLANNED":
            incidents.append(self._incident(execution_id, "WORKFLOW_NOT_STARTED", "LOW", "Workflow is gepland maar nog niet uitgevoerd.", state))
        elif status != "PASS":
            incidents.append(self._incident(execution_id, "UNKNOWN_STATE", "MEDIUM", f"Onbekende workflowstatus: {status}", state))
        return incidents

    def _select_strategy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        status = state.get("status", "UNKNOWN")
        if status == "PASS":
            return {"action": "NO_ACTION", "reason": "Workflow is reeds succesvol afgerond."}
        if status in {"FAILED", "RUNNING", "PLANNED"}:
            return {
                "action": "RESUME_FROM_CHECKPOINT",
                "reason": "v15 resume valideert de bestaande state vÃ³Ã³r hervatting.",
                "max_retries": self.policy["max_resume_attempts"],
            }
        return {"action": "ESCALATE", "reason": "Geen veilige automatische herstelstrategie beschikbaar."}

    def _incident(self, execution_id: str, category: str, severity: str, message: str, state: Dict[str, Any]) -> Dict[str, Any]:
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{execution_id}"
        incident = {
            "incident_id": incident_id,
            "execution_id": execution_id,
            "category": category,
            "severity": severity,
            "message": message,
            "failed_task": state.get("failed_task"),
            "last_checkpoint": state.get("last_checkpoint"),
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }
        directory = OUTPUT_DIR / "incidents"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{incident_id}.json").write_text(json.dumps(incident, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        return incident

    def _state_path(self, execution_id: str) -> Path:
        safe = "".join(char for char in execution_id if char.isalnum() or char in "-_").strip()
        if not safe:
            raise RuntimeError("Ongeldige execution_id.")
        return EXECUTION_STATE_DIR / f"{safe}.json"

    def _blocked(self, execution_id: str, status: str) -> Dict[str, Any]:
        return self._write_report("recovery", {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "execution_id": execution_id,
            "status": status,
            "automatic_commit_push": False,
        })

    def _repository_clean(self) -> bool:
        completed = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        return completed.returncode == 0 and not completed.stdout.strip()

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"workflow_supervisor_{name}_v16_0.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        data["report_path"] = str(path)
        return data

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".phoenix_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    sub.add_parser("health")

    for name in ("inspect", "recovery-plan"):
        item = sub.add_parser(name)
        item.add_argument("--execution-id", default="phoenix-core-v15")

    recover = sub.add_parser("recover")
    recover.add_argument("--execution-id", default="phoenix-core-v15")
    recover.add_argument("--plan-path", default=str(DEFAULT_PLAN))
    recover.add_argument("--approval-token", default="")
    args = parser.parse_args()

    supervisor = PhoenixWorkflowSupervisor()
    if args.command == "self-test":
        result = supervisor.self_test()
    elif args.command == "health":
        result = supervisor.health()
    elif args.command == "inspect":
        result = supervisor.inspect(args.execution_id)
    elif args.command == "recovery-plan":
        result = supervisor.recovery_plan(args.execution_id)
    else:
        result = supervisor.recover(args.execution_id, Path(args.plan_path), args.approval_token)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {
        "FAIL",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_NO_CHECKPOINT",
        "BLOCKED_RECOVERY_PLAN",
        "BLOCKED_UNSUPPORTED_RECOVERY_STRATEGY",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
