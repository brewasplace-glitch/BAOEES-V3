"""Project Phoenix R8.2 geometry-grounded structural interface meshing.

This engine repairs only interfaces for which the existing analytical geometry
already provides direct evidence:
- a member endpoint lying on an existing member segment;
- a member endpoint lying on an existing shell edge;
- a member endpoint lying inside an explicitly allowed coplanar shell face.

The engine may split existing members and shell elements at those already-known
nodes. It never creates supports, columns, rigid links, MPCs, springs, ties, or
solver constraints, and never relocates a structural endpoint.
"""
from __future__ import annotations

from copy import deepcopy
from math import sqrt
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-AUTONOMOUS-STRUCTURAL-INTERFACE-MESHING-R8.2"
SCHEMA_VERSION = "phoenix.autonomous-structural-interface-meshing/1.0"
LOCKED_RELEASE = "LOCKED"
Point = Tuple[float, float, float]
Triangle = Tuple[str, str, str]


class StructuralInterfaceMeshingBlocked(RuntimeError):
    def __init__(self, reason: str, message: str, evidence: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.evidence = dict(evidence or {})


def _xyz(node: Mapping[str, Any]) -> Point:
    return (float(node.get("x", 0.0)), float(node.get("y", 0.0)), float(node.get("z", 0.0)))


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Point) -> float:
    return sqrt(_dot(a, a))


def _distance(a: Point, b: Point) -> float:
    return _norm(_sub(a, b))


def _point_on_segment(point: Point, a: Point, b: Point, tolerance: float) -> bool:
    ab = _sub(b, a)
    ap = _sub(point, a)
    denominator = _dot(ab, ab)
    if denominator <= tolerance * tolerance:
        return _distance(point, a) <= tolerance
    t = _dot(ap, ab) / denominator
    if t < -tolerance or t > 1.0 + tolerance:
        return False
    projection = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
    return _distance(point, projection) <= tolerance


def _segment_parameter(point: Point, a: Point, b: Point) -> float:
    ab = _sub(b, a)
    denominator = _dot(ab, ab)
    if denominator <= 0.0:
        return 0.0
    return _dot(_sub(point, a), ab) / denominator


def _point_in_triangle_3d(
    point: Point,
    a: Point,
    b: Point,
    c: Point,
    tolerance: float,
    include_boundary: bool = True,
) -> bool:
    v0 = _sub(b, a)
    v1 = _sub(c, a)
    normal = _cross(v0, v1)
    normal_norm = _norm(normal)
    if normal_norm <= tolerance:
        return False
    plane_distance = abs(_dot(_sub(point, a), normal)) / normal_norm
    if plane_distance > tolerance:
        return False

    v2 = _sub(point, a)
    d00 = _dot(v0, v0)
    d01 = _dot(v0, v1)
    d11 = _dot(v1, v1)
    d20 = _dot(v2, v0)
    d21 = _dot(v2, v1)
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) <= tolerance * tolerance:
        return False
    v = (d11 * d20 - d01 * d21) / denominator
    w = (d00 * d21 - d01 * d20) / denominator
    u = 1.0 - v - w
    eps = max(tolerance, 1e-10)
    if include_boundary:
        return u >= -eps and v >= -eps and w >= -eps
    return u > eps and v > eps and w > eps


def _fan_triangles(node_ids: Sequence[str]) -> List[Triangle]:
    if len(node_ids) < 3:
        return []
    anchor = str(node_ids[0])
    return [(anchor, str(node_ids[i]), str(node_ids[i + 1])) for i in range(1, len(node_ids) - 1)]


def _triangle_area(triangle: Triangle, nodes: Mapping[str, Mapping[str, Any]]) -> float:
    a, b, c = (_xyz(nodes[nid]) for nid in triangle)
    return 0.5 * _norm(_cross(_sub(b, a), _sub(c, a)))


