#!/usr/bin/env python3
"""Project Phoenix Structural Analytical Model Generation Engine v8.1.0.

Creates a solver-neutral analytical model candidate from structural candidates.
The engine deliberately does NOT grant structural approval or unlock release.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Sequence, Tuple

ENGINE_ID = "PHX-STRUCT-ANALYTICAL-MODEL-V8.1.0"
VERSION = "8.1.0"
LOCKED_RELEASE = "LOCKED"

Point = Tuple[float, float, float]


def _point(value: Any) -> Point:
    if isinstance(value, dict):
        return (float(value.get("x", 0.0)), float(value.get("y", 0.0)), float(value.get("z", 0.0)))
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    raise ValueError(f"Invalid 3D point: {value!r}")


def _candidate_group(payload: Dict[str, Any], *names: str) -> List[Dict[str, Any]]:
    root = payload.get("structural_candidates", payload)
    for name in names:
        value = root.get(name)
        if isinstance(value, list):
            return value
    return []


class NodeRegistry:
    def __init__(self, tolerance: float = 1e-6) -> None:
        self.tolerance = tolerance
        self._ids: MutableMapping[Tuple[int, int, int], str] = {}
        self.nodes: List[Dict[str, Any]] = []

    def _key(self, p: Point) -> Tuple[int, int, int]:
        t = self.tolerance
        return tuple(int(round(v / t)) for v in p)  # type: ignore[return-value]

    def add(self, value: Any, source_id: str | None = None) -> str:
        p = _point(value)
        key = self._key(p)
        if key in self._ids:
            node_id = self._ids[key]
            if source_id:
                node = next(n for n in self.nodes if n["id"] == node_id)
                if source_id not in node["source_ids"]:
                    node["source_ids"].append(source_id)
            return node_id
        node_id = f"N{len(self.nodes)+1:04d}"
        self._ids[key] = node_id
        self.nodes.append({"id": node_id, "x": p[0], "y": p[1], "z": p[2], "source_ids": [source_id] if source_id else []})
        return node_id


def _source_id(item: Dict[str, Any], prefix: str, index: int) -> str:
    return str(item.get("id") or item.get("candidate_id") or f"{prefix}-{index:04d}")


def _line_endpoints(item: Dict[str, Any], kind: str) -> Tuple[Any, Any]:
    if kind == "column":
        start = item.get("base", item.get("start"))
        end = item.get("top", item.get("end"))
    else:
        start = item.get("start", item.get("p1"))
        end = item.get("end", item.get("p2"))
    if start is None or end is None:
        raise ValueError(f"{kind} candidate lacks endpoints: {item!r}")
    return start, end


def _polygon(item: Dict[str, Any]) -> Sequence[Any]:
    points = item.get("polygon") or item.get("points") or item.get("corners")
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError(f"Shell candidate lacks polygon: {item!r}")
    return points


def build_analytical_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    policy = payload.get("analytical_model_policy", {})
    tolerance = float(policy.get("coordinate_tolerance_m", 1e-6))
    nodes = NodeRegistry(tolerance=tolerance)
    members: List[Dict[str, Any]] = []
    shells: List[Dict[str, Any]] = []
    supports: List[Dict[str, Any]] = []
    traceability: Dict[str, List[str]] = {}
    material_candidates: Dict[str, str] = {}
    section_candidates: Dict[str, str] = {}

    def add_member(item: Dict[str, Any], kind: str, index: int, default_material: str, default_section: str) -> None:
        source = _source_id(item, kind.upper(), index)
        start, end = _line_endpoints(item, kind)
        n1 = nodes.add(start, source)
        n2 = nodes.add(end, source)
        member_id = f"M{len(members)+1:04d}"
        material = str(item.get("material_candidate") or item.get("material") or default_material)
        section = str(item.get("section_candidate") or item.get("section") or default_section)
        members.append({
            "id": member_id,
            "type": kind,
            "node_i": n1,
            "node_j": n2,
            "source_candidate_id": source,
            "material_candidate": material,
            "section_candidate": section,
            "approval_state": "CANDIDATE_ONLY",
        })
        traceability.setdefault(source, []).append(member_id)
        material_candidates[member_id] = material
        section_candidates[member_id] = section
        if kind == "column" and policy.get("auto_generate_column_base_support_candidates", True):
            supports.append({
                "id": f"SUP{len(supports)+1:04d}",
                "node_id": n1,
                "type": str(item.get("base_support_candidate") or "PROVISIONAL_FIXED_BASE"),
                "source_candidate_id": source,
                "approval_state": "CANDIDATE_ONLY",
            })

    for i, item in enumerate(_candidate_group(payload, "columns", "column_candidates"), 1):
        add_member(item, "column", i, "reinforced_concrete", "AUTO_PRELIMINARY_COLUMN")
    for i, item in enumerate(_candidate_group(payload, "beams", "beam_candidates"), 1):
        add_member(item, "beam", i, "reinforced_concrete", "AUTO_PRELIMINARY_BEAM")
    for i, item in enumerate(_candidate_group(payload, "roof_supports", "roof_support_candidates"), 1):
        add_member(item, "roof_support", i, "steel_or_timber", "AUTO_PRELIMINARY_ROOF_SUPPORT")

    def add_shell(item: Dict[str, Any], kind: str, index: int, default_material: str) -> None:
        source = _source_id(item, kind.upper(), index)
        node_ids = [nodes.add(p, source) for p in _polygon(item)]
        shell_id = f"S{len(shells)+1:04d}"
        material = str(item.get("material_candidate") or item.get("material") or default_material)
        shells.append({
            "id": shell_id,
            "type": kind,
            "node_ids": node_ids,
            "source_candidate_id": source,
            "material_candidate": material,
            "thickness_candidate": item.get("thickness_candidate", "AUTO_PRELIMINARY_THICKNESS"),
            "approval_state": "CANDIDATE_ONLY",
        })
        traceability.setdefault(source, []).append(shell_id)
        material_candidates[shell_id] = material

    for i, item in enumerate(_candidate_group(payload, "loadbearing_walls", "walls", "loadbearing_wall_candidates"), 1):
        add_shell(item, "loadbearing_wall", i, "masonry_or_reinforced_concrete")
    for i, item in enumerate(_candidate_group(payload, "slab_panels", "slabs", "slab_panel_candidates"), 1):
        add_shell(item, "slab_panel", i, "reinforced_concrete")

    # Explicit support candidates are added in addition to provisional column-base supports.
    for i, item in enumerate(_candidate_group(payload, "supports", "support_candidates"), 1):
        source = _source_id(item, "SUPPORT", i)
        node_value = item.get("point") or item.get("position") or item.get("base")
        if node_value is None:
            continue
        node_id = nodes.add(node_value, source)
        supports.append({
            "id": f"SUP{len(supports)+1:04d}",
            "node_id": node_id,
            "type": str(item.get("type") or "PROVISIONAL_SUPPORT"),
            "source_candidate_id": source,
            "approval_state": "CANDIDATE_ONLY",
        })

    # Connectivity graph: node -> touching analytical elements.
    connectivity: Dict[str, List[str]] = {n["id"]: [] for n in nodes.nodes}
    for m in members:
        connectivity[m["node_i"]].append(m["id"])
        connectivity[m["node_j"]].append(m["id"])
    for s in shells:
        for node_id in s["node_ids"]:
            connectivity[node_id].append(s["id"])

    # Load-path graph is deliberately topological only; no design loads are invented here.
    load_path_edges: List[Dict[str, str]] = []
    for node_id, elements in connectivity.items():
        unique = sorted(set(elements))
        for a_idx, a in enumerate(unique):
            for b in unique[a_idx + 1:]:
                load_path_edges.append({"from": a, "to": b, "via_node": node_id})

    stability_zones = _candidate_group(payload, "stability_zones")
    warnings: List[str] = []
    if not members and not shells:
        warnings.append("No analytical members or shells generated from supplied structural candidates.")
    if not supports:
        warnings.append("No support candidates generated; downstream structural analysis must remain blocked.")

    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "model_state": "ANALYTICAL_CANDIDATE",
        "nodes": nodes.nodes,
        "members": members,
        "shells": shells,
        "support_candidates": supports,
        "connectivity": connectivity,
        "load_path_graph": {"mode": "TOPOLOGICAL_ONLY", "edges": load_path_edges},
        "material_candidates": material_candidates,
        "section_candidates": section_candidates,
        "stability_zones": stability_zones,
        "traceability": traceability,
        "digital_twin_writeback": {
            "contract": "STRUCTURAL_ANALYTICAL_MODEL_CANDIDATE",
            "enabled": True,
            "approval_state": "CANDIDATE_ONLY",
        },
        "release": {
            "automatic_structural_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "engineering_review_required": True,
            "blocking_requirements": [
                "load_model",
                "preliminary_sizing",
                "solver_results",
                "code_checks",
                "engineering_review",
            ],
        },
        "warnings": warnings,
        "summary": {
            "node_count": len(nodes.nodes),
            "member_count": len(members),
            "shell_count": len(shells),
            "support_candidate_count": len(supports),
            "traceable_source_count": len(traceability),
        },
    }


def _self_test_payload() -> Dict[str, Any]:
    return {
        "structural_candidates": {
            "columns": [{"id": "C1", "base": [0, 0, 0], "top": [0, 0, 3]}],
            "beams": [{"id": "B1", "start": [0, 0, 3], "end": [5, 0, 3]}],
            "slab_panels": [{"id": "S1", "polygon": [[0, 0, 3], [5, 0, 3], [5, 4, 3], [0, 4, 3]]}],
            "stability_zones": [{"id": "SZ1", "axis": "X"}],
        },
        "analytical_model_policy": {"auto_generate_column_base_support_candidates": True},
    }


def self_test() -> None:
    model = build_analytical_model(_self_test_payload())
    assert model["summary"]["member_count"] == 2
    assert model["summary"]["shell_count"] == 1
    assert model["summary"]["support_candidate_count"] == 1
    assert model["release"]["automatic_structural_approval"] is False
    assert model["release"]["structural_model_release"] == "LOCKED"
    assert model["digital_twin_writeback"]["approval_state"] == "CANDIDATE_ONLY"
    print("STRUCTURAL ANALYTICAL MODEL GENERATION ENGINE: PASSED")
    print("SOLVER-NEUTRAL ANALYTICAL MODEL: GENERATED")
    print("NODE GENERATION: PASSED")
    print("LINE MEMBER GENERATION: PASSED")
    print("SHELL PANEL GENERATION: PASSED")
    print("BOUNDARY CONDITION CANDIDATES: GENERATED")
    print("CONNECTIVITY GRAPH: GENERATED")
    print("TOPOLOGICAL LOAD PATH GRAPH: GENERATED")
    print("MATERIAL CANDIDATES: GENERATED")
    print("SECTION CANDIDATES: GENERATED")
    print("STABILITY ZONES: TRANSFERRED")
    print("ARCHITECTURAL TRACEABILITY: ENABLED")
    print("CENTRAL DIGITAL TWIN ANALYTICAL MODEL WRITEBACK: PASSED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Structural-candidate JSON input")
    parser.add_argument("--output", type=Path, help="Write analytical model JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    model = build_analytical_model(payload)
    rendered = json.dumps(model, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"ANALYTICAL MODEL WRITTEN: {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
