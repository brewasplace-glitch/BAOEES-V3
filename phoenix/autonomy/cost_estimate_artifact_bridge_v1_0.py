"""Project Phoenix Level-A cost estimate artifact bridge v1.0.

This is an artifact-projection bridge over the existing cost-planning stack.
It does not invent market prices and it is not a replacement cost engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "phoenix.level-a-cost-estimate-artifact/1.0"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def emit_level_a_cost_estimate_artifact(
    *,
    output_dir: Path,
    project_id: str,
    session_id: str | None,
    plan: dict[str, Any],
) -> Path:
    """Emit a concrete Level-A cost-estimate artifact without fabricating prices."""

    price_status = str(plan.get("price_evidence_status") or "UNRESOLVED").upper()
    calculation_ref = plan.get("cost_calculation")
    unresolved = plan.get("unresolved_price_evidence")
    if not isinstance(unresolved, list):
        unresolved = []

    if calculation_ref:
        estimate_status = "LOCAL_COST_CALCULATION_AVAILABLE"
        completeness = "PRICED_OR_PARTIALLY_PRICED_BY_EXISTING_COST_STACK"
    elif price_status == "UNRESOLVED":
        estimate_status = "PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES"
        completeness = "UNPRICED_PENDING_CURRENT_MARKET_EVIDENCE"
    else:
        estimate_status = "READY_FOR_LOCAL_MARKET_COST_ENGINE"
        completeness = "PRICE_ENGINE_COMPLETION_REQUIRED"

    artifact = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "session_id": session_id,
        "artifact_type": "COST_ESTIMATE",
        "output_level": "A",
        "status": estimate_status,
        "completeness": completeness,
        "currency": plan.get("currency"),
        "pricing_level": plan.get("pricing_level"),
        "primary_ratebook": plan.get("primary_ratebook"),
        "pricing_as_of_date": plan.get("pricing_as_of_date"),
        "price_evidence_status": price_status,
        "price_source_register": plan.get("price_source_register"),
        "market_context": plan.get("market_context"),
        "cost_calculation": calculation_ref,
        "unresolved_price_evidence": unresolved,
        "estimate": {
            "line_items": [],
            "known_priced_subtotal": None,
            "unpriced_items_present": calculation_ref is None,
            "subtotal": None,
            "general_costs": None,
            "contingency": None,
            "tax": None,
            "total": None,
        },
        "pricing_rules": {
            "price_fabricated": False,
            "automatic_tax_application": bool(plan.get("automatic_tax_application", False)),
            "fx_used": bool(plan.get("fx_used", False)),
            "international_fx_fallback": bool(plan.get("international_fx_fallback", False)),
            "current_local_price_traceability_required": True,
            "null_amounts_mean_not_yet_supported_by_current_price_evidence": True,
        },
        "source_traceability": {
            "cost_planning_plan": "cost_planning_plan.json",
            "local_material_selection_register": plan.get("local_material_selection_register"),
            "material_selection_register": plan.get("material_selection_register"),
            "global_material_sourcing_register": plan.get("global_material_sourcing_register"),
            "landed_cost_register": plan.get("landed_cost_register"),
        },
        "completion_requirements": [
            "Qualify current local/regional price evidence for unresolved estimate components.",
            "Run or reuse the existing Phoenix cost engine once traceable prices are available.",
            "Professional review remains required before any released project cost claim.",
        ],
        "professional_review_required": True,
        "automatic_professional_approval": False,
        "automatic_code_compliance_claim": False,
        "production_release": "LOCKED",
        "for_construction": "LOCKED",
    }

    path = Path(output_dir) / "cost_estimate.json"
    _write_json(path, artifact)
    return path
