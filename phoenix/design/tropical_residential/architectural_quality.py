from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

QUALITY_SCHEMA = "PHOENIX_REAL_ARCHITECTURAL_QUALITY_V1"

def _f(value: Any, default: float = 0.0) -> float:
    try: return float(value)
    except (TypeError, ValueError): return default

def _storey(room: Mapping[str, Any]) -> int:
    try: return int(room.get("storey_index") or 0)
    except (TypeError, ValueError): return 0

def _zone(room: Mapping[str, Any]) -> str:
    return str(room.get("zone") or room.get("name") or room.get("room_id") or "UNSPECIFIED").strip().upper()

def _area(room: Mapping[str, Any]) -> float:
    return max(0.0, _f(room.get("width"))) * max(0.0, _f(room.get("depth")))

def _box(room: Mapping[str, Any]) -> tuple[float,float,float,float]:
    x,y=_f(room.get("x")),_f(room.get("y"))
    return x,y,x+max(0.0,_f(room.get("width"))),y+max(0.0,_f(room.get("depth")))

def _intersection(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax1,ay1,ax2,ay2=_box(a); bx1,by1,bx2,by2=_box(b)
    dx=min(ax2,bx2)-max(ax1,bx1); dy=min(ay2,by2)-max(ay1,by1)
    return max(0.0,dx)*max(0.0,dy)

def _norm(value: float, origin: float, span: float) -> float:
    return round((value - origin) / max(0.001, span), 3)

def _axis_overlap(a1: float, a2: float, b1: float, b2: float) -> float:
    return max(0.0, min(a2, b2) - max(a1, b1))

def _adjacency_relation(a: Mapping[str, Any], b: Mapping[str, Any]) -> str:
    ax1, ay1, ax2, ay2 = _box(a)
    bx1, by1, bx2, by2 = _box(b)
    # PHOENIX_R1_FIX_R4_DETERMINISTIC_ADJACENCY_TOLERANCE
    # Geometrically identical translated layouts can otherwise straddle the
    # 0.20 m adjacency threshold because of binary floating-point residue.
    horizontal_gap = round(max(0.0, max(bx1 - ax2, ax1 - bx2)), 6)
    vertical_gap = round(max(0.0, max(by1 - ay2, ay1 - by2)), 6)
    y_overlap = _axis_overlap(ay1, ay2, by1, by2)
    x_overlap = _axis_overlap(ax1, ax2, bx1, bx2)
    if horizontal_gap <= 0.20 and y_overlap >= 0.40:
        return "ADJ_EW"
    if vertical_gap <= 0.20 and x_overlap >= 0.40:
        return "ADJ_NS"
    acx, acy = (ax1 + ax2) / 2.0, (ay1 + ay2) / 2.0
    bcx, bcy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
    dx, dy = bcx - acx, bcy - acy
    if abs(dx) >= abs(dy):
        return "REL_E" if dx >= 0 else "REL_W"
    return "REL_N" if dy >= 0 else "REL_S"

def _opening_signature(opening: Mapping[str, Any], min_x: float, min_y: float, span_x: float, span_y: float) -> tuple[Any, ...]:
    return (
        int(opening.get("storey_index") or 0),
        str(opening.get("kind") or opening.get("type") or "OPENING").upper(),
        str(opening.get("side") or opening.get("orientation") or "").upper(),
        _norm(_f(opening.get("x")), min_x, span_x),
        _norm(_f(opening.get("y")), min_y, span_y),
        round(_f(opening.get("width_m") or opening.get("width")), 2),
    )

def _footprint_signature(layout: Mapping[str, Any], min_x: float, min_y: float, span_x: float, span_y: float) -> list[tuple[float, float]]:
    raw = layout.get("footprint") or layout.get("outer_footprint") or []
    points = []
    if isinstance(raw, Mapping):
        raw = raw.get("points") or raw.get("vertices") or []
    for point in raw if isinstance(raw, (list, tuple)) else []:
        if isinstance(point, Mapping):
            x, y = _f(point.get("x")), _f(point.get("y"))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            x, y = _f(point[0]), _f(point[1])
        else:
            continue
        points.append((_norm(x, min_x, span_x), _norm(y, min_y, span_y)))
    return points

def _semantic_signature(layout: Mapping[str, Any]) -> str:
    rooms = list(layout.get("rooms") or [])
    if not rooms:
        return "EMPTY"

    min_x = min(_f(r.get("x")) for r in rooms)
    min_y = min(_f(r.get("y")) for r in rooms)
    max_x = max(_f(r.get("x")) + max(0.0, _f(r.get("width"))) for r in rooms)
    max_y = max(_f(r.get("y")) + max(0.0, _f(r.get("depth"))) for r in rooms)
    span_x = max(0.001, max_x - min_x)
    span_y = max(0.001, max_y - min_y)

    room_rows = []
    for r in sorted(rooms, key=lambda x: (_storey(x), _zone(x), str(x.get("room_id") or ""))):
        x, y = _f(r.get("x")), _f(r.get("y"))
        w, d = max(0.0, _f(r.get("width"))), max(0.0, _f(r.get("depth")))
        room_rows.append((
            _storey(r), _zone(r),
            _norm(x + w / 2.0, min_x, span_x),
            _norm(y + d / 2.0, min_y, span_y),
            round(w / span_x, 3),
            round(d / span_y, 3),
            round(_area(r) / max(0.001, span_x * span_y), 3),
        ))

    ordered = sorted(rooms, key=lambda x: (_storey(x), _zone(x), str(x.get("room_id") or "")))
    relation_rows = []
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if _storey(a) != _storey(b):
                continue
            relation_rows.append((_storey(a), _zone(a), _zone(b), _adjacency_relation(a, b)))

    openings = list(layout.get("openings") or [])
    opening_origin_x = min((_f(o.get("x")) for o in openings), default=min_x)
    opening_origin_y = min((_f(o.get("y")) for o in openings), default=min_y)
    opening_rows = sorted(
        _opening_signature(o, opening_origin_x, opening_origin_y, span_x, span_y)
        for o in openings
    )

    fingerprint = {
        "rooms": room_rows,
        "relations": sorted(relation_rows),
        "footprint": _footprint_signature(layout, min_x, min_y, span_x, span_y),
        "openings": opening_rows,
    }
    raw = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def evaluate_layout_quality(layout: Mapping[str, Any], variant: Mapping[str, Any] | None=None) -> dict[str,Any]:
    variant=dict(variant or {})
    rooms=list(layout.get("rooms") or []); walls=list(layout.get("walls") or []); openings=list(layout.get("openings") or [])
    areas=[_area(r) for r in rooms]
    overlap=0.0
    for i,a in enumerate(rooms):
        for b in rooms[i+1:]:
            if _storey(a)==_storey(b): overlap+=_intersection(a,b)
    total=sum(areas); overlap_ratio=overlap/max(1.0,total)
    zones=sorted({_zone(r) for r in rooms})
    storeys=sorted({_storey(r) for r in rooms})
    dims_ok=all(_f(r.get("width"))>0 and _f(r.get("depth"))>0 for r in rooms)
    min_area=min(areas) if areas else 0.0
    open_per_room=len(openings)/max(1,len(rooms))
    wall_per_room=len(walls)/max(1,len(rooms))
    score=100.0; failures=[]; deductions=[]
    def deduct(code,points,detail):
        nonlocal score
        score-=points; deductions.append({"code":code,"points":points,"detail":detail})
    if len(rooms)<6: failures.append("ROOM_COUNT_LT_6"); deduct("ROOM_COUNT",25,len(rooms))
    if len(zones)<3: failures.append("ZONE_DIVERSITY_LT_3"); deduct("ZONE_DIVERSITY",20,len(zones))
    if not dims_ok: failures.append("NON_POSITIVE_ROOM_DIMENSIONS"); deduct("ROOM_DIMENSIONS",30,False)
    if min_area<2.5: deduct("MIN_ROOM_AREA",10,round(min_area,3))
    if overlap_ratio>0.15: failures.append("EXCESSIVE_ROOM_OVERLAP"); deduct("ROOM_OVERLAP",30,round(overlap_ratio,4))
    elif overlap_ratio>0.05: deduct("ROOM_OVERLAP",12,round(overlap_ratio,4))
    if len(openings)<3: failures.append("OPENING_COUNT_LT_3"); deduct("OPENINGS",20,len(openings))
    if open_per_room<0.35: deduct("OPENING_DENSITY",8,round(open_per_room,3))
    if wall_per_room<0.8: deduct("WALL_DEFINITION",8,round(wall_per_room,3))
    score=max(0.0,min(100.0,score))
    if score<45: failures.append("ARCHITECTURAL_SCORE_LT_45")
    return {
        "schema":QUALITY_SCHEMA,
        "variant_id":str(variant.get("variant_id") or ""),
        "strategy":str(variant.get("strategy") or "").upper(),
        "score":round(score,2),
        "hard_pass":not failures,
        "hard_failures":failures,
        "deductions":deductions,
        "metrics":{"room_count":len(rooms),"wall_count":len(walls),"opening_count":len(openings),"storey_count":len(storeys),"zone_diversity":len(zones),"minimum_room_area_m2":round(min_area,3),"total_room_area_m2":round(total,3),"overlap_ratio":round(overlap_ratio,5),"opening_per_room":round(open_per_room,4),"wall_per_room":round(wall_per_room,4)},
        "semantic_signature":_semantic_signature(layout),
        "release_status":"CONCEPT_QA_ONLY_NOT_FOR_CONSTRUCTION",
    }

def evaluate_variant_set_quality(items: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    rows=[dict(x) for x in items]
    unique=len({str(x.get("semantic_signature") or "") for x in rows})
    scores=[float(x.get("score") or 0) for x in rows]
    failures=[]
    if len(rows)!=5: failures.append(f"VARIANT_COUNT_{len(rows)}_NE_5")
    if unique!=5: failures.append(f"SEMANTICALLY_UNIQUE_VARIANTS_{unique}_NE_5")
    if any(not x.get("hard_pass") for x in rows): failures.append("ONE_OR_MORE_VARIANTS_FAIL_ARCHITECTURAL_QA")
    return {"schema":"PHOENIX_REAL_ARCHITECTURAL_VARIANT_SET_QUALITY_V1","variant_count":len(rows),"unique_semantic_signature_count":unique,"minimum_score":round(min(scores),2) if scores else 0.0,"average_score":round(sum(scores)/max(1,len(scores)),2),"hard_pass":not failures,"hard_failures":failures,"variants":rows,"release_status":"CONCEPT_QA_ONLY_NOT_FOR_CONSTRUCTION"}

def write_quality_report(output_dir: Path, report: Mapping[str,Any]) -> dict[str,str]:
    output_dir.mkdir(parents=True,exist_ok=True)
    jp=output_dir/"architectural_quality_report.json"; mp=output_dir/"architectural_quality_report.md"
    jp.write_text(json.dumps(dict(report),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=["# Phoenix Real Architectural Quality Report","",f"- Variant count: {report.get('variant_count')}",f"- Unique semantic topologies: {report.get('unique_semantic_signature_count')}",f"- Minimum score: {report.get('minimum_score')}",f"- Average score: {report.get('average_score')}",f"- Hard pass: {report.get('hard_pass')}",""]
    for row in report.get("variants") or []:
        lines.append(f"- Variant {row.get('variant_id')}: score={row.get('score')} hard_pass={row.get('hard_pass')}")
    if report.get("hard_failures"):
        lines += ["","## Hard failures"]+[f"- {x}" for x in report["hard_failures"]]
    mp.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return {"json":str(jp),"markdown":str(mp)}
