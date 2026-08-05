"""Phoenix European Certified Supply Priority & Import Optimization v1.0."""
from __future__ import annotations

from typing import Any
import math

VERSION = "1.0.0"

EU27 = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}

def origin_priority(country_code: str | None) -> int:
    code = str(country_code or "").upper()
    if code == "NL":
        return 0
    if code == "BE":
        return 1
    if code in EU27:
        return 2
    return 3

def origin_priority_label(country_code: str | None) -> str:
    return {
        0: "NETHERLANDS",
        1: "BELGIUM",
        2: "OTHER_EU",
        3: "OTHER_GLOBAL",
    }[origin_priority(country_code)]

def european_discovery_queries(base_query: str, material_family: str) -> list[str]:
    base = str(base_query or "").strip()
    if not base:
        return []
    return [
        f"{base} Netherlands EU certified supplier",
        f"{base} Belgium EU certified supplier",
        f"{base} European Union certified supplier",
        base,
    ]

def ready_mix_import_allowed(candidate: dict[str, Any], material_family: str) -> bool:
    family = str(material_family or "")
    if family not in {"structural_concrete", "ready_mix_concrete"}:
        return True

    description = str(candidate.get("description") or "").casefold()
    product_form = str(candidate.get("product_form") or "").upper()
    ready_mix_like = (
        "ready-mix" in description
        or "ready mix" in description
        or "wet concrete" in description
        or product_form in {"READY_MIX", "WET_CONCRETE"}
    )
    if not ready_mix_like:
        return True

    return (
        candidate.get("explicit_importability_evidence") is True
        and bool(candidate.get("importability_source_reference"))
    )

def complete_landed_cost_per_unit(evaluated: dict[str, Any]) -> float:
    landed = evaluated.get("landed_cost")
    if not isinstance(landed, dict) or landed.get("status") != "PASSED":
        return math.inf
    try:
        return float(landed.get("landed_cost_per_unit_srd"))
    except (TypeError, ValueError):
        return math.inf

def import_sort_key(evaluated: dict[str, Any]) -> tuple[float, int, float]:
    # Complete landed cost remains the primary selection rule.
    # EU priority only decides discovery order and exact-cost ties.
    cost = complete_landed_cost_per_unit(evaluated)
    origin = origin_priority(evaluated.get("origin_country_code"))
    try:
        lead = float(evaluated.get("lead_time_days"))
    except (TypeError, ValueError):
        lead = math.inf
    return (cost, origin, lead)

def annotate_candidate(evaluated: dict[str, Any]) -> dict[str, Any]:
    row = dict(evaluated)
    row["origin_priority"] = origin_priority(row.get("origin_country_code"))
    row["origin_priority_label"] = origin_priority_label(row.get("origin_country_code"))
    row["selection_policy"] = (
        "LOWEST_COMPLETE_LANDED_COST; "
        "NL_BE_EU_PRIORITY_ONLY_AS_DISCOVERY_ORDER_AND_EQUAL_COST_TIE_BREAK"
    )
    return row
