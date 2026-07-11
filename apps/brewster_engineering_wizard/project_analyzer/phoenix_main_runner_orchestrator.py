from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set

ENGINE_NAME = "Phoenix Main Runner Orchestrator"
ENGINE_VERSION = "v9.1"

def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")

PROJECT_ROOT = find_project_root()
REGISTRY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "main_runner_registry_v9_1.json"
POLICY_PATH = PROJECT_ROOT / "configs" / "phoenix" / "main_runner_policy_v9_1.json"
RUNTIME_DIR = PROJECT_ROOT / "outputs" / "runtime"

class OrchestratorError(RuntimeError):
    pass

class PhoenixMainRunnerOrchestrator:
    def __init__(self) -> None:
        self.registry = self._read_json(REGISTRY_PATH)
        self.policy = self._read_json(POLICY_PATH)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_path = RUNTIME_DIR / f"phoenix_main_runner_{stamp}.json"

    def self_test(self) -> Dict[str, Any]:
        modules = self.registry.get("modules", {})
        checks = {
            "project_root_exists": PROJECT_ROOT.exists(),
            "git_directory_exists": (PROJECT_ROOT / ".git").exists(),
            "registry_exists": REGISTRY_PATH.exists(),
            "policy_exists": POLICY_PATH.exists(),
            "runtime_writable": self._directory_writable(RUNTIME_DIR),
            "modules_registered": bool(modules),
            "dependencies_valid": self._dependencies_valid(modules),
            "python_version_supported": sys.version_info >= (3, 10),
        }
        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }
        self._write_report(result)
        return result

    def plan(self, workflow: str) -> Dict[str, Any]:
        definition = self._workflow(workflow)
        order = self._resolve_order(definition["modules"])
        modules = []
        for name in order:
            module = self._module(name)
            modules.append({
                "name": name,
                "description": module.get("description", ""),
                "dependencies": module.get("dependencies", []),
                "required": module.get("required", True),
                "mode": module.get("mode", "command"),
                "availability": self._availability(module),
                "command": module.get("command", []),
            })
        result = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "workflow": workflow,
            "execution_mode": "DRY_RUN",
            "modules": modules,
            "ready": all(x["availability"]["available"] or not x["required"] for x in modules),
            "automatic_commit_push": False,
        }
        self._write_report(result)
        return result

    def execute(self, workflow: str, token: str) -> Dict[str, Any]:
        report = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "workflow": workflow,
            "execution_mode": "EXECUTE",
            "approval_received": token == self.policy["required_approval_token"],
            "automatic_commit_push": False,
            "status": "NOT_STARTED",
            "modules": [],
        }
        if token != self.policy["required_approval_token"]:
            report["status"] = "BLOCKED_NO_GO"
            self._write_report(report)
            return report

        preflight = self._repository_preflight()
        report["repository_preflight"] = preflight
        if not preflight["ready"]:
            report["status"] = "BLOCKED_REPOSITORY_PREFLIGHT"
            self._write_report(report)
            return report

        plan = self.plan(workflow)
        if not plan["ready"]:
            report["status"] = "BLOCKED_UNAVAILABLE_REQUIRED_MODULE"
            self._write_report(report)
            return report

        for item in plan["modules"]:
            name = item["name"]
            module = self._module(name)
            if module.get("mode") == "virtual":
                report["modules"].append({"name": name, "status": "SKIPPED_VIRTUAL"})
                continue

            command = self._expand(module.get("command", []))
            completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
            entry = {
                "name": name,
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
            }
            report["modules"].append(entry)
            if completed.returncode != 0 and module.get("required", True):
                report["status"] = "FAILED_REQUIRED_MODULE"
                self._write_report(report)
                return report

        diff = subprocess.run(["git","diff","--check"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        report["post_validation"] = {
            "git_diff_check_passed": diff.returncode == 0,
            "output": diff.stdout + diff.stderr,
        }
        report["status"] = "PASS" if diff.returncode == 0 else "PASS_REVIEW_REQUIRED"
        self._write_report(report)
        return report

    def _workflow(self, name: str) -> Dict[str, Any]:
        workflows = self.registry.get("workflows", {})
        if name not in workflows:
            raise OrchestratorError(f"Onbekende workflow: {name}")
        return workflows[name]

    def _module(self, name: str) -> Dict[str, Any]:
        modules = self.registry.get("modules", {})
        if name not in modules:
            raise OrchestratorError(f"Niet-geregistreerde module: {name}")
        return modules[name]

    def _resolve_order(self, requested: Iterable[str]) -> List[str]:
        resolved: List[str] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise OrchestratorError(f"Circulaire afhankelijkheid: {name}")
            visiting.add(name)
            for dependency in self._module(name).get("dependencies", []):
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            resolved.append(name)

        for name in requested:
            visit(name)
        return resolved

    def _dependencies_valid(self, modules: Dict[str, Any]) -> bool:
        try:
            for name in modules:
                self._resolve_order([name])
            return True
        except OrchestratorError:
            return False

    def _availability(self, module: Dict[str, Any]) -> Dict[str, Any]:
        if module.get("mode") == "virtual":
            return {"available": True, "reason": "virtual"}
        command = self._expand(module.get("command", []))
        if not command:
            return {"available": False, "reason": "empty_command"}
        if command[0] == sys.executable and len(command) >= 2:
            target = Path(command[1])
            return {"available": target.exists(), "target": str(target)}
        return {"available": True, "reason": "path_command"}

    def _expand(self, command: Sequence[str]) -> List[str]:
        replacements = {"{python}": sys.executable, "{project_root}": str(PROJECT_ROOT)}
        result = []
        for token in command:
            value = str(token)
            for key, replacement in replacements.items():
                value = value.replace(key, replacement)
            result.append(value)
        return result

    def _repository_preflight(self) -> Dict[str, Any]:
        tracked = subprocess.run(["git","diff","--name-only"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        staged = subprocess.run(["git","diff","--cached","--name-only"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        untracked = subprocess.run(["git","ls-files","--others","--exclude-standard"], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
        allowed = tuple(self.policy["allowed_untracked_prefixes"])
        unexpected = [x for x in untracked.stdout.splitlines() if x and not x.startswith(allowed)]
        return {
            "tracked_changes": tracked.stdout.splitlines(),
            "staged_changes": staged.stdout.splitlines(),
            "unexpected_untracked": unexpected,
            "ready": not tracked.stdout.strip() and not staged.stdout.strip() and not unexpected,
        }

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(self, report: Dict[str, Any]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    def _directory_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / f".probe_{os.getpid()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except OSError:
            return False

def main() -> None:
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    plan = sub.add_parser("plan")
    plan.add_argument("--workflow", default="platform_foundation")
    execute = sub.add_parser("execute")
    execute.add_argument("--workflow", default="platform_foundation")
    execute.add_argument("--approval-token", default="")
    args = parser.parse_args()

    orchestrator = PhoenixMainRunnerOrchestrator()
    if args.command == "self-test":
        result = orchestrator.self_test()
    elif args.command == "plan":
        result = orchestrator.plan(args.workflow)
    else:
        result = orchestrator.execute(args.workflow, args.approval_token)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {
        "FAIL",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_UNAVAILABLE_REQUIRED_MODULE",
        "FAILED_REQUIRED_MODULE",
    }:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
