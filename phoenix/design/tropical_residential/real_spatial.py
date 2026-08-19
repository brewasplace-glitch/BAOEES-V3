from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .engine import generate_variants


@dataclass(frozen=True)
class RectRoom:
    room_id: str
    name: str
    zone: str
    storey_index: int
    target_area_m2: float
    x: float
    y: float
    width: float
    depth: float

    @property
    def area_m2(self) -> float:
        return self.width * self.depth

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["area_m2"] = round(self.area_m2, 3)
        return out


def _split_program_rooms(project: Dict[str, Any], variant: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive explicit rooms from the installed Foundation v1.0 Variant contract."""
    total = float(variant["floor_area_m2"])
    storeys = max(1, int(variant["storeys"]))
    bedrooms = max(1, int(variant["bedrooms"]))
    bathrooms = max(1.0, float(variant["bathrooms"]))

    bedroom_total = min(total * 0.34, max(total * 0.22, bedrooms * 11.0))
    bedroom_area = bedroom_total / bedrooms

    living = max(22.0, total * 0.18)
    dining = max(11.0, total * 0.075)
    kitchen = max(10.0, total * 0.065)
    bathroom_total = max(5.0 * bathrooms, total * 0.065)
    service = max(5.0, total * 0.04)
    circulation_total = max(8.0, total * (0.08 if storeys == 1 else 0.10))

    rooms: List[Dict[str, Any]] = [
        {"room_id": "living", "name": "Living", "zone": "social", "storey_index": 0, "area_m2": living},
        {"room_id": "dining", "name": "Dining", "zone": "social", "storey_index": 0, "area_m2": dining},
        {"room_id": "kitchen", "name": "Kitchen", "zone": "service", "storey_index": 0, "area_m2": kitchen},
        {"room_id": "service", "name": "Laundry / Service", "zone": "service", "storey_index": 0, "area_m2": service},
    ]

    for s in range(storeys):
        rooms.append({
            "room_id": f"circulation_s{s+1}",
            "name": f"Circulation / Stair S{s+1}",
            "zone": "circulation",
            "storey_index": s,
            "area_m2": max(4.5, circulation_total / storeys),
        })

    if storeys == 1:
        bath_shares = [1.0]
    else:
        ground_share = 0.38
        bath_shares = [ground_share] + [(1.0 - ground_share) / (storeys - 1)] * (storeys - 1)

    for s, share in enumerate(bath_shares):
        rooms.append({
            "room_id": f"bathroom_s{s+1}",
            "name": f"Bathroom / WC S{s+1}",
            "zone": "service",
            "storey_index": s,
            "area_m2": max(4.0, bathroom_total * share),
        })

    # For 4+ bedroom multi-storey villas keep one guest/access bedroom on ground.
    for idx in range(bedrooms):
        if storeys == 1:
            s = 0
        elif bedrooms >= 4 and idx == 0:
            s = 0
        else:
            upper_count = storeys - 1
            offset = idx - (1 if bedrooms >= 4 else 0)
            s = 1 + (max(offset, 0) % upper_count)
        rooms.append({
            "room_id": f"bedroom_{idx+1}",
            "name": f"Bedroom {idx+1}",
            "zone": "private",
            "storey_index": s,
            "area_m2": bedroom_area,
        })

    assigned = sum(float(r["area_m2"]) for r in rooms)
    remaining = max(0.0, total - assigned)
    if remaining >= 7.0:
        target_storey = 0 if storeys == 1 else 1
        rooms.append({
            "room_id": "flex_room",
            "name": "Flexible Study / Family Room",
            "zone": "private",
            "storey_index": target_storey,
            "area_m2": min(remaining, max(8.0, total * 0.07)),
        })

    return rooms


def _strategy_zone_order(strategy: str, storey_index: int) -> List[str]:
    if storey_index > 0:
        return ["private", "circulation", "service", "social"]
    return {
        "PASSIVE_COOLING": ["social", "circulation", "service", "private"],
        "LOW_COST": ["service", "circulation", "social", "private"],
        "RESILIENCE": ["social", "service", "circulation", "private"],
        "INDOOR_OUTDOOR": ["social", "circulation", "private", "service"],
        "BALANCED": ["social", "circulation", "service", "private"],
    }[strategy]


def _pack_storey(
    program_rooms: List[Dict[str, Any]],
    storey_index: int,
    width: float,
    depth: float,
    strategy: str,
    wall_t: float,
) -> List[RectRoom]:
    inner_x = wall_t
    inner_y = wall_t
    inner_w = max(2.5, width - 2 * wall_t)
    inner_d = max(2.5, depth - 2 * wall_t)

    floor_rooms = [r for r in program_rooms if int(r["storey_index"]) == storey_index]
    if not floor_rooms:
        floor_rooms = [{
            "room_id": f"flex_s{storey_index+1}",
            "name": f"Flexible Space S{storey_index+1}",
            "zone": "private",
            "storey_index": storey_index,
            "area_m2": inner_w * inner_d,
        }]

    zone_order = _strategy_zone_order(strategy, storey_index)
    zones: Dict[str, List[Dict[str, Any]]] = {}
    for r in floor_rooms:
        zones.setdefault(str(r["zone"]), []).append(r)

    ordered_zones = [z for z in zone_order if z in zones] + [z for z in zones if z not in zone_order]
    zone_targets = {z: sum(float(r["area_m2"]) for r in zones[z]) for z in ordered_zones}
    total_target = sum(zone_targets.values()) or 1.0

    # Enforce a usable depth per populated strip then renormalise.
    raw_depths = {z: inner_d * zone_targets[z] / total_target for z in ordered_zones}
    min_depth = min(2.2, inner_d / max(len(ordered_zones), 1))
    fixed = {z: max(min_depth, raw_depths[z]) for z in ordered_zones}
    scale = inner_d / sum(fixed.values())
    strip_depths = {z: fixed[z] * scale for z in ordered_zones}

    result: List[RectRoom] = []
    y = inner_y
    for zi, z in enumerate(ordered_zones):
        zd = strip_depths[z]
        if zi == len(ordered_zones) - 1:
            zd = inner_y + inner_d - y
        group = zones[z]
        target_sum = sum(float(r["area_m2"]) for r in group) or 1.0
        x = inner_x
        for ri, room in enumerate(group):
            rw = inner_w * float(room["area_m2"]) / target_sum
            if ri == len(group) - 1:
                rw = inner_x + inner_w - x
            result.append(RectRoom(
                room_id=str(room["room_id"]),
                name=str(room["name"]),
                zone=str(room["zone"]),
                storey_index=storey_index,
                target_area_m2=round(float(room["area_m2"]), 3),
                x=float(x),
                y=float(y),
                width=float(rw),
                depth=float(zd),
            ))
            x += rw
        y += zd
    return result


def _segment_key(x1: float, y1: float, x2: float, y2: float, storey: int) -> str:
    a = (round(x1, 4), round(y1, 4))
    b = (round(x2, 4), round(y2, 4))
    if b < a:
        a, b = b, a
    return f"S{storey+1}:{a[0]:.4f},{a[1]:.4f}-{b[0]:.4f},{b[1]:.4f}"


def _derive_walls(
    rooms: List[RectRoom], width: float, depth: float, storey: int, wall_t: float
) -> List[Dict[str, Any]]:
    segments: Dict[str, Dict[str, Any]] = {}

    def add(x1: float, y1: float, x2: float, y2: float, external: bool, source: str) -> None:
        if math.hypot(x2 - x1, y2 - y1) < 0.25:
            return
        key = _segment_key(x1, y1, x2, y2, storey)
        if key not in segments:
            segments[key] = {
                "wall_key": key,
                "storey_index": storey,
                "x1": round(x1, 4), "y1": round(y1, 4),
                "x2": round(x2, 4), "y2": round(y2, 4),
                "external": bool(external),
                "thickness_m": 0.20 if external else 0.12,
                "source": source,
            }

    # Authoritative external envelope.
    add(0.0, 0.0, width, 0.0, True, "envelope_south")
    add(width, 0.0, width, depth, True, "envelope_east")
    add(width, depth, 0.0, depth, True, "envelope_north")
    add(0.0, depth, 0.0, 0.0, True, "envelope_west")

    # Internal room boundaries. Boundaries near the outer wall are skipped because
    # the external envelope above is the authoritative host.
    eps = wall_t + 1e-3
    for r in rooms:
        edges = [
            (r.x, r.y, r.x+r.width, r.y),
            (r.x+r.width, r.y, r.x+r.width, r.y+r.depth),
            (r.x+r.width, r.y+r.depth, r.x, r.y+r.depth),
            (r.x, r.y+r.depth, r.x, r.y),
        ]
        for x1, y1, x2, y2 in edges:
            on_outer_band = (
                max(abs(y1), abs(y2)) < eps or
                max(abs(y1-depth), abs(y2-depth)) < eps or
                max(abs(x1), abs(x2)) < eps or
                max(abs(x1-width), abs(x2-width)) < eps
            )
            if not on_outer_band:
                add(x1, y1, x2, y2, False, f"room_boundary:{r.room_id}")

    return list(segments.values())


def _touches(a: RectRoom, b: RectRoom, tol: float = 1e-3) -> Optional[Tuple[float, float, float, float]]:
    # Shared vertical boundary.
    if abs((a.x + a.width) - b.x) < tol or abs((b.x + b.width) - a.x) < tol:
        x = b.x if abs((a.x + a.width) - b.x) < tol else a.x
        y1 = max(a.y, b.y)
        y2 = min(a.y + a.depth, b.y + b.depth)
        if y2 - y1 >= 0.90:
            return (x, y1, x, y2)
    # Shared horizontal boundary.
    if abs((a.y + a.depth) - b.y) < tol or abs((b.y + b.depth) - a.y) < tol:
        y = b.y if abs((a.y + a.depth) - b.y) < tol else a.y
        x1 = max(a.x, b.x)
        x2 = min(a.x + a.width, b.x + b.width)
        if x2 - x1 >= 0.90:
            return (x1, y, x2, y)
    return None


def _opening_from_segment(
    seg: Tuple[float, float, float, float],
    storey: int,
    kind: str,
    width_m: float,
    height_m: float,
    sill_m: float,
    host_wall_key: str,
    opening_id: str,
) -> Dict[str, Any]:
    x1, y1, x2, y2 = seg
    length = math.hypot(x2-x1, y2-y1)
    ux = (x2-x1)/length
    uy = (y2-y1)/length
    cx = (x1+x2)/2
    cy = (y1+y2)/2
    start_x = cx - ux * width_m / 2
    start_y = cy - uy * width_m / 2
    return {
        "opening_id": opening_id,
        "kind": kind,
        "storey_index": storey,
        "host_wall_key": host_wall_key,
        "x": round(start_x, 4),
        "y": round(start_y, 4),
        "angle_deg": round(math.degrees(math.atan2(uy, ux)), 4),
        "width_m": round(min(width_m, max(0.8, length - 0.3)), 3),
        "height_m": round(height_m, 3),
        "sill_m": round(sill_m, 3),
    }


def _derive_openings(
    rooms: List[RectRoom],
    walls: List[Dict[str, Any]],
    width: float,
    depth: float,
    storey: int,
    strategy: str,
) -> List[Dict[str, Any]]:
    wall_map = {w["wall_key"]: w for w in walls}
    openings: List[Dict[str, Any]] = []

    # Main entrance in south wall, biased to social zone.
    south = next(w for w in walls if w["source"] == "envelope_south")
    social = [r for r in rooms if r.zone == "social"]
    if social:
        r = social[0]
        center = max(0.7, min(width-0.7, r.x + r.width/2))
    else:
        center = width/2
    seg = (max(0.2, center-0.6), 0.0, min(width-0.2, center+0.6), 0.0)
    openings.append(_opening_from_segment(
        seg, storey, "door", 1.10, 2.20, 0.0, south["wall_key"], f"S{storey+1}_ENTRY"
    ))

    # Windows on exterior-facing rooms. Strategy changes aperture size.
    window_width = 1.80 if strategy in {"PASSIVE_COOLING", "INDOOR_OUTDOOR"} else 1.40
    for r in rooms:
        candidates = []
        if r.y <= 0.21:
            candidates.append(("south", (r.x, 0.0, r.x+r.width, 0.0), "envelope_south"))
        if r.y + r.depth >= depth - 0.21:
            candidates.append(("north", (r.x, depth, r.x+r.width, depth), "envelope_north"))
        if r.x <= 0.21:
            candidates.append(("west", (0.0, r.y, 0.0, r.y+r.depth), "envelope_west"))
        if r.x + r.width >= width - 0.21:
            candidates.append(("east", (width, r.y, width, r.y+r.depth), "envelope_east"))
        for side, edge, source in candidates[:2]:
            host = next(w for w in walls if w["source"] == source)
            openings.append(_opening_from_segment(
                edge, storey, "window", window_width, 1.25, 0.90,
                host["wall_key"], f"S{storey+1}_WIN_{r.room_id}_{side}"
            ))

    # Internal doors: rooms sharing a boundary, prioritising circulation and target adjacency.
    door_pairs = set()
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            shared = _touches(a, b)
            if not shared:
                continue
            desired = (
                a.zone == "circulation" or b.zone == "circulation" or
                {a.zone, b.zone} <= {"social", "service"} or
                (a.zone == "private" and b.zone == "service") or
                (b.zone == "private" and a.zone == "service")
            )
            if not desired:
                continue
            key = _segment_key(*shared, storey)
            if key not in wall_map:
                continue
            pair = tuple(sorted((a.room_id, b.room_id)))
            if pair in door_pairs:
                continue
            door_pairs.add(pair)
            openings.append(_opening_from_segment(
                shared, storey, "door", 0.90, 2.10, 0.0, key,
                f"S{storey+1}_DOOR_{pair[0]}_{pair[1]}"
            ))

    return openings


def _validate_with_shapely(layout: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from shapely.geometry import box
    except Exception:
        return {"engine": "deterministic_fallback", "valid": True, "warnings": ["SHAPELY_NOT_AVAILABLE"]}

    footprint = box(0.0, 0.0, float(layout["footprint"]["width_m"]), float(layout["footprint"]["depth_m"]))
    warnings: List[str] = []
    by_storey: Dict[int, List[Any]] = {}
    for room in layout["rooms"]:
        poly = box(room["x"], room["y"], room["x"]+room["width"], room["y"]+room["depth"])
        if not footprint.buffer(1e-7).contains(poly):
            warnings.append(f"ROOM_OUTSIDE_FOOTPRINT:{room['room_id']}")
        by_storey.setdefault(int(room["storey_index"]), []).append((room["room_id"], poly))

    for storey, items in by_storey.items():
        for i, (aid, ap) in enumerate(items):
            for bid, bp in items[i+1:]:
                if ap.intersection(bp).area > 1e-6:
                    warnings.append(f"ROOM_OVERLAP:S{storey+1}:{aid}:{bid}")

    return {"engine": "Shapely", "valid": not warnings, "warnings": warnings}


def _site_fit(project: Dict[str, Any], width: float, depth: float) -> Dict[str, Any]:
    site = project["site"]
    setbacks = site.get("concept_setbacks_m", {"front": 3.0, "rear": 3.0, "left": 2.0, "right": 2.0})
    avail_w = float(site["width_m"]) - float(setbacks.get("left", 0)) - float(setbacks.get("right", 0))
    avail_d = float(site["depth_m"]) - float(setbacks.get("front", 0)) - float(setbacks.get("rear", 0))
    fits = width <= avail_w + 1e-6 and depth <= avail_d + 1e-6
    return {
        "fits_concept_envelope": fits,
        "available_width_m": round(avail_w, 3),
        "available_depth_m": round(avail_d, 3),
        "setbacks_source": "project_input" if "concept_setbacks_m" in site else "concept_heuristic_not_code_requirement",
    }


def build_real_layout(project: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
    width = float(variant["width_m"])
    depth = float(variant["depth_m"])
    wall_t = 0.20
    program_rooms = _split_program_rooms(project, variant)

    all_rooms: List[RectRoom] = []
    walls: List[Dict[str, Any]] = []
    openings: List[Dict[str, Any]] = []
    storeys = int(variant["storeys"])

    for s in range(storeys):
        sr = _pack_storey(program_rooms, s, width, depth, variant["strategy"], wall_t)
        sw = _derive_walls(sr, width, depth, s, wall_t)
        so = _derive_openings(sr, sw, width, depth, s, variant["strategy"])
        all_rooms += sr
        walls += sw
        openings += so

    veranda_depth = float(variant["veranda_depth_m"])
    veranda = {
        "x": 0.60,
        "y": -veranda_depth,
        "width": round(max(1.0, width-1.20), 3),
        "depth": round(veranda_depth, 3),
        "covered": True,
        "strategy": "shaded_outdoor_transition",
    }

    layout = {
        "schema": "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
        "project_id": project["project_id"],
        "variant_id": variant["variant_id"],
        "strategy": variant["strategy"],
        "storeys": storeys,
        "storey_height_m": round(float(variant["ceiling_height_m"]) + 0.30, 3),
        "footprint": {"width_m": round(width, 3), "depth_m": round(depth, 3)},
        "rooms": [r.to_dict() for r in all_rooms],
        "walls": walls,
        "openings": openings,
        "veranda": veranda,
        "roof": {
            "pitch_deg": float(variant["roof_pitch_deg"]),
            "eave_overhang_m": float(variant["eave_overhang_m"]),
            "representation_stage": "SIMPLIFIED_IFC_VOLUME_WITH_TROPICAL_PITCH_METADATA",
        },
        "elevation": {"raised_floor_m": float(variant["raised_floor_m"])},
        "site_fit": _site_fit(project, width, depth),
        "governance": {
            "layout_status": "REAL_GEOMETRIC_CONCEPT_LAYOUT",
            "professional_approval": "NOT_AUTOMATIC",
            "code_compliance": "NOT_AUTOMATIC",
            "for_construction": "LOCKED",
        },
    }
    layout["geometry_validation"] = _validate_with_shapely(layout)
    return layout


def generate_real_layouts(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants = [v.to_dict() for v in generate_variants(project)]
    return [build_real_layout(project, variant) for variant in variants]
