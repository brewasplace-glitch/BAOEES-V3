from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional, Set, Any
import json
import math

SCHEMA = "PHOENIX_R2D_R4_OPENING_RULE_ENGINE_1.0"
WINDOW_COLOR = "#00D9FF"   # user rule: exterior windows always cyan
EXTERIOR_DOOR_COLOR = "#C69C6D"  # user rule: exterior doors always light brown
INTERIOR_DOOR_COLOR = "#A53B28"
WALL_THICKNESS_M = 0.16
EPS = 1e-6

DEFAULT_REQUIRED_LINKS = {
    "A": [("woonkamer", "keuken_eetruimte")],
    "B": [("woonkamer", "keuken_eetruimte")],
    "C": [("trap", "keuken_eetruimte")],
    "D": [("trap", "keuken_eetruimte")],
    "E": [("woonkamer", "keuken_eetruimte")],
}

PREFERRED_SERVICE_ROOMS = [
    "bijkeuken", "keuken_eetruimte", "woonkamer", "werk_logeerkamer", "techniek"
]

@dataclass(frozen=True)
class Segment:
    orientation: str  # H or V
    coord: float
    lo: float
    hi: float
    side: Optional[str] = None

    @property
    def length(self) -> float:
        return self.hi - self.lo


def _room_tuple(r: List[Any]) -> Tuple[str, float, float, float, float]:
    return str(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])


def room_map(rooms: List[List[Any]]) -> Dict[str, Tuple[str, float, float, float, float]]:
    return {str(r[0]): _room_tuple(r) for r in rooms}


def point_in_room(x: float, y: float, room: List[Any], tol: float = 1e-7) -> bool:
    _, rx, ry, rw, rh = _room_tuple(room)
    return (rx - tol) <= x <= (rx + rw + tol) and (ry - tol) <= y <= (ry + rh + tol)


def rooms_containing_point(x: float, y: float, rooms: List[List[Any]], tol: float = 1e-7) -> List[str]:
    return [str(r[0]) for r in rooms if point_in_room(x, y, r, tol)]


