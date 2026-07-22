"""PXO/PUM adapter for Phoenix Wave 15.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from phoenix.multi_material import (
    DesignContext,
    MaterialCandidate,
    MultiMaterialDesignEngine,
    SystemCandidate,
)


ADAPTER_ID = "phoenix.adapter.multi_material_design.wave15_2"
ADAPTER_VERSION = "1.0.0"


def run_multi_material_design(
    request: Mapping[str, Any],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    context_raw = dict(request["context"])
    context = DesignContext(
        project_id=str(context_raw["project_id"]),
        design_action_kn=float(context_raw["design_action_kn"]),
        maximum_utilization=float(
            context_raw.get("maximum_utilization", 1.0)
        ),
        permitted_families=tuple(
            context_raw.get(
                "permitted_families",
                ["concrete", "steel", "timber", "masonry", "other"],
            )
        ),
    )
    materials = tuple(
        MaterialCandidate(
            material_id=str(item["material_id"]),
            family=str(item["family"]),
            density_kg_m3=float(item["density_kg_m3"]),
            embodied_carbon_kgco2e_kg=float(
                item["embodied_carbon_kgco2e_kg"]
            ),
            cost_per_kg=float(item["cost_per_kg"]),
            strength_mpa=float(item["strength_mpa"]),
            durability_score=float(item.get("durability_score", 0.5)),
            constructability_score=float(
                item.get("constructability_score", 0.5)
            ),
            attributes=dict(item.get("attributes", {})),
        )
        for item in request["materials"]
    )
    systems = tuple(
        SystemCandidate(
            system_id=str(item["system_id"]),
            required_family=str(item.get("required_family", "any")),
            volume_m3=float(item["volume_m3"]),
            design_resistance_kn=float(item["design_resistance_kn"]),
            span_m=float(item["span_m"]),
            element_count=int(item.get("element_count", 1)),
            attributes=dict(item.get("attributes", {})),
        )
        for item in request["systems"]
    )
    engine = MultiMaterialDesignEngine()
    result = engine.generate(
        context=context,
        materials=materials,
        systems=systems,
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
