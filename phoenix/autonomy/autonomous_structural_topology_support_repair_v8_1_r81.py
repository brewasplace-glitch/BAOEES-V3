"""Project Phoenix R8.1 autonomous structural topology and support repair gate.

Conservative safety behavior:
- may coalesce effectively coincident analytical nodes within an explicit tolerance;
- may remove provisional fixed-base supports outside the lowest provisional base plane;
- rebuilds connectivity and load-path graphs;
- never invents new columns, beams, supports, shell ties, rigid links, or solver constraints.

Geometrically plausible but unmeshed interfaces remain blocking.
"""
from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-AUTONOMOUS-STRUCTURAL-TOPOLOGY-SUPPORT-REPAIR-R8.1"
SCHEMA_VERSION = "phoenix.autonomous-structural-topology-support-repair/1.0"
LOCKED_RELEASE = "LOCKED"
Point = Tuple[float, float, float]


def _xyz(node: Mapping[str, Any]) -> Point:
    return (
        float(node.get("x", 0.0)),
        float(node.get("y", 0.0)),
        float(node.get("z", 0.0)),
    )


def _distance(a: Point, b: Point) -> float:
    return sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _node_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in model.get("nodes", []) or []:
        if isinstance(item, Mapping) and item.get("id"):
            result[str(item["id"])] = dict(item)
    return result


