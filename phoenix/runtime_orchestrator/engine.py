"""Core runtime orchestration primitives for Project Phoenix."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable, Mapping


class OrchestrationError(RuntimeError):
    """Base runtime orchestration error."""


class DependencyError(OrchestrationError):
    """Raised when a dependency graph is invalid."""


TaskCallable = Callable[["RuntimeContext"], Any]


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    handler: str | TaskCallable
    dependencies: tuple[str, ...] = ()
    priority: int = 100
    timeout_seconds: float | None = None
    retries: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    attempts: int
    output: Any = None
    error: str = ""


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: str
    timestamp: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class RuntimeSnapshot:
    runtime_id: str
    status: str
    created_at: str
    updated_at: str
    tasks: Mapping[str, Mapping[str, Any]]
    events: tuple[Mapping[str, Any], ...]
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tasks": dict(self.tasks),
            "events": list(self.events),
            "evidence_sha256": self.evidence_sha256,
        }


class RuntimeContext:
    """Execution context shared with task handlers."""

    def __init__(
        self,
        runtime_id: str,
        task_id: str,
        dependency_results: Mapping[str, TaskResult],
        cancel_event: threading.Event,
        emit: Callable[[str, Mapping[str, Any]], None],
    ) -> None:
        self.runtime_id = runtime_id
        self.task_id = task_id
        self.dependency_results = dependency_results
        self._cancel_event = cancel_event
        self._emit = emit

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise OrchestrationError(
                f"Runtime {self.runtime_id} was cancelled."
            )

    def emit(self, event_type: str, **payload: Any) -> None:
        self._emit(event_type, {"task_id": self.task_id, **payload})


class RuntimeOrchestrator:
    """Dependency-aware, parallel, auditable task orchestrator."""

    def __init__(
        self,
        *,
        max_workers: int = 4,
        runtime_id: str | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.runtime_id = runtime_id or f"phoenix-runtime-{stamp}"
        self.max_workers = max_workers
        self._tasks: dict[str, TaskSpec] = {}
        self._results: dict[str, TaskResult] = {}
        self._events: list[RuntimeEvent] = []
        self._cancel_event = threading.Event()
        self._lock = threading.RLock()
        self._created_at = self._now()
        self._updated_at = self._created_at
        self._status = "created"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        with self._lock:
            event = RuntimeEvent(
                event_type=event_type,
                timestamp=self._now(),
                payload=dict(payload),
            )
            self._events.append(event)
            self._updated_at = event.timestamp

    def register(self, spec: TaskSpec) -> None:
        if not spec.task_id.strip():
            raise ValueError("task_id must not be empty.")
        if spec.task_id in self._tasks:
            raise OrchestrationError(
                f"Task already registered: {spec.task_id}"
            )
        self._tasks[spec.task_id] = spec
        self._emit("task_registered", {"task_id": spec.task_id})

    def register_many(self, specs: Iterable[TaskSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def cancel(self) -> None:
        self._cancel_event.set()
        self._status = "cancelling"
        self._emit("runtime_cancellation_requested", {})

    def _resolve_handler(self, handler: str | TaskCallable) -> TaskCallable:
        if callable(handler):
            return handler
        if ":" not in handler:
            raise OrchestrationError(
                "Handler strings must use 'module:function' syntax."
            )
        module_name, function_name = handler.split(":", 1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        if not callable(function):
            raise OrchestrationError(
                f"Resolved handler is not callable: {handler}"
            )
        return function

    def _validate_dependencies(self) -> None:
        for task_id, spec in self._tasks.items():
            for dependency in spec.dependencies:
                if dependency not in self._tasks:
                    raise DependencyError(
                        f"{task_id} depends on unknown task {dependency}."
                    )

        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in permanent:
                return
            if task_id in temporary:
                raise DependencyError(
                    f"Dependency cycle detected at {task_id}."
                )
            temporary.add(task_id)
            for dependency in self._tasks[task_id].dependencies:
                visit(dependency)
            temporary.remove(task_id)
            permanent.add(task_id)

        for task_id in self._tasks:
            visit(task_id)

    def _execute_task(self, spec: TaskSpec) -> TaskResult:
        dependency_results = {
            dependency: self._results[dependency]
            for dependency in spec.dependencies
        }
        context = RuntimeContext(
            self.runtime_id,
            spec.task_id,
            dependency_results,
            self._cancel_event,
            self._emit,
        )
        started = self._now()
        monotonic_started = time.monotonic()
        attempts = 0
        last_error = ""

        self._emit("task_started", {"task_id": spec.task_id})

        for attempts in range(1, spec.retries + 2):
            try:
                context.raise_if_cancelled()
                handler = self._resolve_handler(spec.handler)
                output = handler(context)
                finished = self._now()
                result = TaskResult(
                    task_id=spec.task_id,
                    status="completed",
                    started_at=started,
                    finished_at=finished,
                    duration_seconds=round(
                        time.monotonic() - monotonic_started, 6
                    ),
                    attempts=attempts,
                    output=output,
                )
                self._emit(
                    "task_completed",
                    {
                        "task_id": spec.task_id,
                        "attempts": attempts,
                    },
                )
                return result
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                self._emit(
                    "task_attempt_failed",
                    {
                        "task_id": spec.task_id,
                        "attempt": attempts,
                        "error": last_error,
                    },
                )

        finished = self._now()
        result = TaskResult(
            task_id=spec.task_id,
            status="failed",
            started_at=started,
            finished_at=finished,
            duration_seconds=round(
                time.monotonic() - monotonic_started, 6
            ),
            attempts=attempts,
            error=last_error,
        )
        self._emit(
            "task_failed",
            {"task_id": spec.task_id, "error": last_error},
        )
        return result

    def run(self) -> RuntimeSnapshot:
        self._validate_dependencies()
        self._status = "running"
        self._emit("runtime_started", {"task_count": len(self._tasks)})

        pending = set(self._tasks)
        running: dict[Future[TaskResult], str] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while pending or running:
                if self._cancel_event.is_set():
                    for task_id in sorted(pending):
                        now = self._now()
                        self._results[task_id] = TaskResult(
                            task_id=task_id,
                            status="cancelled",
                            started_at=now,
                            finished_at=now,
                            duration_seconds=0.0,
                            attempts=0,
                            error="runtime cancelled",
                        )
                    pending.clear()

                failed_dependencies = []
                for task_id in sorted(pending):
                    spec = self._tasks[task_id]
                    dependency_states = [
                        self._results.get(dep)
                        for dep in spec.dependencies
                    ]
                    if any(
                        result is not None
                        and result.status != "completed"
                        for result in dependency_states
                    ):
                        failed_dependencies.append(task_id)

                for task_id in failed_dependencies:
                    now = self._now()
                    self._results[task_id] = TaskResult(
                        task_id=task_id,
                        status="blocked",
                        started_at=now,
                        finished_at=now,
                        duration_seconds=0.0,
                        attempts=0,
                        error="dependency did not complete successfully",
                    )
                    pending.remove(task_id)
                    self._emit(
                        "task_blocked",
                        {"task_id": task_id},
                    )

                ready = sorted(
                    (
                        self._tasks[task_id]
                        for task_id in pending
                        if all(
                            dep in self._results
                            and self._results[dep].status == "completed"
                            for dep in self._tasks[task_id].dependencies
                        )
                    ),
                    key=lambda item: (item.priority, item.task_id),
                )

                available_slots = self.max_workers - len(running)
                for spec in ready[:available_slots]:
                    future = executor.submit(self._execute_task, spec)
                    running[future] = spec.task_id
                    pending.remove(spec.task_id)

                if not running:
                    if pending:
                        raise DependencyError(
                            "No runnable tasks remain; dependency graph "
                            "cannot progress."
                        )
                    break

                completed_future = next(
                    future for future in running if future.done()
                ) if any(f.done() for f in running) else None

                if completed_future is None:
                    time.sleep(0.01)
                    continue

                task_id = running.pop(completed_future)
                self._results[task_id] = completed_future.result()

        statuses = {result.status for result in self._results.values()}
        if "failed" in statuses or "blocked" in statuses:
            self._status = "failed"
        elif "cancelled" in statuses or self._cancel_event.is_set():
            self._status = "cancelled"
        else:
            self._status = "completed"

        self._emit("runtime_finished", {"status": self._status})
        return self.snapshot()

    def snapshot(self) -> RuntimeSnapshot:
        task_payload = {
            task_id: asdict(result)
            for task_id, result in sorted(self._results.items())
        }
        event_payload = tuple(
            {
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "payload": dict(event.payload),
            }
            for event in self._events
        )
        core = {
            "runtime_id": self.runtime_id,
            "status": self._status,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "tasks": task_payload,
            "events": event_payload,
        }
        digest = sha256(
            json.dumps(
                core,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return RuntimeSnapshot(
            runtime_id=self.runtime_id,
            status=self._status,
            created_at=self._created_at,
            updated_at=self._updated_at,
            tasks=task_payload,
            events=event_payload,
            evidence_sha256=digest,
        )

    @staticmethod
    def write_snapshot(
        snapshot: RuntimeSnapshot,
        destination: str | Path,
    ) -> Path:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                snapshot.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path
