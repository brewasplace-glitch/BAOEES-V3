from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from ortools.sat.python import cp_model
import networkx as nx
from shapely.geometry import box as shapely_box
from .aec_topology_quality import analyze_aec_topology


ENGINE_ID = "PHOENIX_OPEN_SOURCE_SPATIAL_SYNTHESIS_R4_FIX_R3"
ENGINE_STACK = {
    "synthesis": "Google OR-Tools CP-SAT",
    "geometry": "Shapely",
    "graph": "NetworkX",
    "bim_downstream": "IfcOpenShell",
    "geometry_validation_downstream": "FreeCAD BIM",
}


PUBLIC = ("LIVING","DINING","KITCHEN","ENTRY","ENTRANCE","LOUNGE","FAMILY")
PRIVATE = ("BED","MASTER","PRIVATE","STUDY","OFFICE")
WET = ("BATH","WC","TOILET","SHOWER","LAUNDRY","WASH","UTILITY")
CIRC = ("CIRC","HALL","CORRIDOR","STAIR","LANDING","LOBBY","ENTRY","ENTRANCE")


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _storey(room: Mapping[str, Any]) -> int:
    try:
        return int(room.get("storey_index") or 0)
    except (TypeError, ValueError):
        return 0


def _label(room: Mapping[str, Any]) -> str:
    return str(
        room.get("zone")
        or room.get("name")
        or room.get("room_name")
        or room.get("room_id")
        or "UNSPECIFIED"
    ).upper()


def _category(room: Mapping[str, Any]) -> str:
    s = _label(room)
    if any(t in s for t in WET):
        return "WET"
    if any(t in s for t in CIRC):
        return "CIRCULATION"
    if any(t in s for t in PRIVATE):
        return "PRIVATE"
    if any(t in s for t in PUBLIC):
        return "PUBLIC"
    return "OTHER"


def _strategy(variant: Mapping[str, Any] | None) -> str:
    v = dict(variant or {})
    return str(
        v.get("strategy")
        or v.get("design_strategy")
        or v.get("variant_id")
        or "BALANCED"
    ).upper()


def _cols_for(n: int, strategy: str) -> int:
    if n <= 2:
        return n
    s = strategy.upper()
    if s in {"PASSIVE_COOLING", "A"}:
        return max(2, min(n, round(n * 0.45)))
    if s in {"LOW_COST", "B"}:
        return max(2, round(n ** 0.5))
    if s in {"RESILIENCE", "C"}:
        return max(2, round(n ** 0.5))
    if s in {"INDOOR_OUTDOOR", "D"}:
        return max(3, min(n, round(n * 0.65)))
    return max(2, round(n ** 0.5))


def _pair_score(cat_a: str, cat_b: str, strategy: str) -> int:
    pair = frozenset((cat_a, cat_b))
    s = strategy.upper()
    score = 0

    # R5: route/privacy/wet-core-aware adjacency objective.
    if pair == frozenset(("PUBLIC", "CIRCULATION")):
        score += 12
    if pair == frozenset(("PRIVATE", "CIRCULATION")):
        score += 11
    if pair == frozenset(("WET", "CIRCULATION")):
        score += 9
    if pair == frozenset(("WET", "WET")):
        score += 12
    if pair == frozenset(("PUBLIC", "PRIVATE")):
        score -= 18

    if s in {"LOW_COST", "B"}:
        if pair == frozenset(("WET", "WET")):
            score += 12
        if pair == frozenset(("WET", "CIRCULATION")):
            score += 8
    elif s in {"RESILIENCE", "C"}:
        if pair == frozenset(("WET", "WET")):
            score += 16
        if pair == frozenset(("PUBLIC", "PRIVATE")):
            score -= 8
    elif s in {"INDOOR_OUTDOOR", "D"}:
        if pair == frozenset(("PUBLIC", "PUBLIC")):
            score += 12
        if pair == frozenset(("PUBLIC", "CIRCULATION")):
            score += 7
    elif s in {"PASSIVE_COOLING", "A"}:
        if pair == frozenset(("PUBLIC", "PRIVATE")):
            score -= 10
        if pair == frozenset(("PUBLIC", "CIRCULATION")):
            score += 6
    else:
        if pair == frozenset(("PUBLIC", "CIRCULATION")):
            score += 7
        if pair == frozenset(("PRIVATE", "CIRCULATION")):
            score += 7
    return score
def _slot_edges(n: int, cols: int) -> list[tuple[int, int]]:
    edges = []
    for i in range(n):
        row, col = divmod(i, cols)
        right = i + 1
        down = i + cols
        if right < n and divmod(right, cols)[0] == row:
            edges.append((i, right))
        if down < n:
            edges.append((i, down))
    return edges


