"""Phoenix Orchestrator Runtime (PXO Wave 2) v1.0.

This module executes ready PXO engines through registered adapters, persists
atomic JSON checkpoints and stops on the first adapter failure. It never marks
an engine completed unless the adapter returns outputs and evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Callable, Mapping, Protocol

from .phoenix_orchestrator import (
    OrchestrationError,
    OrchestrationPlan,
    PhoenixOrchestrator,
)


class RuntimeErrorContract(RuntimeError):
    """Raised when the PXO runtime contract is violated."""


@dataclass(frozen=True)
class AdapterResult:
    outputs: tuple[str, ...]
    evidence: tuple[str, ...]
    metadata: Mapping[str, object] | None = None

    def validate(self) -> None:
        if not self.outputs:
            raise RuntimeErrorContract("Adapter result requires at least one output.")
        if not self.evidence:
            raise RuntimeErrorContract("Adapter result requires evidence.")


class EngineAdapter(Protocol):
    def __call__(
        self,
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        ...


@dataclass(frozen=True)
class RuntimePolicy:
    stop_on_first_error: bool = True
    maximum_engine_executions: int = 100
    checkpoint_filename: str = "pxo_runtime_checkpoint.json"

    def validate(self) -> None:
        if self.maximum_engine_executions <= 0:
            raise RuntimeErrorContract(
                "maximum_engine_executions must be positive."
            )
        if not self.checkpoint_filename.strip():
            raise RuntimeErrorContract("checkpoint_filename is required.")


class AdapterRegistry:
    """Explicit engine adapter registry."""

    def __init__(self) -> None:
        self._adapters: dict[str, EngineAdapter] = {}

    def register(self, engine_id: str, adapter: EngineAdapter) -> None:
        if not engine_id.strip():
            raise RuntimeErrorContract("engine_id is required.")
        if engine_id in self._adapters:
            raise RuntimeErrorContract(
                f"Adapter already registered for engine: {engine_id}"
            )
        self._adapters[engine_id] = adapter

    def get(self, engine_id: str) -> EngineAdapter:
        try:
            return self._adapters[engine_id]
        except KeyError as exc:
            raise RuntimeErrorContract(
                f"No adapter registered for engine: {engine_id}"
            ) from exc

    def contains(self, engine_id: str) -> bool:
        return engine_id in self._adapters

    def engine_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


class PhoenixRuntime:
    """Executes PXO plans with explicit adapters and atomic checkpoints."""

    def __init__(
        self,
        *,
        orchestrator: PhoenixOrchestrator | None = None,
        registry: AdapterRegistry | None = None,
        policy: RuntimePolicy | None = None,
    ) -> None:
        self.orchestrator = orchestrator or PhoenixOrchestrator()
        self.registry = registry or AdapterRegistry()
        self.policy = policy or RuntimePolicy()
        self.policy.validate()

    def run_next(
        self,
        plan: OrchestrationPlan,
        *,
        checkpoint_directory: str | Path,
    ) -> OrchestrationPlan:
        ready = self.orchestrator.next_executable_engines(plan)
        if not ready:
            self.write_checkpoint(plan, checkpoint_directory)
            return plan

        engine = ready[0]
        if not self.registry.contains(engine.engine_id):
            failed = self.orchestrator.fail_engine(
                plan,
                engine.engine_id,
                f"No runtime adapter registered for {engine.engine_id}.",
            )
            self.write_checkpoint(failed, checkpoint_directory)
            if self.policy.stop_on_first_error:
                raise RuntimeErrorContract(
                    f"Runtime stopped: no adapter for {engine.engine_id}."
                )
            return failed

        running = self.orchestrator.start_engine(plan, engine.engine_id)
        self.write_checkpoint(running, checkpoint_directory)

        try:
            result = self.registry.get(engine.engine_id)(
                project_id=running.project_id,
                engine_id=engine.engine_id,
                plan_fingerprint=running.plan_fingerprint,
            )
            result.validate()
            completed = self.orchestrator.complete_engine(
                running,
                engine.engine_id,
                outputs=result.outputs,
                evidence=result.evidence,
            )
            self.write_checkpoint(completed, checkpoint_directory)
            return completed
        except Exception as exc:
            if isinstance(exc, OrchestrationError):
                error_text = str(exc)
            else:
                error_text = f"{type(exc).__name__}: {exc}"
            failed = self.orchestrator.fail_engine(
                running,
                engine.engine_id,
                error_text,
            )
            self.write_checkpoint(failed, checkpoint_directory)
            if self.policy.stop_on_first_error:
                raise RuntimeErrorContract(
                    f"Runtime stopped after {engine.engine_id} failed: {error_text}"
                ) from exc
            return failed

    def run_until_blocked_or_complete(
        self,
        plan: OrchestrationPlan,
        *,
        checkpoint_directory: str | Path,
    ) -> OrchestrationPlan:
        current = plan
        executions = 0

        while executions < self.policy.maximum_engine_executions:
            ready = self.orchestrator.next_executable_engines(current)
            if not ready:
                self.write_checkpoint(current, checkpoint_directory)
                return current
            current = self.run_next(
                current,
                checkpoint_directory=checkpoint_directory,
            )
            executions += 1

        raise RuntimeErrorContract(
            "maximum_engine_executions reached before the plan stopped."
        )

    def write_checkpoint(
        self,
        plan: OrchestrationPlan,
        checkpoint_directory: str | Path,
    ) -> Path:
        directory = Path(checkpoint_directory)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / self.policy.checkpoint_filename

        payload = {
            "schema": "phoenix-pxo-runtime-checkpoint-v1.0",
            "project_id": plan.project_id,
            "state": plan.state.value,
            "selected_variant_id": plan.selected_variant_id,
            "plan_fingerprint": plan.plan_fingerprint,
            "audit_log": list(plan.audit_log),
            "engines": [
                {
                    **asdict(engine),
                    "dependencies": list(engine.dependencies),
                    "evidence": list(engine.evidence),
                    "outputs": list(engine.outputs),
                }
                for engine in plan.engines
            ],
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload["checkpoint_sha256"] = sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            delete=False,
            suffix=".tmp",
        ) as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            temporary = Path(handle.name)

        temporary.replace(destination)
        return destination


def deterministic_test_adapter(
    *,
    project_id: str,
    engine_id: str,
    plan_fingerprint: str,
) -> AdapterResult:
    """Safe deterministic adapter for tests and integration scaffolding."""
    token = sha256(
        f"{project_id}|{engine_id}|{plan_fingerprint}".encode("utf-8")
    ).hexdigest()
    return AdapterResult(
        outputs=(f"runtime/{engine_id}/{token[:12]}.json",),
        evidence=(f"deterministic-adapter:{token}",),
        metadata={"adapter": "deterministic_test_adapter"},
    )
