#!/usr/bin/env python3
"""Project Phoenix Structural Solver Input and Analysis Engine v8.3.0.

Generates OpenSees and CalculiX linear-static base-case decks from explicit
Phoenix analytical and action/load input. Solver execution is gated and disabled
by default. Solver success never implies code compliance or structural approval.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

ENGINE_ID = "PHX-STRUCT-SOLVER-INPUT-ANALYSIS-V8.3.0"
VERSION = "8.3.0"
LOCKED_RELEASE = "LOCKED"
DOFS = ("UX", "UY", "UZ", "RX", "RY", "RZ")
DIRECTION_VECTORS = {
    "X": (1.0, 0.0, 0.0),
    "Y": (0.0, 1.0, 0.0),
    "Z": (0.0, 0.0, 1.0),
    "GLOBAL_X": (1.0, 0.0, 0.0),
    "GLOBAL_Y": (0.0, 1.0, 0.0),
    "GLOBAL_Z": (0.0, 0.0, 1.0),
    "GRAVITY": (0.0, 0.0, -1.0),
}


def _items(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be a non-empty string")
    return result


def _num(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive(value: Any, label: str) -> float:
    result = _num(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be > 0")
    return result


def _node_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = {}
    for idx, raw in enumerate(_items(model.get("nodes")), 1):
        if not isinstance(raw, dict):
            raise ValueError("analytical_model.nodes entries must be objects")
        node_id = _text(raw.get("id"), f"node[{idx}].id")
        if node_id in nodes:
            raise ValueError(f"Duplicate node id: {node_id}")
        nodes[node_id] = {
            "id": node_id,
            "x": _num(raw.get("x"), f"node {node_id} x"),
            "y": _num(raw.get("y"), f"node {node_id} y"),
            "z": _num(raw.get("z"), f"node {node_id} z"),
        }
    if not nodes:
        raise ValueError("At least one analytical node is required")
    return nodes


def _element_maps(model: Mapping[str, Any], nodes: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    members: Dict[str, Dict[str, Any]] = {}
    shells: Dict[str, Dict[str, Any]] = {}
    for idx, raw in enumerate(_items(model.get("members")), 1):
        if not isinstance(raw, dict):
            raise ValueError("analytical_model.members entries must be objects")
        element_id = _text(raw.get("id"), f"member[{idx}].id")
        if element_id in members:
            raise ValueError(f"Duplicate member id: {element_id}")
        ni = _text(raw.get("node_i"), f"member {element_id} node_i")
        nj = _text(raw.get("node_j"), f"member {element_id} node_j")
        if ni not in nodes or nj not in nodes:
            raise ValueError(f"Member {element_id} references an unknown node")
        if ni == nj:
            raise ValueError(f"Member {element_id} has zero topology length")
        members[element_id] = {
            **deepcopy(raw),
            "id": element_id,
            "node_i": ni,
            "node_j": nj,
            "material_id": _text(raw.get("material_id"), f"member {element_id} material_id"),
            "section_id": _text(raw.get("section_id"), f"member {element_id} section_id"),
        }
    # PHOENIX_R8_2_TRIANGULAR_SHELL_SOLVER_SUPPORT_V1_0
    for idx, raw in enumerate(_items(model.get("shells")), 1):
        if not isinstance(raw, dict):
            raise ValueError("analytical_model.shells entries must be objects")
        element_id = _text(raw.get("id"), f"shell[{idx}].id")
        if element_id in shells or element_id in members:
            raise ValueError(f"Duplicate analytical element id: {element_id}")
        node_ids = [_text(v, f"shell {element_id} node id") for v in _items(raw.get("node_ids"))]
        if len(node_ids) not in (3, 4):
            raise ValueError(f"Shell {element_id} must have 3 or 4 nodes")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError(f"Shell {element_id} has duplicate node ids")
        for node_id in node_ids:
            if node_id not in nodes:
                raise ValueError(f"Shell {element_id} references unknown node {node_id}")
        shells[element_id] = {
            **deepcopy(raw),
            "id": element_id,
            "node_ids": node_ids,
            "material_id": _text(raw.get("material_id"), f"shell {element_id} material_id"),
            "section_id": _text(raw.get("section_id"), f"shell {element_id} section_id"),
        }
    if not members and not shells:
        raise ValueError("At least one member or shell is required")
    return members, shells


def _distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 + (a["z"] - b["z"]) ** 2)


def _cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(v: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) ** 2 for x in v))


def _polygon_area(node_ids: Sequence[str], nodes: Mapping[str, Mapping[str, float]]) -> float:
    p0 = nodes[node_ids[0]]
    total = 0.0
    for i in range(1, len(node_ids) - 1):
        p1, p2 = nodes[node_ids[i]], nodes[node_ids[i + 1]]
        v1 = (p1["x"] - p0["x"], p1["y"] - p0["y"], p1["z"] - p0["z"])
        v2 = (p2["x"] - p0["x"], p2["y"] - p0["y"], p2["z"] - p0["z"])
        total += 0.5 * _norm(_cross(v1, v2))
    if total <= 0:
        raise ValueError("Shell polygon area must be > 0")
    return total


def _section_properties(section_id: str, raw: Mapping[str, Any]) -> Dict[str, float]:
    kind = _text(raw.get("type"), f"section {section_id} type").lower()
    if kind == "rectangular_beam":
        b = _positive(raw.get("width_m"), f"section {section_id} width_m")
        h = _positive(raw.get("height_m"), f"section {section_id} height_m")
        area = b * h
        iy = b * h ** 3 / 12.0
        iz = h * b ** 3 / 12.0
        # Saint-Venant approximation for a solid rectangle; derived only from explicit geometry.
        long_side = max(b, h)
        short_side = min(b, h)
        ratio = short_side / long_side
        j = long_side * short_side ** 3 * (1.0 / 3.0 - 0.21 * ratio * (1.0 - ratio ** 4 / 12.0))
        return {"type": kind, "width_m": b, "height_m": h, "area_m2": area, "iy_m4": iy, "iz_m4": iz, "j_m4": j}
    if kind == "shell":
        thickness = _positive(raw.get("thickness_m"), f"section {section_id} thickness_m")
        return {"type": kind, "thickness_m": thickness}
    raise ValueError(f"Unsupported section type for {section_id}: {kind}")


def _material_map(basis: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    raw_materials = basis.get("materials") or {}
    if not isinstance(raw_materials, dict) or not raw_materials:
        raise ValueError("solver_basis.materials must be a non-empty object")
    for material_id, raw in raw_materials.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Material {material_id} must be an object")
        e = _positive(raw.get("elastic_modulus_kN_m2"), f"material {material_id} elastic_modulus_kN_m2")
        nu = _num(raw.get("poisson_ratio"), f"material {material_id} poisson_ratio")
        if not (-1.0 < nu < 0.5):
            raise ValueError(f"material {material_id} poisson_ratio outside elastic range")
        density = _positive(raw.get("density_kg_m3"), f"material {material_id} density_kg_m3")
        g = e / (2.0 * (1.0 + nu))
        result[str(material_id)] = {"E": e, "nu": nu, "density": density, "G": g}
    return result


def _section_map(basis: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    raw_sections = basis.get("sections") or {}
    if not isinstance(raw_sections, dict) or not raw_sections:
        raise ValueError("solver_basis.sections must be a non-empty object")
    return {str(k): _section_properties(str(k), v) for k, v in raw_sections.items()}


def _vector(direction: Any, magnitude: float) -> Tuple[float, float, float]:
    key = _text(direction, "action direction").upper()
    if key not in DIRECTION_VECTORS:
        raise ValueError(f"Unsupported action direction: {key}")
    unit = DIRECTION_VECTORS[key]
    return tuple(magnitude * c for c in unit)


def _add_vector(store: MutableMapping[str, List[float]], node_id: str, vector: Sequence[float]) -> None:
    current = store.setdefault(node_id, [0.0, 0.0, 0.0])
    for i in range(3):
        current[i] += float(vector[i])


def _equivalent_nodal_loads(payload: Mapping[str, Any], nodes: Mapping[str, Any], members: Mapping[str, Any], shells: Mapping[str, Any], materials: Mapping[str, Any], sections: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, List[float]]], Dict[str, Any], List[str]]:
    action_model = payload.get("action_load_model") or {}
    basis = payload.get("solver_basis") or {}
    gravity = _positive(basis.get("gravity_acceleration_m_s2"), "solver_basis.gravity_acceleration_m_s2")
    cases: Dict[str, Dict[str, List[float]]] = defaultdict(dict)
    trace: Dict[str, Any] = {}
    warnings: List[str] = []
    all_elements = {**members, **shells}

    known_cases = {_text(c.get("id"), "load case id") for c in _items(action_model.get("load_cases")) if isinstance(c, dict)}
    if not known_cases:
        raise ValueError("At least one load case is required")

    for idx, action in enumerate(_items(action_model.get("action_assignments")), 1):
        if not isinstance(action, dict):
            raise ValueError("action_load_model.action_assignments entries must be objects")
        action_id = _text(action.get("id"), f"action assignment[{idx}].id")
        case_id = _text(action.get("case_id"), f"action {action_id} case_id")
        if case_id not in known_cases:
            raise ValueError(f"Action {action_id} references unknown load case {case_id}")
        kind = _text(action.get("kind"), f"action {action_id} kind").lower()
        direction = action.get("direction", "GLOBAL_Z")
        factor = _num(action.get("factor", 1.0), f"action {action_id} factor")
        contributions: List[Dict[str, Any]] = []

        if kind == "nodal":
            magnitude = _num(action.get("magnitude"), f"action {action_id} magnitude") * factor
            target_nodes = [str(v) for v in _items(action.get("target_node_ids") or action.get("target_node_id"))]
            for node_id in target_nodes:
                if node_id not in nodes:
                    warnings.append(f"Action {action_id} references unknown node {node_id}; no fake load created")
                    continue
                vec = _vector(direction, magnitude)
                _add_vector(cases[case_id], node_id, vec)
                contributions.append({"node_id": node_id, "vector_kN": list(vec), "derivation": "DIRECT_NODAL_ACTION"})

        elif kind in {"line", "area"}:
            element_id = _text(action.get("target_element_id"), f"action {action_id} target_element_id")
            magnitude = _num(action.get("magnitude"), f"action {action_id} magnitude") * factor
            if element_id not in all_elements:
                warnings.append(f"Action {action_id} references unknown analytical element {element_id}; no fake load created")
                trace[action_id] = {"case_id": case_id, "kind": kind, "contributions": []}
                continue
            if kind == "line":
                if element_id not in members:
                    raise ValueError(f"Line action {action_id} must target a member")
                m = members[element_id]
                length = _distance(nodes[m["node_i"]], nodes[m["node_j"]])
                total = magnitude * length
                each = _vector(direction, total / 2.0)
                for node_id in (m["node_i"], m["node_j"]):
                    _add_vector(cases[case_id], node_id, each)
                    contributions.append({"node_id": node_id, "vector_kN": list(each), "derivation": "UNIFORM_LINE_TO_END_NODES", "source_element_id": element_id})
            else:
                if element_id not in shells:
                    raise ValueError(f"Area action {action_id} must target a shell")
                s = shells[element_id]
                area = _polygon_area(s["node_ids"], nodes)
                total = magnitude * area
                each = _vector(direction, total / len(s["node_ids"]))
                for node_id in s["node_ids"]:
                    _add_vector(cases[case_id], node_id, each)
                    contributions.append({"node_id": node_id, "vector_kN": list(each), "derivation": "UNIFORM_AREA_TO_CORNER_NODES", "source_element_id": element_id})

        elif kind == "self_weight":
            target_ids = [str(v) for v in _items(action.get("target_element_ids"))]
            if not target_ids:
                target_ids = sorted(all_elements)
            for element_id in target_ids:
                element = all_elements.get(element_id)
                if element is None:
                    warnings.append(f"Self-weight action {action_id} references unknown element {element_id}; no fake load created")
                    continue
                material_id = element["material_id"]
                section_id = element["section_id"]
                if material_id not in materials or section_id not in sections:
                    raise ValueError(f"Self-weight input missing material/section properties for {element_id}")
                density = materials[material_id]["density"]
                section = sections[section_id]
                if element_id in members:
                    if section["type"] != "rectangular_beam":
                        raise ValueError(f"Member {element_id} requires a beam section")
                    length = _distance(nodes[element["node_i"]], nodes[element["node_j"]])
                    mass = density * section["area_m2"] * length
                    total_weight_kN = mass * gravity / 1000.0 * factor
                    each = _vector("GRAVITY", total_weight_kN / 2.0)
                    for node_id in (element["node_i"], element["node_j"]):
                        _add_vector(cases[case_id], node_id, each)
                        contributions.append({"node_id": node_id, "vector_kN": list(each), "derivation": "EXPLICIT_DENSITY_GEOMETRY_SELF_WEIGHT", "source_element_id": element_id})
                else:
                    if section["type"] != "shell":
                        raise ValueError(f"Shell {element_id} requires a shell section")
                    area = _polygon_area(element["node_ids"], nodes)
                    mass = density * section["thickness_m"] * area
                    total_weight_kN = mass * gravity / 1000.0 * factor
                    each = _vector("GRAVITY", total_weight_kN / len(element["node_ids"]))
                    for node_id in element["node_ids"]:
                        _add_vector(cases[case_id], node_id, each)
                        contributions.append({"node_id": node_id, "vector_kN": list(each), "derivation": "EXPLICIT_DENSITY_GEOMETRY_SELF_WEIGHT", "source_element_id": element_id})
        else:
            raise ValueError(f"Unsupported action kind for v8.3.0: {kind}")

        trace[action_id] = {"case_id": case_id, "kind": kind, "contributions": contributions}

    clean_cases: Dict[str, Dict[str, List[float]]] = {}
    for case_id in sorted(known_cases):
        clean_cases[case_id] = {}
        for node_id, vector in sorted(cases.get(case_id, {}).items()):
            clean_cases[case_id][node_id] = [round(v, 12) for v in vector]
    return clean_cases, trace, warnings


def _orientation_vector(a: Mapping[str, float], b: Mapping[str, float]) -> Tuple[float, float, float]:
    axis = (b["x"] - a["x"], b["y"] - a["y"], b["z"] - a["z"])
    length = _norm(axis)
    unit = tuple(c / length for c in axis)
    refs = [(0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)]
    ref = min(refs, key=lambda r: abs(sum(unit[i] * r[i] for i in range(3))))
    return ref


def _tags(ids: Iterable[str]) -> Dict[str, int]:
    return {item_id: idx for idx, item_id in enumerate(sorted(ids), 1)}


def _opensees_model_lines(nodes: Mapping[str, Any], members: Mapping[str, Any], shells: Mapping[str, Any], supports: Sequence[Mapping[str, Any]], materials: Mapping[str, Any], sections: Mapping[str, Any], node_tags: Mapping[str, int], member_tags: Mapping[str, int], shell_tags: Mapping[str, int]) -> Tuple[List[str], Dict[str, Any]]:
    lines = ["wipe", "model BasicBuilder -ndm 3 -ndf 6", ""]
    for node_id in sorted(nodes):
        n = nodes[node_id]
        lines.append(f"node {node_tags[node_id]} {n['x']:.12g} {n['y']:.12g} {n['z']:.12g} ;# {node_id}")
    lines.append("")
    support_map: Dict[str, set] = defaultdict(set)
    for support in supports:
        node_id = _text(support.get("node_id"), "support node_id")
        if node_id not in nodes:
            raise ValueError(f"Support references unknown node {node_id}")
        for dof in _items(support.get("dofs")):
            key = str(dof).upper()
            if key not in DOFS:
                raise ValueError(f"Unsupported support DOF {dof}")
            support_map[node_id].add(key)
    for node_id in sorted(support_map):
        flags = [1 if dof in support_map[node_id] else 0 for dof in DOFS]
        lines.append(f"fix {node_tags[node_id]} {' '.join(map(str, flags))} ;# {node_id}")
    lines.append("")

    material_tags = _tags(materials)
    shell_section_ids = {s["section_id"] for s in shells.values()}
    shell_section_tags = _tags(shell_section_ids)
    for section_id in sorted(shell_section_ids):
        shell = next(s for s in shells.values() if s["section_id"] == section_id)
        mat = materials[shell["material_id"]]
        sec = sections[section_id]
        # OpenSees ElasticMembranePlateSection rho is mass per unit volume in consistent units.
        rho_kN_s2_m4 = mat["density"] / 1000.0 / 9.81
        lines.append(f"section ElasticMembranePlateSection {shell_section_tags[section_id]} {mat['E']:.12g} {mat['nu']:.12g} {sec['thickness_m']:.12g} {rho_kN_s2_m4:.12g} ;# {section_id}")
    lines.append("")

    transf_tags: Dict[str, int] = {}
    for idx, member_id in enumerate(sorted(members), 1):
        m = members[member_id]
        a, b = nodes[m["node_i"]], nodes[m["node_j"]]
        ox, oy, oz = _orientation_vector(a, b)
        transf_tags[member_id] = idx
        lines.append(f"geomTransf Linear {idx} {ox:.12g} {oy:.12g} {oz:.12g} ;# {member_id}")
    lines.append("")
    for member_id in sorted(members):
        m = members[member_id]
        mat = materials[m["material_id"]]
        sec = sections[m["section_id"]]
        if sec["type"] != "rectangular_beam":
            raise ValueError(f"OpenSees member {member_id} requires rectangular_beam section")
        lines.append(
            f"element elasticBeamColumn {member_tags[member_id]} {node_tags[m['node_i']]} {node_tags[m['node_j']]} "
            f"{sec['area_m2']:.12g} {mat['E']:.12g} {mat['G']:.12g} {sec['j_m4']:.12g} {sec['iy_m4']:.12g} {sec['iz_m4']:.12g} {transf_tags[member_id]} ;# {member_id}"
        )
    for shell_id in sorted(shells):
        s = shells[shell_id]
        n = [node_tags[v] for v in s["node_ids"]]
        if len(n) == 3:
            lines.append(f"element ShellDKGT {shell_tags[shell_id]} {' '.join(map(str, n))} {shell_section_tags[s['section_id']]} ;# {shell_id}")
        elif len(n) == 4:
            lines.append(f"element ShellMITC4 {shell_tags[shell_id]} {' '.join(map(str, n))} {shell_section_tags[s['section_id']]} ;# {shell_id}")
        else:
            raise ValueError(f"OpenSees shell {shell_id} must have 3 or 4 nodes")
    manifest = {
        "node_tags": dict(node_tags),
        "member_tags": dict(member_tags),
        "shell_tags": dict(shell_tags),
        "material_tags": material_tags,
        "shell_section_tags": shell_section_tags,
        "transformation_tags": transf_tags,
    }
    return lines, manifest


def _opensees_decks(payload: Mapping[str, Any], nodes: Mapping[str, Any], members: Mapping[str, Any], shells: Mapping[str, Any], materials: Mapping[str, Any], sections: Mapping[str, Any], nodal_loads: Mapping[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    node_tags, member_tags, shell_tags = _tags(nodes), _tags(members), _tags(shells)
    supports = _items((payload.get("analytical_model") or {}).get("supports"))
    model_lines, tag_manifest = _opensees_model_lines(nodes, members, shells, supports, materials, sections, node_tags, member_tags, shell_tags)
    files: Dict[str, str] = {}
    for case_index, case_id in enumerate(sorted(nodal_loads), 1):
        lines = list(model_lines)
        lines += ["", "timeSeries Linear 1", "pattern Plain 1 1 {"]
        for node_id, vector in sorted(nodal_loads[case_id].items()):
            fx, fy, fz = vector
            lines.append(f"    load {node_tags[node_id]} {fx:.12g} {fy:.12g} {fz:.12g} 0 0 0 ;# {node_id}")
        lines += [
            "}", "",
            "constraints Plain",
            "numberer RCM",
            "system BandGeneral",
            "test NormDispIncr 1.0e-10 20",
            "algorithm Linear",
            "integrator LoadControl 1.0",
            "analysis Static",
            "set ok [analyze 1]",
            "if {$ok != 0} { error \"OpenSees analysis failed\" }",
            "puts \"PHOENIX_ANALYSIS_OK\"",
        ]
        for node_id in sorted(nodes):
            tag = node_tags[node_id]
            lines.append(f"puts \"PHX_NODE {node_id} DISP [nodeDisp {tag}] REACTION [nodeReaction {tag}]\"")
        files[f"opensees_{case_id}.tcl"] = "\n".join(lines) + "\n"
    return files, tag_manifest


def _calculix_id_lines(values, max_entries: int = 16) -> List[str]:
    """Return CalculiX set-data lines with no more than max_entries values per line."""
    if max_entries <= 0:
        raise ValueError("max_entries must be positive")
    entries = [str(value) for value in values]
    return [
        ", ".join(entries[index:index + max_entries])
        for index in range(0, len(entries), max_entries)
    ]


def _validate_calculix_data_line_width(lines, max_entries: int = 16) -> None:
    """Reject generated CalculiX data records that exceed the parser entry limit."""
    if max_entries <= 0:
        raise ValueError("max_entries must be positive")
    for line_number, raw_line in enumerate(lines, 1):
        line = str(raw_line).strip()
        if not line or line.startswith("*"):
            continue
        entry_count = len(line.split(","))
        if entry_count > max_entries:
            raise ValueError(
                f"CalculiX data line {line_number} contains {entry_count} entries; "
                f"maximum is {max_entries}: {line}"
            )

def _calculix_decks(payload: Mapping[str, Any], nodes: Mapping[str, Any], members: Mapping[str, Any], shells: Mapping[str, Any], materials: Mapping[str, Any], sections: Mapping[str, Any], nodal_loads: Mapping[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    node_tags, member_tags, shell_tags = _tags(nodes), _tags(members), _tags(shells)
    supports = _items((payload.get("analytical_model") or {}).get("supports"))
    files: Dict[str, str] = {}
    for case_id in sorted(nodal_loads):
        lines: List[str] = ["*HEADING", f"PROJECT PHOENIX v8.3.0 - BASE CASE {case_id}", "*NODE"]
        for node_id in sorted(nodes):
            n = nodes[node_id]
            lines.append(f"{node_tags[node_id]}, {n['x']:.12g}, {n['y']:.12g}, {n['z']:.12g}")
        for member_id in sorted(members):
            m = members[member_id]
            lines += [f"*ELEMENT, TYPE=B31, ELSET=E_{member_id}", f"{member_tags[member_id]}, {node_tags[m['node_i']]}, {node_tags[m['node_j']]}" ]
        shell_offset = len(member_tags)
        for shell_id in sorted(shells):
            s = shells[shell_id]
            tags = [node_tags[n] for n in s["node_ids"]]
            shell_element_type = "S3" if len(tags) == 3 else "S4"
            lines += [f"*ELEMENT, TYPE={shell_element_type}, ELSET=E_{shell_id}", f"{shell_offset + shell_tags[shell_id]}, {', '.join(map(str, tags))}"]
        lines += ["*NSET, NSET=NALL"]
        lines.extend(_calculix_id_lines(node_tags[n] for n in sorted(nodes)))
        for material_id in sorted(materials):
            mat = materials[material_id]
            lines += [f"*MATERIAL, NAME={material_id}", "*ELASTIC", f"{mat['E']:.12g}, {mat['nu']:.12g}"]
        for member_id in sorted(members):
            m = members[member_id]
            sec = sections[m["section_id"]]
            ref = _orientation_vector(nodes[m["node_i"]], nodes[m["node_j"]])
            lines += [
                f"*BEAM SECTION, ELSET=E_{member_id}, MATERIAL={m['material_id']}, SECTION=RECT",
                f"{sec['width_m']:.12g}, {sec['height_m']:.12g}",
                f"{ref[0]:.12g}, {ref[1]:.12g}, {ref[2]:.12g}",
            ]
        for shell_id in sorted(shells):
            s = shells[shell_id]
            sec = sections[s["section_id"]]
            lines += [f"*SHELL SECTION, ELSET=E_{shell_id}, MATERIAL={s['material_id']}", f"{sec['thickness_m']:.12g}"]
        support_map: Dict[str, set] = defaultdict(set)
        for support in supports:
            node_id = _text(support.get("node_id"), "support node_id")
            for dof in _items(support.get("dofs")):
                support_map[node_id].add(str(dof).upper())
        if support_map:
            lines.append("*BOUNDARY")
            for node_id in sorted(support_map):
                for dof_index, dof in enumerate(DOFS, 1):
                    if dof in support_map[node_id]:
                        lines.append(f"{node_tags[node_id]}, {dof_index}, {dof_index}, 0.0")
        lines += ["*STEP", "*STATIC", "*CLOAD"]
        for node_id, vector in sorted(nodal_loads[case_id].items()):
            for dof_index, value in enumerate(vector, 1):
                if abs(value) > 1e-15:
                    lines.append(f"{node_tags[node_id]}, {dof_index}, {value:.12g}")
        lines += ["*NODE FILE", "U, RF", "*EL FILE", "S, E", "*END STEP"]
        _validate_calculix_data_line_width(lines)
        files[f"calculix_{case_id}.inp"] = "\n".join(lines) + "\n"
    manifest = {"node_tags": node_tags, "member_tags": member_tags, "shell_tags": shell_tags}
    return files, manifest


def build_solver_package(payload: Mapping[str, Any]) -> Dict[str, Any]:
    analytical = payload.get("analytical_model") or {}
    basis = payload.get("solver_basis") or {}
    nodes = _node_map(analytical)
    members, shells = _element_maps(analytical, nodes)
    materials = _material_map(basis)
    sections = _section_map(basis)

    for element in list(members.values()) + list(shells.values()):
        if element["material_id"] not in materials:
            raise ValueError(f"Element {element['id']} references unknown material {element['material_id']}")
        if element["section_id"] not in sections:
            raise ValueError(f"Element {element['id']} references unknown section {element['section_id']}")

    nodal_loads, load_trace, warnings = _equivalent_nodal_loads(payload, nodes, members, shells, materials, sections)
    adapters = [str(v).lower() for v in _items(payload.get("solver_adapters"))]
    unsupported = sorted(set(adapters) - {"opensees", "calculix"})
    if unsupported:
        raise ValueError(f"Unsupported solver adapters: {', '.join(unsupported)}")

    solver_files: Dict[str, Dict[str, str]] = {}
    mapping: Dict[str, Any] = {}
    if "opensees" in adapters:
        solver_files["opensees"], mapping["opensees"] = _opensees_decks(payload, nodes, members, shells, materials, sections, nodal_loads)
    if "calculix" in adapters:
        solver_files["calculix"], mapping["calculix"] = _calculix_decks(payload, nodes, members, shells, materials, sections, nodal_loads)

    combinations = deepcopy(_items((payload.get("action_load_model") or {}).get("load_combinations")))
    execution_policy = deepcopy(payload.get("execution_policy") or {})
    executable_status = {}
    for solver in adapters:
        command = str((execution_policy.get("solver_executables") or {}).get(solver) or ("OpenSees" if solver == "opensees" else "ccx"))
        executable_status[solver] = {"command": command, "discovered": shutil.which(command) is not None}

    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": str(payload.get("project_id") or "UNKNOWN"),
        "model_state": "SOLVER_PACKAGE_CANDIDATE",
        "solver_basis": {
            "source": str(basis.get("basis") or "EXPLICIT_PROJECT_INPUT"),
            "analysis_type": str(basis.get("analysis_type") or "LINEAR_STATIC"),
            "automatic_normative_value_invention": False,
            "derived_section_properties": sections,
        },
        "equivalent_nodal_loads_kN": nodal_loads,
        "solver_files": solver_files,
        "solver_mapping": mapping,
        "load_combinations": combinations,
        "combination_result_contract": {
            "method": "LINEAR_SUPERPOSITION_OF_BASE_CASE_RESULTS",
            "requires_all_referenced_base_cases": True,
            "code_compliance_claimed": False,
        },
        "traceability": {"action_to_nodal_contributions": load_trace},
        "warnings": warnings,
        "execution": {
            "project_policy_allows_execution": bool(execution_policy.get("allow_execution", False)),
            "explicit_cli_opt_in_required": bool(execution_policy.get("require_explicit_cli_opt_in", True)),
            "executable_status": executable_status,
            "executed": False,
        },
        "result_normalization_contract": {
            "base_case_result_fields": ["node_displacements", "node_reactions", "element_forces", "element_stresses"],
            "phoenix_ids_required": True,
            "solver_native_ids_preserved": True,
            "raw_solver_evidence_required": True,
        },
        "digital_twin_writeback": {
            "enabled": True,
            "target": "CENTRAL_DIGITAL_TWIN.structural.analysis",
            "write_state": "SOLVER_PACKAGE_CANDIDATE",
            "approval_state": "CANDIDATE_ONLY",
            "solver_results_required_for_next_state": True,
        },
        "release": {
            "automatic_structural_approval": False,
            "automatic_code_compliance_claim": False,
            "structural_model_release": LOCKED_RELEASE,
            "engineering_review_required": True,
        },
        "summary": {
            "node_count": len(nodes),
            "member_count": len(members),
            "shell_count": len(shells),
            "load_case_count": len(nodal_loads),
            "load_combination_count": len(combinations),
            "solver_adapter_count": len(solver_files),
            "solver_file_count": sum(len(v) for v in solver_files.values()),
        },
    }


def write_solver_package(package: Mapping[str, Any], output_dir: Path) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for solver, files in package.get("solver_files", {}).items():
        solver_dir = output_dir / solver
        solver_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            path = solver_dir / name
            path.write_text(content, encoding="utf-8", newline="\n")
            written.append(str(path))
    manifest = deepcopy(dict(package))
    manifest.pop("solver_files", None)
    manifest_path = output_dir / "PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    written.append(str(manifest_path))
    return written


def execute_solver_package(payload: Mapping[str, Any], package: Mapping[str, Any], output_dir: Path, allow_execution: bool) -> Dict[str, Any]:
    policy = payload.get("execution_policy") or {}
    if not bool(policy.get("allow_execution", False)):
        raise RuntimeError("Solver execution is locked by project execution_policy.allow_execution=false")
    if bool(policy.get("require_explicit_cli_opt_in", True)) and not allow_execution:
        raise RuntimeError("Solver execution requires explicit --allow-execution opt-in")

    results: Dict[str, Any] = {"executed": True, "runs": []}
    commands = policy.get("solver_executables") or {}
    for solver, files in package.get("solver_files", {}).items():
        command = str(commands.get(solver) or ("OpenSees" if solver == "opensees" else "ccx"))
        executable = shutil.which(command)
        if not executable:
            raise RuntimeError(f"Required solver executable not found for {solver}: {command}")
        solver_dir = output_dir / solver
        for name in sorted(files):
            path = solver_dir / name
            if solver == "opensees":
                cmd = [executable, str(path)]
            else:
                cmd = [executable, "-i", path.stem]
            proc = subprocess.run(cmd, cwd=str(solver_dir), text=True, capture_output=True, check=False)
            run = {"solver": solver, "input": name, "returncode": proc.returncode, "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:]}
            results["runs"].append(run)
            if proc.returncode != 0:
                raise RuntimeError(f"{solver} failed for {name} with return code {proc.returncode}")
    return results


def normalize_external_results(solver: str, raw: Mapping[str, Any], mapping: Mapping[str, Any]) -> Dict[str, Any]:
    solver_key = _text(solver, "solver").lower()
    if solver_key not in {"opensees", "calculix"}:
        raise ValueError(f"Unsupported solver for normalization: {solver_key}")
    return {
        "solver": solver_key,
        "normalization_version": VERSION,
        "node_displacements": deepcopy(raw.get("node_displacements") or {}),
        "node_reactions": deepcopy(raw.get("node_reactions") or {}),
        "element_forces": deepcopy(raw.get("element_forces") or {}),
        "element_stresses": deepcopy(raw.get("element_stresses") or {}),
        "solver_mapping": deepcopy(mapping),
        "raw_solver_evidence_reference": raw.get("raw_solver_evidence_reference"),
        "approval_state": "ANALYSIS_RESULT_CANDIDATE_ONLY",
        "code_compliance_claimed": False,
    }


def _demo_payload() -> Dict[str, Any]:
    return {
        "project_id": "SELF-TEST",
        "analytical_model": {
            "nodes": [
                {"id": "N1", "x": 0, "y": 0, "z": 0},
                {"id": "N2", "x": 0, "y": 0, "z": 3},
                {"id": "N3", "x": 4, "y": 0, "z": 3},
                {"id": "N4", "x": 4, "y": 3, "z": 3},
                {"id": "N5", "x": 0, "y": 3, "z": 3},
            ],
            "members": [{"id": "M1", "type": "column", "node_i": "N1", "node_j": "N2", "material_id": "MAT", "section_id": "B"}],
            "shells": [{"id": "S1", "type": "slab_panel", "node_ids": ["N2", "N3", "N4", "N5"], "material_id": "MAT", "section_id": "S"}],
            "supports": [{"id": "SUP1", "node_id": "N1", "dofs": list(DOFS)}],
        },
        "solver_basis": {
            "basis": "EXPLICIT_SELF_TEST_INPUT",
            "analysis_type": "LINEAR_STATIC",
            "gravity_acceleration_m_s2": 9.81,
            "materials": {"MAT": {"elastic_modulus_kN_m2": 30000000, "poisson_ratio": 0.2, "density_kg_m3": 2500}},
            "sections": {"B": {"type": "rectangular_beam", "width_m": 0.3, "height_m": 0.3}, "S": {"type": "shell", "thickness_m": 0.2}},
        },
        "action_load_model": {
            "load_cases": [{"id": "G", "category": "permanent"}, {"id": "Q", "category": "variable"}],
            "action_assignments": [
                {"id": "A1", "case_id": "G", "kind": "self_weight", "direction": "GRAVITY", "factor": 1.0, "target_element_ids": ["M1", "S1"]},
                {"id": "A2", "case_id": "Q", "kind": "area", "direction": "GLOBAL_Z", "magnitude": -2.0, "target_element_id": "S1"},
            ],
            "load_combinations": [{"id": "C1", "limit_state": "ULS", "terms": [{"case_id": "G", "coefficient": 1.35}, {"case_id": "Q", "coefficient": 1.5}]}],
        },
        "solver_adapters": ["opensees", "calculix"],
        "execution_policy": {"allow_execution": False, "require_explicit_cli_opt_in": True, "solver_executables": {"opensees": "OpenSees", "calculix": "ccx"}},
    }


def self_test() -> None:
    package = build_solver_package(_demo_payload())
    assert package["engine"]["version"] == VERSION
    assert package["summary"]["solver_adapter_count"] == 2
    assert package["summary"]["solver_file_count"] == 4
    assert package["equivalent_nodal_loads_kN"]["Q"]["N2"][2] == -6.0
    assert "element elasticBeamColumn" in package["solver_files"]["opensees"]["opensees_G.tcl"]
    assert "*ELEMENT, TYPE=B31" in package["solver_files"]["calculix"]["calculix_G.inp"]
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_solver_package(package, Path(tmp))
        assert len(paths) == 5
        assert Path(tmp, "PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json").exists()
    try:
        execute_solver_package(_demo_payload(), package, Path("."), allow_execution=True)
    except RuntimeError as exc:
        assert "locked by project" in str(exc)
    else:
        raise AssertionError("Execution gate did not block execution")
    assert package["release"]["structural_model_release"] == "LOCKED"
    print("STRUCTURAL SOLVER INPUT AND ANALYSIS ENGINE: PASSED")
    print("OPENSEES SOLVER PACKAGE: GENERATED")
    print("CALCULIX SOLVER PACKAGE: GENERATED")
    print("EQUIVALENT NODAL LOAD MODEL: GENERATED")
    print("LOAD COMBINATION RESULT CONTRACT: GENERATED")
    print("SOLVER EXECUTION DEFAULT: LOCKED")
    print("RESULT NORMALIZATION CONTRACT: GENERATED")
    print("ANALYSIS TRACEABILITY: ENABLED")
    print("CENTRAL DIGITAL TWIN ANALYSIS WRITEBACK: PASSED")
    print("AUTOMATIC CODE COMPLIANCE CLAIM: DISABLED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    package = build_solver_package(payload)
    output_dir = args.output_dir
    if output_dir:
        write_solver_package(package, output_dir)
    if args.execute:
        if not output_dir:
            parser.error("--execute requires --output-dir")
        execution_result = execute_solver_package(payload, package, output_dir, args.allow_execution)
        package = dict(package)
        package["execution"] = execution_result
    printable = deepcopy(package)
    printable.pop("solver_files", None)
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
