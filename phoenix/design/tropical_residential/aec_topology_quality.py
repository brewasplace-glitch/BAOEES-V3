from __future__ import annotations

from typing import Any, Mapping
import networkx as nx
from shapely.geometry import box as shapely_box

ENGINE_ID = "PHOENIX_OPEN_SOURCE_AEC_TOPOLOGY_R5_FIX_R2"

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
    parts = [
        room.get("zone"),
        room.get("name"),
        room.get("room_name"),
        room.get("room_id"),
    ]
    return " | ".join(str(v) for v in parts if v not in (None, "")).upper() or "UNSPECIFIED"

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

def _graph_from_rooms(rooms: list[Mapping[str, Any]], tolerance: float = 0.25) -> nx.Graph:
    graph = nx.Graph()
    polys = []
    for i, room in enumerate(rooms):
        x = _f(room.get("x"))
        y = _f(room.get("y"))
        w = max(0.1, _f(room.get("width"), 1.0))
        d = max(0.1, _f(room.get("depth"), 1.0))
        polys.append(shapely_box(x, y, x + w, y + d))
        graph.add_node(
            i,
            room_id=room.get("room_id"),
            category=_category(room),
            storey=_storey(room),
            x=x + w / 2.0,
            y=y + d / 2.0,
            z=float(_storey(room)),
        )

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            if _storey(rooms[i]) != _storey(rooms[j]):
                continue
            distance = float(polys[i].distance(polys[j]))
            if distance <= tolerance and polys[i].buffer(tolerance + 0.001).intersects(polys[j]):
                graph.add_edge(
                    i,
                    j,
                    weight=max(distance, 0.001),
                    Length=max(distance, 0.001),
                    relation="HORIZONTAL_ADJACENCY",
                )

    circulation_nodes = [i for i, room in enumerate(rooms) if _category(room) == "CIRCULATION"]
    for pos, i in enumerate(circulation_nodes):
        for j in circulation_nodes[pos + 1:]:
            if abs(_storey(rooms[i]) - _storey(rooms[j])) == 1:
                graph.add_edge(
                    i,
                    j,
                    weight=1.0,
                    Length=1.0,
                    relation="VERTICAL_CIRCULATION",
                )
    return graph

def _topologic_context(graph: nx.Graph) -> dict[str, Any]:
    try:
        from topologicpy.TGraph import TGraph
        tgraph = TGraph.ByNetworkXGraph(
            graph,
            vertexID="room_id",
            xKey="x",
            yKey="y",
            zKey="z",
            directed=False,
            allowSelfLoops=False,
            allowParallelEdges=False,
            ontology=True,
        )
        if tgraph is None:
            raise RuntimeError("TGRAPH_BYNETWORKXGRAPH_RETURNED_NONE")
        if graph.number_of_nodes() >= 2:
            nodes = list(graph.nodes)
            _ = TGraph.Distance(tgraph, nodes[0], nodes[1], silent=True)
        return {
            "primary_engine": "TopologicPy TGraph",
            "primary_engine_active": True,
            "fallback_engine": "NetworkX + Shapely",
            "topologicpy_graph": tgraph,
            "distance_backend": "TopologicPy TGraph.Distance",
        }
    except Exception as exc:
        return {
            "primary_engine": "TopologicPy TGraph",
            "primary_engine_active": False,
            "fallback_engine": "NetworkX + Shapely",
            "topologicpy_graph": None,
            "distance_backend": "NetworkX shortest_path_length",
            "fallback_reason": f"{type(exc).__name__}:{exc}",
        }

def _distance(ctx: Mapping[str, Any], graph: nx.Graph, a: int, b: int) -> float | None:
    if a == b:
        return 0.0
    if not nx.has_path(graph, a, b):
        return None
    if ctx.get("primary_engine_active"):
        try:
            from topologicpy.TGraph import TGraph
            value = TGraph.Distance(
                ctx.get("topologicpy_graph"),
                a,
                b,
                type="topological",
                silent=True,
            )
            if value is not None:
                return float(value)
        except Exception:
            pass
    try:
        return float(nx.shortest_path_length(graph, a, b))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

def _category_pairs(graph: nx.Graph, category_a: str, category_b: str, same_storey_only: bool = False) -> list[tuple[int, int]]:
    left = [n for n, d in graph.nodes(data=True) if d.get("category") == category_a]
    right = [n for n, d in graph.nodes(data=True) if d.get("category") == category_b]
    pairs = []
    for a in left:
        for b in right:
            if a == b:
                continue
            if same_storey_only and graph.nodes[a].get("storey") != graph.nodes[b].get("storey"):
                continue
            if category_a == category_b and a >= b:
                continue
            pairs.append((a, b))
    return pairs

def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)

def _storey_connectivity(graph: nx.Graph) -> float:
    ratios = []
    storeys = sorted({d.get("storey") for _, d in graph.nodes(data=True)})
    for storey in storeys:
        nodes = [n for n, d in graph.nodes(data=True) if d.get("storey") == storey]
        if not nodes:
            continue
        sub = graph.subgraph(nodes)
        largest = max((len(c) for c in nx.connected_components(sub)), default=0)
        ratios.append(largest / len(nodes))
    return round(100.0 * (_mean(ratios) or 0.0), 2)

