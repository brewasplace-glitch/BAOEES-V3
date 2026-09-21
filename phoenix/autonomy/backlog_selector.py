from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
import hashlib
import heapq
import json
import re

from .change_classifier import normalize_repository_path


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class BacklogTask:
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
    requires: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BacklogTask":
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
            requires=tuple(str(x) for x in value.get("requires", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["requires"] = list(self.requires)
        return value

    @property
    def sha256(self) -> str:
        return object_sha256(self.to_dict())


@dataclass(frozen=True)
class BacklogSelection:
    task: BacklogTask
    eligible_task_count: int
    eligible_task_ids: tuple[str, ...]
    selection_key: tuple[int, str]
    backlog_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PHOENIX_DETERMINISTIC_BACKLOG_SELECTION_RESULT_V1",
            "task": self.task.to_dict(),
            "task_sha256": self.task.sha256,
            "eligible_task_count": self.eligible_task_count,
            "eligible_task_ids": list(self.eligible_task_ids),
            "selection_key": [self.selection_key[0], self.selection_key[1]],
            "backlog_sha256": self.backlog_sha256,
        }


class DeterministicBacklogSelector:
    def __init__(self, policy: Mapping[str, Any], backlog: Mapping[str, Any]):
        self.policy = dict(policy)
        self.backlog = dict(backlog)
        self._validate_contract()
        tasks = tuple(BacklogTask.from_dict(x) for x in self.backlog.get("tasks", ()))
        ids = [x.task_id for x in tasks]
        if len(ids) != len(set(ids)):
            raise RuntimeError("PHASE12_DUPLICATE_BACKLOG_TASK_ID_DENY")
        self.tasks = tuple(self._validate_task(x) for x in tasks)
        if not self.tasks:
            raise RuntimeError("PHASE12_BACKLOG_EMPTY_DENY")

    def _validate_contract(self) -> None:
        if self.policy.get("schema") != "PHOENIX_AUTONOMOUS_BACKLOG_POLICY_V1":
            raise RuntimeError("Phase-12 backlog policy schema invalid")
        if self.policy.get("status") != "ACTIVE_BOUNDED" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("Phase-12 backlog policy must be active and fail closed")
        if self.policy.get("allowed_risk") != ["LOW"]:
            raise RuntimeError("Phase-12 backlog must allow LOW only")
        if int(self.policy.get("max_tasks_per_invocation", 0)) != 1:
            raise RuntimeError("Phase-12 must select exactly one task at most")
        selection = self.policy.get("selection", {})
        if selection.get("primary") != "python.heapq":
            raise RuntimeError("Phase-12 priority selector invalid")
        if selection.get("tie_breaker") != "TASK_ID_LEXICOGRAPHIC":
            raise RuntimeError("Phase-12 deterministic tie breaker missing")
        if self.backlog.get("schema") != "PHOENIX_AUTONOMOUS_BACKLOG_V1":
            raise RuntimeError("Phase-12 backlog schema invalid")
        if self.backlog.get("status") != "ACTIVE":
            raise RuntimeError("Phase-12 backlog inactive")
        for flag in (
            "automatic_source_change",
            "automatic_dependency_change",
            "automatic_policy_change",
            "automatic_registry_change",
            "automatic_engine_activation",
        ):
            if self.policy.get(flag) is not False:
                raise RuntimeError(f"Phase-12 safety invariant invalid: {flag}")

    def _validate_task(self, task: BacklogTask) -> BacklogTask:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{5,63}", task.task_id):
            raise PermissionError("PHASE12_TASK_ID_DENY")
        if task.status not in {"READY", "BLOCKED", "COMPLETED"}:
            raise PermissionError("PHASE12_TASK_STATUS_DENY")
        if task.risk not in self.policy["allowed_risk"]:
            raise PermissionError("PHASE12_TASK_RISK_DENY")
        if task.task_type not in self.policy["allowed_task_types"]:
            raise PermissionError("PHASE12_TASK_TYPE_DENY")
        if task.action not in self.policy["allowed_actions"]:
            raise PermissionError("PHASE12_TASK_ACTION_DENY")
        if not 0 <= task.priority <= 1000:
            raise PermissionError("PHASE12_TASK_PRIORITY_DENY")
        normalized = normalize_repository_path(task.output_path)
        roots = tuple(str(x).casefold() for x in self.policy["allowed_output_roots"])
        if not any(normalized.casefold().startswith(root) for root in roots):
            raise PermissionError("PHASE12_TASK_OUTPUT_SCOPE_DENY")
        if PurePosixPath(normalized).suffix.casefold() not in {
            str(x).casefold() for x in self.policy["allowed_extensions"]
        }:
            raise PermissionError("PHASE12_TASK_OUTPUT_EXTENSION_DENY")
        if task.generator != "builtin.level3_capability_evidence_v1":
            raise PermissionError("PHASE12_TASK_GENERATOR_DENY")
        if task.promotion_lane != "LOW_NON_EXECUTABLE":
            raise PermissionError("PHASE12_TASK_PROMOTION_LANE_DENY")
        if not task.title.strip() or not task.requires:
            raise PermissionError("PHASE12_TASK_METADATA_DENY")
        return task

    def select(
        self,
        repo_root: Path,
        *,
        completed_task_ids: Iterable[str] = (),
    ) -> BacklogSelection:
        root = Path(repo_root).resolve()
        completed = {str(x) for x in completed_task_ids}
        heap: list[tuple[int, str, BacklogTask]] = []
        eligible: list[str] = []
        for task in self.tasks:
            if task.status != "READY" or task.task_id in completed:
                continue
            if (root / Path(task.output_path)).exists():
                continue
            key = (-task.priority, task.task_id)
            heapq.heappush(heap, (key[0], key[1], task))
            eligible.append(task.task_id)
        if not heap:
            raise RuntimeError("PHASE12_NO_ELIGIBLE_BACKLOG_TASK")
        priority_key, task_id, selected = heapq.heappop(heap)
        selection = BacklogSelection(
            task=selected,
            eligible_task_count=len(eligible),
            eligible_task_ids=tuple(sorted(eligible)),
            selection_key=(priority_key, task_id),
            backlog_sha256=object_sha256(self.backlog),
        )
        repetitions = int(self.policy["selection"]["deterministic_repetitions"])
        if repetitions != 2:
            raise RuntimeError("PHASE12_SELECTION_REPETITION_BOUND_DENY")
        replay = min(
            (-task.priority, task.task_id, task.task_id)
            for task in self.tasks
            if task.status == "READY"
            and task.task_id not in completed
            and not (root / Path(task.output_path)).exists()
        )
        if replay[:2] != selection.selection_key or replay[2] != selected.task_id:
            raise RuntimeError("PHASE12_NONDETERMINISTIC_SELECTION_DENY")
        return selection
