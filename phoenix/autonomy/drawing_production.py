"""Phoenix Architectural Drawing Production Engine v1.0.

Produces deterministic concept-for-review SVG/DXF drawings from the central
architectural candidate model. Drawing production is not professional approval.
A schematic site plan never substitutes for cadastral/planning site facts.
"""
from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

VERSION="1.0.0"

def _f(v:Any,default:float=0.0)->float:
    try:return float(v)
    except (TypeError,ValueError):return default

def _svg_header(title:str,w:int=1180,h:int=840)->list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
        '<g stroke="#111" fill="none" stroke-width="1.4">',
        f'<rect x="28" y="28" width="{w-56}" height="{h-56}"/>',
        '</g>',
        f'<text x="45" y="58" font-family="Arial" font-size="20" font-weight="bold">{html.escape(title)}</text>',
    ]

def _titleblock(project_id:str,drawing_no:str,title:str,stage:str="CONCEPT / TER CONTROLE")->list[str]:
    return [
        '<g font-family="Arial" font-size="12" fill="#111">',
        '<rect x="710" y="730" width="420" height="70" fill="white" stroke="#111"/>',
        f'<text x="725" y="752">PROJECT: {html.escape(project_id)}</text>',
        f'<text x="725" y="771">TEKENING: {html.escape(drawing_no)} · {html.escape(title)}</text>',
        f'<text x="725" y="790">STATUS: {html.escape(stage)} · PHOENIX AUTONOOM CONCEPT</text>',
        '</g>'
    ]

def _save_svg(path:Path,lines:list[str])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(lines+['</svg>'])+"\n",encoding="utf-8")

def _dxf_pair(code:int|str,value:Any)->str:
    return f"{code}\n{value}\n"

def _dxf(lines:list[tuple[float,float,float,float]],texts:list[tuple[float,float,str,float]],path:Path)->None:
    parts=["0\nSECTION\n2\nENTITIES\n"]
    for x1,y1,x2,y2 in lines:
        parts.append("0\nLINE\n8\nPHOENIX\n")
        parts.append(_dxf_pair(10,round(x1,3)));parts.append(_dxf_pair(20,round(y1,3)));parts.append(_dxf_pair(30,0))
        parts.append(_dxf_pair(11,round(x2,3)));parts.append(_dxf_pair(21,round(y2,3)));parts.append(_dxf_pair(31,0))
    for x,y,text,height in texts:
        safe=text.encode("ascii","replace").decode("ascii")
        parts.append("0\nTEXT\n8\nTEXT\n")
        parts.append(_dxf_pair(10,round(x,3)));parts.append(_dxf_pair(20,round(y,3)));parts.append(_dxf_pair(30,0))
        parts.append(_dxf_pair(40,height));parts.append(_dxf_pair(1,safe))
    parts.append("0\nENDSEC\n0\nEOF\n")
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text("".join(parts),encoding="ascii")

