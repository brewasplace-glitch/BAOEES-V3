from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PHOENIX_R8_STRUCTURAL_INPUT_MATERIALIZATION_V1"

def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _file_record(path: Path) -> dict[str, Any]:
    return {"path":str(path),"bytes":path.stat().st_size,"sha256":_sha256(path)}

def materialization_eligibility(canonical_layout_json: Path) -> dict[str, Any]:
    p=Path(canonical_layout_json)
    reasons=[]
    if not p.is_file():
        return {"eligible":False,"reasons":[f"LAYOUT_MISSING:{p}"]}
    try:
        layout=json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"eligible":False,"reasons":[f"LAYOUT_JSON_INVALID:{exc}"]}
    try:
        storeys=int(layout.get("storeys") or 0)
    except Exception:
        storeys=0
    try:
        height=float(layout.get("storey_height_m") or 0.0)
    except Exception:
        height=0.0
    fp=layout.get("footprint") or {}
    try:
        width=float(fp.get("width_m") or 0.0)
        depth=float(fp.get("depth_m") or 0.0)
    except Exception:
        width=depth=0.0
    if storeys < 1: reasons.append("STOREY_COUNT_REQUIRED")
    if height <= 0: reasons.append("STOREY_HEIGHT_REQUIRED")
    if width <= 0 or depth <= 0: reasons.append("POSITIVE_FOOTPRINT_REQUIRED")
    if not isinstance(layout.get("rooms"),list): reasons.append("ROOMS_LIST_REQUIRED")
    if not isinstance(layout.get("walls"),list): reasons.append("WALLS_LIST_REQUIRED")
    if not isinstance(layout.get("openings"),list): reasons.append("OPENINGS_LIST_REQUIRED")
    return {"eligible":not reasons,"reasons":reasons}

