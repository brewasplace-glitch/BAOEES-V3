"""Adapter for Phoenix Autonomous Design Orchestrator Wave 15.6."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from phoenix.autonomous_orchestrator import (
    AutonomousDesignOrchestrator,
    OrchestrationContext,
    OrchestrationStep,
)


ADAPTER_ID = "phoenix.adapter.autonomous_design_orchestrator.wave15_6"
ADAPTER_VERSION = "1.0.0"


def run_autonomous_design_orchestrator(
    request: Mapping[str, Any],
    registry: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    context_raw = dict(request["context"])
    context = OrchestrationContext(
        project_id=str(context_raw["project_id"]),
        mode=str(context_raw.get("mode", "fully_autonomous")),
        stop_on_required_failure=bool(
            context_raw.get("stop_on_required_failure", True)
        ),
        human_approval_required=bool(
            context_raw.get("human_approval_required", True)
        ),
    )
    steps = tuple(
        OrchestrationStep(
            step_id=str(item["step_id"]),
            engine_id=str(item["engine_id"]),
            depends_on=tuple(str(dep) for dep in item.get("depends_on", [])),
            required=bool(item.get("required", True)),
            input_key=str(item.get("input_key", "")),
            output_key=str(item.get("output_key", "")),
            metadata=dict(item.get("metadata", {})),
        )
        for item in request["steps"]
    )
    result = AutonomousDesignOrchestrator(registry).run(
        context=context,
        steps=steps,
        initial_state=dict(request.get("initial_state", {})),
    )
    result["adapter"] = {"id": ADAPTER_ID, "version": ADAPTER_VERSION}

    if output_path is not None:
        import json
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return result