def _nearest_circulation_distances(ctx, graph) -> list[float]:
    circulation = [n for n, d in graph.nodes(data=True) if d.get("category") == "CIRCULATION"]
    values = []
    for n, data in graph.nodes(data=True):
        if data.get("category") == "CIRCULATION":
            continue
        same_storey = [c for c in circulation if graph.nodes[c].get("storey") == data.get("storey")]
        distances = [v for v in (_distance(ctx, graph, n, c) for c in same_storey) if v is not None]
        if distances:
            values.append(min(distances))
    return values

def _score_circulation(mean_hops: float | None) -> float:
    if mean_hops is None:
        return 0.0
    return round(max(0.0, 100.0 - max(0.0, mean_hops - 1.0) * 22.0), 2)

def _score_privacy(mean_hops: float | None) -> float:
    if mean_hops is None:
        return 0.0
    if mean_hops <= 1.0:
        return 35.0
    if mean_hops <= 2.0:
        return 70.0
    if mean_hops <= 3.0:
        return 100.0
    return round(max(65.0, 100.0 - (mean_hops - 3.0) * 12.0), 2)

def _score_wet_core(mean_hops: float | None, pair_count: int) -> float:
    if pair_count == 0 or mean_hops is None:
        return 0.0
    return round(max(0.0, 100.0 - max(0.0, mean_hops - 1.0) * 25.0), 2)

def _score_route(mean_hops: float | None) -> float:
    if mean_hops is None:
        return 0.0
    return round(max(0.0, 100.0 - max(0.0, mean_hops - 1.0) * 18.0), 2)

def analyze_aec_topology(layout: Mapping[str, Any], variant: Mapping[str, Any] | None = None) -> dict[str, Any]:
    rooms = list(layout.get("rooms") or [])
    graph = _graph_from_rooms(rooms)
    ctx = _topologic_context(graph)

    components = list(nx.connected_components(graph))
    isolates = list(nx.isolates(graph))

    pp_pairs = _category_pairs(graph, "PUBLIC", "PRIVATE", same_storey_only=False)
    pp_distances = [v for v in (_distance(ctx, graph, a, b) for a, b in pp_pairs) if v is not None]
    pp_mean = _mean(pp_distances)

    wet_pairs = _category_pairs(graph, "WET", "WET", same_storey_only=False)
    wet_distances = [v for v in (_distance(ctx, graph, a, b) for a, b in wet_pairs) if v is not None]
    wet_mean = _mean(wet_distances)

    circulation_distances = _nearest_circulation_distances(ctx, graph)
    circulation_mean = _mean(circulation_distances)

    storey_count = max(1, len({_storey(r) for r in rooms}))
    metrics = {
        "connectivity": _storey_connectivity(graph),
        "circulation_access": _score_circulation(circulation_mean),
        "privacy": _score_privacy(pp_mean),
        "wet_core_clustering": _score_wet_core(wet_mean, len(wet_pairs)),
        "route_efficiency": _score_route(circulation_mean),
        "public_private_mean_path": None if pp_mean is None else round(pp_mean, 3),
        "wet_core_mean_path": None if wet_mean is None else round(wet_mean, 3),
        "mean_room_to_circulation_path": None if circulation_mean is None else round(circulation_mean, 3),
        "component_count": len(components),
        "expected_storey_components": storey_count,
        "isolated_room_count": len(isolates),
        "edge_count": graph.number_of_edges(),
        "node_count": graph.number_of_nodes(),
        "public_room_count": sum(1 for _, d in graph.nodes(data=True) if d.get("category") == "PUBLIC"),
        "private_room_count": sum(1 for _, d in graph.nodes(data=True) if d.get("category") == "PRIVATE"),
        "wet_room_count": sum(1 for _, d in graph.nodes(data=True) if d.get("category") == "WET"),
        "circulation_room_count": sum(1 for _, d in graph.nodes(data=True) if d.get("category") == "CIRCULATION"),
        "public_private_pair_count": len(pp_pairs),
        "wet_pair_count": len(wet_pairs),
        "vertical_circulation_edge_count": sum(
            1 for _, _, d in graph.edges(data=True) if d.get("relation") == "VERTICAL_CIRCULATION"
        ),
    }

    hard_pass = (
        len(isolates) == 0
        and metrics["connectivity"] >= 95.0
        and metrics["vertical_circulation_edge_count"] >= max(0, storey_count - 1)
    )

    return {
        "schema": "PHOENIX_AEC_TOPOLOGY_QUALITY_R5_FIX_R2",
        "engine_id": ENGINE_ID,
        "engine": {k: v for k, v in ctx.items() if k != "topologicpy_graph"},
        "variant_id": str((variant or {}).get("variant_id") or ""),
        "strategy": str((variant or {}).get("strategy") or (variant or {}).get("design_strategy") or ""),
        "metrics": metrics,
        "hard_pass": hard_pass,
        "release_status": "CONCEPT_AEC_TOPOLOGY_QA_NOT_FOR_CONSTRUCTION",
    }
