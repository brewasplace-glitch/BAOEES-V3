from __future__ import annotations

def build_digital_twin_patch(project, variants, recommended_id):
    return {
        "schema": "PHOENIX_TROPICAL_RESIDENTIAL_DT_PATCH_v1",
        "project_id": project["project_id"],
        "namespace": "design.tropical_residential",
        "recommended_variant_id": recommended_id,
        "variants": variants,
        "governance": {
            "professional_approval": "NOT_AUTOMATIC",
            "code_compliance": "NOT_AUTOMATIC",
            "production": "LOCKED",
            "for_construction": "LOCKED"
        }
    }
