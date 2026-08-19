from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .engine import generate_variants, select_balanced
from .ifc_author import author_ifc4
from .real_output import write_json, write_layout_bundle
from .real_spatial import build_real_layout
from .tool_discovery import discover_tools
from .freecad_bridge import run_freecad_handoff
from .blender_bridge import run_blender_handoff


def generate_real_spatial_ifc_package(
    project: Dict[str, Any],
    output_dir: Path,
    run_freecad_if_available: bool = False,
    run_blender_if_available: bool = False,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True,exist_ok=True)
    variants=generate_variants(project)
    recommended=select_balanced(variants)
    tools=discover_tools()

    layouts=[]
    layout_paths={}
    ifc_evidence={}
    for variant_obj in variants:
        variant=variant_obj.to_dict()
        layout=build_real_layout(project,variant)
        if not layout["geometry_validation"]["valid"]:
            raise RuntimeError(f"Spatial validation failed for variant {variant['variant_id']}: {layout['geometry_validation']['warnings']}")
        layouts.append(layout)
        bundle=write_layout_bundle(output_dir/"variants",layout)
        layout_paths[variant["variant_id"]]=bundle
        ifc_path=output_dir/"variants"/f"variant_{variant['variant_id']}"/f"variant_{variant['variant_id']}.ifc"
        ifc_evidence[variant["variant_id"]]=author_ifc4(project,layout,ifc_path)

    rec_id=recommended.variant_id
    authoritative_dir=output_dir/"authoritative"
    authoritative_dir.mkdir(parents=True,exist_ok=True)
    source_ifc=Path(ifc_evidence[rec_id]["ifc_file"])
    authoritative_ifc=authoritative_dir/f"{project['project_id']}_authoritative_recommended_{rec_id}.ifc"
    shutil.copy2(source_ifc,authoritative_ifc)
    rec_layout_json=Path(layout_paths[rec_id]["layout_json"])

    freecad_result={"status":"NOT_REQUESTED","executed":False}
    blender_result={"status":"NOT_REQUESTED","executed":False}

    if run_freecad_if_available:
        if tools["freecad"]["found"]:
            freecad_result=run_freecad_handoff(
                rec_layout_json, authoritative_dir/f"{project['project_id']}_recommended_{rec_id}.FCStd",
                executable=str(tools["freecad"]["executable"])
            )
        else:
            freecad_result={"status":"NOT_FOUND","executed":False}

    if run_blender_if_available:
        if tools["blender"]["found"]:
            blender_result=run_blender_handoff(
                rec_layout_json, authoritative_dir/f"{project['project_id']}_recommended_{rec_id}.blend",
                executable=str(tools["blender"]["executable"])
            )
        else:
            blender_result={"status":"NOT_FOUND","executed":False}

    dt_patch={
        "schema":"PHOENIX_TROPICAL_REAL_SPATIAL_DT_PATCH_v1",
        "project_id":project["project_id"],
        "recommended_variant_id":rec_id,
        "authoritative_ifc":str(authoritative_ifc),
        "variant_layouts":layouts,
        "external_tools":tools,
        "freecad_handoff":freecad_result,
        "blender_handoff":blender_result,
        "governance":{
            "professional_approval":"NOT_AUTOMATIC",
            "code_compliance":"NOT_AUTOMATIC",
            "production":"LOCKED",
            "for_construction":"LOCKED"
        }
    }
    write_json(output_dir/"real_spatial_digital_twin_patch.json",dt_patch)

    summary={
        "engine":"PROJECT_PHOENIX_TROPICAL_RESIDENTIAL_REAL_SPATIAL_LAYOUT_AUTHORITATIVE_IFC_v1_0",
        "project_id":project["project_id"],
        "variant_count":5,
        "recommended_variant_id":rec_id,
        "authoritative_ifc":str(authoritative_ifc),
        "authoritative_ifc_bytes":authoritative_ifc.stat().st_size,
        "tools":tools,
        "freecad_handoff":freecad_result,
        "blender_handoff":blender_result,
        "release_status":"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"
    }
    write_json(output_dir/"real_spatial_summary.json",summary)
    write_json(output_dir/"ifc_evidence.json",ifc_evidence)
    return summary
