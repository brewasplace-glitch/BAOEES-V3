from __future__ import annotations
import math
from typing import Dict, Any, List
from .models import Variant
from .rules import tropical_features
from .scoring import score_variant

STRATEGIES = ["PASSIVE_COOLING", "LOW_COST", "RESILIENCE", "INDOOR_OUTDOOR", "BALANCED"]

def _variant_geometry(target_area: float, storeys: int, strategy: str):
    footprint = target_area / max(storeys, 1)
    aspect_map = {
        "PASSIVE_COOLING": 1.75,
        "LOW_COST": 1.35,
        "RESILIENCE": 1.30,
        "INDOOR_OUTDOOR": 1.90,
        "BALANCED": 1.55,
    }
    aspect = aspect_map[strategy]
    width = math.sqrt(footprint * aspect)
    depth = footprint / width
    return footprint, aspect, width, depth

def generate_variants(project: Dict[str, Any]) -> List[Variant]:
    program = project["program"]
    site = project["site"]
    target = float(program["target_floor_area_m2"])
    storeys = int(program.get("storeys", 1))
    bedrooms = int(program["bedrooms"])
    bathrooms = float(program["bathrooms"])

    variants = []
    for idx, strategy in enumerate(STRATEGIES, start=1):
        footprint, aspect, width, depth = _variant_geometry(target, storeys, strategy)
        raised = 0.55 if site.get("flood_risk") else 0.15
        ceiling = 3.4 if strategy == "PASSIVE_COOLING" else 3.2
        veranda = 2.8 if strategy == "INDOOR_OUTDOOR" else 2.2
        roof_pitch = 32 if strategy == "RESILIENCE" else 28
        overhang = 1.1 if strategy in {"PASSIVE_COOLING", "INDOOR_OUTDOOR"} else 0.9

        assumptions = [
            "Conceptual tropical design heuristics; not a building-code compliance result.",
            "Room packing and exact geometry require the next spatial-layout/BIM stage.",
            "Climate and wind/flood assumptions must be replaced by project-specific evidence."
        ]

        variants.append(Variant(
            variant_id=chr(64 + idx),
            strategy=strategy,
            floor_area_m2=round(target, 2),
            footprint_m2=round(footprint, 2),
            storeys=storeys,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            width_m=round(width, 2),
            depth_m=round(depth, 2),
            orientation_deg=float(site.get("north_deg", 0)),
            ceiling_height_m=ceiling,
            veranda_depth_m=veranda,
            roof_pitch_deg=roof_pitch,
            eave_overhang_m=overhang,
            raised_floor_m=raised,
            features=tropical_features(project, strategy),
            scores=score_variant(project, strategy, footprint, aspect),
            assumptions=assumptions
        ))
    return variants

def select_balanced(variants: List[Variant]) -> Variant:
    def avg(v: Variant):
        return sum(v.scores.values()) / max(len(v.scores), 1)
    return max(variants, key=avg)
