from __future__ import annotations

from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
import hashlib
import json
import re


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class AgentTaskSpec:
    task_id: str
    agent_id: str
    action: str
    dependencies: tuple[str, ...] = ()
    risk: str = "LOW"
    mutating: bool = False
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AgentTaskSpec":
        if value.get("schema", "PHOENIX_AGENT_TASK_SPEC_V1") != "PHOENIX_AGENT_TASK_SPEC_V1":
            raise ValueError("PHASE11_TASK_SCHEMA_DENY")
        return cls(
            task_id=str(value["task_id"]),
            agent_id=str(value["agent_id"]),
            action=str(value["action"]),
            dependencies=tuple(str(x) for x in value.get("dependencies", ())),
            risk=str(value.get("risk", "LOW")),
            mutating=bool(value.get("mutating", False)),
            payload=dict(value.get("payload", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema"] = "PHOENIX_AGENT_TASK_SPEC_V1"
        value["dependencies"] = list(self.dependencies)
        return value


@dataclass(frozen=True)
class AgentTaskResult:
    task_id: str
    agent_id: str
    action: str
    status: str
    output: dict[str, Any]
    output_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SpecializedAgentRegistry:
    def __init__(self, registry: Mapping[str, Any]):
        self.registry = dict(registry)
        if self.registry.get("schema") != "PHOENIX_SPECIALIZED_AGENT_REGISTRY_V1":
            raise RuntimeError("Phase-11 specialized-agent registry schema invalid")
        if self.registry.get("status") != "ACTIVE" or self.registry.get("fail_closed") is not True:
            raise RuntimeError("Phase-11 specialized-agent registry must be active and fail closed")
        self._agents: dict[str, dict[str, Any]] = {}
        for raw in self.registry.get("agents", ()):
            agent = dict(raw)
            agent_id = str(agent.get("agent_id", ""))
            if not re.fullmatch(r"agent\.[a-z0-9_.-]+", agent_id):
                raise RuntimeError("PHASE11_AGENT_ID_INVALID")
            if agent_id in self._agents:
                raise RuntimeError("PHASE11_DUPLICATE_AGENT_ID")
            if agent.get("status") != "ACTIVE" or agent.get("read_only") is not True:
                raise RuntimeError("PHASE11_AGENT_NOT_READ_ONLY_ACTIVE")
            if agent.get("implementation") != "builtin.deterministic_digest":
                raise RuntimeError("PHASE11_AGENT_IMPLEMENTATION_DENY")
            if not agent.get("actions"):
                raise RuntimeError("PHASE11_AGENT_ACTIONS_REQUIRED")
            self._agents[agent_id] = agent

    def descriptor(self, agent_id: str, action: str) -> Mapping[str, Any]:
        agent = self._agents.get(str(agent_id))
        if agent is None:
            raise PermissionError(f"PHASE11_UNKNOWN_AGENT_DENY:{agent_id}")
        if action not in agent["actions"]:
            raise PermissionError(f"PHASE11_AGENT_ACTION_DENY:{agent_id}:{action}")
        return MappingProxyType(dict(agent))

    def execute(
        self,
        task: AgentTaskSpec,
        dependency_results: Mapping[str, AgentTaskResult],
    ) -> AgentTaskResult:
        agent = self.descriptor(task.agent_id, task.action)
        dependency_hashes = {
            key: dependency_results[key].output_sha256
            for key in sorted(dependency_results)
        }
        material = {
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "action": task.action,
            "role": str(agent["role"]),
            "payload_sha256": object_sha256(task.payload),
            "dependency_output_sha256": dependency_hashes,
        }
        finding = object_sha256(material)
        output = {
            "schema": "PHOENIX_SPECIALIZED_AGENT_OUTPUT_V1",
            **material,
            "finding_sha256": finding,
            "network_access": False,
            "arbitrary_shell_executed": False,
            "repository_write_performed": False,
        }
        return AgentTaskResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            action=task.action,
            status="PASS",
            output=output,
            output_sha256=object_sha256(output),
        )

    def boundary_descriptors(self, tasks: tuple[AgentTaskSpec, ...]) -> dict[str, str]:
        return {
            task.agent_id: str(self.descriptor(task.agent_id, task.action)["role"])
            for task in tasks
        }
