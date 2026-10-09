from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping

from .real_spatial import _derive_openings, _derive_walls


_SIDE_BY_SOURCE = {
    "envelope_north": "N",
    "envelope_east": "E",
    "envelope_south": "S",
    "envelope_west": "W",
}


def _room_namespace(room: Mapping[str, Any]) -> SimpleNamespace:
    # Existing Phoenix real_spatial helpers are duck-typed around RectRoom fields.
    return SimpleNamespace(
        room_id=str(room["room_id"]),
        name=str(room.get("name") or room["room_id"]),
        zone=str(room.get("zone") or "other"),
        x=float(room["x"]),
        y=float(room["y"]),
        width=float(room["width"]),
        depth=float(room["depth"]),
        area_m2=float(room.get("area_m2") or (float(room["width"]) * float(room["depth"]))),
        storey_index=int(room["storey_index"]),
    )


def _wall_thickness(layout: Mapping[str, Any]) -> float:
    vals = []
    for wall in layout.get("walls") or []:
        try:
            vals.append(float(wall["thickness_m"]))
        except Exception:
            pass
    if vals:
        # Preserve the established Phoenix wall convention rather than inventing one.
        return round(sorted(vals)[len(vals) // 2], 4)
    return 0.20


def _opening_end(opening: Mapping[str, Any]) -> tuple[float, float]:
    x = float(opening["x"])
    y = float(opening["y"])
    width = float(opening["width_m"])
    angle = math.radians(float(opening["angle_deg"]))
    return x + width * math.cos(angle), y + width * math.sin(angle)


def _point_line_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / denom
    qx = x1 + t * dx
    qy = y1 + t * dy
    return math.hypot(px - qx, py - qy)


def _projection_t(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return 999.0
    return ((px - x1) * dx + (py - y1) * dy) / denom


def _canonicalize_opening_to_host(
    opening: Dict[str, Any],
    wall: Mapping[str, Any],
    edge_margin_m: float = 0.15,
) -> Dict[str, Any]:
    # Project and clamp an opening onto its authoritative host-wall span.
    x1 = float(wall["x1"])
    y1 = float(wall["y1"])
    x2 = float(wall["x2"])
    y2 = float(wall["y2"])
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise RuntimeError(f"R7_ZERO_LENGTH_HOST_WALL:{wall.get('wall_key')}")

    ux = dx / length
    uy = dy / length
    width = float(opening["width_m"])
    max_width = length - (2.0 * edge_margin_m)
    if max_width <= 0.20:
        raise RuntimeError(f"R7_HOST_WALL_TOO_SHORT:{wall.get('wall_key')}")
    width = min(width, max_width)

    sx = float(opening["x"])
    sy = float(opening["y"])
    ex, ey = _opening_end(opening)
    cx = (sx + ex) / 2.0
    cy = (sy + ey) / 2.0
    projected_center = ((cx - x1) * ux) + ((cy - y1) * uy)

    half = width / 2.0
    lower = edge_margin_m + half
    upper = length - edge_margin_m - half
    projected_center = length / 2.0 if upper < lower else max(lower, min(upper, projected_center))

    start_distance = projected_center - half
    repaired = dict(opening)
    repaired["x"] = round(x1 + ux * start_distance, 4)
    repaired["y"] = round(y1 + uy * start_distance, 4)
    repaired["angle_deg"] = round(math.degrees(math.atan2(uy, ux)), 4)
    repaired["width_m"] = round(width, 3)
    repaired["host_wall_key"] = str(wall["wall_key"])
    repaired["storey_index"] = int(wall["storey_index"])
    return repaired


def _canonicalize_openings_to_hosts(
    openings: Iterable[Mapping[str, Any]],
    walls: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    wall_map = {str(w["wall_key"]): w for w in walls}
    repaired: List[Dict[str, Any]] = []
    for opening in openings:
        host_key = str(opening.get("host_wall_key") or "")
        wall = wall_map.get(host_key)
        if wall is None:
            raise RuntimeError(
                f"R7_OPENING_HOST_WALL_MISSING:{opening.get('opening_id')}:{host_key}"
            )
        repaired.append(_canonicalize_opening_to_host(dict(opening), wall))
    return repaired


def validate_canonical_host_geometry(
    layout: Mapping[str, Any], tolerance_m: float = 0.03
) -> Dict[str, Any]:
    walls = list(layout.get("walls") or [])
    openings = list(layout.get("openings") or [])
    wall_map = {str(w["wall_key"]): w for w in walls}

    failures: List[Dict[str, Any]] = []
    exterior_sides = set()

    for opening in openings:
        oid = str(opening.get("opening_id") or "")
        host_key = str(opening.get("host_wall_key") or "")
        wall = wall_map.get(host_key)
        if wall is None:
            failures.append({"opening_id": oid, "reason": "HOST_WALL_MISSING"})
            continue

        if int(opening.get("storey_index", -1)) != int(wall.get("storey_index", -2)):
            failures.append({"opening_id": oid, "reason": "STOREY_MISMATCH"})
            continue

        x1 = float(wall["x1"])
        y1 = float(wall["y1"])
        x2 = float(wall["x2"])
        y2 = float(wall["y2"])
        sx = float(opening["x"])
        sy = float(opening["y"])
        ex, ey = _opening_end(opening)

        d1 = _point_line_distance(sx, sy, x1, y1, x2, y2)
        d2 = _point_line_distance(ex, ey, x1, y1, x2, y2)
        t1 = _projection_t(sx, sy, x1, y1, x2, y2)
        t2 = _projection_t(ex, ey, x1, y1, x2, y2)

        reasons = []
        if d1 > tolerance_m or d2 > tolerance_m:
            reasons.append("NOT_ON_HOST_LINE")
        if min(t1, t2) < -0.001 or max(t1, t2) > 1.001:
            reasons.append("OUTSIDE_HOST_SPAN")
        if reasons:
            failures.append({
                "opening_id": oid,
                "host_wall_key": host_key,
                "reasons": reasons,
                "distance_start_m": round(d1, 5),
                "distance_end_m": round(d2, 5),
                "t_start": round(t1, 5),
                "t_end": round(t2, 5),
            })

        side = _SIDE_BY_SOURCE.get(str(wall.get("source") or ""))
        if side:
            exterior_sides.add(side)

    windows = list(layout.get("windows") or [])
    doors = list(layout.get("doors") or [])
    opening_sides = dict(layout.get("opening_sides") or {})
    facades = dict(layout.get("facades") or {})

    semantic_failures = []
    if len(windows) != sum(1 for o in openings if o.get("kind") == "window"):
        semantic_failures.append("WINDOW_SUBSET_COUNT")
    if len(doors) != sum(1 for o in openings if o.get("kind") == "door"):
        semantic_failures.append("DOOR_SUBSET_COUNT")
    if set(opening_sides) != {str(o.get("opening_id")) for o in openings}:
        semantic_failures.append("OPENING_SIDES_COVERAGE")
    if set(facades) != {"N", "E", "S", "W"}:
        semantic_failures.append("FACADE_SET")

    failures.extend({"reason": x} for x in semantic_failures)

    return {
        "schema": "PHOENIX_R7_CANONICAL_HOST_GEOMETRY_QA_V1",
        "hard_pass": not failures,
        "wall_count": len(walls),
        "opening_count": len(openings),
        "window_count": len(windows),
        "door_count": len(doors),
        "exterior_sides_with_openings": sorted(exterior_sides),
        "failure_count": len(failures),
        "failures": failures,
        "tolerance_m": tolerance_m,
    }


def finalize_canonical_host_geometry(layout: Dict[str, Any]) -> Dict[str, Any]:
    """Re-derive host geometry from the final, post-optimization room model.

    This is the single Phoenix R7 canonical finalization step. It intentionally
    reuses the existing real_spatial wall/opening derivation functions rather
    than introducing a second geometry engine.
    """
    width = float(layout["footprint"]["width_m"])
    depth = float(layout["footprint"]["depth_m"])
    storeys = int(layout["storeys"])
    strategy = str(layout.get("strategy") or "")
    wall_t = _wall_thickness(layout)

    rooms_raw = list(layout.get("rooms") or [])
    if not rooms_raw:
        raise RuntimeError("R7_CANONICAL_HOST_GEOMETRY_NO_ROOMS")

    # Keep area metadata synchronized with the final optimized dimensions.
    for room in rooms_raw:
        room["area_m2"] = round(float(room["width"]) * float(room["depth"]), 2)

    new_walls: List[Dict[str, Any]] = []
    new_openings: List[Dict[str, Any]] = []

    for storey in range(storeys):
        room_objs = [
            _room_namespace(room)
            for room in rooms_raw
            if int(room["storey_index"]) == storey
        ]
        if not room_objs:
            raise RuntimeError(f"R7_CANONICAL_HOST_GEOMETRY_NO_ROOMS_STOREY_{storey}")

        storey_walls = _derive_walls(room_objs, width, depth, storey, wall_t)
        storey_openings = _derive_openings(
            room_objs, storey_walls, width, depth, storey, strategy
        )
        storey_openings = _canonicalize_openings_to_hosts(
            storey_openings, storey_walls
        )
        new_walls.extend(storey_walls)
        new_openings.extend(storey_openings)

    layout["walls"] = new_walls
    layout["openings"] = new_openings
    layout["windows"] = [dict(o) for o in new_openings if o.get("kind") == "window"]
    layout["doors"] = [dict(o) for o in new_openings if o.get("kind") == "door"]

    wall_map = {str(w["wall_key"]): w for w in new_walls}
    opening_sides: Dict[str, str] = {}
    for opening in new_openings:
        wall = wall_map[str(opening["host_wall_key"])]
        opening_sides[str(opening["opening_id"])] = (
            _SIDE_BY_SOURCE.get(str(wall.get("source") or "")) or "INTERNAL"
        )
    layout["opening_sides"] = opening_sides

    facades: Dict[str, Dict[str, Any]] = {}
    for side in ("N", "E", "S", "W"):
        sources = {
            "N": "envelope_north",
            "E": "envelope_east",
            "S": "envelope_south",
            "W": "envelope_west",
        }
        wall_keys = [
            str(w["wall_key"])
            for w in new_walls
            if str(w.get("source") or "") == sources[side]
        ]
        ids = [
            str(o["opening_id"])
            for o in new_openings
            if opening_sides[str(o["opening_id"])] == side
        ]
        facades[side] = {
            "orientation": side,
            "wall_keys": wall_keys,
            "opening_ids": ids,
            "window_ids": [
                str(o["opening_id"])
                for o in new_openings
                if opening_sides[str(o["opening_id"])] == side
                and o.get("kind") == "window"
            ],
            "door_ids": [
                str(o["opening_id"])
                for o in new_openings
                if opening_sides[str(o["opening_id"])] == side
                and o.get("kind") == "door"
            ],
        }
    layout["facades"] = facades

    roof = dict(layout.get("roof") or {})
    pitch = float(roof.get("pitch_deg") or 0.0)
    roof["canonical_footprint"] = {
        "width_m": width,
        "depth_m": depth,
        "eave_overhang_m": float(roof.get("eave_overhang_m") or 0.0),
    }
    roof["geometry_source"] = "FINAL_POST_OPTIMIZATION_FOOTPRINT"
    if abs(pitch) <= 1.0e-9:
        roof["roof_type"] = "FLAT"
        roof["architectural_form"] = "FLAT"
        roof["architectural_pitch_deg"] = 0.0
        roof["drainage_fall_model"] = "SEPARATE_FROM_ARCHITECTURAL_FORM"
        roof["drainage_design_status"] = "UNRESOLVED_CONCEPT_INPUT_REQUIRED"
        roof["representation_stage"] = "CANONICAL_FLAT_ROOF_IFC_VOLUME"
    else:
        roof.setdefault("roof_type", "PITCHED_UNSPECIFIED")
        roof.setdefault("architectural_form", roof["roof_type"])
        roof["architectural_pitch_deg"] = pitch
    layout["roof"] = roof

    qa = validate_canonical_host_geometry(layout)
    layout["canonical_host_geometry"] = {
        **qa,
        "finalization_stage": "POST_SPATIAL_OPTIMIZATION_PRE_OUTPUT",
        "wall_derivation": "REUSE_REAL_SPATIAL_DERIVE_WALLS",
        "opening_derivation": "REUSE_REAL_SPATIAL_DERIVE_OPENINGS",
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
    }
    if not qa["hard_pass"]:
        raise RuntimeError(
            "R7_CANONICAL_HOST_GEOMETRY_DENY:"
            + ",".join(str(x) for x in qa["failures"][:10])
        )
    return layout