def _storey_records(layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    count=int(layout.get("storeys") or 0)
    h=float(layout.get("storey_height_m") or 0.0)
    raised=float((layout.get("elevation") or {}).get("raised_floor_m") or 0.0)
    rooms=list(layout.get("rooms") or [])
    walls=list(layout.get("walls") or [])
    openings=list(layout.get("openings") or [])
    result=[]
    for idx in range(count):
        s_rooms=[dict(x) for x in rooms if int(x.get("storey_index",-1))==idx]
        s_walls=[dict(x) for x in walls if int(x.get("storey_index",-1))==idx]
        s_openings=[dict(x) for x in openings if int(x.get("storey_index",-1))==idx]
        doors=[x for x in s_openings if str(x.get("kind") or "").lower()=="door"]
        windows=[x for x in s_openings if str(x.get("kind") or "").lower()=="window"]
        result.append({
            "storey_id":f"S{idx+1}","index":idx,"name":f"Storey {idx+1}",
            "elevation_m":raised + idx*h,"height_m":h,
            "spaces":s_rooms,"rooms":s_rooms,"walls":s_walls,
            "doors":doors,"windows":windows,"openings":s_openings,
        })
    return result

def materialize_structural_adapter_inputs(*, project_id: str, recommended_variant_id: str,
                                          canonical_layout_json: Path, authoritative_ifc: Path,
                                          output_dir: Path) -> dict[str, Any]:
    canonical_layout_json=Path(canonical_layout_json)
    authoritative_ifc=Path(authoritative_ifc)
    output_dir=Path(output_dir)
    eligibility=materialization_eligibility(canonical_layout_json)
    if not eligibility["eligible"]:
        raise RuntimeError("R8_MATERIALIZER_LAYOUT_INELIGIBLE:"+";".join(eligibility["reasons"]))
    if not authoritative_ifc.is_file():
        raise RuntimeError(f"R8_MATERIALIZER_IFC_MISSING:{authoritative_ifc}")

    layout=json.loads(canonical_layout_json.read_text(encoding="utf-8-sig"))
    if str(layout.get("variant_id") or "") != str(recommended_variant_id):
        raise RuntimeError(f"R8_MATERIALIZER_VARIANT_MISMATCH:{layout.get('variant_id')}:{recommended_variant_id}")

    storeys=_storey_records(layout)
    footprint=dict(layout.get("footprint") or {})
    width=float(footprint.get("width_m"))
    depth=float(footprint.get("depth_m"))
    rooms=[dict(x) for x in layout.get("rooms") or []]

    model={
        "schema_version":"phoenix.architectural-model/1.0",
        "generator":"PHOENIX_R8_STRUCTURAL_INPUT_MATERIALIZER",
        "project_id":project_id,
        "status":"CANDIDATE_GEOMETRY_AVAILABLE",
        "generation_mode":"R8_AUTHORITATIVE_REAL_SPATIAL",
        "candidate_only":True,
        "professional_approval":False,
        "professional_review_required":True,
        "production_release":"LOCKED",
        "for_construction":"LOCKED",
        "units":"SI",
        "selected_variant":recommended_variant_id,
        "selected_variant_name":str(layout.get("strategy") or recommended_variant_id),
        "variant_count":5,
        "architectural_model_source":str(canonical_layout_json),
        "authoritative_geometry_source":str(canonical_layout_json),
        "authoritative_geometry_format":"PHOENIX_REAL_SPATIAL_JSON",
        "authoritative_ifc":str(authoritative_ifc),
        "building":{"storey_count":len(storeys),"footprint_width_m":width,"footprint_depth_m":depth},
        "building_envelope_m":{"width":width,"depth":depth,"height":len(storeys)*float(layout["storey_height_m"])},
        "gross_floor_area_m2":sum(float(x.get("area_m2") or 0.0) for x in rooms),
        "storeys":storeys,
        "levels":[{"level_id":x["storey_id"],"name":x["name"],"elevation_m":x["elevation_m"],"height_m":x["height_m"]} for x in storeys],
        "rooms":rooms,
        "roof":dict(layout.get("roof") or {}),
        "site_context":{"status":"NOT_MATERIALIZED_BY_R8"},
    }

    detailed={
        "schema_version":"phoenix.architectural-detailed-elements/1.0",
        "project_id":project_id,
        "status":"CANDIDATE_GEOMETRY_AVAILABLE",
        "professional_review_required":True,
        "production_release":"LOCKED",
        "for_construction":"LOCKED",
        "storeys":storeys,
    }

    from phoenix.autonomy import session_adapters
    if not session_adapters._architecture_model_candidate(model):
        raise RuntimeError("R8_MATERIALIZER_ARCHITECTURE_GATE_DENY")
    if not session_adapters._detailed_elements_candidate(detailed):
        raise RuntimeError("R8_MATERIALIZER_DETAILED_ELEMENTS_GATE_DENY")

    generator=getattr(session_adapters,"generate_structural_project_profile",None)
    if not callable(generator):
        raise RuntimeError("R8_MATERIALIZER_EXISTING_STRUCTURAL_PROFILE_GENERATOR_MISSING")

    project_context={
        "schema_version":"phoenix.project-context/r8-materialization",
        "project_id":project_id,
        "facts":{},"assumptions":{},
        "status":"GEOMETRY_ONLY_CONTEXT",
        "note":"No jurisdiction, loads, soil facts, material strengths or design-code facts are invented by R8.",
    }

    profile=generator(project_id=project_id,architectural_model=model,project_context=project_context)
    if not isinstance(profile,dict):
        raise RuntimeError("R8_MATERIALIZER_PROFILE_GENERATOR_RESULT_INVALID")
    profile["automatic_structural_approval"]=False
    profile["professional_structural_review_required"]=True
    profile["production_release"]="LOCKED"
    profile["for_construction"]="LOCKED"
    profile.setdefault("r8_materialization_provenance",{}).update({
        "recommended_variant_id":recommended_variant_id,
        "canonical_layout_json":str(canonical_layout_json),
        "canonical_layout_sha256":_sha256(canonical_layout_json),
        "authoritative_ifc":str(authoritative_ifc),
        "authoritative_ifc_sha256":_sha256(authoritative_ifc),
        "solver_execution_started":False,
        "automatic_design_value_invention":False,
    })
    if not session_adapters._structural_profile_candidate(profile):
        raise RuntimeError("R8_MATERIALIZER_STRUCTURAL_PROFILE_GATE_DENY")

    model_path=output_dir/"architectural_model.json"
    detail_path=output_dir/"detailed_elements.json"
    profile_path=output_dir/"structural_project_profile.json"
    context_path=output_dir/"project_context.json"
    _write(model_path,model)
    _write(detail_path,detailed)
    _write(profile_path,profile)
    _write(context_path,project_context)

    result={
        "schema":SCHEMA,
        "project_id":project_id,
        "recommended_variant_id":recommended_variant_id,
        "status":"MATERIALIZED_READY_FOR_EXISTING_STRUCTURAL_ADAPTER",
        "architecture_adapter_outputs":{
            "architectural_model.json":_file_record(model_path),
            "detailed_elements.json":_file_record(detail_path),
            "structural_project_profile.json":_file_record(profile_path),
            "project_context.json":_file_record(context_path),
        },
        "existing_consumer":{
            "module":"phoenix.autonomy.session_adapters",
            "function":"run_structural",
            "downstream_chain":"phoenix.autonomy.structural_session_chain.run_structural_chain"
        },
        "solver_execution_started":False,
        "automatic_design_value_invention":False,
        "automatic_professional_approval":False,
        "production_release":"LOCKED",
        "for_construction":"LOCKED",
    }
    evidence_path=output_dir/"structural_input_materialization_evidence.json"
    _write(evidence_path,result)
    result["evidence_path"]=str(evidence_path)
    return result
