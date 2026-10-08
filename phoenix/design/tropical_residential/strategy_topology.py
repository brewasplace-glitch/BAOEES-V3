from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence

R3_SCHEMA="PHOENIX_STRATEGY_DRIVEN_TOPOLOGY_SYNTHESIS_V3"
PUBLIC=("LIVING","DINING","KITCHEN","ENTRY","ENTRANCE","LOUNGE","FAMILY")
PRIVATE=("BED","MASTER","PRIVATE","STUDY","OFFICE")
WET=("BATH","WC","TOILET","SHOWER","LAUNDRY","WASH","UTILITY")
CIRC=("CIRC","HALL","CORRIDOR","STAIR","LANDING","LOBBY","ENTRY","ENTRANCE")

def _f(v,d=0.0):
    try:return float(v)
    except (TypeError,ValueError):return d

def _storey(r):
    try:return int(r.get("storey_index") or 0)
    except (TypeError,ValueError):return 0

def _label(r):
    return str(r.get("zone") or r.get("name") or r.get("room_name") or r.get("room_id") or "UNSPECIFIED").upper()

def _cat(r):
    s=_label(r)
    if any(t in s for t in WET):return "WET"
    if any(t in s for t in CIRC):return "CIRCULATION"
    if any(t in s for t in PRIVATE):return "PRIVATE"
    if any(t in s for t in PUBLIC):return "PUBLIC"
    return "OTHER"

def _cx(r):return _f(r.get("x"))+max(0.0,_f(r.get("width")))/2.0
def _cy(r):return _f(r.get("y"))+max(0.0,_f(r.get("depth")))/2.0

def _semantic_fields(r):
    geometry={"x","y","width","depth","area","area_m2","polygon","geometry","bbox"}
    return {k:deepcopy(v) for k,v in r.items() if k not in geometry}

def _apply_semantics(slot,source):
    out=deepcopy(dict(slot))
    for k,v in _semantic_fields(source).items():out[k]=v
    return out

def _source_order(rooms,strategy):
    s=strategy.upper()
    if s in {"LOW_COST","B"}:
        rank={"CIRCULATION":0,"WET":1,"PUBLIC":2,"OTHER":3,"PRIVATE":4}
        return sorted(rooms,key=lambda r:(rank[_cat(r)],_label(r),str(r.get("room_id") or "")))
    if s in {"RESILIENCE","CLIMATE","C"}:
        rank={"WET":0,"CIRCULATION":1,"PUBLIC":2,"PRIVATE":3,"OTHER":4}
        return sorted(rooms,key=lambda r:(rank[_cat(r)],-_f(r.get("width"))*_f(r.get("depth")),_label(r)))
    if s in {"INDOOR_OUTDOOR","D"}:
        rank={"PUBLIC":0,"CIRCULATION":1,"PRIVATE":2,"WET":3,"OTHER":4}
        return sorted(rooms,key=lambda r:(rank[_cat(r)],_label(r)))
    buckets={k:[] for k in ("PUBLIC","CIRCULATION","PRIVATE","WET","OTHER")}
    for r in sorted(rooms,key=lambda r:(_label(r),str(r.get("room_id") or ""))):buckets[_cat(r)].append(r)
    order=(["PUBLIC","CIRCULATION","PRIVATE","WET","PUBLIC","PRIVATE","OTHER","WET"]
           if s in {"BALANCED","E"} else
           ["PUBLIC","CIRCULATION","PRIVATE","WET","PUBLIC","PRIVATE","OTHER","CIRCULATION"])
    out=[]
    while any(buckets.values()):
        moved=False
        for c in order:
            if buckets[c]:
                out.append(buckets[c].pop(0));moved=True
        if not moved:break
    return out

def _slot_order(slots,strategy):
    s=strategy.upper();slots=list(slots)
    minx,maxx=min(_cx(r) for r in slots),max(_cx(r) for r in slots)
    miny,maxy=min(_cy(r) for r in slots),max(_cy(r) for r in slots)
    mx,my=(minx+maxx)/2,(miny+maxy)/2
    center=lambda r:abs(_cx(r)-mx)+abs(_cy(r)-my)
    edge=lambda r:min(abs(_cx(r)-minx),abs(_cx(r)-maxx),abs(_cy(r)-miny),abs(_cy(r)-maxy))
    if s in {"LOW_COST","B"}:return sorted(slots,key=lambda r:(_storey(r),_cy(r),_cx(r)))
    if s in {"RESILIENCE","CLIMATE","C"}:return sorted(slots,key=lambda r:(_storey(r),center(r),_cy(r),_cx(r)))
    if s in {"INDOOR_OUTDOOR","D"}:return sorted(slots,key=lambda r:(_storey(r),edge(r),_cy(r),_cx(r)))
    if s in {"BALANCED","E"}:return sorted(slots,key=lambda r:(_storey(r),abs(_cy(r)-my),abs(_cx(r)-mx),_cy(r),_cx(r)))
    return sorted(slots,key=lambda r:(_storey(r),abs(_cy(r)-my),-abs(_cx(r)-mx),_cx(r)))

def apply_strategy_topology(layout:Mapping[str,Any],variant:Mapping[str,Any]|None=None)->dict[str,Any]:
    variant=dict(variant or {})
    strategy=str(variant.get("strategy") or variant.get("design_strategy") or variant.get("variant_id") or "A").upper()
    result=deepcopy(dict(layout))
    rooms=list(result.get("rooms") or [])
    if len(rooms)<2:
        result["strategy_topology"]={"schema":R3_SCHEMA,"strategy":strategy,"applied":False,"reason":"INSUFFICIENT_ROOMS"}
        return result
    by_storey={}
    for r in rooms:by_storey.setdefault(_storey(r),[]).append(r)
    synthesized=[];assignments=[]
    for storey in sorted(by_storey):
        group=by_storey[storey]
        slots=_slot_order(group,strategy);sources=_source_order(group,strategy)
        if len(slots)!=len(sources):raise RuntimeError("R3_SLOT_SOURCE_COUNT_MISMATCH")
        for slot,source in zip(slots,sources):
            synthesized.append(_apply_semantics(slot,source))
            assignments.append({"storey_index":storey,"slot_center":[round(_cx(slot),3),round(_cy(slot),3)],"source_room_id":source.get("room_id"),"source_label":_label(source),"source_category":_cat(source)})
    result["rooms"]=sorted(synthesized,key=lambda r:(_storey(r),round(_cy(r),4),round(_cx(r),4)))
    result["strategy_topology"]={"schema":R3_SCHEMA,"strategy":strategy,"applied":True,"assignment_count":len(assignments),"assignments":assignments,"geometry_policy":"PRESERVE_EXISTING_REAL_SPATIAL_SLOTS","semantic_policy":"STRATEGY_DRIVEN_FUNCTION_TO_SLOT_ASSIGNMENT","release_status":"CONCEPT_SYNTHESIS_NOT_FOR_CONSTRUCTION"}
    return result
