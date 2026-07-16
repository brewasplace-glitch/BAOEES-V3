from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME = "Phoenix Autonomous Multi-Agent Orchestrator"
ENGINE_VERSION = "v19.0"


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = find_root()
POLICY_PATH = ROOT / "configs/phoenix/multi_agent_policy_v19_0.json"
REGISTRY_PATH = ROOT / "configs/phoenix/multi_agent_registry_v19_0.json"
OUTPUT_DIR = ROOT / "outputs/runtime/v19_0"
BUS_DIR = OUTPUT_DIR / "message_bus"
STATE_DIR = OUTPUT_DIR / "state"


class MultiAgentError(RuntimeError):
    pass


class PhoenixMultiAgentOrchestrator:
    def __init__(self) -> None:
        self.policy = self._read_json(POLICY_PATH)
        self.registry = self._read_json(REGISTRY_PATH)

    def self_test(self) -> Dict[str, Any]:
        checks = {
            "policy_exists": POLICY_PATH.exists(),
            "registry_exists": REGISTRY_PATH.exists(),
            "python_supported": sys.version_info >= (3, 10),
            "agents_registered": bool(self.registry.get("agents")),
            "workflows_registered": bool(self.registry.get("workflows")),
            "dependency_graph_valid": self._registry_valid(),
            "runtime_writable": self._writable(OUTPUT_DIR),
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

    def plan(self, workflow: str, run_id: str) -> Dict[str, Any]:
        definition = self._workflow(workflow)
        ordered_agents = self._resolve_agents(definition["agents"])
        assignments = []

        for sequence, agent_id in enumerate(ordered_agents, start=1):
            agent = self._agent(agent_id)
            assignments.append(
                {
                    "sequence": sequence,
                    "agent_id": agent_id,
                    "role": agent["role"],
                    "capabilities": agent.get("capabilities", []),
                    "dependencies": agent.get("dependencies", []),
                    "mode": agent.get("mode", "virtual"),
                    "status": "PLANNED",
                }
            )

        state = {
            "run_id": run_id,
            "workflow": workflow,
            "status": "PLANNED",
            "assignments": assignments,
            "completed_agents": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        state_path = self._write_state(state)

        return self._write_report(
            "plan",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "workflow": workflow,
                "run_id": run_id,
                "mode": "DRY_RUN",
                "assignments": assignments,
                "state_path": str(state_path),
                "automatic_execution": False,
                "automatic_commit_push": False,
                "status": "PASS",
            },
        )

    def validate(self, workflow: str) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            definition = self._workflow(workflow)
            self._resolve_agents(definition["agents"])
        except MultiAgentError as exc:
            errors.append(str(exc))

        for agent_id, agent in self.registry.get("agents", {}).items():
            if not agent.get("role"):
                errors.append(f"Agent zonder rol: {agent_id}")
            if agent.get("mode") == "command" and not agent.get("command"):
                errors.append(f"Command-agent zonder commando: {agent_id}")

        return self._write_report(
            "validation",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "workflow": workflow,
                "errors": errors,
                "status": "PASS" if not errors else "FAIL",
            },
        )

    def execute(self, workflow: str, run_id: str, approval_token: str) -> Dict[str, Any]:
        if approval_token != self.policy["required_approval_token"]:
            return self._blocked(run_id, "BLOCKED_NO_GO")

        if not self._repository_clean():
            return self._blocked(run_id, "BLOCKED_REPOSITORY_PREFLIGHT")

        validation = self.validate(workflow)
        if validation["status"] != "PASS":
            return self._blocked(run_id, "BLOCKED_INVALID_REGISTRY")

        state_path = self._state_path(run_id)
        if not state_path.exists():
            self.plan(workflow, run_id)
        state = self._read_json(state_path)
        completed = set(state.get("completed_agents", []))
        results: List[Dict[str, Any]] = []

        state["status"] = "RUNNING"
        self._write_state(state)

        for assignment in state["assignments"]:
            agent_id = assignment["agent_id"]
            if agent_id in completed:
                continue

            if not all(dep in completed for dep in assignment.get("dependencies", [])):
                state["status"] = "FAILED"
                state["failed_agent"] = agent_id
                self._write_state(state)
                return self._write_report(
                    "execution",
                    {
                        "engine": ENGINE_NAME,
                        "version": ENGINE_VERSION,
                        "run_id": run_id,
                        "results": results,
                        "status": "FAILED_DEPENDENCY_GATE",
                    },
                )

            result = self._run_agent(agent_id, run_id)
            results.append(result)
            self._publish_message(
                run_id,
                {
                    "from": agent_id,
                    "to": "orchestrator",
                    "type": "agent_result",
                    "payload": result,
                },
            )

            if result["status"] != "PASS":
                state["status"] = "FAILED"
                state["failed_agent"] = agent_id
                self._write_state(state)
                return self._write_report(
                    "execution",
                    {
                        "engine": ENGINE_NAME,
                        "version": ENGINE_VERSION,
                        "run_id": run_id,
                        "results": results,
                        "status": "FAILED_REQUIRED_AGENT",
                    },
                )

            completed.add(agent_id)
            state["completed_agents"] = sorted(completed)
            assignment["status"] = "PASS"
            self._write_state(state)

        state["status"] = "PASS"
        state["completed_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_state(state)

        return self._write_report(
            "execution",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "workflow": workflow,
                "run_id": run_id,
                "results": results,
                "completed_agents": sorted(completed),
                "status": "PASS",
                "automatic_commit_push": False,
            },
        )

    def status(self, run_id: str) -> Dict[str, Any]:
        path = self._state_path(run_id)
        if not path.exists():
            return self._write_report(
                "status",
                {
                    "engine": ENGINE_NAME,
                    "version": ENGINE_VERSION,
                    "run_id": run_id,
                    "status": "NOT_FOUND",
                },
            )

        return self._write_report(
            "status",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "run_id": run_id,
                "state": self._read_json(path),
                "status": "PASS",
            },
        )

    def _run_agent(self, agent_id: str, run_id: str) -> Dict[str, Any]:
        agent = self._agent(agent_id)
        mode = agent.get("mode", "virtual")

        if mode == "virtual":
            return {
                "agent_id": agent_id,
                "run_id": run_id,
                "mode": mode,
                "role": agent["role"],
                "status": "PASS",
                "message": "Virtuele agenttaak gecontroleerd voltooid.",
            }

        if mode == "command":
            command = [
                token.replace("{python}", sys.executable).replace("{project_root}", str(ROOT))
                for token in agent.get("command", [])
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            return {
                "agent_id": agent_id,
                "run_id": run_id,
                "mode": mode,
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
            }

        return {
            "agent_id": agent_id,
            "run_id": run_id,
            "mode": mode,
            "status": "FAIL",
            "message": f"Onbekende agentmodus: {mode}",
        }

    def _workflow(self, workflow: str) -> Dict[str, Any]:
        workflows = self.registry.get("workflows", {})
        if workflow not in workflows:
            raise MultiAgentError(f"Onbekende workflow: {workflow}")
        return workflows[workflow]

    def _agent(self, agent_id: str) -> Dict[str, Any]:
        agents = self.registry.get("agents", {})
        if agent_id not in agents:
            raise MultiAgentError(f"Niet-geregistreerde agent: {agent_id}")
        return agents[agent_id]

    def _resolve_agents(self, requested: List[str]) -> List[str]:
        ordered: List[str] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(agent_id: str) -> None:
            if agent_id in visited:
                return
            if agent_id in visiting:
                raise MultiAgentError(f"Circulaire agentdependency: {agent_id}")

            visiting.add(agent_id)
            agent = self._agent(agent_id)
            for dependency in agent.get("dependencies", []):
                visit(dependency)
            visiting.remove(agent_id)
            visited.add(agent_id)
            ordered.append(agent_id)

        for agent_id in requested:
            visit(agent_id)
        return ordered

    def _registry_valid(self) -> bool:
        try:
            for workflow in self.registry.get("workflows", {}).values():
                self._resolve_agents(workflow.get("agents", []))
            return True
        except MultiAgentError:
            return False

    def _publish_message(self, run_id: str, message: Dict[str, Any]) -> None:
        directory = BUS_DIR / run_id
        directory.mkdir(parents=True, exist_ok=True)
        sequence = len(list(directory.glob("*.json"))) + 1
        message["sequence"] = sequence
        message["timestamp"] = datetime.now().isoformat(timespec="seconds")
        path = directory / f"{sequence:04d}.json"
        path.write_text(
            json.dumps(message, ensure_ascii=False, indent=2),
            encoding="utf-8-sig",
        )

    def _state_path(self, run_id: str) -> Path:
        safe = "".join(c for c in run_id if c.isalnum() or c in "-_").strip()
        if not safe:
            raise MultiAgentError("Ongeldige run_id.")
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

    def _blocked(self, run_id: str, status: str) -> Dict[str, Any]:
        return self._write_report(
            "execution",
            {
                "engine": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "run_id": run_id,
                "status": status,
                "automatic_commit_push": False,
            },
        )

    def _repository_clean(self) -> bool:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0 and not result.stdout.strip()

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _write_report(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        path = OUTPUT_DIR / f"multi_agent_{name}_v19_0.json"
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
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} {ENGINE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test")

    for name in ("plan", "validate", "execute"):
        item = sub.add_parser(name)
        item.add_argument("--workflow", default="phoenix_core_coordination")
        if name != "validate":
            item.add_argument("--run-id", default="phoenix-core-v19")
        if name == "execute":
            item.add_argument("--approval-token", default="")

    status = sub.add_parser("status")
    status.add_argument("--run-id", default="phoenix-core-v19")

    args = parser.parse_args()
    orchestrator = PhoenixMultiAgentOrchestrator()

    if args.command == "self-test":
        result = orchestrator.self_test()
    elif args.command == "plan":
        result = orchestrator.plan(args.workflow, args.run_id)
    elif args.command == "validate":
        result = orchestrator.validate(args.workflow)
    elif args.command == "execute":
        result = orchestrator.execute(args.workflow, args.run_id, args.approval_token)
    else:
        result = orchestrator.status(args.run_id)

    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("status") in {
        "FAIL",
        "BLOCKED_NO_GO",
        "BLOCKED_REPOSITORY_PREFLIGHT",
        "BLOCKED_INVALID_REGISTRY",
        "FAILED_DEPENDENCY_GATE",
        "FAILED_REQUIRED_AGENT",
    }:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