def _merge_intervals(values: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    vals = sorted((float(a), float(b)) for a, b in values if b - a > EPS)
    out: List[List[float]] = []
    for lo, hi in vals:
        if not out or lo > out[-1][1] + EPS:
            out.append([lo, hi])
        else:
            out[-1][1] = max(out[-1][1], hi)
    return [(a, b) for a, b in out]


def _subtract_interval(lo: float, hi: float, covers: Iterable[Tuple[float, float]]) -> List[Tuple[float, float]]:
    pieces = [(float(lo), float(hi))]
    for clo, chi in _merge_intervals(covers):
        nxt = []
        for a, b in pieces:
            if chi <= a + EPS or clo >= b - EPS:
                nxt.append((a, b))
            else:
                if clo > a + EPS:
                    nxt.append((a, min(b, clo)))
                if chi < b - EPS:
                    nxt.append((max(a, chi), b))
        pieces = nxt
    return [(a, b) for a, b in pieces if b - a > 0.20]


def exterior_segments_for_room(rooms: List[List[Any]], room_name: str) -> List[Segment]:
    rm = room_map(rooms)
    if room_name not in rm:
        return []
    _, x, y, w, h = rm[room_name]
    sides = [
        ("H", y, x, x + w, "S"),
        ("H", y + h, x, x + w, "N"),
        ("V", x, y, y + h, "W"),
        ("V", x + w, y, y + h, "E"),
    ]
    out: List[Segment] = []
    for ori, coord, lo, hi, side in sides:
        covers = []
        for r in rooms:
            rn, rx, ry, rw, rh = _room_tuple(r)
            if rn == room_name:
                continue
            rx1, ry1 = rx + rw, ry + rh
            if ori == "H":
                if (abs(coord - y) < EPS and abs(ry1 - coord) < EPS) or (abs(coord - (y + h)) < EPS and abs(ry - coord) < EPS):
                    a, b = max(lo, rx), min(hi, rx1)
                    if b - a > EPS:
                        covers.append((a, b))
            else:
                if (abs(coord - x) < EPS and abs(rx1 - coord) < EPS) or (abs(coord - (x + w)) < EPS and abs(rx - coord) < EPS):
                    a, b = max(lo, ry), min(hi, ry1)
                    if b - a > EPS:
                        covers.append((a, b))
        for a, b in _subtract_interval(lo, hi, covers):
            out.append(Segment(ori, coord, a, b, side))
    return out


def shared_boundaries(rooms: List[List[Any]], a: str, b: str) -> List[Segment]:
    rm = room_map(rooms)
    if a not in rm or b not in rm:
        return []
    _, ax, ay, aw, ah = rm[a]
    _, bx, by, bw, bh = rm[b]
    ax1, ay1, bx1, by1 = ax + aw, ay + ah, bx + bw, by + bh
    out = []
    if abs(ax1 - bx) < EPS or abs(bx1 - ax) < EPS:
        x = bx if abs(ax1 - bx) < EPS else ax
        lo, hi = max(ay, by), min(ay1, by1)
        if hi - lo > 0.5:
            out.append(Segment("V", x, lo, hi))
    if abs(ay1 - by) < EPS or abs(by1 - ay) < EPS:
        y = by if abs(ay1 - by) < EPS else ay
        lo, hi = max(ax, bx), min(ax1, bx1)
        if hi - lo > 0.5:
            out.append(Segment("H", y, lo, hi))
    return out


def opening_span(o: Dict[str, Any]) -> Tuple[float, float]:
    cx, cy = map(float, o["center_xy"])
    w = float(o["width_m"])
    if o["orientation"] == "H":
        return cx - w / 2.0, cx + w / 2.0
    return cy - w / 2.0, cy + w / 2.0


def opening_on_segment(o: Dict[str, Any], s: Segment, tol: float = 0.08) -> bool:
    if o.get("orientation") != s.orientation:
        return False
    cx, cy = map(float, o["center_xy"])
    normal = cy if s.orientation == "H" else cx
    if abs(normal - s.coord) > tol:
        return False
    lo, hi = opening_span(o)
    return lo >= s.lo - tol and hi <= s.hi + tol


def _sample_window_exterior_proof(o: Dict[str, Any], rooms: List[List[Any]], normal_offset: float = 0.12) -> Tuple[bool, Dict[str, Any]]:
    cx, cy = map(float, o["center_xy"])
    width = float(o["width_m"])
    ori = o["orientation"]
    fractions = (-0.40, -0.20, 0.0, 0.20, 0.40)
    details = []
    inside_rooms: Set[str] = set()
    outside_side = None
    for f in fractions:
        tx = cx + (f * width if ori == "H" else 0.0)
        ty = cy + (f * width if ori == "V" else 0.0)
        if ori == "H":
            p1 = (tx, ty - normal_offset)
            p2 = (tx, ty + normal_offset)
        else:
            p1 = (tx - normal_offset, ty)
            p2 = (tx + normal_offset, ty)
        r1 = rooms_containing_point(*p1, rooms, tol=1e-7)
        r2 = rooms_containing_point(*p2, rooms, tol=1e-7)
        occ1, occ2 = bool(r1), bool(r2)
        if occ1 == occ2:
            return False, {"reason": "GLOBAL_ROOM_UNION_XOR_FAIL", "sample": f, "p1_rooms": r1, "p2_rooms": r2}
        local_outside = "NEG" if not occ1 else "POS"
        if outside_side is None:
            outside_side = local_outside
        elif outside_side != local_outside:
            return False, {"reason": "INCONSISTENT_OUTSIDE_SIDE", "sample": f}
        inside_rooms.update(r2 if occ2 else r1)
        details.append({"sample": f, "p1_rooms": r1, "p2_rooms": r2})
    return True, {
        "reason": "GLOBAL_ROOM_UNION_XOR_5_POINT_PASS",
        "outside_side": outside_side,
        "inside_rooms": sorted(inside_rooms),
        "samples": details,
    }


def _next_id(openings: List[Dict[str, Any]], code: str, prefix: str) -> str:
    nums = []
    for o in openings:
        oid = str(o.get("opening_id", ""))
        if oid.startswith(f"{code}-{prefix}"):
            tail = oid.split(f"{code}-{prefix}", 1)[1]
            digits = "".join(ch for ch in tail if ch.isdigit())
            if digits:
                nums.append(int(digits))
    return f"{code}-{prefix}{max(nums, default=0)+1:02d}"


def _is_door(o: Dict[str, Any]) -> bool:
    return o.get("opening_type") == "DOOR" or o.get("kind") in {"door", "sliding_door", "front_door", "rear_garden_door", "side_service_door"}


def _is_access_door(o: Dict[str, Any]) -> bool:
    return _is_door(o) and o.get("kind") != "open_passage"


def _pair(o: Dict[str, Any]) -> frozenset:
    return frozenset((o.get("from"), o.get("to")))


def _door_duplicate_key(o: Dict[str, Any]) -> Tuple:
    pair = tuple(sorted(str(x) for x in (o.get("from"), o.get("to"))))
    cx, cy = [round(float(v), 2) for v in o.get("center_xy", (0, 0))]
    return (o.get("level"), pair, o.get("orientation"), cx, cy)


def dedupe_doors(doors: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    kept: List[Dict[str, Any]] = []
    removed: List[str] = []
    for d in doors:
        duplicate = None
        for k in kept:
            if d.get("level") != k.get("level") or _pair(d) != _pair(k):
                continue
            if d.get("orientation") != k.get("orientation"):
                continue
            dcx, dcy = map(float, d.get("center_xy", (0, 0)))
            kcx, kcy = map(float, k.get("center_xy", (0, 0)))
            if math.hypot(dcx-kcx, dcy-kcy) <= max(0.18, min(float(d.get("width_m", .9)), float(k.get("width_m", .9))) * 0.4):
                duplicate = k
                break
        if duplicate is None:
            kept.append(d)
            continue
        # Prefer a real swing/sliding door over an open passage.
        if duplicate.get("kind") == "open_passage" and d.get("kind") != "open_passage":
            removed.append(str(duplicate.get("opening_id")))
            kept.remove(duplicate)
            kept.append(d)
        else:
            removed.append(str(d.get("opening_id")))
    return kept, removed


def _door_graph(rooms: List[List[Any]], doors: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    g = {str(r[0]): set() for r in rooms}
    for d in doors:
        if not _is_access_door(d):
            continue
        a, b = d.get("from"), d.get("to")
        if a in g and b in g:
            g[a].add(b)
            g[b].add(a)
    return g


def _reachable(g: Dict[str, Set[str]], start: str) -> Set[str]:
    seen = {start} if start in g else set()
    stack = list(seen)
    while stack:
        n = stack.pop()
        for q in g[n]:
            if q not in seen:
                seen.add(q)
                stack.append(q)
    return seen


def _opening_level(o: Dict[str, Any]) -> Optional[str]:
    level = o.get("level")
    if level in {"ground", "upper"}:
        return str(level)
    storey = o.get("storey")
    if storey == 0:
        return "ground"
    if storey == 1:
        return "upper"
    return None


def _same_collision_level(o: Dict[str, Any], target_level: Optional[str]) -> bool:
    if target_level is None:
        return True
    existing = _opening_level(o)
    # Unknown legacy openings remain conservative blockers; known other-storey openings do not.
    return existing is None or existing == target_level


def _safe_center_on_segment(seg: Segment, width: float, openings: List[Dict[str, Any]], margin: float = 0.18, level: Optional[str] = None) -> Optional[Tuple[float, float]]:
    if seg.length < width + 2*margin:
        return None
    candidates = [(seg.lo+seg.hi)/2.0, seg.lo+margin+width/2.0, seg.hi-margin-width/2.0]
    for t in candidates:
        lo, hi = t-width/2.0, t+width/2.0
        collision = False
        for o in openings:
            if not _same_collision_level(o, level):
                continue
            if o.get("orientation") != seg.orientation:
                continue
            cx, cy = map(float, o.get("center_xy", (999,999)))
            normal = cy if seg.orientation == "H" else cx
            if abs(normal-seg.coord) > 0.08:
                continue
            olo, ohi = opening_span(o)
            if not (hi + 0.08 <= olo or lo - 0.08 >= ohi):
                collision = True
                break
        if not collision:
            return ((t, seg.coord) if seg.orientation == "H" else (seg.coord, t))
    return None


def _same_wall(a: Dict[str, Any], b: Dict[str, Any], tol: float = 0.08) -> bool:
    if a.get("orientation") != b.get("orientation"):
        return False
    al, bl = _opening_level(a), _opening_level(b)
    if al is not None and bl is not None and al != bl:
        return False
    acx, acy = map(float, a.get("center_xy", (999,999)))
    bcx, bcy = map(float, b.get("center_xy", (999,999)))
    return abs((acy if a.get("orientation")=="H" else acx) - (bcy if b.get("orientation")=="H" else bcx)) <= tol


def _spans_overlap(a: Dict[str, Any], b: Dict[str, Any], clearance: float = 0.08) -> bool:
    if not _same_wall(a,b):
        return False
    alo,ahi=opening_span(a); blo,bhi=opening_span(b)
    return not (ahi + clearance <= blo or bhi + clearance <= alo)


def _resolve_overlapping_internal_doors(code: str, level: str, rooms: List[List[Any]], doors: List[Dict[str, Any]], other_openings: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> None:
    # Overlapping door symbols are forbidden even when they connect different room pairs.
    # Keep the earlier door stable and relocate the later door on its own exact shared boundary.
    for _ in range(len(doors)*3 + 2):
        collision=None
        for i,a in enumerate(doors):
            for j in range(i+1,len(doors)):
                b=doors[j]
                if _spans_overlap(a,b):
                    collision=(i,j,a,b);break
            if collision:break
        if not collision:
            return
        i,j,a,b=collision
        moved=False
        for idx in (j,i):
            d=doors[idx]; aa,bb=d.get("from"),d.get("to")
            if aa in (None,"OUTSIDE") or bb in (None,"OUTSIDE"):
                continue
            segs=sorted(shared_boundaries(rooms,str(aa),str(bb)),key=lambda q:q.length,reverse=True)
            blockers=[o for o in other_openings + doors if o is not d and o.get("opening_id") != d.get("opening_id")]
            for seg in segs:
                center=_safe_center_on_segment(seg,float(d.get("width_m",.9)),blockers,margin=.18,level=level)
                if center is None:
                    continue
                old=list(d.get("center_xy",[]))
                d["orientation"]=seg.orientation
                d["center_xy"]=[round(center[0],4),round(center[1],4)]
                d["wall"]={"orientation":seg.orientation,"coord":seg.coord,"lo":seg.lo,"hi":seg.hi}
                d["repair_reason"]="R2D_R4_OVERLAPPING_DOOR_RELOCATION"
                report.append({"action":"RELOCATE_OVERLAPPING_DOOR","opening_id":d.get("opening_id"),"from_center":old,"to_center":d["center_xy"]})
                moved=True;break
            if moved:break
        if not moved:
            raise RuntimeError(f"{code} {level}: overlapping door openings cannot be separated legally: {a.get('opening_id')} / {b.get('opening_id')}")
    raise RuntimeError(f"{code} {level}: overlapping door resolution did not converge")


def _remove_window_door_overlaps(windows: List[Dict[str, Any]], doors: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out=[]
    for w in windows:
        hit=next((d for d in doors if _spans_overlap(w,d,clearance=.06)),None)
        if hit:
            report.append({"action":"REMOVE_WINDOW_OVERLAPPING_DOOR","opening_id":w.get("opening_id"),"door_id":hit.get("opening_id")})
        else:
            out.append(w)
    return out


def _ensure_pair_door(code: str, level: str, rooms: List[List[Any]], doors: List[Dict[str, Any]], all_openings: List[Dict[str, Any]], a: str, b: str, report: List[Dict[str, Any]]) -> None:
    pair = frozenset((a,b))
    existing = [d for d in doors if _pair(d) == pair]
    if any(_is_access_door(d) for d in existing):
        return
    # If an open passage already exists, convert it into a visible swing door.
    if existing:
        d = existing[0]
        d["opening_type"] = "DOOR"
        d["kind"] = "door"
        d["render_style"] = {"stroke": INTERIOR_DOOR_COLOR}
        report.append({"action": "CONVERT_OPEN_PASSAGE_TO_DOOR", "opening_id": d.get("opening_id"), "pair": [a,b]})
        return
    segs = shared_boundaries(rooms, a, b)
    if not segs:
        raise RuntimeError(f"{code} {level}: required access pair {a}<->{b} has no exact shared room boundary")
    for seg in sorted(segs, key=lambda s: s.length, reverse=True):
        width = 1.00 if set((a,b)) == set(("woonkamer","keuken_eetruimte")) else 0.90
        center = _safe_center_on_segment(seg, width, all_openings, level=level)
        if center is None:
            continue
        oid = _next_id(all_openings, code, "DG" if level == "ground" else "DU")
        d = {
            "opening_id": oid, "opening_type": "DOOR", "kind": "door",
            "level": level, "storey": 0 if level == "ground" else 1,
            "from": a, "to": b, "orientation": seg.orientation,
            "center_xy": [round(center[0],4), round(center[1],4)], "width_m": width,
            "wall": {"orientation": seg.orientation, "coord": seg.coord, "lo": seg.lo, "hi": seg.hi},
            "repair_reason": "R2D_R4_REQUIRED_ACCESS_LINK",
            "render_style": {"stroke": INTERIOR_DOOR_COLOR},
        }
        doors.append(d); all_openings.append(d)
        report.append({"action": "ADD_REQUIRED_ACCESS_DOOR", "opening_id": oid, "pair": [a,b]})
        return
    raise RuntimeError(f"{code} {level}: no collision-free capacity for required access door {a}<->{b}")


def _repair_reachability(code: str, level: str, rooms: List[List[Any]], doors: List[Dict[str, Any]], all_openings: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> None:
    if not rooms:
        return
    start = "entree" if level == "ground" else "overloop"
    if start not in room_map(rooms):
        start = str(rooms[0][0])
    for _ in range(len(rooms)+2):
        g = _door_graph(rooms, doors)
        seen = _reachable(g, start)
        missing = set(g) - seen
        if not missing:
            return
        candidates = []
        for a in seen:
            for b in missing:
                for seg in shared_boundaries(rooms, a, b):
                    candidates.append((seg.length, a, b, seg))
        candidates.sort(reverse=True, key=lambda x: x[0])
        placed = False
        for _, a, b, seg in candidates:
            center = _safe_center_on_segment(seg, 0.90, all_openings, level=level)
            if center is None:
                continue
            oid = _next_id(all_openings, code, "DG" if level == "ground" else "DU")
            d = {
                "opening_id": oid, "opening_type": "DOOR", "kind": "door",
                "level": level, "storey": 0 if level == "ground" else 1,
                "from": a, "to": b, "orientation": seg.orientation,
                "center_xy": [round(center[0],4), round(center[1],4)], "width_m": 0.90,
                "wall": {"orientation": seg.orientation, "coord": seg.coord, "lo": seg.lo, "hi": seg.hi},
                "repair_reason": "R2D_R4_CIRCULATION_REPAIR",
                "render_style": {"stroke": INTERIOR_DOOR_COLOR},
            }
            doors.append(d); all_openings.append(d)
            report.append({"action": "ADD_CIRCULATION_DOOR", "opening_id": oid, "pair": [a,b]})
            placed = True
            break
        if not placed:
            raise RuntimeError(f"{code} {level}: cannot make all rooms reachable by swing/sliding doors; disconnected={sorted(missing)}")
    raise RuntimeError(f"{code} {level}: reachability repair did not converge")


def _remove_internal_windows(code: str, level: str, rooms: List[List[Any]], windows: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for w in windows:
        ok, proof = _sample_window_exterior_proof(w, rooms)
        if not ok:
            report.append({"action": "REMOVE_INTERNAL_OR_NONBOUNDARY_WINDOW", "opening_id": w.get("opening_id"), "proof": proof})
            continue
        w["exterior_boundary_proof"] = proof["reason"]
        w["exterior_inside_rooms"] = proof.get("inside_rooms", [])
        w["render_style"] = {"stroke": WINDOW_COLOR, "fill": WINDOW_COLOR}
        out.append(w)
    return out


def _room_has_window(room_name: str, windows: List[Dict[str, Any]], rooms: List[List[Any]]) -> bool:
    for w in windows:
        if room_name in w.get("exterior_inside_rooms", []):
            return True
        # Backstop: exact exterior segment match on the room.
        if any(opening_on_segment(w, s) for s in exterior_segments_for_room(rooms, room_name)):
            return True
    return False


def _add_bathroom_window(code: str, level: str, room_name: str, rooms: List[List[Any]], windows: List[Dict[str, Any]], all_openings: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> None:
    if _room_has_window(room_name, [w for w in windows if _opening_level(w) == level], rooms):
        return
    segs = sorted(exterior_segments_for_room(rooms, room_name), key=lambda s: s.length, reverse=True)
    if not segs:
        raise RuntimeError(f"{code} {level} {room_name}: bathroom has no exterior boundary; room relayout required before a legal window can be added")
    for seg in segs:
        width = min(1.05, max(0.70, seg.length - 0.40))
        center = _safe_center_on_segment(seg, width, all_openings, margin=0.15, level=level)
        if center is None:
            continue
        oid = _next_id(all_openings, code, "W")
        w = {
            "opening_id": oid, "opening_type": "WINDOW", "kind": "window",
            "level": level, "storey": 0 if level == "ground" else 1,
            "source_room": room_name, "orientation": seg.orientation,
            "center_xy": [round(center[0],4), round(center[1],4)], "width_m": round(width,3),
            "wall": {"orientation": seg.orientation, "coord": seg.coord, "lo": seg.lo, "hi": seg.hi},
            "repair_reason": "R2D_R4_BATHROOM_MINIMUM_EXTERIOR_WINDOW",
            "exterior_boundary_proof": "GLOBAL_ROOM_UNION_XOR_5_POINT_PASS",
            "exterior_inside_rooms": [room_name],
            "render_style": {"stroke": WINDOW_COLOR, "fill": WINDOW_COLOR},
        }
        windows.append(w); all_openings.append(w)
        report.append({"action": "ADD_BATHROOM_EXTERIOR_WINDOW", "opening_id": oid, "room": room_name})
        return
    raise RuntimeError(f"{code} {level} {room_name}: exterior boundary exists but no collision-free bathroom window capacity remains")


def _exterior_door_side(d: Dict[str, Any], rooms: List[List[Any]]) -> Optional[str]:
    room_name = d.get("to") if d.get("from") == "OUTSIDE" else d.get("from")
    if room_name in (None, "OUTSIDE"):
        room_name = d.get("room")
    for s in exterior_segments_for_room(rooms, str(room_name)):
        if opening_on_segment(d, s):
            return s.side
    return None


def _ensure_side_or_rear_door(code: str, rooms: List[List[Any]], doors_external: List[Dict[str, Any]], all_openings: List[Dict[str, Any]], report: List[Dict[str, Any]]) -> None:
    for d in doors_external:
        side = _exterior_door_side(d, rooms)
        if d.get("kind") in {"rear_garden_door", "side_service_door"} or side in {"N","E","W"}:
            d["render_style"] = {"stroke": EXTERIOR_DOOR_COLOR, "fill": "none"}
            return
    rm = room_map(rooms)
    for room_name in PREFERRED_SERVICE_ROOMS:
        if room_name not in rm:
            continue
        segs = [s for s in exterior_segments_for_room(rooms, room_name) if s.side in {"N","E","W"}]
        segs.sort(key=lambda s: (0 if s.side == "N" else 1, -s.length))
        for seg in segs:
            width = 1.00
            center = _safe_center_on_segment(seg, width, all_openings, margin=0.18, level="ground")
            if center is None:
                continue
            oid = _next_id(all_openings, code, "DE")
            kind = "rear_garden_door" if seg.side == "N" else "side_service_door"
            d = {
                "opening_id": oid, "opening_type": "DOOR", "kind": kind,
                "level": "ground", "storey": 0, "from": "OUTSIDE", "to": room_name, "room": room_name,
                "orientation": seg.orientation, "center_xy": [round(center[0],4), round(center[1],4)],
                "width_m": width, "wall": {"orientation": seg.orientation, "coord": seg.coord, "lo": seg.lo, "hi": seg.hi},
                "repair_reason": "R2D_R4_MINIMUM_REAR_OR_SIDE_DOOR",
                "render_style": {"stroke": EXTERIOR_DOOR_COLOR, "fill": "none"},
            }
            doors_external.append(d); all_openings.append(d)
            report.append({"action": "ADD_REAR_OR_SIDE_EXTERIOR_DOOR", "opening_id": oid, "room": room_name, "side": seg.side})
            return
    raise RuntimeError(f"{code}: no collision-free legal exterior boundary available for mandatory rear/side door")


def _sync_variant_openings(v: Dict[str, Any]) -> None:
    ground = list(v.get("doors_internal_ground", []))
    upper = list(v.get("doors_internal_upper", []))
    external = list(v.get("doors_external", []))
    windows = list(v.get("windows", []))
    v["openings"] = windows + ground + upper + external


def _assert_unique_ids(openings: List[Dict[str, Any]], code: str) -> None:
    ids = [str(o.get("opening_id")) for o in openings]
    if len(ids) != len(set(ids)):
        dup = sorted({x for x in ids if ids.count(x) > 1})
        raise RuntimeError(f"{code}: duplicate opening IDs remain: {dup}")


def apply_rules(manifest: Dict[str, Any], policy: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    m = deepcopy(manifest)
    policy = deepcopy(policy or {})
    required_links = policy.get("required_links_by_variant", DEFAULT_REQUIRED_LINKS)
    action_log = []
    variant_reports = {}

    for code in sorted(m.get("variants", {})):
        v = m["variants"][code]
        rooms_by_level = v.get("rooms", {})
        ground_rooms = rooms_by_level.get("ground", [])
        upper_rooms = rooms_by_level.get("upper", [])
        # Start from current structured collections, not from a stale combined list.
        ground_doors = deepcopy(v.get("doors_internal_ground", []))
        upper_doors = deepcopy(v.get("doors_internal_upper", []))
        ext_doors = deepcopy(v.get("doors_external", []))
        windows = deepcopy(v.get("windows", []))

        ground_doors, removed_g = dedupe_doors(ground_doors)
        upper_doors, removed_u = dedupe_doors(upper_doors)
        ext_doors, removed_e = dedupe_doors(ext_doors)
        for oid in removed_g + removed_u + removed_e:
            action_log.append({"variant": code, "action": "REMOVE_DUPLICATE_DOOR", "opening_id": oid})

        # Remove all internal/non-boundary windows level by level.
        kept_windows = []
        for level, rooms in (("ground", ground_rooms), ("upper", upper_rooms)):
            part = [w for w in windows if w.get("level") == level]
            repaired = _remove_internal_windows(code, level, rooms, part, action_log)
            kept_windows.extend(repaired)
        windows = kept_windows

        v["doors_internal_ground"] = ground_doors
        v["doors_internal_upper"] = upper_doors
        v["doors_external"] = ext_doors
        v["windows"] = windows
        _sync_variant_openings(v)
        all_openings = v["openings"]

        # Resolve overlapping/double door graphics even when room-pairs differ.
        _resolve_overlapping_internal_doors(code, "ground", ground_rooms, ground_doors, windows + ext_doors, action_log)
        _resolve_overlapping_internal_doors(code, "upper", upper_rooms, upper_doors, windows, action_log)
        windows = _remove_window_door_overlaps(windows, ground_doors + upper_doors + ext_doors, action_log)
        v["windows"] = windows
        _sync_variant_openings(v)
        all_openings = v["openings"]

        # Required named connections.
        for a, b in required_links.get(code, []):
            level = "ground" if a in room_map(ground_rooms) and b in room_map(ground_rooms) else "upper"
            rooms = ground_rooms if level == "ground" else upper_rooms
            doors = ground_doors if level == "ground" else upper_doors
            _ensure_pair_door(code, level, rooms, doors, all_openings, a, b, action_log)

        # Every room must be reachable through a swing/sliding door.
        _repair_reachability(code, "ground", ground_rooms, ground_doors, all_openings, action_log)
        _repair_reachability(code, "upper", upper_rooms, upper_doors, all_openings, action_log)

        # Every bathroom must have at least one legal exterior window.
        for level, rooms in (("ground", ground_rooms), ("upper", upper_rooms)):
            for r in rooms:
                rn = str(r[0])
                if "badkamer" in rn.lower() or "bathroom" in rn.lower():
                    _add_bathroom_window(code, level, rn, rooms, windows, all_openings, action_log)

        # Every design must have at least one rear or side door.
        _ensure_side_or_rear_door(code, ground_rooms, ext_doors, all_openings, action_log)

        # Standardized styles for all surviving openings.
        for w in windows:
            w["render_style"] = {"stroke": WINDOW_COLOR, "fill": WINDOW_COLOR}
        for d in ext_doors:
            d["render_style"] = {"stroke": EXTERIOR_DOOR_COLOR, "fill": "none"}
        for d in ground_doors + upper_doors:
            d["render_style"] = {"stroke": INTERIOR_DOOR_COLOR, "fill": "none"}

        v["doors_internal_ground"] = ground_doors
        v["doors_internal_upper"] = upper_doors
        v["doors_external"] = ext_doors
        v["windows"] = windows
        _sync_variant_openings(v)
        _assert_unique_ids(v["openings"], code)

        # Final machine checks on the repaired manifest.
        internal_window_ids = []
        bathroom_missing = []
        for level, rooms in (("ground", ground_rooms), ("upper", upper_rooms)):
            for w in [x for x in windows if x.get("level") == level]:
                ok, _ = _sample_window_exterior_proof(w, rooms)
                if not ok:
                    internal_window_ids.append(w["opening_id"])
            for r in rooms:
                rn = str(r[0])
                if ("badkamer" in rn.lower() or "bathroom" in rn.lower()) and not _room_has_window(rn, [x for x in windows if x.get("level") == level], rooms):
                    bathroom_missing.append(rn)
        missing_ground = sorted(set(_door_graph(ground_rooms, ground_doors)) - _reachable(_door_graph(ground_rooms, ground_doors), "entree" if "entree" in room_map(ground_rooms) else (str(ground_rooms[0][0]) if ground_rooms else "")))
        missing_upper = sorted(set(_door_graph(upper_rooms, upper_doors)) - _reachable(_door_graph(upper_rooms, upper_doors), "overloop" if "overloop" in room_map(upper_rooms) else (str(upper_rooms[0][0]) if upper_rooms else "")))
        side_or_rear = any((_exterior_door_side(d, ground_rooms) in {"N","E","W"}) or d.get("kind") in {"rear_garden_door","side_service_door"} for d in ext_doors)
        req_missing = []
        all_doors = ground_doors + upper_doors
        for a,b in required_links.get(code, []):
            if not any(_pair(d)==frozenset((a,b)) and _is_access_door(d) for d in all_doors):
                req_missing.append([a,b])
        ok = not any((internal_window_ids, bathroom_missing, missing_ground, missing_upper, req_missing)) and side_or_rear
        if not ok:
            raise RuntimeError(f"{code}: post-repair rule validation failed")
        variant_reports[code] = {
            "status": "PASS",
            "windows": len(windows),
            "interior_doors_ground": len(ground_doors),
            "interior_doors_upper": len(upper_doors),
            "exterior_doors": len(ext_doors),
            "internal_windows": internal_window_ids,
            "bathrooms_without_exterior_window": bathroom_missing,
            "unreachable_ground": missing_ground,
            "unreachable_upper": missing_upper,
            "required_links_missing": req_missing,
            "rear_or_side_door_present": side_or_rear,
        }

    m["schema"] = m.get("schema", "PHOENIX_OPENING_MANIFEST")
    m["r2d_r4_rule_engine"] = {
        "schema": SCHEMA,
        "status": "PASS_AUTOREPAIRED_MACHINE_RULES_VISUAL_REVIEW_REQUIRED",
        "window_color": WINDOW_COLOR,
        "exterior_door_color": EXTERIOR_DOOR_COLOR,
        "interior_door_color": INTERIOR_DOOR_COLOR,
        "rules": [
            "WINDOWS_EXTERIOR_ONLY",
            "EXTERIOR_WINDOWS_CYAN",
            "EXTERIOR_DOORS_LIGHT_BROWN",
            "BATHROOM_MIN_ONE_EXTERIOR_WINDOW",
            "MIN_ONE_REAR_OR_SIDE_DOOR_PER_DESIGN",
            "ALL_ROOMS_REACHABLE_BY_SWING_OR_SLIDING_DOOR",
            "NO_DUPLICATE_DOORS",
            "REQUIRED_VARIANT_ACCESS_LINKS",
            "OPENING_IDS_AUTHORITATIVE_FOR_2D_CAD_3D",
            "LONG_CYAN_3D_ARTIFACT_FORBIDDEN",
        ],
    }
    report = {
        "schema": SCHEMA,
        "status": "PASS_AUTOREPAIRED_MACHINE_RULES_VISUAL_REVIEW_REQUIRED",
        "variants": variant_reports,
        "actions": action_log,
        "locks": {
            "design_selection": "LOCKED",
            "structural_solver": "LOCKED",
            "permit": "LOCKED",
            "construction": "LOCKED",
            "professional_architect_review": "REQUIRED",
        },
        "label": "PRELIMINARY_NOT_FOR_CONSTRUCTION",
    }
    return m, report


def load_policy(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Project Phoenix R2D R4 permanent opening rule engine")
    ap.add_argument("input_manifest")
    ap.add_argument("output_manifest")
    ap.add_argument("report")
    ap.add_argument("--policy")
    ns = ap.parse_args(argv)
    src = json.loads(Path(ns.input_manifest).read_text(encoding="utf-8"))
    repaired, report = apply_rules(src, load_policy(ns.policy))
    Path(ns.output_manifest).write_text(json.dumps(repaired, indent=2), encoding="utf-8")
    Path(ns.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("R2D_R4_PERMANENT_OPENING_RULE_ENGINE=PASS")
    print(f"R2D_R4_ACTIONS={len(report['actions'])}")
    for code, rec in report["variants"].items():
        print(f"R2D_R4_VARIANT_{code}=PASS WINDOWS={rec['windows']} EXT_DOORS={rec['exterior_doors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
