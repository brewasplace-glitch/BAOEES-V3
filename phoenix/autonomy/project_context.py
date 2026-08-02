"""Phoenix Autonomous Project Context Engine v1.0.

Builds a central project-context record from explicit project text and
architectural geometry. Facts and assumptions are separated. No legal,
jurisdictional, cadastral or currency fact is silently invented.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

VERSION = "1.0.0"

@dataclass
class ProjectContextResult:
    context: dict[str, Any]
    assumptions: dict[str, Any]
    site_context: dict[str, Any]
    manifest_updates: dict[str, Any]

def _clean_lines(brief: str) -> list[str]:
    return [x.strip() for x in str(brief or "").splitlines() if x.strip()]

def _country(text: str) -> tuple[str | None, str]:
    low=text.lower()
    if re.search(r"\b(nederland|netherlands)\b", low): return "NL","EXPLICIT_BRIEF"
    if re.search(r"\b(suriname)\b", low): return "SR","EXPLICIT_BRIEF"
    if re.search(r"\b(belgi[eë]|belgium)\b", low): return "BE","EXPLICIT_BRIEF"
    if re.search(r"\b(duitsland|germany)\b", low): return "DE","EXPLICIT_BRIEF"
    if re.search(r"\b(france|frankrijk)\b", low): return "FR","EXPLICIT_BRIEF"
    if re.search(r"\b(united states|verenigde staten|usa|u\.s\.)\b", low): return "US","EXPLICIT_BRIEF"
    return None,"MISSING"

def _location(lines: list[str]) -> tuple[str | None,str]:
    for line in lines:
        m=re.match(r"(?i)^(?:projectlocatie|locatie|adres|plaats)\s*[:=-]\s*(.+)$",line)
        if m and m.group(1).strip():
            return m.group(1).strip(),"EXPLICIT_BRIEF"
    return None,"MISSING"

def _currency(text: str,country_code: str | None) -> tuple[str | None,str]:
    low=text.lower()
    m=re.search(r"(?i)\b(?:valuta|currency)\s*[:=-]\s*(EUR|USD|SRD|GBP)\b",text)
    if m: return m.group(1).upper(),"EXPLICIT_BRIEF"
    if re.search(r"\beuro(?:'s)?\b|€",low): return "EUR","EXPLICIT_BRIEF"
    if re.search(r"\bsurinam(?:e|ese)\s+dollar\b|\bsrd\b",low): return "SRD","EXPLICIT_BRIEF"
    if re.search(r"\bus\s*dollar\b|\busd\b",low): return "USD","EXPLICIT_BRIEF"
    mapping={"NL":"EUR","BE":"EUR","DE":"EUR","FR":"EUR","SR":"SRD","US":"USD"}
    if country_code in mapping:
        return mapping[country_code],"DERIVED_FROM_EXPLICIT_COUNTRY"
    return None,"MISSING"

def _plot_dimensions(text: str) -> tuple[float | None,float | None,str]:
    low=text.lower().replace("×","x")
    patterns=[
        r"\b(?:perceel|kavel|plot)\s*(?:is|van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*(?:m)?\s*x\s*(\d+(?:[.,]\d+)?)\s*m\b",
        r"\b(?:perceelbreedte|kavelbreedte)\s*(?:van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*m\b.*?\b(?:perceeldiepte|kaveldiepte)\s*(?:van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*m\b",
    ]
    for p in patterns:
        m=re.search(p,low)
        if m:
            try:
                a=float(m.group(1).replace(",","."))
                b=float(m.group(2).replace(",","."))
            except ValueError:
                continue
            if 5 <= a <= 1000 and 5 <= b <= 1000:
                return round(a,2),round(b,2),"EXPLICIT_BRIEF"
    return None,None,"MISSING"

def _orientation(text: str) -> tuple[str | None,str]:
    low=text.lower()
    m=re.search(r"\b(?:noordrichting|ori[eë]ntatie)\s*[:=-]\s*([a-zA-Z -]+)",text,re.I)
    if m: return m.group(1).strip().upper(),"EXPLICIT_BRIEF"
    if "noord boven" in low or "north up" in low: return "NORTH_UP","EXPLICIT_BRIEF"
    return None,"MISSING"

def _building_extent(architectural_model: dict[str,Any]) -> tuple[float,float]:
    b=architectural_model.get("building") if isinstance(architectural_model,dict) else {}
    try:
        w=float((b or {}).get("footprint_width_m") or 0)
        d=float((b or {}).get("footprint_depth_m") or 0)
    except (TypeError,ValueError):
        w=d=0.0
    if w>0 and d>0: return w,d
    xs=[];ys=[]
    for s in architectural_model.get("storeys",[]) if isinstance(architectural_model,dict) else []:
        for space in s.get("spaces",[]):
            try:
                x=float(space.get("x_m",0));y=float(space.get("y_m",0))
                sw=float(space.get("width_m",0));sd=float(space.get("depth_m",0))
            except (TypeError,ValueError):
                continue
            xs.extend([x,x+sw]);ys.extend([y,y+sd])
    return (max(xs)-min(xs) if xs else 10.0, max(ys)-min(ys) if ys else 8.0)

def generate_project_context(*, project_id:str, brief:str, architectural_model:dict[str,Any]) -> ProjectContextResult:
    lines=_clean_lines(brief)
    text="\n".join(lines)
    location,location_basis=_location(lines)
    country_code,country_basis=_country(text)
    currency,currency_basis=_currency(text,country_code)
    plot_w,plot_d,plot_basis=_plot_dimensions(text)
    orientation,orientation_basis=_orientation(text)
    bw,bd=_building_extent(architectural_model)

    site_assumed=False
    if not plot_w or not plot_d:
        # Only a schematic design canvas, never a cadastral/site fact.
        plot_w=round(max(bw+6.0,bw*1.60),2)
        plot_d=round(max(bd+10.0,bd*1.80),2)
        plot_basis="AUTO_SCHEMATIC_DESIGN_CANVAS"
        site_assumed=True
    if not orientation:
        orientation="NORTH_UP_SCHEMATIC"
        orientation_basis="AUTO_SCHEMATIC_DESIGN_CANVAS"
        site_assumed=True

    side=max(1.5,round((plot_w-bw)/2,2))
    front=max(3.0,round((plot_d-bd)/2,2))
    rear=front
    setbacks={
        "front_m":front,
        "rear_m":rear,
        "left_m":side,
        "right_m":side,
        "basis":"AUTO_SCHEMATIC_DESIGN_CANVAS" if site_assumed else "DERIVED_FROM_USER_PLOT_DIMENSIONS",
        "legal_status":"NOT_VALIDATED",
    }

    facts={
        "project_location":location,
        "project_location_basis":location_basis,
        "country_code":country_code,
        "country_basis":country_basis,
        "currency":currency,
        "currency_basis":currency_basis,
        "jurisdiction_status":"PARTIAL" if country_code else "MISSING",
        "municipality":None,
        "municipality_status":"MISSING",
    }
    assumptions={
        "schema_version":"phoenix.project-context-assumptions/1.0",
        "project_id":project_id,
        "items":[
            {"id":"site_plot_width_m","value":plot_w,"unit":"m","basis":plot_basis,"review_required":plot_basis!="EXPLICIT_BRIEF"},
            {"id":"site_plot_depth_m","value":plot_d,"unit":"m","basis":plot_basis,"review_required":plot_basis!="EXPLICIT_BRIEF"},
            {"id":"site_orientation","value":orientation,"basis":orientation_basis,"review_required":orientation_basis!="EXPLICIT_BRIEF"},
            {"id":"concept_setbacks","value":setbacks,"basis":setbacks["basis"],"review_required":True},
        ],
        "professional_approval":False,
        "production_release":"LOCKED",
    }
    site={
        "schema_version":"phoenix.site-context/1.0",
        "project_id":project_id,
        "status":"PROJECT_INPUT_CANDIDATE" if plot_basis=="EXPLICIT_BRIEF" else "SCHEMATIC_ASSUMPTION",
        "plot":{"width_m":plot_w,"depth_m":plot_d,"source":plot_basis,"legal_boundary":False},
        "orientation":{"value":orientation,"source":orientation_basis},
        "building_placement":{
            "x_m":side,"y_m":front,"width_m":round(bw,2),"depth_m":round(bd,2),
            "basis":"CENTERED_CONCEPT_PLACEMENT","legal_position":False,
        },
        "setbacks":setbacks,
        "location":location,
        "country_code":country_code,
        "cadastral_validation":False,
        "planning_validation":False,
        "production_release":"LOCKED",
    }
    context={
        "schema_version":"phoenix.project-context/1.0",
        "project_id":project_id,
        "facts":facts,
        "site_context_status":site["status"],
        "site_context":"site_context.json",
        "assumptions_register":"project_context_assumptions.json",
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    updates={"project_context_status":"AVAILABLE_CANDIDATE"}
    if location: updates["location"]=location
    if country_code: updates["country_code"]=country_code
    if currency: updates["currency"]=currency
    return ProjectContextResult(context,assumptions,site,updates)
