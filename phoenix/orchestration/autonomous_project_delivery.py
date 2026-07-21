from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class DeliveryError(ValueError):
    pass

class StageStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass(frozen=True)
class DesignVariant:
    variant_id: str
    title: str
    score: float

@dataclass
class ProjectDeliveryState:
    project_id: str
    instruction: str
    location_reference: str
    variants_required: int = 10
    selected_variant_id: str | None = None
    stage_status: dict[str, StageStatus] = field(default_factory=dict)

ENGINE_DEPENDENCIES = {
    "gis": (),
    "concept_generation": ("gis",),
    "variant_scoring": ("concept_generation",),
    "geotechnical": ("gis",),
    "structural": ("concept_generation",),
    "foundation": ("geotechnical", "structural"),
    "traffic": ("gis",),
    "road_design": ("traffic",),
    "hydraulics": ("gis",),
    "concrete": ("structural",),
    "structural_steel": ("structural",),
    "sustainability": ("concept_generation",),
    "electrical": ("concept_generation",),
    "fire_safety": ("concept_generation",),
    "water_supply": ("concept_generation",),
    "sewer_design": ("gis", "concept_generation"),
    "climate_installations": ("concept_generation",),
    "bim": ("concept_generation",),
    "cost": ("bim", "structural", "electrical", "water_supply", "sewer_design"),
    "permit": ("gis", "traffic", "fire_safety", "bim"),
    "planning": ("cost", "bim"),
    "ai_optimization": ("variant_scoring", "cost", "sustainability"),
    "dossier": ("permit", "planning", "cost", "bim"),
}

DELIVERABLES = (
    "10_concept_designs",
    "selected_design",
    "geotechnical_report",
    "foundation_design",
    "structural_report",
    "construction_drawings",
    "sewer_design",
    "climate_installation_design",
    "electrical_installation_design",
    "water_supply_design",
    "parking_and_traffic_report",
    "total_cost_estimate",
    "permit_dossiers",
    "construction_schedule",
    "specification_drawings",
    "bill_of_quantities",
    "complete_project_dossier",
)

def create_project_state(project_id: str, instruction: str, location_reference: str) -> ProjectDeliveryState:
    if not project_id.strip() or not instruction.strip() or not location_reference.strip():
        raise DeliveryError("project_id, instruction and location_reference are required.")
    status = {name: StageStatus.PENDING for name in ENGINE_DEPENDENCIES}
    status["gis"] = StageStatus.READY
    return ProjectDeliveryState(project_id.strip(), instruction.strip(), location_reference.strip(), stage_status=status)

def validate_variants(variants: tuple[DesignVariant, ...]) -> tuple[DesignVariant, ...]:
    if len(variants) != 10:
        raise DeliveryError("exactly 10 design variants are required.")
    if len({v.variant_id for v in variants}) != 10:
        raise DeliveryError("variant identifiers must be unique.")
    if any(not 0.0 <= v.score <= 1.0 for v in variants):
        raise DeliveryError("variant scores must be between 0 and 1.")
    return variants

def select_variant(state: ProjectDeliveryState, variants: tuple[DesignVariant, ...], selected_id: str | None = None) -> DesignVariant:
    ranked = sorted(validate_variants(variants), key=lambda v: (-v.score, v.variant_id))
    selected = ranked[0] if selected_id is None else next((v for v in ranked if v.variant_id == selected_id), None)
    if selected is None:
        raise DeliveryError("selected variant does not exist.")
    state.selected_variant_id = selected.variant_id
    state.stage_status["concept_generation"] = StageStatus.COMPLETE
    state.stage_status["variant_scoring"] = StageStatus.COMPLETE
    return selected

def ready_engines(state: ProjectDeliveryState) -> tuple[str, ...]:
    ready = []
    for engine, dependencies in ENGINE_DEPENDENCIES.items():
        if state.stage_status[engine] != StageStatus.PENDING:
            continue
        if all(state.stage_status[d] == StageStatus.COMPLETE for d in dependencies):
            ready.append(engine)
    return tuple(ready)

def dossier_manifest(state: ProjectDeliveryState) -> dict[str, object]:
    return {
        "project_id": state.project_id,
        "instruction": state.instruction,
        "location_reference": state.location_reference,
        "selected_variant_id": state.selected_variant_id,
        "deliverables": list(DELIVERABLES),
        "engine_status": {k: v.value for k, v in state.stage_status.items()},
    }
