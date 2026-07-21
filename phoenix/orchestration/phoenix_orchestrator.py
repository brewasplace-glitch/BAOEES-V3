"""Phoenix Orchestrator (PXO) v1.0.

PXO is the deterministic workflow coordinator between the selected PPG concept
and downstream Phoenix engines. It creates a traceable execution plan, enforces
dependencies, records engine results and exposes the next executable engines.

PXO v1.0 coordinates contracts only. It does not claim that absent discipline
engines have executed successfully.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Iterable, Mapping


class OrchestrationError(ValueError):
    """Raised when an orchestration transition violates the PXO contract."""


class OrchestrationState(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ProjectContext:
    project_id: str
    instruction: str
    location_reference: str
    selected_variant_id: str
    selected_variant_fingerprint: str
    available_engines: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        required = {
            "project_id": self.project_id,
            "instruction": self.instruction,
            "location_reference": self.location_reference,
            "selected_variant_id": self.selected_variant_id,
            "selected_variant_fingerprint": self.selected_variant_fingerprint,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise OrchestrationError(
                "Missing required project context fields: " + ", ".join(missing)
            )


@dataclass(frozen=True)
class EngineExecution:
    engine_id: str
    status: str = "pending"
    dependencies: tuple[str, ...] = ()
    required: bool = True
    evidence: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    error: str | None = None

    def validate(self) -> None:
        allowed = {"pending", "ready", "running", "completed", "blocked", "failed", "skipped"}
        if self.status not in allowed:
            raise OrchestrationError(f"Unsupported engine status: {self.status}")
        if self.engine_id in self.dependencies:
            raise OrchestrationError("An engine cannot depend on itself.")


@dataclass(frozen=True)
class OrchestrationPlan:
    project_id: str
    state: OrchestrationState
    engines: tuple[EngineExecution, ...]
    selected_variant_id: str
    plan_fingerprint: str
    audit_log: tuple[str, ...] = ()

    def engine_map(self) -> dict[str, EngineExecution]:
        return {engine.engine_id: engine for engine in self.engines}


_ENGINE_GRAPH: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("gis", (), True),
    ("geotechnical", ("gis",), True),
    ("traffic", ("gis",), True),
    ("parking", ("gis", "traffic"), True),
    ("foundation", ("geotechnical",), True),
    ("structural", ("foundation",), True),
    ("structural_steel", ("structural",), False),
    ("concrete", ("structural",), False),
    ("fire_safety", ("gis",), True),
    ("water_supply", ("gis",), True),
    ("sewer", ("gis", "water_supply"), True),
    ("climate_installations", ("gis",), True),
    ("electrical", ("gis",), True),
    ("sustainability", ("gis",), True),
    ("cost", ("foundation", "structural", "parking"), True),
    ("permit", ("gis", "traffic", "parking", "fire_safety"), True),
    ("planning", ("cost", "permit"), True),
    ("bim", ("foundation", "structural", "sewer", "electrical"), True),
    ("digital_twin", ("bim", "planning"), True),
    ("dossier", ("digital_twin", "permit", "cost"), True),
)


def _fingerprint(context: ProjectContext, engines: Iterable[EngineExecution]) -> str:
    canonical = "|".join(
        [
            context.project_id,
            context.selected_variant_id,
            context.selected_variant_fingerprint,
            *[
                f"{engine.engine_id}:{engine.status}:{','.join(engine.dependencies)}"
                for engine in engines
            ],
        ]
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class PhoenixOrchestrator:
    """Builds and advances deterministic Phoenix execution plans."""

    def create_plan(self, context: ProjectContext) -> OrchestrationPlan:
        context.validate()
        available = set(context.available_engines)
        executions: list[EngineExecution] = []

        for engine_id, dependencies, required in _ENGINE_GRAPH:
            status = "pending"
            evidence = ("PXO-v1.0-contract",)
            if available and engine_id not in available:
                status = "blocked" if required else "skipped"
                evidence += ("engine-not-available",)
            executions.append(
                EngineExecution(
                    engine_id=engine_id,
                    status=status,
                    dependencies=dependencies,
                    required=required,
                    evidence=evidence,
                )
            )

        executions = self._refresh_ready(tuple(executions))
        state = self._derive_state(executions)
        fp = _fingerprint(context, executions)
        return OrchestrationPlan(
            project_id=context.project_id,
            state=state,
            engines=executions,
            selected_variant_id=context.selected_variant_id,
            plan_fingerprint=fp,
            audit_log=(
                "plan-created",
                f"variant:{context.selected_variant_id}",
                f"plan-fingerprint:{fp}",
            ),
        )

    def next_executable_engines(
        self,
        plan: OrchestrationPlan,
    ) -> tuple[EngineExecution, ...]:
        return tuple(engine for engine in plan.engines if engine.status == "ready")

    def start_engine(
        self,
        plan: OrchestrationPlan,
        engine_id: str,
    ) -> OrchestrationPlan:
        engine = self._get_engine(plan, engine_id)
        if engine.status != "ready":
            raise OrchestrationError(
                f"Engine {engine_id} cannot start from status {engine.status}."
            )
        return self._replace_engine(
            plan,
            replace(engine, status="running"),
            f"engine-started:{engine_id}",
        )

    def complete_engine(
        self,
        plan: OrchestrationPlan,
        engine_id: str,
        *,
        outputs: Iterable[str],
        evidence: Iterable[str],
    ) -> OrchestrationPlan:
        engine = self._get_engine(plan, engine_id)
        if engine.status != "running":
            raise OrchestrationError(
                f"Engine {engine_id} cannot complete from status {engine.status}."
            )

        output_tuple = tuple(outputs)
        evidence_tuple = tuple(evidence)
        if not output_tuple:
            raise OrchestrationError("Completed engines require at least one output.")
        if not evidence_tuple:
            raise OrchestrationError("Completed engines require evidence.")

        updated = replace(
            engine,
            status="completed",
            outputs=output_tuple,
            evidence=engine.evidence + evidence_tuple,
            error=None,
        )
        return self._replace_engine(
            plan,
            updated,
            f"engine-completed:{engine_id}",
        )

    def fail_engine(
        self,
        plan: OrchestrationPlan,
        engine_id: str,
        error: str,
    ) -> OrchestrationPlan:
        engine = self._get_engine(plan, engine_id)
        if engine.status not in {"ready", "running"}:
            raise OrchestrationError(
                f"Engine {engine_id} cannot fail from status {engine.status}."
            )
        if not error.strip():
            raise OrchestrationError("A failed engine requires an error message.")
        return self._replace_engine(
            plan,
            replace(engine, status="failed", error=error),
            f"engine-failed:{engine_id}",
        )

    def status_summary(self, plan: OrchestrationPlan) -> Mapping[str, object]:
        counts: dict[str, int] = {}
        for engine in plan.engines:
            counts[engine.status] = counts.get(engine.status, 0) + 1
        return {
            "project_id": plan.project_id,
            "selected_variant_id": plan.selected_variant_id,
            "state": plan.state.value,
            "counts": counts,
            "next_engines": [
                engine.engine_id for engine in self.next_executable_engines(plan)
            ],
            "plan_fingerprint": plan.plan_fingerprint,
        }

    def _get_engine(
        self,
        plan: OrchestrationPlan,
        engine_id: str,
    ) -> EngineExecution:
        for engine in plan.engines:
            if engine.engine_id == engine_id:
                return engine
        raise OrchestrationError(f"Unknown engine: {engine_id}")

    def _replace_engine(
        self,
        plan: OrchestrationPlan,
        updated: EngineExecution,
        audit_entry: str,
    ) -> OrchestrationPlan:
        engines = tuple(
            updated if engine.engine_id == updated.engine_id else engine
            for engine in plan.engines
        )
        engines = self._refresh_ready(engines)
        state = self._derive_state(engines)
        fp = sha256(
            (
                plan.project_id
                + "|"
                + plan.selected_variant_id
                + "|"
                + "|".join(
                    f"{e.engine_id}:{e.status}:{','.join(e.outputs)}" for e in engines
                )
            ).encode("utf-8")
        ).hexdigest()
        return OrchestrationPlan(
            project_id=plan.project_id,
            state=state,
            engines=engines,
            selected_variant_id=plan.selected_variant_id,
            plan_fingerprint=fp,
            audit_log=plan.audit_log + (audit_entry, f"plan-fingerprint:{fp}"),
        )

    @staticmethod
    def _refresh_ready(
        engines: tuple[EngineExecution, ...],
    ) -> tuple[EngineExecution, ...]:
        engine_map = {engine.engine_id: engine for engine in engines}
        refreshed: list[EngineExecution] = []

        for engine in engines:
            if engine.status not in {"pending", "ready"}:
                refreshed.append(engine)
                continue

            dependency_states = [
                engine_map[dependency].status for dependency in engine.dependencies
            ]
            if any(status == "failed" for status in dependency_states):
                refreshed.append(replace(engine, status="blocked"))
            elif all(status in {"completed", "skipped"} for status in dependency_states):
                refreshed.append(replace(engine, status="ready"))
            else:
                refreshed.append(replace(engine, status="pending"))

        return tuple(refreshed)

    @staticmethod
    def _derive_state(
        engines: tuple[EngineExecution, ...],
    ) -> OrchestrationState:
        required = tuple(engine for engine in engines if engine.required)
        if any(engine.status == "failed" for engine in required):
            return OrchestrationState.FAILED
        if all(engine.status == "completed" for engine in required):
            return OrchestrationState.COMPLETED
        if any(engine.status == "running" for engine in required):
            return OrchestrationState.RUNNING
        if any(engine.status == "ready" for engine in required):
            return OrchestrationState.READY
        if any(engine.status == "blocked" for engine in required):
            return OrchestrationState.BLOCKED
        return OrchestrationState.CREATED