def _support_kind(item: Mapping[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("type", "source_support_type", "solver_boundary_condition_basis")
    ).upper()


def _is_provisional_fixed_base(item: Mapping[str, Any]) -> bool:
    token = _support_kind(item)
    return (
        "PROVISIONAL_FIXED_BASE" in token
        or "V8_1_PROVISIONAL_FIXED_BASE_CANDIDATE" in token
    )


def _coalesce_nodes(
    model: MutableMapping[str, Any], tolerance: float
) -> Dict[str, Any]:
    """Merge only effectively coincident nodes; never relocate a remote node."""
    nodes = [
        dict(n)
        for n in (model.get("nodes") or [])
        if isinstance(n, Mapping) and n.get("id")
    ]
    if tolerance <= 0:
        return {"merged_node_count": 0, "node_remap": {}}

    buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for node in nodes:
        p = _xyz(node)
        key = tuple(int(round(v / tolerance)) for v in p)
        buckets.setdefault(key, []).append(node)

    remap: Dict[str, str] = {}
    survivors: List[Dict[str, Any]] = []

    for group in buckets.values():
        group.sort(key=lambda n: str(n["id"]))
        keep = group[0]
        keep_id = str(keep["id"])
        source_ids = list(keep.get("source_ids") or [])
        survivors.append(keep)

        for duplicate in group[1:]:
            if _distance(_xyz(keep), _xyz(duplicate)) > tolerance:
                survivors.append(duplicate)
                continue
            dup_id = str(duplicate["id"])
            remap[dup_id] = keep_id
            for source in duplicate.get("source_ids") or []:
                if source not in source_ids:
                    source_ids.append(source)
        keep["source_ids"] = source_ids

    if not remap:
        return {"merged_node_count": 0, "node_remap": {}}

    def mapped(value: Any) -> str:
        token = str(value)
        return remap.get(token, token)

    for member in model.get("members", []) or []:
        if isinstance(member, MutableMapping):
            if member.get("node_i") is not None:
                member["node_i"] = mapped(member["node_i"])
            if member.get("node_j") is not None:
                member["node_j"] = mapped(member["node_j"])

    for shell in model.get("shells", []) or []:
        if isinstance(shell, MutableMapping) and isinstance(shell.get("node_ids"), list):
            shell["node_ids"] = [mapped(x) for x in shell["node_ids"]]

    for collection_name in ("supports", "support_candidates"):
        for support in model.get(collection_name, []) or []:
            if isinstance(support, MutableMapping) and support.get("node_id") is not None:
                support["node_id"] = mapped(support["node_id"])

    model["nodes"] = sorted(survivors, key=lambda n: str(n["id"]))
    return {"merged_node_count": len(remap), "node_remap": remap}


def _filter_provisional_supports(
    model: MutableMapping[str, Any],
    foundation_tolerance_m: float,
) -> Dict[str, Any]:
    nodes = _node_map(model)

    all_supports = [
        dict(s)
        for s in (model.get("supports") or [])
        if isinstance(s, Mapping)
    ]
    candidate_supports = [
        dict(s)
        for s in (model.get("support_candidates") or [])
        if isinstance(s, Mapping)
    ]

    basis = all_supports if all_supports else candidate_supports
    provisional = [
        s
        for s in basis
        if _is_provisional_fixed_base(s)
        and str(s.get("node_id") or "") in nodes
    ]

    if not provisional:
        return {
            "foundation_elevation_m": None,
            "removed_provisional_support_ids": [],
            "preserved_explicit_support_ids": [
                str(s.get("id") or "") for s in basis if s.get("id")
            ],
            "provisional_support_count_before": 0,
            "provisional_support_count_after": 0,
        }

    foundation_z = min(
        _xyz(nodes[str(s["node_id"])])[2] for s in provisional
    )

    def keep_provisional(s: Mapping[str, Any]) -> bool:
        if not _is_provisional_fixed_base(s):
            return True
        node = nodes.get(str(s.get("node_id") or ""))
        if not node:
            return False
        return abs(_xyz(node)[2] - foundation_z) <= foundation_tolerance_m

    removed = [
        str(s.get("id") or "")
        for s in basis
        if _is_provisional_fixed_base(s)
        and not keep_provisional(s)
        and s.get("id")
    ]

    if all_supports:
        model["supports"] = [s for s in all_supports if keep_provisional(s)]
    if candidate_supports:
        model["support_candidates"] = [
            s for s in candidate_supports if keep_provisional(s)
        ]

    after_basis = model.get("supports") or model.get("support_candidates") or []
    after_provisional = [
        s
        for s in after_basis
        if isinstance(s, Mapping) and _is_provisional_fixed_base(s)
    ]
    explicit_ids = [
        str(s.get("id") or "")
        for s in after_basis
        if isinstance(s, Mapping)
        and not _is_provisional_fixed_base(s)
        and s.get("id")
    ]

    return {
        "foundation_elevation_m": foundation_z,
        "removed_provisional_support_ids": sorted(set(removed)),
        "preserved_explicit_support_ids": explicit_ids,
        "provisional_support_count_before": len(provisional),
        "provisional_support_count_after": len(after_provisional),
    }


def _point_on_segment(
    point: Point, a: Point, b: Point, tolerance: float
) -> bool:
    ab = tuple(b[i] - a[i] for i in range(3))
    ap = tuple(point[i] - a[i] for i in range(3))
    denom = sum(v * v for v in ab)
    if denom <= tolerance * tolerance:
        return _distance(point, a) <= tolerance

    t = sum(ap[i] * ab[i] for i in range(3)) / denom
    if t < -tolerance or t > 1.0 + tolerance:
        return False

    projection = tuple(a[i] + t * ab[i] for i in range(3))
    return _distance(point, projection) <= tolerance


def _shell_edge_candidates(
    node_id: str,
    point: Point,
    model: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    tolerance: float,
) -> List[str]:
    found: List[str] = []
    for shell in model.get("shells", []) or []:
        if not isinstance(shell, Mapping):
            continue
        ids = [str(x) for x in (shell.get("node_ids") or [])]
        if node_id in ids or len(ids) < 3:
            continue
        if any(x not in nodes for x in ids):
            continue
        pts = [_xyz(nodes[x]) for x in ids]
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            if _point_on_segment(point, a, b, tolerance):
                found.append(str(shell.get("id") or ""))
                break
    return sorted(set(x for x in found if x))


def _member_segment_candidates(
    own_member_id: str,
    node_id: str,
    point: Point,
    model: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    tolerance: float,
) -> List[str]:
    found: List[str] = []
    for other in model.get("members", []) or []:
        if not isinstance(other, Mapping):
            continue
        other_id = str(other.get("id") or "")
        if not other_id or other_id == own_member_id:
            continue
        ni = str(other.get("node_i") or "")
        nj = str(other.get("node_j") or "")
        if node_id in (ni, nj) or ni not in nodes or nj not in nodes:
            continue
        if _point_on_segment(point, _xyz(nodes[ni]), _xyz(nodes[nj]), tolerance):
            found.append(other_id)
    return sorted(set(found))


def _rebuild_connectivity(
    model: MutableMapping[str, Any]
) -> Dict[str, List[str]]:
    node_ids = [
        str(n.get("id"))
        for n in model.get("nodes", []) or []
        if isinstance(n, Mapping) and n.get("id")
    ]
    connectivity: Dict[str, List[str]] = {nid: [] for nid in node_ids}

    for member in model.get("members", []) or []:
        if not isinstance(member, Mapping):
            continue
        mid = str(member.get("id") or "")
        for key in ("node_i", "node_j"):
            nid = str(member.get(key) or "")
            if nid in connectivity and mid:
                connectivity[nid].append(mid)

    for shell in model.get("shells", []) or []:
        if not isinstance(shell, Mapping):
            continue
        sid = str(shell.get("id") or "")
        for raw in shell.get("node_ids", []) or []:
            nid = str(raw)
            if nid in connectivity and sid:
                connectivity[nid].append(sid)

    for nid in connectivity:
        connectivity[nid] = sorted(set(connectivity[nid]))

    model["connectivity"] = connectivity
    edges: List[Dict[str, str]] = []
    for nid, elements in connectivity.items():
        for i, a in enumerate(elements):
            for b in elements[i + 1 :]:
                edges.append({"from": a, "to": b, "via_node": nid})
    model["load_path_graph"] = {
        "mode": "TOPOLOGICAL_ONLY_R8_1_VALIDATED",
        "edges": edges,
    }
    return connectivity


def _element_components(
    model: Mapping[str, Any],
    connectivity: Mapping[str, Sequence[str]],
    supported_nodes: Set[str],
) -> List[Dict[str, Any]]:
    element_nodes: Dict[str, Set[str]] = {}

    for member in model.get("members", []) or []:
        if isinstance(member, Mapping) and member.get("id"):
            element_nodes[str(member["id"])] = {
                str(member.get("node_i") or ""),
                str(member.get("node_j") or ""),
            }

    for shell in model.get("shells", []) or []:
        if isinstance(shell, Mapping) and shell.get("id"):
            element_nodes[str(shell["id"])] = {
                str(x) for x in (shell.get("node_ids") or [])
            }

    adjacency: Dict[str, Set[str]] = {
        eid: set() for eid in element_nodes
    }
    for elements in connectivity.values():
        unique = [e for e in elements if e in adjacency]
        for i, a in enumerate(unique):
            for b in unique[i + 1 :]:
                adjacency[a].add(b)
                adjacency[b].add(a)

    seen: Set[str] = set()
    components: List[Dict[str, Any]] = []
    for root in sorted(adjacency):
        if root in seen:
            continue

        stack = [root]
        seen.add(root)
        element_ids: List[str] = []
        node_ids: Set[str] = set()

        while stack:
            current = stack.pop()
            element_ids.append(current)
            node_ids.update(
                x for x in element_nodes.get(current, set()) if x
            )
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)

        anchors = sorted(node_ids & supported_nodes)
        components.append(
            {
                "element_ids": sorted(element_ids),
                "node_ids": sorted(node_ids),
                "support_node_ids": anchors,
                "anchored": bool(anchors),
            }
        )

    return components


