from __future__ import annotations
from .adapters import detect_open_source_stack

def build_authoritative_ifc_contract(project, variant):
    stack=detect_open_source_stack()
    return {
        "contract": "PHOENIX_AUTHORITATIVE_IFC_HANDOFF_v1",
        "project_id": project["project_id"],
        "variant_id": variant["variant_id"],
        "status": "IFCOPENSHELL_AVAILABLE_FOR_AUTHORING" if stack["ifcopenshell"]["available"] else "IFCOPENSHELL_NOT_INSTALLED_CONTRACT_READY",
        "geometry": {k: variant[k] for k in ("width_m","depth_m","storeys","floor_area_m2","raised_floor_m","roof_pitch_deg")},
        "features": variant["features"],
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
        "note": "Foundation v1.0 defines the IFC handoff contract and never fabricates an IFC file when the OSS authoring engine is unavailable."
    }
