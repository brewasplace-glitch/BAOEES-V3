from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from threading import Lock
from time import monotonic
from types import MappingProxyType
from typing import Any, Callable, Mapping
import json
import re

from .specialized_agents import AgentTaskResult, AgentTaskSpec, object_sha256


@dataclass(frozen=True)
class DagExecutionResult:
    status: str
    dag_sha256: str
    result_sha256: str
    batches: tuple[tuple[str, ...], ...]
    topological_order: tuple[str, ...]
    results: tuple[AgentTaskResult, ...]
    max_observed_parallelism: int
    parallel_overlap_proven: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PHOENIX_MULTI_AGENT_DAG_RESULT_V1",
            "status": self.status,
            "dag_sha256": self.dag_sha256,
            "result_sha256": self.result_sha256,
            "batches": [list(x) for x in self.batches],
            "topological_order": list(self.topological_order),
            "results": [x.to_dict() for x in self.results],
            "max_observed_parallelism": self.max_observed_parallelism,
            "parallel_overlap_proven": self.parallel_overlap_proven,
            "repository_write_performed": False,
            "automatic_engine_activation": False,
        }


class BoundedDagScheduler:
    def __init__(self, policy: Mapping[str, Any], agent_registry: Any):
        self.policy = dict(policy)
        self.agent_registry = agent_registry
        if self.policy.get("schema") != "PHOENIX_MULTI_AGENT_DAG_POLICY_V1":
            raise RuntimeError("Phase-11 DAG policy schema invalid")
        if self.policy.get("status") != "ACTIVE_BOUNDED" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("Phase-11 DAG policy must be active and fail closed")
        if self.policy.get("allowed_risk") != ["LOW"]:
            raise RuntimeError("Phase-11 DAG must allow LOW only")
        if self.policy.get("read_only_tasks_only") is not True:
            raise RuntimeError("Phase-11 DAG must remain read only")

    def _tasks(self, tasks: tuple[AgentTaskSpec, ...] | list[AgentTaskSpec]) -> tuple[AgentTaskSpec, ...]:
        normalized = tuple(tasks)
        if not normalized:
            raise ValueError("PHASE11_EMPTY_DAG_DENY")
        if len(normalized) > int(self.policy["max_tasks_per_dag"]):
            raise PermissionError("PHASE11_TASK_BOUND_DENY")
        ids = [x.task_id for x in normalized]
        if len(ids) != len(set(ids)):
            raise PermissionError("PHASE11_DUPLICATE_TASK_ID_DENY")
        known = set(ids)
        payload_limit = int(self.policy["max_task_payload_bytes"])
        for task in normalized:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", task.task_id):
                raise PermissionError("PHASE11_TASK_ID_DENY")
            if task.risk != "LOW":
                raise PermissionError("PHASE11_NON_LOW_RISK_DENY")
            if task.mutating:
                raise PermissionError("PHASE11_PARALLEL_MUTATION_DENY")
            if len(task.dependencies) > int(self.policy["max_dependencies_per_task"]):
                raise PermissionError("PHASE11_DEPENDENCY_BOUND_DENY")
            if len(task.dependencies) != len(set(task.dependencies)):
                raise PermissionError("PHASE11_DUPLICATE_DEPENDENCY_DENY")
            unknown = sorted(set(task.dependencies) - known)
            if unknown:
                raise PermissionError("PHASE11_UNKNOWN_DEPENDENCY_DENY:" + ",".join(unknown))
            if task.task_id in task.dependencies:
                raise PermissionError("PHASE11_SELF_DEPENDENCY_DENY")
            if len(json.dumps(task.payload, sort_keys=True, ensure_ascii=False).encode("utf-8")) > payload_limit:
                raise PermissionError("PHASE11_PAYLOAD_SIZE_DENY")
            self.agent_registry.descriptor(task.agent_id, task.action)
        return tuple(sorted(normalized, key=lambda x: x.task_id))

    def plan(self, tasks: tuple[AgentTaskSpec, ...] | list[AgentTaskSpec]) -> tuple[tuple[AgentTaskSpec, ...], tuple[tuple[str, ...], ...]]:
        normalized = self._tasks(tasks)
        dependencies = {x.task_id: tuple(sorted(x.dependencies)) for x in normalized}
        dependents = {x.task_id: 0 for x in normalized}
        for deps in dependencies.values():
            for dep in deps:
                dependents[dep] += 1
        if any(x > int(self.policy["max_dependents_per_task"]) for x in dependents.values()):
            raise PermissionError("PHASE11_FANOUT_BOUND_DENY")
        sorter = TopologicalSorter(dependencies)
        try:
            sorter.prepare()
        except CycleError as exc:
            raise PermissionError("PHASE11_DAG_CYCLE_DENY") from exc
        batches: list[tuple[str, ...]] = []
        depth: dict[str, int] = {}
        while sorter.is_active():
            ready = tuple(sorted(sorter.get_ready()))
            if not ready:
                raise RuntimeError("PHASE11_DAG_STALLED")
            for task_id in ready:
                deps = dependencies[task_id]
                depth[task_id] = 1 + max((depth[x] for x in deps), default=0)
                if depth[task_id] > int(self.policy["max_dag_depth"]):
                    raise PermissionError("PHASE11_DAG_DEPTH_DENY")
            batches.append(ready)
            sorter.done(*ready)
        return normalized, tuple(batches)

    def execute(
        self,
        tasks: tuple[AgentTaskSpec, ...] | list[AgentTaskSpec],
        runner: Callable[[AgentTaskSpec, Mapping[str, AgentTaskResult]], AgentTaskResult],
    ) -> DagExecutionResult:
        normalized, batches = self.plan(tasks)
        by_id = {x.task_id: x for x in normalized}
        results: dict[str, AgentTaskResult] = {}
        active = 0
        max_active = 0
        active_lock = Lock()
        start = monotonic()

        def invoke(task: AgentTaskSpec, deps: Mapping[str, AgentTaskResult]) -> AgentTaskResult:
            nonlocal active, max_active
            with active_lock:
                active += 1
                max_active = max(max_active, active)
            try:
                result = runner(task, deps)
                if not isinstance(result, AgentTaskResult) or result.status != "PASS":
                    raise RuntimeError("PHASE11_AGENT_RESULT_DENY")
                if result.task_id != task.task_id or result.agent_id != task.agent_id:
                    raise RuntimeError("PHASE11_AGENT_RESULT_BINDING_DENY")
                return result
            finally:
                with active_lock:
                    active -= 1

        max_workers = int(self.policy["max_parallel_workers"])
        task_timeout = float(self.policy["max_task_seconds"])
        total_timeout = float(self.policy["max_total_seconds"])
        for batch in batches:
            if monotonic() - start > total_timeout:
                raise TimeoutError("PHASE11_DAG_TOTAL_TIMEOUT")
            workers = min(max_workers, len(batch))
            executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="phoenix-p11")
            futures = {}
            try:
                for task_id in batch:
                    task = by_id[task_id]
                    deps = {
                        dep: results[dep]
                        for dep in sorted(task.dependencies)
                    }
                    immutable_deps = MappingProxyType(dict(deps))
                    futures[task_id] = executor.submit(invoke, task, immutable_deps)
                for task_id in batch:
                    try:
                        results[task_id] = futures[task_id].result(timeout=task_timeout)
                    except FutureTimeout as exc:
                        for future in futures.values():
                            future.cancel()
                        raise TimeoutError(f"PHASE11_TASK_TIMEOUT:{task_id}") from exc
            except Exception:
                for future in futures.values():
                    future.cancel()
                executor.shutdown(wait=True, cancel_futures=True)
                raise
            else:
                executor.shutdown(wait=True, cancel_futures=False)

        ordered_results = tuple(results[key] for key in sorted(results))
        result_material = [x.to_dict() for x in ordered_results]
        dag_material = [x.to_dict() for x in normalized]
        order = tuple(task_id for batch in batches for task_id in batch)
        return DagExecutionResult(
            status="PASS",
            dag_sha256=object_sha256(dag_material),
            result_sha256=object_sha256(result_material),
            batches=batches,
            topological_order=order,
            results=ordered_results,
            max_observed_parallelism=max_active,
            parallel_overlap_proven=any(len(x) > 1 for x in batches) and max_active > 1,
        )
