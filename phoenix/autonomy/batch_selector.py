from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import hashlib
import heapq
import json
import re

from .change_classifier import normalize_repository_path


def canonical_batch_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def batch_object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_batch_bytes(value)).hexdigest()


@dataclass(frozen=True)
class BatchTask:
    task_id: str
    status: str
    title: str
    risk: str
    task_type: str
    action: str
    priority: int
    output_path: str
    generator: str
    promotion_lane: str
    depends_on: tuple[str, ...]
    repair_probe: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BatchTask":
        return cls(
            task_id=str(value["task_id"]),
            status=str(value["status"]),
            title=str(value["title"]),
            risk=str(value["risk"]),
            task_type=str(value["task_type"]),
            action=str(value["action"]),
            priority=int(value["priority"]),
            output_path=str(value["output_path"]),
            generator=str(value["generator"]),
            promotion_lane=str(value["promotion_lane"]),
            depends_on=tuple(str(x) for x in value.get("depends_on", ())),
            repair_probe=str(value.get("repair_probe", "NONE")),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["depends_on"] = list(self.depends_on)
        return value

    @property
    def sha256(self) -> str:
        return batch_object_sha256(self.to_dict())


@dataclass(frozen=True)
class BatchSelection:
    tasks: tuple[BatchTask, ...]
    selection_keys: tuple[tuple[int, str], ...]
    backlog_sha256: str

    @property
    def task_ids(self) -> tuple[str, ...]:
        return tuple(task.task_id for task in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PHOENIX_DETERMINISTIC_BATCH_SELECTION_RESULT_V1",
            "tasks": [task.to_dict() for task in self.tasks],
            "task_sha256s": {task.task_id: task.sha256 for task in self.tasks},
            "task_ids": list(self.task_ids),
            "selection_keys": [[key[0], key[1]] for key in self.selection_keys],
            "backlog_sha256": self.backlog_sha256,
        }


class DeterministicBatchSelector:
    def __init__(self, policy: Mapping[str, Any], backlog: Mapping[str, Any]):
        self.policy = dict(policy)
        self.backlog = dict(backlog)
        self._validate_contract()
        tasks = tuple(BatchTask.from_dict(row) for row in self.backlog.get("tasks", ()))
        ids = [task.task_id for task in tasks]
        if len(ids) != len(set(ids)):
            raise RuntimeError("PHASE13_DUPLICATE_BATCH_TASK_ID_DENY")
        self.tasks = tuple(self._validate_task(task, set(ids)) for task in tasks)
        if len(self.tasks) < int(self.policy["min_tasks_per_batch"]):
            raise RuntimeError("PHASE13_BATCH_BACKLOG_TOO_SMALL_DENY")
        self._assert_acyclic()

    def _validate_contract(self) -> None:
        if self.policy.get("schema") != "PHOENIX_AUTONOMOUS_BATCH_POLICY_V1":
            raise RuntimeError("Phase-13 batch policy schema invalid")
        if self.policy.get("status") != "ACTIVE_BOUNDED" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("Phase-13 batch policy must be active and fail closed")
        if self.policy.get("allowed_risk") != ["LOW"]:
            raise RuntimeError("Phase-13 batch must allow LOW only")
        minimum = int(self.policy.get("min_tasks_per_batch", 0))
        maximum = int(self.policy.get("max_tasks_per_batch", 0))
        if minimum != 3 or maximum != 3:
            raise RuntimeError("Phase-13 batch size boundary invalid")
        selection = self.policy.get("selection", {})
        if selection.get("primary") != "python.heapq":
            raise RuntimeError("Phase-13 priority selector invalid")
        if selection.get("tie_breaker") != "TASK_ID_LEXICOGRAPHIC":
            raise RuntimeError("Phase-13 deterministic tie breaker missing")
        if self.backlog.get("schema") != "PHOENIX_AUTONOMOUS_BATCH_V1":
            raise RuntimeError("Phase-13 batch backlog schema invalid")
        if self.backlog.get("status") != "ACTIVE":
            raise RuntimeError("Phase-13 batch backlog inactive")
        for flag in (
            "automatic_source_change",
            "automatic_dependency_change",
            "automatic_policy_change",
            "automatic_registry_change",
            "automatic_engine_activation",
        ):
            if self.policy.get(flag) is not False:
                raise RuntimeError(f"Phase-13 safety invariant invalid: {flag}")

    def _validate_task(self, task: BatchTask, known_ids: set[str]) -> BatchTask:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{5,63}", task.task_id):
            raise PermissionError("PHASE13_TASK_ID_DENY")
        if task.status not in {"READY", "BLOCKED", "COMPLETED"}:
            raise PermissionError("PHASE13_TASK_STATUS_DENY")
        if task.risk not in self.policy["allowed_risk"]:
            raise PermissionError("PHASE13_TASK_RISK_DENY")
        if task.task_type not in self.policy["allowed_task_types"]:
            raise PermissionError("PHASE13_TASK_TYPE_DENY")
        if task.action not in self.policy["allowed_actions"]:
            raise PermissionError("PHASE13_TASK_ACTION_DENY")
        if not 0 <= task.priority <= 1000:
            raise PermissionError("PHASE13_TASK_PRIORITY_DENY")
        normalized = normalize_repository_path(task.output_path)
        roots = tuple(str(root).casefold() for root in self.policy["allowed_output_roots"])
        if not any(normalized.casefold().startswith(root) for root in roots):
            raise PermissionError("PHASE13_TASK_OUTPUT_SCOPE_DENY")
        if PurePosixPath(normalized).suffix.casefold() not in {
            str(ext).casefold() for ext in self.policy["allowed_extensions"]
        }:
            raise PermissionError("PHASE13_TASK_OUTPUT_EXTENSION_DENY")
        if task.generator != "builtin.level4_batch_evidence_v1":
            raise PermissionError("PHASE13_TASK_GENERATOR_DENY")
        if task.promotion_lane != "LOW_NON_EXECUTABLE":
            raise PermissionError("PHASE13_TASK_PROMOTION_LANE_DENY")
        if task.repair_probe not in {"NONE", "TRAILING_WHITESPACE_ON_FIRST_ATTEMPT"}:
            raise PermissionError("PHASE13_TASK_REPAIR_PROBE_DENY")
        if task.task_id in task.depends_on or any(dep not in known_ids for dep in task.depends_on):
            raise PermissionError("PHASE13_TASK_DEPENDENCY_DENY")
        if not task.title.strip():
            raise PermissionError("PHASE13_TASK_METADATA_DENY")
        return task

    def _assert_acyclic(self) -> None:
        by_id = {task.task_id: task for task in self.tasks}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise RuntimeError("PHASE13_BATCH_DEPENDENCY_CYCLE_DENY")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency in by_id[task_id].depends_on:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)

        for task in self.tasks:
            visit(task.task_id)

    def _select_ids(self, root: Path) -> tuple[str, ...]:
        selected: list[str] = []
        selected_set: set[str] = set()
        maximum = int(self.policy["max_tasks_per_batch"])
        while len(selected) < maximum:
            heap: list[tuple[int, str, BatchTask]] = []
            for task in self.tasks:
                if task.status != "READY" or task.task_id in selected_set:
                    continue
                if (root / Path(task.output_path)).exists():
                    continue
                if any(dependency not in selected_set for dependency in task.depends_on):
                    continue
                heapq.heappush(heap, (-task.priority, task.task_id, task))
            if not heap:
                break
            _, task_id, _ = heapq.heappop(heap)
            selected.append(task_id)
            selected_set.add(task_id)
        return tuple(selected)

    def select(self, repo_root: Path) -> BatchSelection:
        root = Path(repo_root).resolve()
        one = self._select_ids(root)
        repetitions = int(self.policy["selection"]["deterministic_repetitions"])
        if repetitions != 2 or self._select_ids(root) != one:
            raise RuntimeError("PHASE13_NONDETERMINISTIC_BATCH_SELECTION_DENY")
        if len(one) < int(self.policy["min_tasks_per_batch"]):
            raise RuntimeError("PHASE13_NO_ELIGIBLE_COMPLETE_BATCH")
        by_id = {task.task_id: task for task in self.tasks}
        tasks = tuple(by_id[task_id] for task_id in one)
        return BatchSelection(
            tasks=tasks,
            selection_keys=tuple((-task.priority, task.task_id) for task in tasks),
            backlog_sha256=batch_object_sha256(self.backlog),
        )