def _insert_node_into_triangles(
    triangles: List[Triangle],
    node_id: str,
    nodes: Mapping[str, Mapping[str, Any]],
    tolerance: float,
) -> Tuple[List[Triangle], str]:
    if any(node_id in triangle for triangle in triangles):
        return triangles, "ALREADY_MESH_VERTEX"

    point = _xyz(nodes[node_id])
    edge_hits: List[Tuple[int, int]] = []
    for index, tri in enumerate(triangles):
        pairs = ((0, 1), (1, 2), (2, 0))
        for edge_index, (i, j) in enumerate(pairs):
            if _point_on_segment(point, _xyz(nodes[tri[i]]), _xyz(nodes[tri[j]]), tolerance):
                if _distance(point, _xyz(nodes[tri[i]])) <= tolerance or _distance(point, _xyz(nodes[tri[j]])) <= tolerance:
                    continue
                edge_hits.append((index, edge_index))
                break

    if edge_hits:
        hit_by_triangle = {index: edge_index for index, edge_index in edge_hits}
        rebuilt: List[Triangle] = []
        for index, tri in enumerate(triangles):
            if index not in hit_by_triangle:
                rebuilt.append(tri)
                continue
            edge_index = hit_by_triangle[index]
            if edge_index == 0:
                u, v, opposite = tri[0], tri[1], tri[2]
            elif edge_index == 1:
                u, v, opposite = tri[1], tri[2], tri[0]
            else:
                u, v, opposite = tri[2], tri[0], tri[1]
            rebuilt.extend([(u, node_id, opposite), (node_id, v, opposite)])
        return rebuilt, "SHELL_EDGE_SPLIT"

    for index, tri in enumerate(triangles):
        a, b, c = (_xyz(nodes[nid]) for nid in tri)
        if _point_in_triangle_3d(point, a, b, c, tolerance, include_boundary=False):
            rebuilt = list(triangles[:index])
            rebuilt.extend(
                [
                    (tri[0], tri[1], node_id),
                    (tri[1], tri[2], node_id),
                    (tri[2], tri[0], node_id),
                ]
            )
            rebuilt.extend(triangles[index + 1 :])
            return rebuilt, "SHELL_FACE_SPLIT"

    return triangles, "NOT_ON_OR_IN_SHELL"


def _next_numeric_id(existing: Iterable[str], prefix: str) -> int:
    maximum = 0
    for raw in existing:
        token = str(raw)
        if token.startswith(prefix) and token[len(prefix) :].isdigit():
            maximum = max(maximum, int(token[len(prefix) :]))
    return maximum + 1


def _node_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(n["id"]): dict(n)
        for n in (model.get("nodes") or [])
        if isinstance(n, Mapping) and n.get("id")
    }


def _member_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(m["id"]): dict(m)
        for m in (model.get("members") or [])
        if isinstance(m, Mapping) and m.get("id")
    }


def _shell_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(s["id"]): dict(s)
        for s in (model.get("shells") or [])
        if isinstance(s, Mapping) and s.get("id")
    }


def _shell_edge_hits(
    point_node_id: str,
    shell: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    tolerance: float,
) -> bool:
    ids = [str(x) for x in (shell.get("node_ids") or [])]
    if len(ids) < 3 or point_node_id in ids or any(nid not in nodes for nid in ids):
        return False
    p = _xyz(nodes[point_node_id])
    for index, a_id in enumerate(ids):
        b_id = ids[(index + 1) % len(ids)]
        if _point_on_segment(p, _xyz(nodes[a_id]), _xyz(nodes[b_id]), tolerance):
            return True
    return False


def _shell_face_hit(
    point_node_id: str,
    shell: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    tolerance: float,
) -> bool:
    ids = [str(x) for x in (shell.get("node_ids") or [])]
    if len(ids) < 3 or point_node_id in ids or any(nid not in nodes for nid in ids):
        return False
    p = _xyz(nodes[point_node_id])
    for tri in _fan_triangles(ids):
        a, b, c = (_xyz(nodes[nid]) for nid in tri)
        if _point_in_triangle_3d(p, a, b, c, tolerance, include_boundary=True):
            return True
    return False


