"""Autonomous Architectural Concept Bootstrap v1.0.

Transforms a sufficiently clear BOUW free-text brief into a deterministic,
dimensioned *concept candidate* model. Every default is explicit in the
assumptions register. This module never grants professional approval, never
invents site/jurisdiction facts, and never marks production release ready.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


VERSION = "1.1.0"


@dataclass
class ArchitecturalBootstrapResult:
    status: str
    reason: str | None
    program: dict[str, Any] | None
    assumptions: dict[str, Any] | None
    model: dict[str, Any] | None
    detailed_elements: dict[str, Any] | None
    structural_handoff: dict[str, Any] | None
    desired_output_states: dict[str, Any]


def _clean_brief(brief: str) -> str:
    lines=[x.strip() for x in str(brief or "").splitlines() if x.strip()]
    if lines and re.fullmatch(r"[A-Za-z0-9._-]+",lines[0]):
        lines=lines[1:]
    return " ".join(lines).strip()


def _num(text: str) -> float | None:
    try: return float(text.replace(",","."))
    except (TypeError,ValueError): return None


def _extract_storeys(text: str) -> tuple[int,bool]:
    low=text.lower()
    words={"een":1,"één":1,"twee":2,"drie":3,"vier":4}
    for word,n in words.items():
        if re.search(rf"\b{re.escape(word)}\s+(?:bouwlagen?|verdiepingen?)\b",low): return n,True
    m=re.search(r"\b([1-4])\s+(?:bouwlagen?|verdiepingen?)\b",low)
    if m: return int(m.group(1)),True
    if re.search(r"\b(?:begane grond|grondvloer)\b",low) and re.search(r"\b(?:verdieping|etage)\b",low): return 2,True
    return 2,False


def _extract_dimensions(text: str) -> tuple[float,float,bool]:
    low=text.lower().replace("×","x")
    m=re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:m)?\s*x\s*(\d+(?:[.,]\d+)?)\s*m\b",low)
    if m:
        a,b=_num(m.group(1)),_num(m.group(2))
        if a and b and 4.0 <= a <= 40.0 and 4.0 <= b <= 40.0: return round(a,2),round(b,2),True
    mw=re.search(r"\bbreedte\s*(?:van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*m\b",low)
    md=re.search(r"\b(?:diepte|lengte)\s*(?:van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*m\b",low)
    if mw and md:
        a,b=_num(mw.group(1)),_num(md.group(1))
        if a and b and 4.0 <= a <= 40.0 and 4.0 <= b <= 40.0: return round(a,2),round(b,2),True
    ma=re.search(r"\b(?:oppervlakte|footprint)\s*(?:van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*m(?:2|²)\b",low)
    if ma:
        area=_num(ma.group(1))
        if area and 35 <= area <= 800:
            width=round((area*1.25)**0.5,2); depth=round(area/width,2)
            return width,depth,True
    return 10.0,8.0,False


def _space(storey: str, sid: str, name: str, x: float, y: float, w: float, d: float, use: str) -> dict[str,Any]:
    return {
        "space_id":f"{storey}-{sid}","name":name,"use":use,
        "x_m":round(x,3),"y_m":round(y,3),"width_m":round(w,3),"depth_m":round(d,3),
        "area_m2":round(w*d,2),"status":"CONCEPT_CANDIDATE"
    }


def _outer_walls(storey: str,w:float,d:float,t:float) -> list[dict[str,Any]]:
    pts=[((0,0),(w,0)),((w,0),(w,d)),((w,d),(0,d)),((0,d),(0,0))]
    return [{"wall_id":f"{storey}-EW{i+1}","element_id":f"{storey}-EW{i+1}","storey_id":storey,"kind":"external","category":"external_wall","x1_m":a[0],"y1_m":a[1],"x2_m":b[0],"y2_m":b[1],"length_m":round(((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5,3),"height_m":3.0,"thickness_m":t,"status":"CONCEPT_CANDIDATE"} for i,(a,b) in enumerate(pts)]


def _internal_walls(storey:str,w:float,d:float,t:float,upper:bool=False) -> list[dict[str,Any]]:
    if not upper:
        seg=[((0,d*0.58),(w,d*0.58)),((w*0.60,0),(w*0.60,d*0.58)),((w*0.32,d*0.58),(w*0.32,d)),((w*0.54,d*0.58),(w*0.54,d)),((w*0.74,d*0.58),(w*0.74,d))]
    else:
        seg=[((0,d*0.52),(w,d*0.52)),((w*0.40,0),(w*0.40,d*0.52)),((w*0.70,0),(w*0.70,d*0.52)),((w*0.32,d*0.52),(w*0.32,d)),((w*0.62,d*0.52),(w*0.62,d))]
    return [{"wall_id":f"{storey}-IW{i+1}","element_id":f"{storey}-IW{i+1}","storey_id":storey,"kind":"internal","category":"internal_wall","x1_m":round(a[0],3),"y1_m":round(a[1],3),"x2_m":round(b[0],3),"y2_m":round(b[1],3),"length_m":round(((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5,3),"height_m":3.0,"thickness_m":t,"status":"CONCEPT_CANDIDATE"} for i,(a,b) in enumerate(seg)]


def _doors(storey:str,w:float,d:float,upper:bool=False) -> list[dict[str,Any]]:
    vals=[("D1","external",0.95,w*0.15,d,0.0)] if not upper else []
    vals += [("D2","internal",0.90,w*0.32,d*0.58,90.0),("D3","internal",0.90,w*0.54,d*0.58,90.0),("D4","internal",0.90,w*0.74,d*0.58,90.0)]
    return [{"door_id":f"{storey}-{i}","kind":k,"width_m":ww,"x_m":round(x,3),"y_m":round(y,3),"rotation_deg":r,"status":"CONCEPT_CANDIDATE"} for i,k,ww,x,y,r in vals]


def _windows(storey:str,w:float,d:float) -> list[dict[str,Any]]:
    vals=[("W1",w*0.28,0,1.8,0),("W2",w*0.75,0,1.8,0),("W3",w,d*0.30,1.5,90),("W4",w,d*0.75,1.5,90),("W5",w*0.28,d,1.5,180),("W6",w*0.72,d,1.5,180)]
    return [{"window_id":f"{storey}-{i}","width_m":ww,"sill_height_m":0.9,"x_m":round(x,3),"y_m":round(y,3),"rotation_deg":r,"status":"CONCEPT_CANDIDATE"} for i,x,y,ww,r in vals]


def _residential_program(storeys:int,w:float,d:float) -> list[dict[str,Any]]:
    out=[]
    # Ground floor proportional zones.
    s="L0"; h=d*0.58; back=d-h
    spaces=[
        _space(s,"S01","Woonkamer / eetruimte",0,0,w*0.60,h,"living_dining"),
        _space(s,"S02","Keuken",w*0.60,0,w*0.40,h,"kitchen"),
        _space(s,"S03","Entree / hal",0,h,w*0.20,back,"entrance_hall"),
        _space(s,"S04","Toilet",w*0.20,h,w*0.12,back*0.48,"wc"),
        _space(s,"S05","Trapzone",w*0.32,h,w*0.22,back,"stair"),
        _space(s,"S06","Berging / techniek",w*0.54,h,w*0.20,back,"utility"),
        _space(s,"S07","Werk-/logeerkamer",w*0.74,h,w*0.26,back,"flex_room"),
    ]
    out.append({"storey_id":s,"name":"Begane grond","elevation_m":0.0,"height_m":3.0,"spaces":spaces})
    if storeys >= 2:
        s="L1"; front=d*0.52; back=d-front
        spaces=[
            _space(s,"S01","Slaapkamer 1",0,0,w*0.40,front,"bedroom"),
            _space(s,"S02","Slaapkamer 2",w*0.40,0,w*0.30,front,"bedroom"),
            _space(s,"S03","Slaapkamer 3",w*0.70,0,w*0.30,front,"bedroom"),
            _space(s,"S04","Overloop / trap",0,front,w*0.32,back,"landing_stair"),
            _space(s,"S05","Badkamer",w*0.32,front,w*0.30,back,"bathroom"),
            _space(s,"S06","Toilet / kast",w*0.62,front,w*0.14,back,"wc_storage"),
            _space(s,"S07","Werk-/slaapkamer",w*0.76,front,w*0.24,back,"flex_room"),
        ]
        out.append({"storey_id":s,"name":"Eerste verdieping","elevation_m":3.0,"height_m":3.0,"spaces":spaces})
    for idx in range(2,storeys):
        s=f"L{idx}"
        spaces=[_space(s,"S01",f"Flexibele verblijfsruimte {idx}",0,0,w,d,"flexible")]
        out.append({"storey_id":s,"name":f"Verdieping {idx}","elevation_m":round(idx*3.0,2),"height_m":3.0,"spaces":spaces})
    return out


def generate_architectural_bootstrap(*, project_id:str, project_type:str, brief:str, desired_outputs:list[str] | None=None) -> ArchitecturalBootstrapResult:
    desired_outputs=list(desired_outputs or [])
    clean=_clean_brief(brief)
    low=clean.lower()
    if str(project_type or "").upper() != "BOUW":
        return ArchitecturalBootstrapResult("BLOCKED","ARCHITECTURAL_BOOTSTRAP_BUILDING_ONLY",None,None,None,None,None,{})
    if not clean:
        return ArchitecturalBootstrapResult("BLOCKED","ARCHITECTURAL_BRIEF_INSUFFICIENT",None,None,None,None,None,{})
    residential=any(k in low for k in ("woning","woonhuis","huis","villa","residential","dwelling"))
    if not residential:
        return ArchitecturalBootstrapResult("BLOCKED","ARCHITECTURAL_USE_TYPE_REQUIRED",None,None,None,None,None,{})

    storeys,storeys_explicit=_extract_storeys(clean)
    width,depth,dims_explicit=_extract_dimensions(clean)
    storeys=max(1,min(4,storeys))
    gross=round(width*depth*storeys,2)
    ext_t=0.30; int_t=0.12; floor_h=3.0

    assumptions={
        "schema_version":"phoenix.architectural-assumptions-register/1.0",
        "project_id":project_id,
        "status":"CONCEPT_ASSUMPTIONS_REQUIRE_REVIEW",
        "professional_approval":False,
        "items":[
            {"id":"building_use","value":"residential_detached_candidate","basis":"BRIEF_INTERPRETATION","confidence":"MEDIUM","review_required":True},
            {"id":"storey_count","value":storeys,"basis":"USER_BRIEF" if storeys_explicit else "AUTO_CONCEPT_DEFAULT","confidence":"HIGH" if storeys_explicit else "LOW","review_required":not storeys_explicit},
            {"id":"footprint_width_m","value":width,"unit":"m","basis":"USER_BRIEF" if dims_explicit else "AUTO_CONCEPT_DEFAULT","confidence":"HIGH" if dims_explicit else "LOW","review_required":not dims_explicit},
            {"id":"footprint_depth_m","value":depth,"unit":"m","basis":"USER_BRIEF" if dims_explicit else "AUTO_CONCEPT_DEFAULT","confidence":"HIGH" if dims_explicit else "LOW","review_required":not dims_explicit},
            {"id":"floor_to_floor_height_m","value":floor_h,"unit":"m","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"external_wall_thickness_m","value":ext_t,"unit":"m","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"internal_wall_thickness_m","value":int_t,"unit":"m","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"roof_form","value":"gable_roof_candidate","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"roof_pitch_deg","value":35.0,"unit":"deg","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"space_layout_template","value":"detached_house_v1","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"door_width_defaults_m","value":{"external":0.95,"internal":0.90},"unit":"m","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"window_layout_template","value":"residential_candidate_v1","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"stair_zone_template","value":"residential_candidate_v1","basis":"AUTO_CONCEPT_DEFAULT","confidence":"LOW","review_required":True},
            {"id":"site_orientation","value":None,"basis":"MISSING_PROJECT_INPUT","confidence":"NONE","review_required":True},
            {"id":"plot_boundaries_setbacks","value":None,"basis":"MISSING_PROJECT_INPUT","confidence":"NONE","review_required":True},
        ]
    }

    program_storeys=_residential_program(storeys,width,depth)
    program={
        "schema_version":"phoenix.architectural-space-program/1.0",
        "project_id":project_id,"building_use":"residential_detached_candidate",
        "storey_count":storeys,"gross_floor_area_candidate_m2":gross,
        "storeys":[{"storey_id":s["storey_id"],"name":s["name"],"spaces":s["spaces"]} for s in program_storeys],
        "status":"CONCEPT_CANDIDATE","review_required":True,
    }

    model_storeys=[]
    detail_storeys=[]
    for idx,s in enumerate(program_storeys):
        sid=s["storey_id"]; upper=idx>0
        walls=_outer_walls(sid,width,depth,ext_t)+_internal_walls(sid,width,depth,int_t,upper)
        doors=_doors(sid,width,depth,upper)
        windows=_windows(sid,width,depth)
        stairs=[]
        if idx < storeys-1:
            stairs=[{"stair_id":f"{sid}-ST1","x_m":round(width*0.34,3),"y_m":round(depth*0.60,3),"width_m":round(width*0.18,3),"depth_m":round(depth*0.34,3),"from_storey":sid,"to_storey":f"L{idx+1}","status":"CONCEPT_CANDIDATE"}]
        model_storeys.append({**s,"walls":walls,"doors":doors,"windows":windows,"stairs":stairs,"floor_zone":{"status":"ARCHITECTURAL_CONCEPT_ONLY_NO_STRUCTURAL_THICKNESS_ASSIGNED"}})
        detail_storeys.append({"storey_id":sid,"walls":walls,"doors":doors,"windows":windows,"stairs":stairs})

    model={
        "schema_version":"phoenix.architectural-model/1.0",
        "generator":"autonomous_architectural_bootstrap_v1.0",
        "project_id":project_id,"units":"m","coordinate_system":"LOCAL_CONCEPT",
        "status":"CONCEPT_CANDIDATE","professional_approval":False,"production_release":"LOCKED",
        "building":{"type":"residential_detached_candidate","footprint_width_m":width,"footprint_depth_m":depth,"footprint_area_m2":round(width*depth,2),"storey_count":storeys,"gross_floor_area_m2":gross,"floor_to_floor_height_m":floor_h},
        "storeys":model_storeys,
        "roof":{"type":"gable_candidate","ridge_direction":"LONG_AXIS_CANDIDATE","pitch_deg":35.0,"status":"CONCEPT_CANDIDATE_REQUIRE_REVIEW"},
        "site_context":{"status":"MISSING","orientation":None,"plot_boundary":None,"setbacks":None},
    }
    detailed={
        "schema_version":"phoenix.architectural-detailed-elements/1.0","project_id":project_id,
        "status":"CONCEPT_CANDIDATE","storeys":detail_storeys,
        "professional_review_required":True,"production_release":"LOCKED",
    }
    structural_handoff={
        "schema_version":"phoenix.architectural-structural-handoff/1.0","project_id":project_id,
        "geometry_status":"CANDIDATE_GEOMETRY_AVAILABLE","structural_profile_status":"REQUIRED_SEPARATELY",
        "building_extents":{"width_m":width,"depth_m":depth,"storeys":storeys,"floor_to_floor_height_m":floor_h},
        "no_structural_material_or_load_assumptions_generated":True,"production_release":"LOCKED",
    }

    # Capability may proceed downstream, but final drawings are not falsely claimed.
    coverage={
        "site_plan":{"status":"BLOCKED","reason":"SITE_CONTEXT_REQUIRED","message":"Perceelgrenzen, oriëntatie en setbacks ontbreken."},
        "floor_plans":{"status":"CANDIDATE_MODEL_READY","reason":"FINAL_DRAWING_EXPORT_REQUIRED","message":"Maatvoerend conceptmodel beschikbaar; definitieve tekeningexport/review nog vereist."},
        "facades":{"status":"CANDIDATE_MODEL_READY","reason":"FINAL_DRAWING_EXPORT_REQUIRED","message":"Conceptgeometrie beschikbaar; definitieve geveltekening nog vereist."},
        "sections":{"status":"CANDIDATE_MODEL_READY","reason":"FINAL_DRAWING_EXPORT_REQUIRED","message":"Conceptgeometrie beschikbaar; definitieve doorsnedetekening nog vereist."},
        "details":{"status":"BLOCKED","reason":"ARCHITECTURAL_DETAIL_ENGINE_REQUIRED","message":"Detailengineering is nog niet uitgevoerd."},
        "dwg_dxf":{"status":"BLOCKED","reason":"CAD_EXPORT_ENGINE_REQUIRED","message":"CAD-export van het conceptmodel is nog niet uitgevoerd."},
    }
    return ArchitecturalBootstrapResult("PASSED",None,program,assumptions,model,detailed,structural_handoff,coverage)
