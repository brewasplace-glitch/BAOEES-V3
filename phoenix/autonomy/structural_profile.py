"""Phoenix Autonomous Structural Project Profile Generator v1.0.

Creates a concept structural profile sufficient for v8.0 geometric derivation.
All material/grid/span defaults are explicit hypotheses. It deliberately does
not invent code basis, design loads, soil facts, member sizes or approval.
"""
from __future__ import annotations
from typing import Any

VERSION="1.0.0"

def generate_structural_project_profile(*, project_id:str, architectural_model:dict[str,Any], project_context:dict[str,Any]) -> dict[str,Any]:
    building=architectural_model.get("building") or {}
    storeys=int(building.get("storey_count") or len(architectural_model.get("storeys",[])) or 1)
    country=((project_context.get("facts") or {}).get("country_code") if isinstance(project_context,dict) else None)
    return {
        "schema_version":"phoenix.structural-project-profile/1.0",
        "generator":"autonomous_structural_project_profile_v1.0",
        "project_id":project_id,
        "profile_status":"CONCEPT_ENGINEERING_HYPOTHESES",
        "building":{
            "storey_count":storeys,
            "building_type":building.get("type"),
            "gross_floor_area_m2":building.get("gross_floor_area_m2"),
        },
        "project_context":{
            "country_code":country,
            "jurisdiction_confirmed":False,
        },
        "assumptions":{
            "minimum_loadbearing_wall_thickness_m":0.20,
            "default_wall_material":"masonry_candidate",
            "column_grid_target_m":4.0,
            "default_column_material":"reinforced_concrete_candidate",
            "default_slab_material":"reinforced_concrete_candidate",
            "maximum_preferred_slab_span_m":5.0,
            "default_beam_material":"reinforced_concrete_candidate",
            "default_roof_material":"timber_candidate",
        },
        "assumption_register":[
            {"id":"minimum_loadbearing_wall_thickness_m","value":0.20,"unit":"m","basis":"CONCEPT_ENGINEERING_DEFAULT","review_required":True},
            {"id":"default_wall_material","value":"masonry_candidate","basis":"CONCEPT_ENGINEERING_HYPOTHESIS","review_required":True},
            {"id":"column_grid_target_m","value":4.0,"unit":"m","basis":"CONCEPT_ENGINEERING_DEFAULT","review_required":True},
            {"id":"default_column_material","value":"reinforced_concrete_candidate","basis":"CONCEPT_ENGINEERING_HYPOTHESIS","review_required":True},
            {"id":"default_slab_material","value":"reinforced_concrete_candidate","basis":"CONCEPT_ENGINEERING_HYPOTHESIS","review_required":True},
            {"id":"maximum_preferred_slab_span_m","value":5.0,"unit":"m","basis":"CONCEPT_ENGINEERING_DEFAULT","review_required":True},
            {"id":"default_beam_material","value":"reinforced_concrete_candidate","basis":"CONCEPT_ENGINEERING_HYPOTHESIS","review_required":True},
            {"id":"default_roof_material","value":"timber_candidate","basis":"CONCEPT_ENGINEERING_HYPOTHESIS","review_required":True},
        ],
        "code_basis":{
            "status":"UNRESOLVED_REQUIRES_JURISDICTION_AND_ENGINEERING_REVIEW",
            "standard":None,
            "national_annex":None,
        },
        "loads":{
            "status":"NOT_DEFINED_BY_THIS_GENERATOR",
            "dead_loads":None,
            "imposed_loads":None,
            "wind":None,
            "snow":None,
            "seismic":None,
        },
        "geotechnical":{
            "status":"NOT_PROVIDED",
            "soil_profile":None,
            "groundwater":None,
            "foundation_advice":None,
        },
        "automatic_structural_approval":False,
        "professional_structural_review_required":True,
        "production_release":"LOCKED",
    }