def repair_structural_topology_for_solver(
    *,
    project_id: str,
    analytical_model: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    policy = dict(policy or {})
    model: Dict[str, Any] = deepcopy(dict(analytical_model))

    coordinate_tolerance = float(
        policy.get("coordinate_tolerance_m", 1e-6)
    )
    interface_tolerance = float(
        policy.get("geometric_interface_detection_tolerance_m", 1e-6)
    )
    foundation_tolerance = float(
        policy.get("foundation_plane_tolerance_m", 1e-6)
    )

    initial = {
        "node_count": len(model.get("nodes", []) or []),
        "member_count": len(model.get("members", []) or []),
        "shell_count": len(model.get("shells", []) or []),
        "support_count": len(
            model.get("supports", [])
            or model.get("support_candidates", [])
            or []
        ),
    }

    node_merge = _coalesce_nodes(model, coordinate_tolerance)
    support_repair = _filter_provisional_supports(
        model, foundation_tolerance
    )
    connectivity = _rebuild_connectivity(model)
    nodes = _node_map(model)

    active_supports = [
        s
        for s in (
            model.get("supports")
            or model.get("support_candidates")
            or []
        )
        if isinstance(s, Mapping)
    ]
    supported_nodes = {
        str(s.get("node_id") or "")
        for s in active_supports
        if s.get("node_id")
    }

    unresolved_endpoints: List[Dict[str, Any]] = []

    for member in model.get("members", []) or []:
        if not isinstance(member, Mapping):
            continue
        mid = str(member.get("id") or "")

        for end_name, key in (("I", "node_i"), ("J", "node_j")):
            nid = str(member.get(key) or "")

            if not nid or nid not in nodes:
                unresolved_endpoints.append(
                    {
                        "member_id": mid,
                        "member_type": str(member.get("type") or ""),
                        "end": end_name,
                        "node_id": nid,
                        "reason": "MEMBER_ENDPOINT_NODE_MISSING",
                        "candidate_member_intersections": [],
                        "candidate_shell_edge_interfaces": [],
                    }
                )
                continue

            degree = len(connectivity.get(nid, []))
            if degree >= 2 or nid in supported_nodes:
                continue

            point = _xyz(nodes[nid])
            member_candidates = _member_segment_candidates(
                mid,
                nid,
                point,
                model,
                nodes,
                interface_tolerance,
            )
            shell_candidates = _shell_edge_candidates(
                nid,
                point,
                model,
                nodes,
                interface_tolerance,
            )

            reason = "STRUCTURAL_MEMBER_ENDPOINT_FLOATING"
            if member_candidates:
                reason = "UNMESHED_MEMBER_INTERSECTION"
            elif shell_candidates:
                reason = "UNMESHED_SHELL_EDGE_INTERFACE"

            unresolved_endpoints.append(
                {
                    "member_id": mid,
                    "member_type": str(member.get("type") or ""),
                    "end": end_name,
                    "node_id": nid,
                    "coordinate_m": {
                        "x": point[0],
                        "y": point[1],
                        "z": point[2],
                    },
                    "connectivity_degree": degree,
                    "reason": reason,
                    "candidate_member_intersections": member_candidates,
                    "candidate_shell_edge_interfaces": shell_candidates,
                }
            )

    components = _element_components(
        model, connectivity, supported_nodes
    )
    unanchored_components = [
        component
        for component in components
        if not component["anchored"]
    ]

    blockers: List[Dict[str, Any]] = []

    if not active_supports:
        blockers.append(
            {
                "reason": "STRUCTURAL_FOUNDATION_SUPPORT_PLANE_REQUIRED",
                "message": (
                    "Geen solver-supports resteren op een aantoonbare "
                    "funderings-/basislaag."
                ),
            }
        )

    if unresolved_endpoints:
        blockers.append(
            {
                "reason": "STRUCTURAL_LOAD_PATH_UNRESOLVED",
                "message": (
                    "Een of meer analytische member-eindpunten hebben geen "
                    "gedeelde structurele knoop of support. Phoenix maakt "
                    "geen fictieve koppeling om de solver te laten convergeren."
                ),
                "unresolved_endpoint_count": len(unresolved_endpoints),
                "examples": unresolved_endpoints[:50],
            }
        )

    if unanchored_components:
        blockers.append(
            {
                "reason": "STRUCTURAL_UNANCHORED_COMPONENTS",
                "message": (
                    "Een of meer analytische elementcomponenten hebben "
                    "geen load path naar een support."
                ),
                "unanchored_component_count": len(unanchored_components),
                "examples": unanchored_components[:20],
            }
        )

    final = {
        "node_count": len(model.get("nodes", []) or []),
        "member_count": len(model.get("members", []) or []),
        "shell_count": len(model.get("shells", []) or []),
        "support_count": len(active_supports),
        "connected_component_count": len(components),
        "unanchored_component_count": len(unanchored_components),
        "unresolved_member_endpoint_count": len(unresolved_endpoints),
    }

    status = "PASSED" if not blockers else "BLOCKED"

    register = {
        "schema_version": SCHEMA_VERSION,
        "engine": ENGINE_ID,
        "project_id": project_id,
        "status": status,
        "policy": {
            "coordinate_tolerance_m": coordinate_tolerance,
            "geometric_interface_detection_tolerance_m": interface_tolerance,
            "foundation_plane_tolerance_m": foundation_tolerance,
            "automatic_new_support_generation": False,
            "automatic_new_column_generation": False,
            "automatic_new_member_generation": False,
            "automatic_member_endpoint_relocation": False,
            "automatic_shell_mesh_rewrite": False,
            "automatic_solver_constraint_invention": False,
        },
        "initial_model_summary": initial,
        "node_coalescing": node_merge,
        "support_repair": support_repair,
        "unresolved_member_endpoints": unresolved_endpoints,
        "components": components,
        "final_model_summary": final,
        "blockers": blockers,
        "safety": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "engineering_review_required": True,
            "for_construction_release": LOCKED_RELEASE,
            "production_release": LOCKED_RELEASE,
        },
    }

    model["model_state"] = (
        "R8_1_TOPOLOGY_VALIDATED_CANDIDATE"
        if status == "PASSED"
        else "R8_1_TOPOLOGY_BLOCKED_CANDIDATE"
    )
    model["r8_1_topology_support_repair"] = {
        "status": status,
        "engine": ENGINE_ID,
        "foundation_elevation_m": support_repair.get(
            "foundation_elevation_m"
        ),
        "removed_provisional_support_count": len(
            support_repair.get("removed_provisional_support_ids") or []
        ),
        "unresolved_member_endpoint_count": len(unresolved_endpoints),
        "unanchored_component_count": len(unanchored_components),
        "automatic_structural_approval": False,
        "production_release": LOCKED_RELEASE,
    }

    return {
        "status": status,
        "analytical_model": model,
        "register": register,
        "blockers": blockers,
    }
