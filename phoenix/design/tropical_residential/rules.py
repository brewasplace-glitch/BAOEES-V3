from __future__ import annotations
from typing import Dict, Any, List

def tropical_features(project: Dict[str, Any], strategy: str) -> List[str]:
    site = project.get("site", {})
    prefs = project.get("preferences", {})
    climate = project.get("climate_profile", "hot_humid")

    f = ["cross_ventilation_layout", "external_shading", "screen_ready_openings"]
    if prefs.get("veranda", True):
        f.append("shaded_veranda")
    if prefs.get("open_plan", True):
        f.append("open_living_zone")
    if prefs.get("courtyard", False):
        f.append("shaded_courtyard")
    if climate in {"hot_humid", "coastal_tropical"}:
        f += ["ventilated_roof_strategy", "high_ceiling_strategy"]
    if climate == "monsoon":
        f += ["high_capacity_roof_drainage", "covered_transitions"]
    if site.get("flood_risk"):
        f += ["raised_floor_strategy", "flood_resilient_service_placement"]
    if site.get("cyclone_risk"):
        f += ["wind_resilience_review_required", "regular_structural_grid"]
    if site.get("coastal_exposure"):
        f += ["coastal_material_durability_review"]

    by_strategy = {
        "PASSIVE_COOLING": ["maximise_breeze_paths", "deep_shading_priority"],
        "LOW_COST": ["simple_structural_grid", "compact_wet_core", "repeatable_openings"],
        "RESILIENCE": ["robust_roof_geometry", "protected_service_core", "redundant_drainage_paths"],
        "INDOOR_OUTDOOR": ["large_shaded_transition", "garden_connection", "privacy_gradient"],
        "BALANCED": ["balanced_passive_cost_resilience"]
    }
    f += by_strategy[strategy]
    return sorted(set(f))
