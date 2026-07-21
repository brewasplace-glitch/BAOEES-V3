"""PXO-compatible adapter for Phoenix Optimization Core Wave 15.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from phoenix.optimization import (
    Constraint,
    Objective,
    OptimizationConfig,
    OptimizationCore,
    Variant,
)


ADAPTER_ID = "phoenix.adapter.optimization_core.wave15_1"
ADAPTER_VERSION = "1.0.0"


def _objectives(raw: Sequence[Mapping[str, Any]]) -> tuple[Objective, ...]:
    return tuple(
        Objective(
            name=str(item["name"]),
            direction=str(item.get("direction", "minimize")),
            weight=float(item.get("weight", 1.0)),
            lower_bound=(
                None
                if item.get("lower_bound") is None
                else float(item["lower_bound"])
            ),
            upper_bound=(
                None
                if item.get("upper_bound") is None
                else float(item["upper_bound"])
            ),
        )
        for item in raw
    )


def _constraints(raw: Sequence[Mapping[str, Any]]) -> tuple[Constraint, ...]:
    return tuple(
        Constraint(
            name=str(item["name"]),
            metric=str(item["metric"]),
            operator=str(item["operator"]),
            limit=float(item["limit"]),
            tolerance=float(item.get("tolerance", 1e-9)),
        )
        for item in raw
    )


def _variants(raw: Sequence[Mapping[str, Any]]) -> tuple[Variant, ...]:
    return tuple(
        Variant(
            variant_id=str(item["variant_id"]),
            metrics={
                str(key): float(value)
                for key, value in dict(item["metrics"]).items()
            },
            attributes=dict(item.get("attributes", {})),
        )
        for item in raw
    )


def run_optimization_core(
    request: Mapping[str, Any],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute Wave 15.1 from a JSON-compatible request mapping."""

    config_data = dict(request["config"])
    config = OptimizationConfig(
        project_id=str(config_data["project_id"]),
        objectives=_objectives(config_data["objectives"]),
        constraints=_constraints(config_data.get("constraints", [])),
        sensitivity_delta=float(config_data.get("sensitivity_delta", 0.10)),
        rounding_digits=int(config_data.get("rounding_digits", 9)),
    )
    core = OptimizationCore(config)
    variants = _variants(request["variants"])
    result = core.evaluate(variants)
    result["adapter"] = {"id": ADAPTER_ID, "version": ADAPTER_VERSION}

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        import json
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return result


def create_optimization_core_adapter() -> dict[str, Any]:
    """Return declarative adapter metadata for runtime discovery."""

    return {
        "id": ADAPTER_ID,
        "version": ADAPTER_VERSION,
        "engine_id": "phoenix.optimization_core.wave15_1",
        "entrypoint": (
            "phoenix.adapters.optimization_core_adapter:run_optimization_core"
        ),
        "input_media_type": "application/json",
        "output_media_type": "application/json",
        "deterministic": True,
    }