def _split_members(
    model: MutableMapping[str, Any],
    split_requests: Mapping[str, Set[str]],
    tolerance: float,
) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    nodes = _node_map(model)
    members = [dict(m) for m in (model.get("members") or []) if isinstance(m, Mapping)]
    existing_ids = [str(m.get("id") or "") for m in members]
    next_id = _next_numeric_id(existing_ids, "M")
    parent_to_children: Dict[str, List[str]] = {}
    evidence: List[Dict[str, Any]] = []
    rebuilt: List[Dict[str, Any]] = []

    for member in members:
        parent_id = str(member.get("id") or "")
        requested = sorted(split_requests.get(parent_id) or set())
        if not requested:
            rebuilt.append(member)
            continue
        ni, nj = str(member.get("node_i") or ""), str(member.get("node_j") or "")
        if ni not in nodes or nj not in nodes:
            raise StructuralInterfaceMeshingBlocked(
                "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                f"Member {parent_id} mist geldige eindknopen voor een geometrisch bewezen split.",
                {"member_id": parent_id},
            )
        a, b = _xyz(nodes[ni]), _xyz(nodes[nj])
        split_nodes: List[Tuple[float, str]] = []
        for node_id in requested:
            if node_id not in nodes or not _point_on_segment(_xyz(nodes[node_id]), a, b, tolerance):
                raise StructuralInterfaceMeshingBlocked(
                    "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                    f"Node {node_id} ligt niet aantoonbaar op member {parent_id}.",
                    {"member_id": parent_id, "node_id": node_id},
                )
            t = _segment_parameter(_xyz(nodes[node_id]), a, b)
            if t <= tolerance or t >= 1.0 - tolerance:
                continue
            split_nodes.append((t, node_id))
        split_nodes = sorted(set(split_nodes))
        chain = [ni] + [nid for _, nid in split_nodes] + [nj]
        if len(chain) <= 2:
            rebuilt.append(member)
            continue
        children: List[str] = []
        for index in range(len(chain) - 1):
            child = deepcopy(member)
            if index == 0:
                child_id = parent_id
            else:
                child_id = f"M{next_id:04d}"
                next_id += 1
            child["id"] = child_id
            child["node_i"] = chain[index]
            child["node_j"] = chain[index + 1]
            child["r8_2_parent_member_id"] = parent_id
            child["r8_2_geometry_grounded_split"] = True
            rebuilt.append(child)
            children.append(child_id)
        parent_to_children[parent_id] = children
        evidence.append(
            {
                "parent_member_id": parent_id,
                "split_node_ids": [nid for _, nid in split_nodes],
                "child_member_ids": children,
                "basis": "EXISTING_ENDPOINT_ON_EXISTING_MEMBER_SEGMENT",
            }
        )

    model["members"] = rebuilt
    return parent_to_children, evidence


