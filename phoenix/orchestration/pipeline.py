"""Phoenix Autonomous Delivery Pipeline — Wave 3 v1.0.

Bridges PPG variant generation and selection to PXO plan creation and runtime
execution. The pipeline is deterministic, resumable from JSON checkpoints and
does not claim completion for engines without registered runtime adapters.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from phoenix.project_generator import (
    ProjectBrief,
    ProjectVariant,
    VariantWeights,
    generate_project_variants,
    select_project_variant,
    variant_presentation_queue,
)
from phoenix.orchestration.phoenix_orchestrator import (
    EngineExecution,
    OrchestrationPlan,
    OrchestrationState,
    PhoenixOrchestrator,
    ProjectContext,
)
from phoenix.orchestration.runtime import (
    AdapterRegistry,
    PhoenixRuntime,
    RuntimePolicy,
)


class PipelineError(RuntimeError):
    """Raised when the autonomous delivery pipeline contract is violated."""


@dataclass(frozen=True)
class PipelineBootstrap:
    project_id: str
    selected_variant_id: str
    selected_variant_fingerprint: str
    variant_count: int
    presentation_queue: tuple[dict[str, object], ...]
    plan: OrchestrationPlan
    bootstrap_fingerprint: str


@dataclass(frozen=True)
class PipelineResumeResult:
    plan: OrchestrationPlan
    checkpoint_sha256: str
    source_checkpoint: str


class PhoenixDeliveryPipeline:
    """High-level PPG → PXO → Runtime coordinator."""

    def __init__(
        self,
        *,
        orchestrator: PhoenixOrchestrator | None = None,
        registry: AdapterRegistry | None = None,
        runtime_policy: RuntimePolicy | None = None,
    ) -> None:
        self.orchestrator = orchestrator or PhoenixOrchestrator()
        self.registry = registry or AdapterRegistry()
        self.runtime = PhoenixRuntime(
            orchestrator=self.orchestrator,
            registry=self.registry,
            policy=runtime_policy or RuntimePolicy(),
        )

    def bootstrap(
        self,
        brief: ProjectBrief,
        *,
        weights: VariantWeights | None = None,
        selected_variant_id: str | None = None,
    ) -> PipelineBootstrap:
        variants = generate_project_variants(brief, weights)
        selected = select_project_variant(variants, selected_variant_id)
        queue = variant_presentation_queue(variants)

        context = ProjectContext(
            project_id=brief.project_id,
            instruction=brief.instruction,
            location_reference=brief.location_reference,
            selected_variant_id=selected.variant_id,
            selected_variant_fingerprint=selected.fingerprint,
            available_engines=self.registry.engine_ids(),
            assumptions=brief.assumptions,
        )
        plan = self.orchestrator.create_plan(context)

        fingerprint = sha256(
            (
                brief.project_id
                + "|"
                + selected.variant_id
                + "|"
                + selected.fingerprint
                + "|"
                + plan.plan_fingerprint
            ).encode("utf-8")
        ).hexdigest()

        return PipelineBootstrap(
            project_id=brief.project_id,
            selected_variant_id=selected.variant_id,
            selected_variant_fingerprint=selected.fingerprint,
            variant_count=len(variants),
            presentation_queue=queue,
            plan=plan,
            bootstrap_fingerprint=fingerprint,
        )

    def run_next(
        self,
        bootstrap: PipelineBootstrap,
        *,
        checkpoint_directory: str | Path,
    ) -> OrchestrationPlan:
        return self.runtime.run_next(
            bootstrap.plan,
            checkpoint_directory=checkpoint_directory,
        )

    def run_plan_until_blocked_or_complete(
        self,
        plan: OrchestrationPlan,
        *,
        checkpoint_directory: str | Path,
    ) -> OrchestrationPlan:
        return self.runtime.run_until_blocked_or_complete(
            plan,
            checkpoint_directory=checkpoint_directory,
        )

    def write_bootstrap_manifest(
        self,
        bootstrap: PipelineBootstrap,
        destination: str | Path,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema": "phoenix-delivery-bootstrap-v1.0",
            "project_id": bootstrap.project_id,
            "selected_variant_id": bootstrap.selected_variant_id,
            "selected_variant_fingerprint": bootstrap.selected_variant_fingerprint,
            "variant_count": bootstrap.variant_count,
            "presentation_queue": list(bootstrap.presentation_queue),
            "plan": self._serialize_plan(bootstrap.plan),
            "bootstrap_fingerprint": bootstrap.bootstrap_fingerprint,
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload["manifest_sha256"] = sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def resume_from_checkpoint(
        self,
        checkpoint_file: str | Path,
    ) -> PipelineResumeResult:
        path = Path(checkpoint_file)
        if not path.is_file():
            raise PipelineError(f"Checkpoint does not exist: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        expected_hash = payload.get("checkpoint_sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise PipelineError("Checkpoint SHA-256 is missing or invalid.")

        verification_payload = dict(payload)
        verification_payload.pop("checkpoint_sha256", None)
        canonical = json.dumps(
            verification_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        actual_hash = sha256(canonical.encode("utf-8")).hexdigest()
        if actual_hash != expected_hash:
            raise PipelineError("Checkpoint integrity verification failed.")

        try:
            engines = tuple(
                EngineExecution(
                    engine_id=item["engine_id"],
                    status=item["status"],
                    dependencies=tuple(item.get("dependencies", ())),
                    required=bool(item.get("required", True)),
                    evidence=tuple(item.get("evidence", ())),
                    outputs=tuple(item.get("outputs", ())),
                    error=item.get("error"),
                )
                for item in payload["engines"]
            )
            state = OrchestrationState(payload["state"])
            plan = OrchestrationPlan(
                project_id=payload["project_id"],
                state=state,
                engines=engines,
                selected_variant_id=payload["selected_variant_id"],
                plan_fingerprint=payload["plan_fingerprint"],
                audit_log=tuple(payload.get("audit_log", ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PipelineError("Checkpoint structure is invalid.") from exc

        return PipelineResumeResult(
            plan=plan,
            checkpoint_sha256=expected_hash,
            source_checkpoint=str(path),
        )

    @staticmethod
    def _serialize_plan(plan: OrchestrationPlan) -> dict[str, object]:
        return {
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