def _floor_plan(project_id:str,storey:dict[str,Any],out:Path)->list[Path]:
    sid=str(storey.get("storey_id") or "L0");name=str(storey.get("name") or sid)
    spaces=storey.get("spaces") or [];walls=storey.get("walls") or []
    xs=[];ys=[]
    for s in spaces:
        x=_f(s.get("x_m"));y=_f(s.get("y_m"));w=_f(s.get("width_m"));d=_f(s.get("depth_m"))
        xs += [x,x+w];ys += [y,y+d]
    width=max(xs)-min(xs) if xs else 10;depth=max(ys)-min(ys) if ys else 8
    scale=min(70.0,620/max(width,1),520/max(depth,1));ox=100;oy=120
    svg=_svg_header(f"PLATTEGROND {name.upper()} · SCHAAL CA. 1:{max(20,round(1000/scale/5)*5)}")
    svg += ['<g stroke="#111" fill="none" stroke-linecap="square">']
    dxf_lines=[]
    for wall in walls:
        x1=_f(wall.get("x1_m"));y1=_f(wall.get("y1_m"));x2=_f(wall.get("x2_m"));y2=_f(wall.get("y2_m"))
        th=max(2.0,_f(wall.get("thickness_m"),0.12)*scale)
        svg.append(f'<line x1="{ox+x1*scale:.1f}" y1="{oy+(depth-y1)*scale:.1f}" x2="{ox+x2*scale:.1f}" y2="{oy+(depth-y2)*scale:.1f}" stroke-width="{th:.1f}"/>')
        dxf_lines.append((x1,y1,x2,y2))
    svg.append('</g>')
    for s in spaces:
        x=_f(s.get("x_m"));y=_f(s.get("y_m"));w=_f(s.get("width_m"));d=_f(s.get("depth_m"))
        cx=ox+(x+w/2)*scale;cy=oy+(depth-(y+d/2))*scale
        label=str(s.get("name") or s.get("space_id") or "")
        svg += [f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{html.escape(label)}</text>',
                f'<text x="{cx:.1f}" y="{cy+15:.1f}" text-anchor="middle" font-family="Arial" font-size="10">{_f(s.get("area_m2")):.1f} m²</text>']
    # overall dimensions
    svg += [
        f'<line x1="{ox}" y1="{oy+depth*scale+35}" x2="{ox+width*scale}" y2="{oy+depth*scale+35}" stroke="#111"/>',
        f'<text x="{ox+width*scale/2:.1f}" y="{oy+depth*scale+30:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{width:.2f} m</text>',
        f'<line x1="{ox-35}" y1="{oy}" x2="{ox-35}" y2="{oy+depth*scale}" stroke="#111"/>',
        f'<text x="{ox-45}" y="{oy+depth*scale/2:.1f}" transform="rotate(-90 {ox-45},{oy+depth*scale/2:.1f})" text-anchor="middle" font-family="Arial" font-size="11">{depth:.2f} m</text>',
    ]
    svg += _titleblock(project_id,f"A-{sid}-01",f"Plattegrond {name}")
    sp=out/f"floor_plan_{sid}.svg";dp=out/f"floor_plan_{sid}.dxf"
    _save_svg(sp,svg);_dxf(dxf_lines,[(0,depth+1.0,f"{project_id} - floor plan {sid}",0.25)],dp)
    return [sp,dp]

def _elevation(project_id:str,model:dict[str,Any],side:str,out:Path)->list[Path]:
    b=model.get("building") or {};bw=_f(b.get("footprint_width_m"),10);bd=_f(b.get("footprint_depth_m"),8)
    storeys=int(b.get("storey_count") or len(model.get("storeys",[])) or 1);fh=_f(b.get("floor_to_floor_height_m"),3)
    span=bw if side in {"north","south"} else bd
    pitch=_f((model.get("roof") or {}).get("pitch_deg"),35);roof_h=(span/2)*math.tan(math.radians(pitch))
    scale=min(65.0,650/max(span,1));ox=100;ground=610
    svg=_svg_header(f"GEVEL {side.upper()} · CONCEPT / TER CONTROLE")
    x0=ox;x1=ox+span*scale;top=ground-storeys*fh*scale
    svg += [f'<rect x="{x0:.1f}" y="{top:.1f}" width="{span*scale:.1f}" height="{storeys*fh*scale:.1f}" fill="none" stroke="#111" stroke-width="2"/>']
    for i in range(1,storeys):
        y=ground-i*fh*scale;svg.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="#777" stroke-dasharray="5,4"/>')
    ridge_x=(x0+x1)/2;ridge_y=top-roof_h*scale
    svg += [f'<polyline points="{x0:.1f},{top:.1f} {ridge_x:.1f},{ridge_y:.1f} {x1:.1f},{top:.1f}" fill="none" stroke="#111" stroke-width="2"/>']
    # schematic windows
    for level in range(storeys):
        y=ground-(level+0.65)*fh*scale
        for frac in (0.22,0.50,0.78):
            wx=x0+frac*span*scale
            svg.append(f'<rect x="{wx-0.55*scale:.1f}" y="{y-0.6*scale:.1f}" width="{1.1*scale:.1f}" height="{1.2*scale:.1f}" fill="none" stroke="#333"/>')
    svg += [f'<line x1="{x0-20}" y1="{ground}" x2="{x1+20}" y2="{ground}" stroke="#111"/>']
    svg += _titleblock(project_id,f"A-E-{side[:1].upper()}",f"Gevel {side}")
    sp=out/f"elevation_{side}.svg"
    _save_svg(sp,svg)
    # simplified DXF
    dxf_lines=[(0,0,span,0),(0,0,0,storeys*fh),(span,0,span,storeys*fh),(0,storeys*fh,span,storeys*fh),
               (0,storeys*fh,span/2,storeys*fh+roof_h),(span/2,storeys*fh+roof_h,span,storeys*fh)]
    dp=out/f"elevation_{side}.dxf";_dxf(dxf_lines,[(0,storeys*fh+roof_h+0.5,f"{project_id} elevation {side}",0.25)],dp)
    return [sp,dp]

