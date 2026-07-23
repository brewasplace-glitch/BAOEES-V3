"""Autonomous Design Orchestrator for Project Phoenix — Wave 15.6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ENGINE_ID = "phoenix.autonomous_design_orchestrator.wave15_6"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"


class OrchestrationError(RuntimeError):
    """Raised when orchestration input or execution is invalid."""


@dataclass(frozen=True)
class OrchestrationStep:
    step_id: str
    engine_id: str
    depends_on: tuple[str, ...] = ()
    required: bool = True
    input_key: str = ""
    output_key: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.step_id.strip():
            raise OrchestrationError("step_id must not be empty.")
        if not self.engine_id.strip():
            raise OrchestrationError("engine_id must not be empty.")
        if self.step_id in self.depends_on:
            raise OrchestrationError(f"Step {self.step_id} cannot depend on itself.")


@dataclass(frozen=True)
class OrchestrationContext:
    project_id: str
    mode: str = "fully_autonomous"
    stop_on_required_failure: bool = True
    human_approval_required: bool = True

    def validate(self) -> None:
        if not self.project_id.strip():
            raise OrchestrationError("project_id must not be empty.")
        if self.mode not in {"assistant", "semi_autonomous", "fully_autonomous"}:
            raise OrchestrationError("Unsupported orchestration mode.")


class AutonomousDesignOrchestrator:
    """Runs a deterministic dependency-ordered engine workflow."""

    def __init__(self, registry: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]]):
        self._registry = dict(registry)

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _topological_order(steps: Iterable[OrchestrationStep]) -> list[OrchestrationStep]:
        step_list = list(steps)
        if not step_list:
            raise OrchestrationError("At least one orchestration step is required.")

        by_id: dict[str, OrchestrationStep] = {}
        for step in step_list:
            step.validate()
            if step.step_id in by_id:
                raise OrchestrationError(f"Duplicate step_id: {step.step_id}")
            by_id[step.step_id] = step

        for step in step_list:
            for dep in step.depends_on:
                if dep not in by_id:
                    raise OrchestrationError(
                        f"Step {step.step_id} depends on unknown step {dep}."
                    )

        indegree = {step.step_id: 0 for step in step_list}
        children: dict[str, list[str]] = {step.step_id: [] for step in step_list}
        for step in step_list:
            for dep in step.depends_on:
                indegree[step.step_id] += 1
                children[dep].append(step.step_id)

        ready = sorted([sid for sid, degree in indegree.items() if degree == 0])
        order: list[OrchestrationStep] = []

        while ready:
            current = ready.pop(0)
            order.append(by_id[current])
            for child in sorted(children[current]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()

        if len(order) != len(step_list):
            raise OrchestrationError("Dependency cycle detected.")
        return order

    def run(
        self,
        *,
        context: OrchestrationContext,
        steps: Iterable[OrchestrationStep],
        initial_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        context.validate()
        order = self._topological_order(steps)
        state: dict[str, Any] = dict(initial_state or {})
        step_results: list[dict[str, Any]] = []
        failed_required = False

        for sequence, step in enumerate(order, start=1):
            blocked_dependencies = [
                dep
                for dep in step.depends_on
                if next(
                    item["status"]
                    for item in step_results
                    if item["step_id"] == dep
                ) not in {"completed", "skipped_optional"}
            ]
            if blocked_dependencies:
                status = "blocked"
                result = {
                    "sequence": sequence,
                    "step_id": step.step_id,
                    "engine_id": step.engine_id,
                    "status": status,
                    "reason": "dependency_failed",
                    "blocked_by": blocked_dependencies,
                    "required": step.required,
                }
                step_results.append(result)
                if step.required:
                    failed_required = True
                    if context.stop_on_required_failure:
                        break
                continue

            runner = self._registry.get(step.engine_id)
            if runner is None:
                status = "failed" if step.required else "skipped_optional"
                result = {
                    "sequence": sequence,
                    "step_id": step.step_id,
                    "engine_id": step.engine_id,
                    "status": status,
                    "reason": "engine_not_registered",
                    "required": step.required,
                }
                step_results.append(result)
                if step.required:
                    failed_required = True
                    if context.stop_on_required_failure:
                        break
                continue

            input_payload: Mapping[str, Any]
            if step.input_key:
                raw = state.get(step.input_key, {})
                if not isinstance(raw, Mapping):
                    raise OrchestrationError(
                        f"Input for step {step.step_id} must be a mapping."
                    )
                input_payload = raw
            else:
                input_payload = state

            try:
                output = dict(runner(input_payload))
                if step.output_key:
                    state[step.output_key] = output
                else:
                    state[step.step_id] = output
                result = {
                    "sequence": sequence,
                    "step_id": step.step_id,
                    "engine_id": step.engine_id,
                    "status": "completed",
                    "required": step.required,
                    "input_key": step.input_key or None,
                    "output_key": step.output_key or step.step_id,
                    "output_sha256": self._digest(output),
                }
            except Exception as exc:
                result = {
                    "sequence": sequence,
                    "step_id": step.step_id,
                    "engine_id": step.engine_id,
                    "status": "failed",
                    "required": step.required,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                if step.required:
                    failed_required = True
                    step_results.append(result)
                    if context.stop_on_required_failure:
                        break
                    continue
            step_results.append(result)

        completed_ids = {item["step_id"] for item in step_results}
        pending = [
            step.step_id for step in order if step.step_id not in completed_ids
        ]

        if failed_required:
            workflow_status = "failed"
        elif pending:
            workflow_status = "incomplete"
        else:
            workflow_status = "completed"

        approval_status = (
            "awaiting_human_approval"
            if context.human_approval_required and workflow_status == "completed"
            else workflow_status
        )

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
            "project_id": context.project_id,
            "context": asdict(context),
            "workflow_status": workflow_status,
            "approval_status": approval_status,
            "execution_order": [step.step_id for step in order],
            "step_results": step_results,
            "pending_steps": pending,
            "state": state,
            "integration_contract": {
                "upstream_engines": [
                    "phoenix.optimization_core.wave15_1",
                    "phoenix.multi_material_design.wave15_2",
                    "phoenix.cost_carbon_optimization.wave15_3",
                    "phoenix.variant_ranking_decision_intelligence.wave15_4",
                    "phoenix.autonomous_decision_engine.wave15_5",
                ],
                "downstream_engine": "phoenix.digital_twin_synchronization.wave15_7",
            },
            "limitations": [
                "Only registered engines can be executed.",
                "Engine outputs are trusted as supplied but checksummed.",
                "No engineering, legal or regulatory certification is claimed.",
                "Human approval is enabled by default.",
            ],
        }
        payload["evidence"] = {
            "algorithm": "sha256",
            "payload_sha256": self._digest(payload),
        }
        return payload

    def write_result(
        self,
        *,
        context: OrchestrationContext,
        steps: Iterable[OrchestrationStep],
        initial_state: Mapping[str, Any] | None,
        destination: str | Path,
    ) -> Path:
        result = self.run(
            context=context,
            steps=steps,
            initial_state=initial_state,
        )
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(path)
        return path