def _solve_assignment(rooms: list[Mapping[str, Any]], strategy: str) -> list[int]:
    """
    Open-source CP-SAT assignment:
    returns room index per slot index.
    """
    n = len(rooms)
    cols = _cols_for(n, strategy)
    edges = _slot_edges(n, cols)

    model = cp_model.CpModel()

    # x[r,s] = room r assigned to slot s.
    x = {}
    for r in range(n):
        for s in range(n):
            x[r, s] = model.new_bool_var(f"x_{r}_{s}")

    for r in range(n):
        model.add(sum(x[r, s] for s in range(n)) == 1)
    for s in range(n):
        model.add(sum(x[r, s] for r in range(n)) == 1)

    cats = [_category(r) for r in rooms]
    objective_terms = []

    # Adjacency reward/penalty on neighboring slots.
    for edge_idx, (sa, sb) in enumerate(edges):
        for ra in range(n):
            for rb in range(n):
                if ra == rb:
                    continue
                pair = model.new_bool_var(f"e_{edge_idx}_{ra}_{rb}")
                model.add(pair <= x[ra, sa])
                model.add(pair <= x[rb, sb])
                model.add(pair >= x[ra, sa] + x[rb, sb] - 1)
                weight = _pair_score(cats[ra], cats[rb], strategy)
                if weight:
                    objective_terms.append(weight * pair)

    # Position preferences by strategy. These are intentionally modest so
    # adjacency remains the main driver.
    rows = (n + cols - 1) // cols
    for r in range(n):
        cat = cats[r]
        for s in range(n):
            row, col = divmod(s, cols)
            perimeter = int(row in (0, rows - 1) or col in (0, cols - 1))
            center_distance = abs(row * 2 - (rows - 1)) + abs(col * 2 - (cols - 1))

            weight = 0
            st = strategy.upper()
            if st in {"INDOOR_OUTDOOR", "D"} and cat == "PUBLIC":
                weight += 4 * perimeter
            if st in {"RESILIENCE", "C"} and cat == "WET":
                weight -= center_distance
            if st in {"LOW_COST", "B"} and cat in {"WET", "CIRCULATION"}:
                weight -= center_distance
            if st in {"PASSIVE_COOLING", "A"} and cat == "PUBLIC":
                weight += 2 * perimeter
            if weight:
                objective_terms.append(weight * x[r, s])

    model.maximize(sum(objective_terms) if objective_terms else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"OPEN_SOURCE_CP_SAT_NO_SOLUTION:{status}")

    assignment = [-1] * n
    for s in range(n):
        for r in range(n):
            if solver.value(x[r, s]):
                assignment[s] = r
                break
    if any(v < 0 for v in assignment):
        raise RuntimeError("OPEN_SOURCE_CP_SAT_INCOMPLETE_ASSIGNMENT")
    return assignment


def _gap(strategy: str) -> tuple[float, float]:
    s = strategy.upper()
    if s in {"LOW_COST", "B"}:
        return 0.05, 0.05
    if s in {"RESILIENCE", "C"}:
        return 0.08, 0.08
    if s in {"INDOOR_OUTDOOR", "D"}:
        return 0.18, 0.12
    if s in {"PASSIVE_COOLING", "A"}:
        return 0.14, 0.08
    return 0.10, 0.10


def _pack_connected(
    rooms: list[Mapping[str, Any]],
    assignment: list[int],
    strategy: str,
) -> tuple[list[dict[str, Any]], dict[int, tuple[float, float]]]:
    """
    Phoenix glue only: deterministic coordinate materialization of the
    CP-SAT assignment. Rooms are packed by actual dimensions into connected
    rows. Every row starts on the same x-origin, creating a vertical bridge.
    """
    n = len(rooms)
    cols = _cols_for(n, strategy)
    gap_x, gap_y = _gap(strategy)

    min_x = min(_f(r.get("x")) for r in rooms)
    min_y = min(_f(r.get("y")) for r in rooms)

    generated = []
    moves = {}
    row_y = min_y
    for row_start in range(0, n, cols):
        slot_ids = list(range(row_start, min(n, row_start + cols)))
        room_ids = [assignment[s] for s in slot_ids]

        # Put deepest room first so next row can bridge to it vertically.
        room_ids = sorted(
            room_ids,
            key=lambda rid: (-_f(rooms[rid].get("depth"), 1.0), rid),
        )

        x_cursor = min_x
        row_depth = 0.0
        for rid in room_ids:
            room = rooms[rid]
            new_room = deepcopy(dict(room))
            old_x, old_y = _f(room.get("x")), _f(room.get("y"))
            w = max(0.1, _f(room.get("width"), 1.0))
            d = max(0.1, _f(room.get("depth"), 1.0))

            new_room["x"] = round(x_cursor, 4)
            new_room["y"] = round(row_y, 4)
            generated.append(new_room)
            moves[rid] = (x_cursor - old_x, row_y - old_y)

            x_cursor += w + gap_x
            row_depth = max(row_depth, d)

        row_y += row_depth + gap_y

    return generated, moves