def _section(project_id:str,model:dict[str,Any],axis:str,out:Path)->list[Path]:
    b=model.get("building") or {};bw=_f(b.get("footprint_width_m"),10);bd=_f(b.get("footprint_depth_m"),8)
    storeys=int(b.get("storey_count") or len(model.get("storeys",[])) or 1);fh=_f(b.get("floor_to_floor_height_m"),3)
    span=bw if axis=="AA" else bd;pitch=_f((model.get("roof") or {}).get("pitch_deg"),35);roof_h=(span/2)*math.tan(math.radians(pitch))
    scale=min(65.0,650/max(span,1));ox=110;ground=620;top=ground-storeys*fh*scale
    svg=_svg_header(f"DOORSNEDE {axis} · CONCEPT / TER CONTROLE")
    svg += [f'<line x1="{ox}" y1="{ground}" x2="{ox+span*scale}" y2="{ground}" stroke="#111" stroke-width="3"/>',
            f'<line x1="{ox}" y1="{ground}" x2="{ox}" y2="{top}" stroke="#111" stroke-width="2"/>',
            f'<line x1="{ox+span*scale}" y1="{ground}" x2="{ox+span*scale}" y2="{top}" stroke="#111" stroke-width="2"/>']
    for i in range(storeys+1):
        y=ground-i*fh*scale
        svg.append(f'<line x1="{ox}" y1="{y:.1f}" x2="{ox+span*scale:.1f}" y2="{y:.1f}" stroke="#111" stroke-width="2"/>')
        svg.append(f'<text x="{ox+span*scale+12:.1f}" y="{y+4:.1f}" font-family="Arial" font-size="11">+{i*fh:.2f} m</text>')
    ridge_x=ox+span*scale/2;ridge_y=top-roof_h*scale
    svg.append(f'<polyline points="{ox:.1f},{top:.1f} {ridge_x:.1f},{ridge_y:.1f} {ox+span*scale:.1f},{top:.1f}" fill="none" stroke="#111" stroke-width="2"/>')
    svg += _titleblock(project_id,f"A-S-{axis}",f"Doorsnede {axis}")
    sp=out/f"section_{axis}.svg";_save_svg(sp,svg)
    dxf_lines=[(0,0,span,0),(0,0,0,storeys*fh),(span,0,span,storeys*fh)]
    for i in range(storeys+1):dxf_lines.append((0,i*fh,span,i*fh))
    dxf_lines += [(0,storeys*fh,span/2,storeys*fh+roof_h),(span/2,storeys*fh+roof_h,span,storeys*fh)]
    dp=out/f"section_{axis}.dxf";_dxf(dxf_lines,[(0,storeys*fh+roof_h+0.5,f"{project_id} section {axis}",0.25)],dp)
    return [sp,dp]

def _site_plan(project_id:str,model:dict[str,Any],site:dict[str,Any],out:Path)->list[Path]:
    plot=site.get("plot") or {};place=site.get("building_placement") or {}
    pw=_f(plot.get("width_m"),20);pd=_f(plot.get("depth_m"),20)
    bx=_f(place.get("x_m"));by=_f(place.get("y_m"));bw=_f(place.get("width_m"),10);bd=_f(place.get("depth_m"),8)
    scale=min(28.0,650/max(pw,1),520/max(pd,1));ox=100;oy=120
    svg=_svg_header("SITUATIE / TERREINCONTEXT · CONCEPT")
    svg += [f'<rect x="{ox}" y="{oy}" width="{pw*scale:.1f}" height="{pd*scale:.1f}" fill="none" stroke="#111" stroke-width="2"/>',
            f'<rect x="{ox+bx*scale:.1f}" y="{oy+(pd-by-bd)*scale:.1f}" width="{bw*scale:.1f}" height="{bd*scale:.1f}" fill="none" stroke="#111" stroke-width="3"/>']
    orientation=site.get("orientation") or {}
    north=orientation.get("north_angle_deg") if isinstance(orientation,dict) else None
    if north is not None:
        svg += [f'<text x="{ox+pw*scale+35:.1f}" y="{oy+30:.1f}" font-family="Arial" font-size="16">N {float(north):.1f}°</text>']
    else:
        svg += [f'<text x="{ox+pw*scale+35:.1f}" y="{oy+30:.1f}" font-family="Arial" font-size="12">NOORDRICHTING NIET GEVALIDEERD</text>']
    if site.get("status")=="SCHEMATIC_ASSUMPTION":
        svg += [f'<text x="{ox}" y="{oy+pd*scale+35:.1f}" font-family="Arial" font-size="12" font-weight="bold">LET OP: SCHEMATISCHE PERCEELCONTEXT — GEEN KADASTRALE / JURIDISCHE GRENS</text>']
    else:
        svg += [f'<text x="{ox}" y="{oy+pd*scale+35:.1f}" font-family="Arial" font-size="12">Perceelafmetingen uit projectomschrijving; kadastrale validatie vereist.</text>']
    svg += _titleblock(project_id,"A-SIT-01","Situatie / terreincontext")
    sp=out/"site_plan.svg";_save_svg(sp,svg)
    dxf_lines=[(0,0,pw,0),(pw,0,pw,pd),(pw,pd,0,pd),(0,pd,0,0),
               (bx,by,bx+bw,by),(bx+bw,by,bx+bw,by+bd),(bx+bw,by+bd,bx,by+bd),(bx,by+bd,bx,by)]
    dp=out/"site_plan.dxf";_dxf(dxf_lines,[(0,pd+1,f"{project_id} site plan - concept",0.25)],dp)
    return [sp,dp]

