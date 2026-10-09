from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import math, re, xml.etree.ElementTree as ET

@dataclass(frozen=True)
class XYBox:
    minx: float
    miny: float
    maxx: float
    maxy: float
    @property
    def width(self): return max(0.0, self.maxx-self.minx)
    @property
    def depth(self): return max(0.0, self.maxy-self.miny)
    @property
    def cx(self): return (self.minx+self.maxx)/2.0
    @property
    def cy(self): return (self.miny+self.maxy)/2.0

def _f(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return default

def _norm_name(v):
    return re.sub(r"[^a-z0-9]+","",str(v or "").lower())

def room_box(room: Mapping[str, Any]) -> XYBox:
    x=_f(room.get("x")); y=_f(room.get("y"))
    w=max(0.0,_f(room.get("width"))); d=max(0.0,_f(room.get("depth")))
    return XYBox(x,y,x+w,y+d)

def canonical_rooms(layout: Mapping[str, Any]):
    out=[]
    for room in list(layout.get("rooms") or []):
        out.append({
            "room_id":str(room.get("room_id") or ""),
            "name":str(room.get("name") or room.get("room_name") or room.get("room_id") or ""),
            "storey_index":int(room.get("storey_index") or 0),
            "box":room_box(room),
        })
    return out

def normalize_boxes(rows):
    if not rows: return []
    minx=min(r["box"].minx for r in rows); miny=min(r["box"].miny for r in rows)
    out=[]
    for r in rows:
        b=r["box"]
        out.append({**r,"box":XYBox(b.minx-minx,b.miny-miny,b.maxx-minx,b.maxy-miny)})
    return out

def _distance(a,b):
    return math.hypot(a.cx-b.cx,a.cy-b.cy)+abs(a.width-b.width)+abs(a.depth-b.depth)

def _bbox_diff(a,b):
    return {
        "center_distance":round(math.hypot(a.cx-b.cx,a.cy-b.cy),6),
        "width_difference":round(abs(a.width-b.width),6),
        "depth_difference":round(abs(a.depth-b.depth),6),
    }

def greedy_match(canonical, spaces):
    canon=normalize_boxes(canonical); sp=normalize_boxes(spaces)
    unused=set(range(len(sp))); matches=[]
    for c in canon:
        cname=_norm_name(c.get("name") or c.get("room_id"))
        preferred=[i for i in unused if cname and (
            cname==_norm_name(sp[i].get("name")) or
            cname in _norm_name(sp[i].get("name")) or
            _norm_name(sp[i].get("name")) in cname
        )]
        pool=preferred or list(unused)
        if not pool:
            matches.append({"canonical_room_id":c["room_id"],"matched":False,"ifc_space":None}); continue
        best=min(pool,key=lambda i:_distance(c["box"],sp[i]["box"]))
        unused.remove(best); s=sp[best]
        matches.append({
            "canonical_room_id":c["room_id"],
            "canonical_name":c["name"],
            "ifc_space":s.get("name"),
            "ifc_global_id":s.get("global_id"),
            "matched":True,
            **_bbox_diff(c["box"],s["box"]),
        })
    return matches

def svg_summary(svg_path):
    path=Path(svg_path); root=ET.parse(path).getroot(); counts={}
    for elem in root.iter():
        tag=elem.tag.rsplit("}",1)[-1].lower()
        counts[tag]=counts.get(tag,0)+1
    primitives=sum(counts.get(k,0) for k in ("rect","path","polygon","polyline","line"))
    return {"path":str(path),"primitive_count":primitives,"element_counts":counts,"hard_pass":primitives>0}


def _shape_box(shape):
    verts=list(getattr(shape.geometry,"verts",[]) or [])
    if len(verts)<6: return None
    xs=verts[0::3]; ys=verts[1::3]
    if not xs or not ys: return None
    return XYBox(min(xs),min(ys),max(xs),max(ys))

def inspect_ifc(ifc_path):
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import ifcopenshell.validate

    p=Path(ifc_path)
    model=ifcopenshell.open(str(p))
    unit_scale=float(ifcopenshell.util.unit.calculate_unit_scale(model))
    settings=ifcopenshell.geom.settings()
    try: settings.set("use-world-coords",True)
    except Exception: pass

    entity_box={}; geometric={}; geometry_failures=[]
    iterator=ifcopenshell.geom.iterator(settings,model,1)
    if iterator.initialize():
        while True:
            shape=iterator.get()
            element=model.by_id(shape.id)
            try:
                box=_shape_box(shape)
                if box is not None:
                    entity_box[int(shape.id)]=box
                    typ=element.is_a()
                    geometric[typ]=geometric.get(typ,0)+1
            except Exception as exc:
                geometry_failures.append({"id":int(shape.id),"type":element.is_a(),"error":f"{type(exc).__name__}:{exc}"})
            if not iterator.next():
                break

    spaces=[]
    for space in model.by_type("IfcSpace"):
        box=entity_box.get(int(space.id()))
        if box is None:
            try:
                shape=ifcopenshell.geom.create_shape(settings,space)
                box=_shape_box(shape)
            except Exception:
                box=None
        if box is not None:
            spaces.append({
                "name":str(getattr(space,"LongName",None) or getattr(space,"Name",None) or ""),
                "global_id":str(getattr(space,"GlobalId","") or ""),
                "box":box,
            })

    # IFC schema validation using IfcOpenShell's validator.
    logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model,logger,express_rules=False)
    statements=list(getattr(logger,"statements",[]) or [])
    schema_errors=[
        s for s in statements
        if str(s.get("level","")).lower() in {"error","critical"}
    ]

    walls=list(model.by_type("IfcWall"))
    openings=list(model.by_type("IfcOpeningElement"))
    windows=list(model.by_type("IfcWindow"))
    doors=list(model.by_type("IfcDoor"))
    rel_voids=list(model.by_type("IfcRelVoidsElement"))
    rel_fills=list(model.by_type("IfcRelFillsElement"))

    return {
        "path":str(p),
        "schema":str(model.schema),
        "unit_scale":unit_scale,
        "entity_count":len(list(model)),
        "space_count":len(model.by_type("IfcSpace")),
        "geometric_space_count":len(spaces),
        "wall_count":len(walls),
        "opening_count":len(openings),
        "window_count":len(windows),
        "door_count":len(doors),
        "rel_voids_count":len(rel_voids),
        "rel_fills_count":len(rel_fills),
        "geometric_types":geometric,
        "geometry_failure_count":len(geometry_failures),
        "geometry_failures":geometry_failures[:25],
        "schema_error_count":len(schema_errors),
        "schema_errors":schema_errors[:25],
        "spaces":spaces,
    }