def _mesh_shells(
    model: MutableMapping[str, Any],
    shell_insertions: Mapping[str, Set[str]],
    tolerance: float,
) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    nodes = _node_map(model)
    shells = [dict(s) for s in (model.get("shells") or []) if isinstance(s, Mapping)]
    existing_ids = [str(s.get("id") or "") for s in shells]
    next_id = _next_numeric_id(existing_ids, "S")
    parent_to_children: Dict[str, List[str]] = {}
    evidence: List[Dict[str, Any]] = []
    rebuilt: List[Dict[str, Any]] = []

    for shell in shells:
        parent_id = str(shell.get("id") or "")
        insertions = sorted(shell_insertions.get(parent_id) or set())
        if not insertions:
            rebuilt.append(shell)
            continue
        original_ids = [str(x) for x in (shell.get("node_ids") or [])]
        if len(original_ids) < 3 or any(nid not in nodes for nid in original_ids):
            raise StructuralInterfaceMeshingBlocked(
                "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                f"Shell {parent_id} heeft geen geldige polygonale meshbasis.",
                {"shell_id": parent_id},
            )
        triangles = _fan_triangles(original_ids)
        insertion_evidence: List[Dict[str, str]] = []
        original_area = sum(_triangle_area(tri, nodes) for tri in triangles)
        for node_id in insertions:
            if node_id not in nodes:
                raise StructuralInterfaceMeshingBlocked(
                    "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                    f"Interface-node {node_id} ontbreekt in de analytische node-set.",
                    {"shell_id": parent_id, "node_id": node_id},
                )
            triangles, mode = _insert_node_into_triangles(triangles, node_id, nodes, tolerance)
            if mode == "NOT_ON_OR_IN_SHELL":
                raise StructuralInterfaceMeshingBlocked(
                    "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                    f"Node {node_id} ligt niet aantoonbaar op/in shell {parent_id}.",
                    {"shell_id": parent_id, "node_id": node_id},
                )
            insertion_evidence.append({"node_id": node_id, "meshing_mode": mode})
        new_area = sum(_triangle_area(tri, nodes) for tri in triangles)
        area_tolerance = max(1e-9, original_area * 1e-9)
        if abs(new_area - original_area) > area_tolerance:
            raise StructuralInterfaceMeshingBlocked(
                "STRUCTURAL_INTERFACE_MESH_AREA_CONSERVATION_FAILED",
                f"Triangulatie van shell {parent_id} conserveert het oppervlak niet.",
                {"shell_id": parent_id, "original_area_m2": original_area, "new_area_m2": new_area},
            )
        children: List[str] = []
        for index, triangle in enumerate(triangles):
            child = deepcopy(shell)
            if index == 0:
                child_id = parent_id
            else:
                child_id = f"S{next_id:04d}"
                next_id += 1
            child["id"] = child_id
            child["node_ids"] = list(triangle)
            child["r8_2_parent_shell_id"] = parent_id
            child["r8_2_geometry_grounded_mesh"] = True
            rebuilt.append(child)
            children.append(child_id)
        parent_to_children[parent_id] = children
        evidence.append(
            {
                "parent_shell_id": parent_id,
                "insertions": insertion_evidence,
                "child_shell_ids": children,
                "original_area_m2": original_area,
                "meshed_area_m2": new_area,
                "basis": "EXISTING_ENDPOINT_ON_OR_IN_EXISTING_SHELL",
            }
        )

    model["shells"] = rebuilt
    return parent_to_children, evidence


