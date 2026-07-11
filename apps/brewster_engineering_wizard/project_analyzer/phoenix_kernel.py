from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ENGINE_NAME = "Phoenix Kernel"
ENGINE_VERSION = "v10.0"

def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")

PROJECT_ROOT = find_project_root()
KERNEL_POLICY = PROJECT_ROOT / "configs" / "phoenix" / "phoenix_kernel_policy_v10_0.json"
KERNEL_WORKFLOWS = PROJECT_ROOT / "configs" / "phoenix" / "phoenix_kernel_workflows_v10_0.json"
RUNTIME_DIR = PROJECT_ROOT / "outputs" / "runtime"
ORCHESTRATOR = PROJECT_ROOT / "apps" / "brewster_engineering_wizard" / "project_analyzer" / "phoenix_main_runner_orchestrator.py"

class PhoenixKernel:
    def __init__(self) -> None:
        self.policy = self._read_json(KERNEL_POLICY)
        self.workflows = self._read_json(KERNEL_WORKFLOWS)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "git_directory_exists": (PROJECT_ROOT / ".git").exists(),
            "policy_exists": KERNEL_POLICY.exists(),
            "workflows_exists": KERNEL_WORKFLOWS.exists(),
            "orchestrator_exists": ORCHESTRATOR.exists(),
            "runtime_writable": self._directory_writable(RUNTIME_DIR),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        return {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }

    def start_project(self, workflow: str, mode: str, approval_token: str) -> Dict[str, Any]:
        if workflow not in self.workflows["workflows"]:
            return self._report({
                "status": "BLOCKED_UNKNOWN_WORKFLOW",
                "workflow": workflow,
                "mode": mode,
            })

        if mode == "execute" and approval_token != self.policy["required_approval_token"]:
            return self._report({
                "status": "BLOCKED_NO_GO",
                "workflow": workflow,
                "mode": mode,
            })

        mapped = self.workflows["workflows"][workflow]["orchestrator_workflow"]
        command: List[str] = [sys.executable, str(ORCHESTRATOR)]

        if mode == "plan":
            command += ["plan", "--workflow", mapped]
        elif mode == "execute":
            command += ["execute", "--workflow", mapped, "--approval-token", approval_token]
        else:
            return self._report({
                "status": "BLOCKED_INVALID_MODE",
                "workflow": workflow,
                "mode": mode,
            })

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        status = "PASS" if completed.returncode == 0 else "FAIL"
        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "workflow": workflow,
            "mapped_orchestrator_workflow": mapped,
            "mode": mode,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "status": status,
            "automatic_commit_push": False,
        }
        return self._report(result)

    def status(self) -> Dict[str, Any]:
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return self._report({
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "branch": branch.stdout.strip(),
            "working_tree_clean": not git_status.stdout.strip(),
            "git_status": git_status.stdout,
            "available_workflows": sorted(self.workflows["workflows"].keys()),
            "default_mode": self.policy["default_mode"],
            "status": "PASS",
        })

    def _report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        result.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
        path = RUNTIME_DIR / f"phoenix_kernel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        result["report_path"] = str(path)
        return result

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _directory_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / f".phoenix_kernel_probe_{os.getpid()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")
    sub.add_parser("status")

    start = sub.add_parser("start-project")
    start.add_argument("--workflow", default="platform_foundation")
    start.add_argument("--mode", choices=["plan", "execute"], default="plan")
    start.add_argument("--approval-token", default="")

    args = parser.parse_args()
    kernel = PhoenixKernel()

    if args.command == "self-test":
        result = kernel.self_test()
    elif args.command == "status":
        result = kernel.status()
    else:
        result = kernel.start_project(args.workflow, args.mode, args.approval_token)

    print(json.dumps(result, ensure_ascii=True, indent=2))

    if result.get("status") in {
        "FAIL",
        "BLOCKED_UNKNOWN_WORKFLOW",
        "BLOCKED_NO_GO",
        "BLOCKED_INVALID_MODE",
    }:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
