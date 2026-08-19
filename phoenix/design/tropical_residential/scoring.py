from __future__ import annotations
from typing import Dict, Any

def score_variant(project: Dict[str, Any], strategy: str, footprint_m2: float, aspect: float) -> Dict[str, float]:
    site = project.get("site", {})
    prefs = project.get("preferences", {})
    scores = {
        "passive_cooling": 0.72,
        "cost_efficiency": 0.68,
        "resilience": 0.70,
        "indoor_outdoor": 0.70,
        "structural_regular": 0.76,
        "privacy": 0.70,
        "compactness": max(0.3, min(1.0, 1.0 - abs(aspect - 1.6) * 0.18)),
    }
    if strategy == "PASSIVE_COOLING":
        scores["passive_cooling"] += 0.18
    elif strategy == "LOW_COST":
        scores["cost_efficiency"] += 0.20
        scores["structural_regular"] += 0.10
    elif strategy == "RESILIENCE":
        scores["resilience"] += 0.22
    elif strategy == "INDOOR_OUTDOOR":
        scores["indoor_outdoor"] += 0.22
        scores["privacy"] += 0.05
    elif strategy == "BALANCED":
        for k in scores:
            scores[k] += 0.05

    if site.get("flood_risk") and strategy == "RESILIENCE":
        scores["resilience"] += 0.05
    if prefs.get("veranda", True):
        scores["indoor_outdoor"] += 0.04
        scores["passive_cooling"] += 0.03

    return {k: round(max(0.0, min(1.0, v)), 3) for k, v in scores.items()}
