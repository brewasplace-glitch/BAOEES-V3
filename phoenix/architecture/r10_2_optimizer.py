from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from pathlib import Path
import json

from phoenix.architecture.r2d_r4_opening_rule_engine import WINDOW_COLOR, EXTERIOR_DOOR_COLOR


@dataclass(frozen=True)
class VariantIntent:
    code: str
    identity: str
    climate_devices: List[str]
    site_goals: List[str]


VARIANT_INTENTS = {
    "A": VariantIntent("A", "tropical_modern_courtyard_house", ["deep overhangs", "shaded courtyard edges", "cross-ventilation"], ["clear arrival", "courtyard privacy", "front garden threshold"]),
    "B": VariantIntent("B", "contemporary_paramaribo_veranda_house", ["veranda shading", "rain-protected circulation", "screened openings"], ["L-shaped outdoor room", "street-facing entry"]),
    "C": VariantIntent("C", "breezeway_pavilion_house", ["breezeway cooling", "ventilation axis", "covered connectors"], ["pavilion separation", "readable site porosity"]),
    "D": VariantIntent("D", "tropical_screen_and_patio_house", ["privacy screen", "filtered light", "covered patio"], ["controlled street edge", "private open space"]),
    "E": VariantIntent("E", "biophilic_climate_house", ["planted edges", "stepped shading", "outdoor living terraces"], ["garden integration", "soft boundary treatment"]),
}


def load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, payload: Dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def refine_variant(variant_code: str, source_design: Dict[str, Any]) -> Dict[str, Any]:
    if variant_code not in VARIANT_INTENTS:
        raise ValueError(f"Unknown variant code: {variant_code}")
    intent = VARIANT_INTENTS[variant_code]
    refined = dict(source_design)
    refinement_tags = list(refined.get("refinement_tags", []))
    refinement_tags.extend([
        "r10_2_architectural_quality_optimizer",
        "site_climate_facade_refinement",
        "camera_composition_gate_required",
        "r2d_r4_permanent_opening_rule_engine_required",
        intent.identity,
    ])
    refined["variant_code"] = variant_code
    refined["variant_identity"] = intent.identity
    refined["refinement_tags"] = sorted(set(refinement_tags))
    refined["design_status"] = "PRELIMINARY / NOT FOR CONSTRUCTION"
    refined["locks"] = {
        "design_selection": "LOCKED",
        "structural_solver": "LOCKED",
        "permit": "LOCKED",
        "construction": "LOCKED",
        "professional_architect_review": "REQUIRED",
    }
    refined["r10_2_guidance"] = {
        "architectural_goals": [
            "improve entrance hierarchy",
            "improve facade hierarchy of solid/void/shade",
            "strengthen relationship between plan and external form",
            "make climate devices legible",
            "improve site integration",
        ],
        "climate_devices": intent.climate_devices,
        "site_goals": intent.site_goals,
        "opening_rule_engine": {
            "engine": "PHOENIX_R2D_R4_PERMANENT_OPENING_RULE_ENGINE_1.0",
            "required_before_cad_or_render": True,
            "windows_exterior_only": True,
            "window_color": WINDOW_COLOR,
            "exterior_door_color": EXTERIOR_DOOR_COLOR,
            "bathroom_minimum_exterior_window_count": 1,
            "minimum_rear_or_side_door_per_design": 1,
            "all_rooms_reachable_by_swing_or_sliding_door": True,
            "open_passage_does_not_satisfy_room_access": True,
            "opening_ids_authoritative_across_2d_cad_3d": True,
            "visual_review_required": True,
        },
    }
    return refined


def build_evaluation_summary(variant_code: str, refined_design: Dict[str, Any]) -> Dict[str, Any]:
    intent = VARIANT_INTENTS[variant_code]
    return {
        "variant_code": variant_code,
        "variant_identity": intent.identity,
        "status": "READY_FOR_R10_2_VISUAL_AND_QA_PIPELINE",
        "design_status": refined_design.get("design_status", "PRELIMINARY / NOT FOR CONSTRUCTION"),
        "required_views": ["street_corner", "rear", "side", "courtyard_or_patio", "aerial"],
        "review_focus": [
            "entrance hierarchy",
            "climate-responsive facade articulation",
            "parcel integration",
            "non-orthogonal gesture legibility",
            "camera/composition pass",
        ],
    }