def validate_variant(layout,ifc_path,svg_path,tolerance_m=0.35):
    rooms=canonical_rooms(layout)
    ifc=inspect_ifc(ifc_path)
    svg=svg_summary(svg_path)
    matches=greedy_match(rooms,ifc["spaces"])
    matched=[m for m in matches if m.get("matched")]
    max_center=max((m["center_distance"] for m in matched),default=999.0)
    max_width=max((m["width_difference"] for m in matched),default=999.0)
    max_depth=max((m["depth_difference"] for m in matched),default=999.0)
    coverage=0.0 if not rooms else len(matched)/len(rooms)

    failures=[]
    if not rooms: failures.append("NO_CANONICAL_ROOMS")
    if ifc["schema_error_count"]>0: failures.append("IFC_SCHEMA_ERRORS")
    if ifc["geometric_space_count"]<len(rooms): failures.append("IFC_SPACE_COVERAGE")
    if coverage<1.0: failures.append("ROOM_SPACE_MATCH_COVERAGE")
    if max_center>tolerance_m: failures.append("ROOM_SPACE_CENTER_MISMATCH")
    if max_width>tolerance_m: failures.append("ROOM_SPACE_WIDTH_MISMATCH")
    if max_depth>tolerance_m: failures.append("ROOM_SPACE_DEPTH_MISMATCH")
    if ifc["wall_count"]<=0: failures.append("NO_IFC_WALLS")
    if ifc["opening_count"]<=0 and (ifc["window_count"]+ifc["door_count"])>0:
        failures.append("NO_IFC_OPENING_ELEMENTS")
    if ifc["opening_count"]>0 and ifc["rel_voids_count"]<ifc["opening_count"]:
        failures.append("OPENING_VOID_RELATION_COVERAGE")
    if not svg["hard_pass"]: failures.append("SVG_GEOMETRY_EMPTY")

    return {
        "hard_pass":not failures,
        "hard_failures":failures,
        "tolerance_m":tolerance_m,
        "canonical_room_count":len(rooms),
        "match_coverage":round(coverage,6),
        "max_center_difference_m":round(max_center,6),
        "max_width_difference_m":round(max_width,6),
        "max_depth_difference_m":round(max_depth,6),
        "matches":matches,
        "ifc":{k:v for k,v in ifc.items() if k!="spaces"},
        "svg":svg,
        "release_status":"CANONICAL_GEOMETRY_QA_NOT_FOR_CONSTRUCTION",
    }