def produce_architectural_drawings(*,project_id:str,architectural_model:dict[str,Any],site_context:dict[str,Any],output_dir:Path,requested_outputs:list[str])->dict[str,Any]:
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    requested=set(requested_outputs or [])
    files:list[Path]=[];coverage:dict[str,Any]={}
    if "floor_plans" in requested:
        for storey in architectural_model.get("storeys",[]):files += _floor_plan(project_id,storey,output_dir)
        coverage["floor_plans"]={"status":"PASSED","stage":"CONCEPT_FOR_REVIEW","reason":None,"message":"Maatgevoerde conceptplattegronden als SVG/DXF geproduceerd; professionele vrijgave blijft geblokkeerd."}
    if "facades" in requested:
        for side in ("north","east","south","west"):files += _elevation(project_id,architectural_model,side,output_dir)
        coverage["facades"]={"status":"PASSED","stage":"CONCEPT_FOR_REVIEW","reason":None,"message":"Vier conceptgevels als SVG/DXF geproduceerd; professionele vrijgave blijft geblokkeerd."}
    if "sections" in requested:
        for axis in ("AA","BB"):files += _section(project_id,architectural_model,axis,output_dir)
        coverage["sections"]={"status":"PASSED","stage":"CONCEPT_FOR_REVIEW","reason":None,"message":"Twee conceptdoorsneden als SVG/DXF geproduceerd; professionele vrijgave blijft geblokkeerd."}
    if "site_plan" in requested:
        files += _site_plan(project_id,architectural_model,site_context,output_dir)
        if site_context.get("status")=="SCHEMATIC_ASSUMPTION":
            coverage["site_plan"]={"status":"BLOCKED","stage":"SCHEMATIC_ONLY","reason":"SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN","message":"Schematische situatietekening geproduceerd, maar echte perceel-/locatiegegevens ontbreken."}
        else:
            coverage["site_plan"]={"status":"PASSED","stage":"CONCEPT_FOR_REVIEW","reason":None,"message":"Situatietekening uit site-evidence geproduceerd; kadastrale/planningsvalidatie en eventueel ontbrekende noordrichting blijven ter controle."}
    if "dwg_dxf" in requested:
        dxf=[p for p in files if p.suffix.lower()==".dxf"]
        coverage["dwg_dxf"]={"status":"PASSED" if dxf else "BLOCKED","stage":"CONCEPT_FOR_REVIEW","reason":None if dxf else "CAD_EXPORT_EMPTY","message":"DXF-concepttekeningen geproduceerd." if dxf else "Geen DXF-tekeningen geproduceerd."}
    register={
        "schema_version":"phoenix.architectural-drawing-register/1.0",
        "project_id":project_id,
        "generator":"architectural_drawing_production_v1.0",
        "drawing_stage":"CONCEPT_FOR_REVIEW",
        "files":[{"name":p.name,"path":p.as_posix(),"format":p.suffix.lower().lstrip(".")} for p in files],
        "desired_output_states":coverage,
        "professional_approval":False,
        "production_release":"LOCKED",
    }
    return {"files":files,"coverage":coverage,"register":register}
