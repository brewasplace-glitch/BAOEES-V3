"""Phoenix Site Drawing & Parcel Intelligence Engine v1.0.

Supported evidence:
- GeoJSON / JSON site geometry
- DXF LWPOLYLINE site boundary with explicit DXF units
- PDF text extraction when pypdf/PyPDF2 is installed
- explicit site dimensions/orientation in a machine-readable JSON upload

DWG and raster drawings are registered but are not guessed. No cadastral or
legal boundary is fabricated.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION="1.0.0"

@dataclass
class SiteParcelResult:
    status:str
    site_context:dict[str,Any]
    evidence_register:dict[str,Any]
    blockers:list[dict[str,Any]]
    warnings:list[str]

def _read_json(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):raise ValueError("JSON root must be object")
    return value

def _dimensions_from_text(text:str)->tuple[float|None,float|None]:
    low=str(text or "").lower().replace("×","x")
    patterns=[
        r"\b(?:perceel|kavel|plot|parcel)\s*(?:is|van|=|:)?\s*(\d+(?:[.,]\d+)?)\s*(?:m)?\s*x\s*(\d+(?:[.,]\d+)?)\s*m\b",
        r"\b(?:breedte|width)\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*m\b.*?\b(?:diepte|depth|lengte|length)\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*m\b",
    ]
    for pattern in patterns:
        m=re.search(pattern,low,re.S)
        if m:
            a=float(m.group(1).replace(",","."))
            b=float(m.group(2).replace(",","."))
            if 1<a<10000 and 1<b<10000:return round(a,3),round(b,3)
    return None,None

def _north_from_text(text:str)->tuple[float|None,str|None]:
    raw=str(text or "")
    m=re.search(r"(?i)\b(?:noordrichting|north(?:\s+angle)?|ori[eë]ntatie)\s*[:=-]\s*(-?\d+(?:[.,]\d+)?)\s*(?:°|deg|graden)?",raw)
    if m:
        return float(m.group(1).replace(",","."))%360,"EXPLICIT_ANGLE"
    low=raw.lower()
    if "noord boven" in low or "north up" in low or "n ↑" in low or "n↑" in low:
        return 0.0,"EXPLICIT_NORTH_UP"
    return None,None

def _bbox(points:list[tuple[float,float]])->tuple[float,float,float,float]:
    xs=[p[0] for p in points];ys=[p[1] for p in points]
    return min(xs),min(ys),max(xs),max(ys)

def _geo_dimensions(points:list[tuple[float,float]])->tuple[float,float]:
    minx,miny,maxx,maxy=_bbox(points)
    midlat=math.radians((miny+maxy)/2)
    width=abs(maxx-minx)*111320.0*max(math.cos(midlat),0.01)
    depth=abs(maxy-miny)*110540.0
    return width,depth

def _geojson_polygon(value:dict[str,Any])->tuple[list[tuple[float,float]]|None,dict[str,Any]]:
    meta={}
    geometry=None
    if value.get("type")=="Feature":
        geometry=value.get("geometry")
        meta=value.get("properties") or {}
    elif value.get("type")=="FeatureCollection":
        features=[x for x in value.get("features",[]) if isinstance(x,dict)]
        polys=[x for x in features if isinstance(x.get("geometry"),dict) and x["geometry"].get("type") in {"Polygon","MultiPolygon"}]
        if polys:
            feature=polys[0]
            geometry=feature.get("geometry")
            meta=feature.get("properties") or {}
    elif value.get("type") in {"Polygon","MultiPolygon"}:
        geometry=value
        meta=value.get("properties") or {}
    if not isinstance(geometry,dict):
        return None,meta
    coords=geometry.get("coordinates")
    if geometry.get("type")=="Polygon" and isinstance(coords,list) and coords:
        ring=coords[0]
    elif geometry.get("type")=="MultiPolygon" and isinstance(coords,list) and coords and coords[0]:
        ring=coords[0][0]
    else:
        return None,meta
    points=[]
    for pair in ring:
        if isinstance(pair,(list,tuple)) and len(pair)>=2:
            try:points.append((float(pair[0]),float(pair[1])))
            except (TypeError,ValueError):pass
    return points if len(points)>=3 else None,meta

def _json_site(path:Path)->dict[str,Any]|None:
    value=_read_json(path)
    site=value.get("site_context") if isinstance(value.get("site_context"),dict) else value
    plot=site.get("plot") if isinstance(site,dict) else None
    if isinstance(plot,dict):
        try:
            width=float(plot.get("width_m"));depth=float(plot.get("depth_m"))
        except (TypeError,ValueError):
            width=depth=0
        if width>0 and depth>0:
            orientation=site.get("orientation") or {}
            north=orientation.get("north_angle_deg") if isinstance(orientation,dict) else None
            return {
                "width_m":width,"depth_m":depth,
                "north_angle_deg":north,
                "boundary_points_m":plot.get("boundary_points_m"),
                "source_type":"JSON_SITE_CONTEXT",
            }
    points,meta=_geojson_polygon(value)
    if points:
        geographic=all(-180<=x<=180 and -90<=y<=90 for x,y in points)
        if geographic:
            width,depth=_geo_dimensions(points)
            north=0.0
            return {
                "width_m":round(width,3),"depth_m":round(depth,3),
                "north_angle_deg":north,
                "boundary_coordinates":points,
                "coordinate_type":"GEOGRAPHIC",
                "source_type":"GEOJSON_GEOGRAPHIC",
            }
        units=str(meta.get("units") or value.get("units") or "").lower()
        factor={"m":1.0,"meter":1.0,"meters":1.0,"mm":0.001,"cm":0.01}.get(units)
        if factor:
            minx,miny,maxx,maxy=_bbox(points)
            return {
                "width_m":round((maxx-minx)*factor,3),
                "depth_m":round((maxy-miny)*factor,3),
                "north_angle_deg":meta.get("north_angle_deg"),
                "boundary_points_m":[[(x-minx)*factor,(y-miny)*factor] for x,y in points],
                "coordinate_type":"PROJECTED",
                "source_type":"GEOJSON_PROJECTED",
            }
    return None

def _dxf_pairs(path:Path)->list[tuple[str,str]]:
    lines=path.read_text(encoding="utf-8",errors="ignore").splitlines()
    pairs=[]
    for i in range(0,len(lines)-1,2):
        pairs.append((lines[i].strip(),lines[i+1].strip()))
    return pairs

def _dxf_site(path:Path)->tuple[dict[str,Any]|None,list[str]]:
    warnings=[]
    pairs=_dxf_pairs(path)
    unit_code=None
    for i,(code,val) in enumerate(pairs):
        if val=="$INSUNITS":
            for j in range(i+1,min(i+5,len(pairs))):
                if pairs[j][0]=="70":
                    try:unit_code=int(float(pairs[j][1]))
                    except ValueError:pass
                    break
    factor={4:0.001,5:0.01,6:1.0}.get(unit_code)
    if factor is None:
        return None,["DXF_UNITS_REQUIRED"]

    polylines=[]
    texts=[]
    i=0
    while i<len(pairs):
        code,val=pairs[i]
        if code=="0" and val=="LWPOLYLINE":
            pts=[];closed=False;i+=1
            while i<len(pairs) and pairs[i][0]!="0":
                c,v=pairs[i]
                if c=="70":
                    try:closed=bool(int(float(v))&1)
                    except ValueError:pass
                if c=="10":
                    try:
                        x=float(v);y=None
                        if i+1<len(pairs) and pairs[i+1][0]=="20":
                            y=float(pairs[i+1][1]);i+=1
                        if y is not None:pts.append((x,y))
                    except ValueError:pass
                i+=1
            if len(pts)>=3:
                polylines.append((pts,closed))
            continue
        if code=="0" and val in {"TEXT","MTEXT"}:
            i+=1;chunks=[]
            while i<len(pairs) and pairs[i][0]!="0":
                if pairs[i][0] in {"1","3"}:chunks.append(pairs[i][1])
                i+=1
            if chunks:texts.append(" ".join(chunks))
            continue
        i+=1

    if not polylines:
        return None,["DXF_CLOSED_SITE_POLYLINE_REQUIRED"]
    def area_bbox(item):
        pts,_=item
        minx,miny,maxx,maxy=_bbox(pts)
        return (maxx-minx)*(maxy-miny)
    pts,closed=max(polylines,key=area_bbox)
    if not closed:
        warnings.append("DXF_SITE_BOUNDARY_NOT_MARKED_CLOSED")
    minx,miny,maxx,maxy=_bbox(pts)
    north,north_basis=_north_from_text("\n".join(texts))
    return {
        "width_m":round((maxx-minx)*factor,3),
        "depth_m":round((maxy-miny)*factor,3),
        "north_angle_deg":north,
        "north_basis":north_basis,
        "boundary_points_m":[[(x-minx)*factor,(y-miny)*factor] for x,y in pts],
        "source_type":"DXF_LWPOLYLINE",
        "dxf_insunits":unit_code,
    },warnings

def _pdf_text(path:Path)->tuple[str|None,str|None]:
    try:
        from pypdf import PdfReader
        reader=PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages),"pypdf"
    except Exception:
        try:
            from PyPDF2 import PdfReader
            reader=PdfReader(str(path))
            return "\n".join((p.extract_text() or "") for p in reader.pages),"PyPDF2"
        except Exception:
            return None,None

def analyze_site_drawings(
    *,
    project_id:str,
    upload_paths:list[Path],
    base_site_context:dict[str,Any],
    brief:str,
    repository:Path,
)->SiteParcelResult:
    evidence=[]
    warnings=[]
    candidates=[]
    for path in upload_paths:
        suffix=path.suffix.lower()
        try:
            data=None
            if suffix in {".json",".geojson"}:
                data=_json_site(path)
            elif suffix==".dxf":
                data,dxf_warnings=_dxf_site(path);warnings.extend(dxf_warnings)
            elif suffix==".pdf":
                text,extractor=_pdf_text(path)
                if text:
                    width,depth=_dimensions_from_text(text)
                    north,north_basis=_north_from_text(text)
                    if width and depth:
                        data={
                            "width_m":width,"depth_m":depth,
                            "north_angle_deg":north,"north_basis":north_basis,
                            "source_type":"PDF_TEXT_EVIDENCE","pdf_text_extractor":extractor,
                        }
                else:
                    warnings.append(f"PDF_TEXT_EXTRACTION_UNAVAILABLE:{path.name}")
            elif suffix==".dwg":
                warnings.append(f"DWG_TO_DXF_CONVERSION_REQUIRED:{path.name}")
            elif suffix in {".png",".jpg",".jpeg",".webp"}:
                warnings.append(f"RASTER_SITE_GEOMETRY_EXTRACTION_REQUIRED:{path.name}")

            if data:
                score=0
                if data.get("width_m") and data.get("depth_m"):score+=100
                if data.get("boundary_points_m") or data.get("boundary_coordinates"):score+=100
                if data.get("north_angle_deg") is not None:score+=50
                candidates.append((score,path,data))
                evidence.append({
                    "source":path.relative_to(repository).as_posix() if repository in path.parents else str(path),
                    "status":"PARSED",
                    "source_type":data.get("source_type"),
                    "score":score,
                })
            else:
                evidence.append({
                    "source":path.relative_to(repository).as_posix() if repository in path.parents else str(path),
                    "status":"NO_VALIDATED_SITE_FACTS",
                    "format":suffix,
                })
        except Exception as exc:
            warnings.append(f"SITE_DRAWING_PARSE_FAILED:{path.name}:{exc}")

    # If no upload yields site facts, preserve the existing context exactly.
    if not candidates:
        register={
            "schema_version":"phoenix.site-parcel-evidence-register/1.0",
            "engine_version":VERSION,"project_id":project_id,
            "evidence":evidence,"warnings":warnings,
            "selected_source":None,
            "cadastral_validation":False,
            "planning_validation":False,
            "production_release":"LOCKED",
        }
        return SiteParcelResult("NO_NEW_EVIDENCE",dict(base_site_context),register,[],warnings)

    _,source,data=max(candidates,key=lambda x:x[0])
    site=json.loads(json.dumps(base_site_context))
    site["schema_version"]="phoenix.site-context/1.1"
    site["status"]="SITE_DRAWING_EVIDENCE"
    site["site_evidence_source"]=source.relative_to(repository).as_posix() if repository in source.parents else str(source)
    site["site_evidence_type"]=data.get("source_type")
    site.setdefault("plot",{})
    site["plot"].update({
        "width_m":data["width_m"],"depth_m":data["depth_m"],
        "source":"SITE_DRAWING_EVIDENCE","legal_boundary":False,
    })
    if data.get("boundary_points_m"):
        site["plot"]["boundary_points_m"]=data["boundary_points_m"]
    if data.get("boundary_coordinates"):
        site["plot"]["boundary_coordinates"]=data["boundary_coordinates"]
    site.setdefault("orientation",{})
    if data.get("north_angle_deg") is not None:
        site["orientation"]={
            "value":"NORTH_ANGLE",
            "north_angle_deg":float(data["north_angle_deg"]),
            "source":"SITE_DRAWING_EVIDENCE",
        }
    else:
        site["orientation"]={
            **site.get("orientation",{}),
            "orientation_validation":"NOT_EXTRACTED_FROM_SITE_DRAWING",
        }
    site["cadastral_validation"]=False
    site["planning_validation"]=False
    site["professional_review_required"]=True
    site["production_release"]="LOCKED"

    register={
        "schema_version":"phoenix.site-parcel-evidence-register/1.0",
        "engine_version":VERSION,"project_id":project_id,
        "evidence":evidence,
        "selected_source":site["site_evidence_source"],
        "selected_type":data.get("source_type"),
        "plot_width_m":data["width_m"],"plot_depth_m":data["depth_m"],
        "north_angle_deg":data.get("north_angle_deg"),
        "legal_boundary_confirmed":False,
        "cadastral_validation":False,
        "planning_validation":False,
        "warnings":warnings,
        "production_release":"LOCKED",
    }
    return SiteParcelResult("PASSED",site,register,[],warnings)