def _remap_action_model(
    action_load_model: Mapping[str, Any],
    element_children: Mapping[str, List[str]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    action_model: Dict[str, Any] = deepcopy(dict(action_load_model))
    assignments = [dict(a) for a in (action_model.get("action_assignments") or []) if isinstance(a, Mapping)]
    remapped: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    distributed_kinds = {"self_weight", "line", "area"}

    for index, action in enumerate(assignments, 1):
        action_id = str(action.get("id") or f"ACTION-{index:04d}")
        kind = str(action.get("kind") or "").lower()
        list_targets = action.get("target_element_ids")
        scalar_target = action.get("target_element_id")

        if isinstance(list_targets, list):
            touched = [str(x) for x in list_targets if str(x) in element_children]
            if not touched:
                remapped.append(action)
                continue
            if kind not in distributed_kinds:
                raise StructuralInterfaceMeshingBlocked(
                    "STRUCTURAL_REPAIR_ACTION_REMAP_REQUIRED",
                    f"Actietype {kind!r} op gesplitste elementen kan niet veilig automatisch worden herverdeeld.",
                    {"action_id": action_id, "kind": kind, "target_element_ids": touched},
                )
            expanded: List[str] = []
            for raw in list_targets:
                target = str(raw)
                expanded.extend(element_children.get(target, [target]))
            clone = deepcopy(action)
            clone["target_element_ids"] = list(dict.fromkeys(expanded))
            remapped.append(clone)
            evidence.append(
                {
                    "action_id": action_id,
                    "kind": kind,
                    "mode": "TARGET_LIST_EXPANDED",
                    "split_parent_ids": touched,
                    "target_element_ids_after": clone["target_element_ids"],
                }
            )
            continue

        if scalar_target is not None and str(scalar_target) in element_children:
            parent = str(scalar_target)
            children = element_children[parent]
            if kind not in distributed_kinds:
                raise StructuralInterfaceMeshingBlocked(
                    "STRUCTURAL_REPAIR_ACTION_REMAP_REQUIRED",
                    f"Actietype {kind!r} op gesplitst element {parent} kan niet veilig automatisch worden herverdeeld.",
                    {"action_id": action_id, "kind": kind, "target_element_id": parent},
                )
            if kind == "self_weight":
                clone = deepcopy(action)
                clone.pop("target_element_id", None)
                clone["target_element_ids"] = children
                remapped.append(clone)
            else:
                for child_index, child_id in enumerate(children, 1):
                    clone = deepcopy(action)
                    clone["id"] = f"{action_id}-R82-{child_index:02d}"
                    clone["target_element_id"] = child_id
                    remapped.append(clone)
            evidence.append(
                {
                    "action_id": action_id,
                    "kind": kind,
                    "mode": "DISTRIBUTED_ACTION_CLONED_TO_CHILDREN",
                    "split_parent_id": parent,
                    "child_element_ids": children,
                    "per_unit_magnitude_preserved": True,
                }
            )
            continue

        remapped.append(action)

    action_model["action_assignments"] = remapped
    action_model["r8_2_element_split_remap"] = {
        "engine": ENGINE_ID,
        "distributed_action_kinds_supported": sorted(distributed_kinds),
        "action_assignment_count_before": len(assignments),
        "action_assignment_count_after": len(remapped),
        "evidence": evidence,
        "unknown_element_target_action_policy": "FAIL_CLOSED",
    }
    return action_model, evidence


def repair_geometry_grounded_interfaces(
    *,
    project_id: str,
    analytical_model: Mapping[str, Any],
    action_load_model: Mapping[str, Any],
    r8_1_register: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    policy = dict(policy or {})
    model: Dict[str, Any] = deepcopy(dict(analytical_model))
    tolerance = float(policy.get("geometry_tolerance_m", 1e-6))
    allowed_face_types = {
        str(x).lower()
        for x in (policy.get("interior_face_allowed_shell_types") or ["slab_panel"])
    }
    require_unique_face = bool(policy.get("require_unique_interior_shell_face", True))

    unresolved = [
        dict(x)
        for x in (r8_1_register.get("unresolved_member_endpoints") or [])
        if isinstance(x, Mapping)
    ]
    if not unresolved:
        return {
            "status": "PASSED",
            "analytical_model": model,
            "action_load_model": deepcopy(dict(action_load_model)),
            "register": {
                "schema_version": SCHEMA_VERSION,
                "engine": ENGINE_ID,
                "project_id": project_id,
                "status": "PASSED",
                "message": "R8.1 rapporteerde geen onopgeloste interfaces; geen R8.2 meshwijziging nodig.",
                "member_parent_to_children": {},
                "shell_parent_to_children": {},
                "blockers": [],
                "safety": _safety(),
            },
            "blockers": [],
        }

    nodes = _node_map(model)
    members = _member_map(model)
    shells = _shell_map(model)
    member_split_requests: Dict[str, Set[str]] = {}
    shell_insertions: Dict[str, Set[str]] = {}
    classified: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []

    for item in unresolved:
        member_id = str(item.get("member_id") or "")
        node_id = str(item.get("node_id") or "")
        reason = str(item.get("reason") or "")
        if member_id not in members or node_id not in nodes:
            blockers.append(
                {
                    "reason": "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                    "message": "R8.1-interface verwijst naar ontbrekend member of node.",
                    "member_id": member_id,
                    "node_id": node_id,
                }
            )
            continue

        if reason == "UNMESHED_MEMBER_INTERSECTION":
            candidate_ids = [str(x) for x in (item.get("candidate_member_intersections") or [])]
            verified: List[str] = []
            point = _xyz(nodes[node_id])
            for candidate_id in candidate_ids:
                other = members.get(candidate_id)
                if not other:
                    continue
                ni, nj = str(other.get("node_i") or ""), str(other.get("node_j") or "")
                if ni in nodes and nj in nodes and _point_on_segment(point, _xyz(nodes[ni]), _xyz(nodes[nj]), tolerance):
                    member_split_requests.setdefault(candidate_id, set()).add(node_id)
                    verified.append(candidate_id)
            if not verified:
                blockers.append(
                    {
                        "reason": "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                        "message": f"Member-interface {member_id}/{node_id} kon niet opnieuw geometrisch worden bewezen.",
                        "member_id": member_id,
                        "node_id": node_id,
                    }
                )
            else:
                classified.append(
                    {
                        "member_id": member_id,
                        "node_id": node_id,
                        "classification": "MEMBER_SEGMENT_INTERSECTION",
                        "target_member_ids": verified,
                    }
                )
            continue

        if reason == "UNMESHED_SHELL_EDGE_INTERFACE":
            candidate_ids = [str(x) for x in (item.get("candidate_shell_edge_interfaces") or [])]
            verified = [sid for sid in candidate_ids if sid in shells and _shell_edge_hits(node_id, shells[sid], nodes, tolerance)]
            if not verified:
                blockers.append(
                    {
                        "reason": "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                        "message": f"Shell-edge-interface {member_id}/{node_id} kon niet opnieuw geometrisch worden bewezen.",
                        "member_id": member_id,
                        "node_id": node_id,
                    }
                )
            else:
                for sid in verified:
                    shell_insertions.setdefault(sid, set()).add(node_id)
                classified.append(
                    {
                        "member_id": member_id,
                        "node_id": node_id,
                        "classification": "SHELL_EDGE_INTERFACE",
                        "target_shell_ids": verified,
                    }
                )
            continue

        if reason == "STRUCTURAL_MEMBER_ENDPOINT_FLOATING":
            face_hits: List[str] = []
            for sid, shell in shells.items():
                shell_type = str(shell.get("type") or "").lower()
                if shell_type not in allowed_face_types:
                    continue
                if _shell_face_hit(node_id, shell, nodes, tolerance):
                    face_hits.append(sid)
            if not face_hits:
                blockers.append(
                    {
                        "reason": "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                        "message": f"Floating endpoint {member_id}/{node_id} ligt niet aantoonbaar in een toegestane bestaande shell-face.",
                        "member_id": member_id,
                        "node_id": node_id,
                    }
                )
                continue
            if require_unique_face and len(face_hits) != 1:
                blockers.append(
                    {
                        "reason": "STRUCTURAL_INTERFACE_GEOMETRY_AMBIGUOUS",
                        "message": f"Floating endpoint {member_id}/{node_id} ligt in meerdere shell-faces; automatische keuze is geblokkeerd.",
                        "member_id": member_id,
                        "node_id": node_id,
                        "candidate_shell_ids": sorted(face_hits),
                    }
                )
                continue
            targets = sorted(face_hits)
            for sid in targets:
                shell_insertions.setdefault(sid, set()).add(node_id)
            classified.append(
                {
                    "member_id": member_id,
                    "node_id": node_id,
                    "classification": "SHELL_FACE_INTERFACE",
                    "target_shell_ids": targets,
                }
            )
            continue

        blockers.append(
            {
                "reason": "STRUCTURAL_INTERFACE_REASON_NOT_AUTOMATABLE",
                "message": f"R8.2 automatiseert reason {reason!r} niet.",
                "member_id": member_id,
                "node_id": node_id,
            }
        )

    if blockers:
        register = _register(
            project_id=project_id,
            status="BLOCKED",
            classified=classified,
            member_map={},
            shell_map={},
            member_evidence=[],
            shell_evidence=[],
            action_evidence=[],
            blockers=blockers,
            initial_model=model,
            final_model=model,
            policy=policy,
        )
        return {"status": "BLOCKED", "analytical_model": model, "action_load_model": deepcopy(dict(action_load_model)), "register": register, "blockers": blockers}

    member_parent_to_children, member_evidence = _split_members(model, member_split_requests, tolerance)
    shell_parent_to_children, shell_evidence = _mesh_shells(model, shell_insertions, tolerance)
    element_children = {**member_parent_to_children, **shell_parent_to_children}
    try:
        remapped_actions, action_evidence = _remap_action_model(action_load_model, element_children)
    except StructuralInterfaceMeshingBlocked as exc:
        blockers = [{"reason": exc.reason, "message": exc.message, **exc.evidence}]
        register = _register(
            project_id=project_id,
            status="BLOCKED",
            classified=classified,
            member_map=member_parent_to_children,
            shell_map=shell_parent_to_children,
            member_evidence=member_evidence,
            shell_evidence=shell_evidence,
            action_evidence=[],
            blockers=blockers,
            initial_model=analytical_model,
            final_model=model,
            policy=policy,
        )
        return {"status": "BLOCKED", "analytical_model": model, "action_load_model": deepcopy(dict(action_load_model)), "register": register, "blockers": blockers}

    model["model_state"] = "R8_2_GEOMETRY_GROUNDED_INTERFACE_MESHED_CANDIDATE"
    model["r8_2_structural_interface_meshing"] = {
        "engine": ENGINE_ID,
        "geometry_grounded": True,
        "member_split_parent_count": len(member_parent_to_children),
        "shell_mesh_parent_count": len(shell_parent_to_children),
        "automatic_new_support_generation": False,
        "automatic_new_column_generation": False,
        "automatic_solver_constraint_invention": False,
        "automatic_structural_approval": False,
        "production_release": LOCKED_RELEASE,
    }
    register = _register(
        project_id=project_id,
        status="PASSED",
        classified=classified,
        member_map=member_parent_to_children,
        shell_map=shell_parent_to_children,
        member_evidence=member_evidence,
        shell_evidence=shell_evidence,
        action_evidence=action_evidence,
        blockers=[],
        initial_model=analytical_model,
        final_model=model,
        policy=policy,
    )
    return {"status": "PASSED", "analytical_model": model, "action_load_model": remapped_actions, "register": register, "blockers": []}


def _safety() -> Dict[str, Any]:
    return {
        "automatic_new_support_generation": False,
        "automatic_new_column_generation": False,
        "automatic_new_member_design": False,
        "automatic_solver_constraint_invention": False,
        "automatic_rigid_link_or_tie_generation": False,
        "automatic_code_compliance_claim": False,
        "automatic_structural_approval": False,
        "engineering_review_required": True,
        "for_construction_release": LOCKED_RELEASE,
        "production_release": LOCKED_RELEASE,
    }


def _register(
    *,
    project_id: str,
    status: str,
    classified: Sequence[Mapping[str, Any]],
    member_map: Mapping[str, Sequence[str]],
    shell_map: Mapping[str, Sequence[str]],
    member_evidence: Sequence[Mapping[str, Any]],
    shell_evidence: Sequence[Mapping[str, Any]],
    action_evidence: Sequence[Mapping[str, Any]],
    blockers: Sequence[Mapping[str, Any]],
    initial_model: Mapping[str, Any],
    final_model: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine": ENGINE_ID,
        "project_id": project_id,
        "status": status,
        "policy": {
            "geometry_tolerance_m": float(policy.get("geometry_tolerance_m", 1e-6)),
            "interior_face_allowed_shell_types": list(policy.get("interior_face_allowed_shell_types") or ["slab_panel"]),
            "require_unique_interior_shell_face": bool(policy.get("require_unique_interior_shell_face", True)),
            "member_segment_split": "EXISTING_ENDPOINT_ONLY",
            "shell_edge_insertion": "EXISTING_ENDPOINT_ONLY",
            "shell_face_insertion": "EXISTING_ENDPOINT_ONLY",
            "distributed_action_remap": ["self_weight", "line", "area"],
            "unknown_element_target_action_policy": "FAIL_CLOSED",
        },
        "classified_interfaces": list(classified),
        "member_parent_to_children": {str(k): list(v) for k, v in member_map.items()},
        "shell_parent_to_children": {str(k): list(v) for k, v in shell_map.items()},
        "member_split_evidence": list(member_evidence),
        "shell_meshing_evidence": list(shell_evidence),
        "action_remap_evidence": list(action_evidence),
        "summary": {
            "unresolved_input_interface_count": len(classified) + len(blockers),
            "classified_interface_count": len(classified),
            "member_split_parent_count": len(member_map),
            "shell_mesh_parent_count": len(shell_map),
            "initial_member_count": len(initial_model.get("members", []) or []),
            "final_member_count": len(final_model.get("members", []) or []),
            "initial_shell_count": len(initial_model.get("shells", []) or []),
            "final_shell_count": len(final_model.get("shells", []) or []),
            "blocker_count": len(blockers),
        },
        "blockers": list(blockers),
        "safety": _safety(),
    }