def _translate_openings(
    openings: list[Mapping[str, Any]],
    original_rooms: list[Mapping[str, Any]],
    moves: Mapping[int, tuple[float, float]],
) -> list[dict[str, Any]]:
    def center(room):
        return (
            _f(room.get("x")) + _f(room.get("width")) / 2.0,
            _f(room.get("y")) + _f(room.get("depth")) / 2.0,
        )

    out = []
    for opening in openings:
        ox, oy = _f(opening.get("x")), _f(opening.get("y"))
        host = min(
            range(len(original_rooms)),
            key=lambda i: (center(original_rooms[i])[0] - ox) ** 2
            + (center(original_rooms[i])[1] - oy) ** 2,
        )
        dx, dy = moves.get(host, (0.0, 0.0))
        item = deepcopy(dict(opening))
        if "x" in item:
            item["x"] = round(_f(item.get("x")) + dx, 4)
        if "y" in item:
            item["y"] = round(_f(item.get("y")) + dy, 4)
        out.append(item)
    return out


def _open_source_graph(rooms: list[Mapping[str, Any]]) -> dict[str, Any]:
    graph = nx.Graph()
    polys = []
    for i, room in enumerate(rooms):
        x = _f(room.get("x"))
        y = _f(room.get("y"))
        w = max(0.1, _f(room.get("width"), 1.0))
        d = max(0.1, _f(room.get("depth"), 1.0))
        polys.append(shapely_box(x, y, x + w, y + d))
        graph.add_node(i, room_id=room.get("room_id"), category=_category(room))

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            if _storey(rooms[i]) != _storey(rooms[j]):
                continue
            # Shapely computes the true geometric distance between rectangles.
            distance = polys[i].distance(polys[j])
            boundary_overlap = polys[i].buffer(0.251).intersects(polys[j])
            if distance <= 0.25 and boundary_overlap:
                graph.add_edge(i, j, distance=float(distance))

    components = [sorted(c) for c in nx.connected_components(graph)]
    isolated = list(nx.isolates(graph))

    return {
        "engine": "NetworkX + Shapely",
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "component_count": len(components),
        "isolated_room_count": len(isolated),
        "components": components,
        "isolated": isolated,
        "is_connected": nx.is_connected(graph) if graph.number_of_nodes() else True,
    }


def synthesize_with_open_source_engines(
    layout: Mapping[str, Any],
    variant: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = deepcopy(dict(layout))
    strategy = _strategy(variant)
    rooms = list(result.get("rooms") or [])
    if len(rooms) < 2:
        result["open_source_spatial_engine"] = {
            "engine_id": ENGINE_ID,
            "stack": ENGINE_STACK,
            "applied": False,
            "reason": "INSUFFICIENT_ROOMS",
        }
        return result

    original_rooms = deepcopy(rooms)
    generated_all = []
    move_map_global = {}

    # Solve each storey independently using CP-SAT.
    storeys = sorted(set(_storey(r) for r in rooms))
    for storey in storeys:
        indices = [i for i, r in enumerate(rooms) if _storey(r) == storey]
        group = [rooms[i] for i in indices]
        assignment_local = _solve_assignment(group, strategy)
        generated, moves_local = _pack_connected(group, assignment_local, strategy)

        generated_all.extend(generated)
        for local_idx, delta in moves_local.items():
            move_map_global[indices[local_idx]] = delta

    result["rooms"] = sorted(
        generated_all,
        key=lambda r: (_storey(r), _f(r.get("y")), _f(r.get("x"))),
    )
    if "openings" in result:
        result["openings"] = _translate_openings(
            list(result.get("openings") or []),
            original_rooms,
            move_map_global,
        )

    graph = _open_source_graph(result["rooms"])
    if graph["isolated_room_count"] > 0:
        raise RuntimeError(
            "OPEN_SOURCE_SPATIAL_GRAPH_ISOLATED_ROOM_DENY:"
            + str(graph["isolated"])
        )
    if graph["component_count"] > max(1, len(storeys)):
        raise RuntimeError(
            "OPEN_SOURCE_SPATIAL_GRAPH_COMPONENT_DENY:"
            + str(graph["component_count"])
        )

    result["circulation_graph"] = {
        "schema": "PHOENIX_OPEN_SOURCE_CIRCULATION_GRAPH_V1",
        **graph,
    }
    result["geometry_topology"] = {
        "schema": "PHOENIX_GEOMETRY_AWARE_TOPOLOGY_SYNTHESIS_V4_FIX_R3",
        "strategy": strategy,
        "applied": True,
        "engine_id": ENGINE_ID,
        "open_source_stack": ENGINE_STACK,
        "solver": "OR-Tools CP-SAT",
        "geometry_engine": "Shapely",
        "graph_engine": "NetworkX",
        "custom_code_role": "ORCHESTRATION_ADAPTER_GOVERNANCE_ONLY",
        "release_status": "CONCEPT_GEOMETRY_SYNTHESIS_NOT_FOR_CONSTRUCTION",
    }
    result["open_source_spatial_engine"] = result["geometry_topology"]

    # PHOENIX_OPEN_SOURCE_AEC_TOPOLOGY_R5
    result["aec_topology_quality"] = analyze_aec_topology(result, variant)
    if not result["aec_topology_quality"]["hard_pass"]:
        raise RuntimeError(
            "R5_AEC_TOPOLOGY_HARD_FAIL:"
            + str(result["aec_topology_quality"]["metrics"])
        )

    return result
