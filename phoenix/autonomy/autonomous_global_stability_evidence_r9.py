"""Project Phoenix R9 autonomous global-stability evidence engine.

R9 derives traceable model/solver evidence after v8.5 has genuinely reached
MEMBER_VERIFICATION_CANDIDATE_PASSED. It deliberately does not invent
normative limits, global buckling factors, storey strengths, robustness
capacity, professional approval, or statutory code-compliance claims.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ENGINE_ID = "PHX-AUTONOMOUS-GLOBAL-STABILITY-EVIDENCE-R9"
VERSION = "R9.0.0"
SCHEMA = "phoenix.autonomous-global-stability-evidence/1.0"
LOCKED_RELEASE = "LOCKED"

CHECK_TYPES = (
    "ALTERNATE_LOAD_PATH_EVIDENCE",
    "DIAPHRAGM_CONTINUITY",
    "GLOBAL_BUCKLING_FACTOR",
    "LOAD_PATH_CONTINUITY",
    "SECOND_ORDER_AMPLIFICATION",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "STOREY_STABILITY_INDEX",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _node_xyz(node: Mapping[str, Any]) -> tuple[float, float, float] | None:
    if isinstance(node.get("coords"), (list, tuple)) and len(node["coords"]) >= 3:
        vals = tuple(_num(x) for x in node["coords"][:3])
    elif isinstance(node.get("coordinate"), (list, tuple)) and len(node["coordinate"]) >= 3:
        vals = tuple(_num(x) for x in node["coordinate"][:3])
    else:
        vals = (_num(node.get("x")), _num(node.get("y")), _num(node.get("z")))
    if any(v is None for v in vals):
        return None
    return vals  # type: ignore[return-value]


def _support_node_ids(model: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for index, support in enumerate(model.get("supports") or model.get("support_candidates") or []):
        if not isinstance(support, Mapping):
            continue
        sid = str(support.get("id") or f"SUP-{index+1:04d}")
        node_id = support.get("node_id") or support.get("node") or support.get("node_ref")
        if node_id:
            out[sid] = str(node_id)
    return out


def derive_topology_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    nodes = {str(n.get("id")): n for n in model.get("nodes", []) if isinstance(n, Mapping) and n.get("id")}
    graph: dict[str, set[str]] = {nid: set() for nid in nodes}
    edge_records: list[dict[str, str]] = []

    def add(a: Any, b: Any) -> None:
        a, b = str(a or ""), str(b or "")
        if not a or not b or a == b or a not in graph or b not in graph:
            return
        if b not in graph[a]:
            graph[a].add(b); graph[b].add(a)
            edge_records.append({"from": a, "to": b})

    for m in model.get("members", []):
        if isinstance(m, Mapping):
            add(m.get("node_i") or m.get("start_node") or m.get("node_start"), m.get("node_j") or m.get("end_node") or m.get("node_end"))
    for s in model.get("shells", []):
        if not isinstance(s, Mapping):
            continue
        ids = [str(x) for x in (s.get("node_ids") or s.get("nodes") or []) if str(x) in graph]
        for i, a in enumerate(ids):
            add(a, ids[(i + 1) % len(ids)]) if len(ids) > 1 else None

    support_map = _support_node_ids(model)
    support_nodes = set(support_map.values())
    loaded_nodes = sorted(n for n in graph if n not in support_nodes)
    missing_paths: list[str] = []
    predecessor_edges: set[tuple[str, str]] = set()

    for start in loaded_nodes:
        q = deque([start]); prev: dict[str, str | None] = {start: None}; target = None
        while q:
            cur = q.popleft()
            if cur in support_nodes:
                target = cur; break
            for nxt in sorted(graph.get(cur, ())):
                if nxt not in prev:
                    prev[nxt] = cur; q.append(nxt)
        if target is None:
            missing_paths.append(start); continue
        cur = target
        while prev[cur] is not None:
            parent = prev[cur]
            predecessor_edges.add((parent, cur))
            cur = parent

    support_edges = []
    for sid, nid in sorted(support_map.items()):
        if nid in graph:
            support_edges.append({"from": nid, "to": sid})

    return {
        "evidence_class": "MODEL_DERIVED_CANDIDATE_EVIDENCE",
        "node_count": len(nodes),
        "support_count": len(support_map),
        "loaded_node_count": len(loaded_nodes),
        "all_loaded_nodes_reach_support": bool(loaded_nodes) and not missing_paths and bool(support_map),
        "unreachable_node_ids": missing_paths,
        "loaded_nodes": loaded_nodes,
        "load_path_edges": [{"from": a, "to": b} for a, b in sorted(predecessor_edges)] + support_edges,
        "graph_edges": edge_records,
        "note": "Topological connectivity only; this is not a member-capacity or alternate-load-path robustness proof.",
    }


def _levels(model: Mapping[str, Any], architecture: Mapping[str, Any], tol: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, s in enumerate(architecture.get("storeys", []) if isinstance(architecture, Mapping) else []):
        if not isinstance(s, Mapping):
            continue
        z = _num(s.get("elevation_m"))
        if z is None:
            continue
        out.append({"id": str(s.get("storey_id") or s.get("id") or f"L{idx+1}"), "elevation_m": z, "height_m": _num(s.get("height_m"))})
    if out:
        return sorted(out, key=lambda x: x["elevation_m"])
    zs = sorted({_node_xyz(n)[2] for n in model.get("nodes", []) if isinstance(n, Mapping) and _node_xyz(n) is not None})
    merged: list[float] = []
    for z in zs:
        if not merged or abs(z - merged[-1]) > tol:
            merged.append(z)
    return [{"id": f"Z{i+1}", "elevation_m": z, "height_m": None} for i, z in enumerate(merged)]


def derive_diaphragm_evidence(model: Mapping[str, Any], architecture: Mapping[str, Any], tol: float) -> dict[str, Any]:
    nodes = {str(n.get("id")): _node_xyz(n) for n in model.get("nodes", []) if isinstance(n, Mapping) and n.get("id")}
    levels = _levels(model, architecture, tol)
    storeys = []
    for level in levels:
        z = level["elevation_m"]
        shell_sets: list[set[str]] = []
        shell_ids: list[str] = []
        for s in model.get("shells", []):
            if not isinstance(s, Mapping):
                continue
            ids = [str(x) for x in (s.get("node_ids") or s.get("nodes") or [])]
            xyz = [nodes.get(x) for x in ids]
            if not ids or any(p is None for p in xyz):
                continue
            zvals = [p[2] for p in xyz if p is not None]
            if max(zvals) - min(zvals) <= tol and abs(sum(zvals) / len(zvals) - z) <= tol:
                shell_sets.append(set(ids)); shell_ids.append(str(s.get("id") or f"S{len(shell_ids)+1}"))
        components = 0
        if shell_sets:
            unseen = set(range(len(shell_sets)))
            while unseen:
                components += 1; q = [unseen.pop()]
                while q:
                    i = q.pop()
                    touching = [j for j in list(unseen) if shell_sets[i] & shell_sets[j]]
                    for j in touching:
                        unseen.remove(j); q.append(j)
        storeys.append({"storey_id": level["id"], "elevation_m": z, "horizontal_shell_count": len(shell_sets), "shell_ids": shell_ids, "connected_components": components, "continuity_verified": bool(shell_sets) and components == 1})
    assessed = [s for s in storeys if s["horizontal_shell_count"] > 0]
    return {
        "evidence_class": "MODEL_DERIVED_CANDIDATE_EVIDENCE",
        "storeys": storeys,
        "assessed_storey_count": len(assessed),
        "continuity_verified": bool(assessed) and all(s["continuity_verified"] for s in assessed),
        "note": "Geometry/connectivity evidence only; diaphragm strength/stiffness adequacy is not inferred.",
    }


def derive_floor_response(model: Mapping[str, Any], architecture: Mapping[str, Any], analysis_validation: Mapping[str, Any], tol: float) -> dict[str, Any]:
    nodes = {str(n.get("id")): _node_xyz(n) for n in model.get("nodes", []) if isinstance(n, Mapping) and n.get("id")}
    levels = _levels(model, architecture, tol)
    synthesized = analysis_validation.get("synthesized_combination_results") or {}
    calc = synthesized.get("calculix") if isinstance(synthesized, Mapping) else None
    if not isinstance(calc, Mapping):
        return {"evidence_class": "REAL_CALCULIX_FIRST_ORDER_EVIDENCE", "status": "UNAVAILABLE", "combinations": []}
    rows = []
    for combo_id, result in calc.items():
        if not isinstance(result, Mapping):
            continue
        token = str(combo_id).upper()
        if "W" not in token and "WIND" not in token:
            continue
        disp = result.get("node_displacements") or {}
        if not isinstance(disp, Mapping):
            continue
        previous_mean = (0.0, 0.0)
        for level in levels:
            level_nodes = [nid for nid, xyz in nodes.items() if xyz is not None and abs(xyz[2] - level["elevation_m"]) <= tol and nid in disp]
            vectors = []
            for nid in level_nodes:
                d = disp.get(nid) or {}
                if isinstance(d, Mapping):
                    ux, uy = _num(d.get("UX")), _num(d.get("UY"))
                    if ux is not None and uy is not None:
                        vectors.append((ux, uy))
            if not vectors:
                continue
            mean = (sum(v[0] for v in vectors)/len(vectors), sum(v[1] for v in vectors)/len(vectors))
            inter = [(v[0]-previous_mean[0], v[1]-previous_mean[1]) for v in vectors]
            mags = [math.hypot(x, y) for x, y in inter]
            avg = sum(mags)/len(mags) if mags else 0.0
            rows.append({"combination_id": str(combo_id), "storey_id": level["id"], "elevation_m": level["elevation_m"], "node_count": len(vectors), "mean_translation_m": math.hypot(*mean), "mean_interstorey_drift_m": math.hypot(mean[0]-previous_mean[0], mean[1]-previous_mean[1]), "max_nodal_interstorey_drift_m": max(mags) if mags else 0.0, "average_nodal_interstorey_drift_m": avg, "nodal_drift_spread_ratio": (max(mags)/avg if avg > 0 else None)})
            previous_mean = mean
    return {"evidence_class": "REAL_CALCULIX_FIRST_ORDER_EVIDENCE", "status": "AVAILABLE" if rows else "UNAVAILABLE", "combinations": rows, "note": "Nodal drift spread is reported as evidence; it is not automatically promoted to a torsional-code check."}


def _find_calculix() -> Path | None:
    explicit = os.environ.get("CALCULIX_EXE") or os.environ.get("CCX_EXE")
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    for name in ("ccx.exe", "ccx", "calculix.exe", "calculix"):
        found = shutil.which(name)
        if found and Path(found).is_file():
            return Path(found)
    for path in (Path(r"C:\Program Files\FreeCAD 1.1\bin\ccx.exe"), Path(r"C:\Program Files\FreeCAD 1.0\bin\ccx.exe"), Path(r"C:\CalculiX\ccx.exe"), Path(r"C:\ccx\ccx.exe")):
        if path.is_file():
            return path
    return None


def make_nlgeom_deck(text: str) -> str:
    lines = text.splitlines()
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.upper().startswith("*STEP") and not stripped.startswith("**"):
            if "NLGEOM" not in stripped.upper():
                lines[i] = line.rstrip() + ", NLGEOM"
            changed = True
            break
    if not changed:
        raise ValueError("CalculiX deck has no *STEP card")
    return "\n".join(lines) + "\n"


def _max_horizontal(displacements: Mapping[Any, Any]) -> float | None:
    vals = []
    for value in displacements.values():
        if isinstance(value, Mapping):
            ux, uy = _num(value.get("UX")), _num(value.get("UY"))
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            ux, uy = _num(value[0]), _num(value[1])
        else:
            continue
        if ux is not None and uy is not None:
            vals.append(math.hypot(ux, uy))
    return max(vals) if vals else None


def run_real_second_order(repository: Path, v84_evidence_dir: Path, output_dir: Path) -> dict[str, Any]:
    if os.environ.get("PHOENIX_TEST_MODE"):
        return {"status": "SKIPPED_TEST_MODE", "evidence_class": "REAL_CALCULIX_NLGEOM_EVIDENCE", "cases": []}
    exe = _find_calculix()
    if exe is None:
        return {"status": "BLOCKED", "reason": "CALCULIX_EXECUTABLE_REQUIRED_FOR_R9_SECOND_ORDER", "evidence_class": "REAL_CALCULIX_NLGEOM_EVIDENCE", "cases": []}
    try:
        from phoenix.autonomy.autonomous_calculix_results_v8_4 import parse_calculix_dat
    except Exception as exc:
        return {"status": "BLOCKED", "reason": "R9_CALCULIX_DAT_PARSER_UNAVAILABLE", "error": str(exc), "evidence_class": "REAL_CALCULIX_NLGEOM_EVIDENCE", "cases": []}
    cases = []
    for case_dir in sorted(v84_evidence_dir.glob("LC-W*")) if v84_evidence_dir.is_dir() else []:
        source_deck = case_dir / "phoenix_v8_4_case.inp"
        source_dat = case_dir / "phoenix_v8_4_case.dat"
        if not source_deck.is_file() or not source_dat.is_file():
            continue
        case_id = case_dir.name
        target_dir = output_dir / "second_order" / "calculix" / case_id
        target_dir.mkdir(parents=True, exist_ok=True)
        job = f"phoenix_r9_nlgeom_{case_id.replace('-', '_')}"
        deck = target_dir / f"{job}.inp"
        deck.write_text(make_nlgeom_deck(source_deck.read_text(encoding="utf-8", errors="replace")), encoding="utf-8", newline="\n")
        cp = subprocess.run([str(exe), job], cwd=target_dir, text=True, capture_output=True, check=False, timeout=180)
        (target_dir / "solver_stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
        (target_dir / "solver_stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
        dat = target_dir / f"{job}.dat"
        if cp.returncode != 0 or not dat.is_file():
            cases.append({"case_id": case_id, "status": "FAILED", "return_code": cp.returncode, "deck": _repo_ref(deck, repository), "stdout": _repo_ref(target_dir/"solver_stdout.txt", repository), "stderr": _repo_ref(target_dir/"solver_stderr.txt", repository)})
            continue
        try:
            first = parse_calculix_dat(source_dat.read_text(encoding="utf-8", errors="replace"))
            second = parse_calculix_dat(dat.read_text(encoding="utf-8", errors="replace"))
            u1 = _max_horizontal(first.get("node_displacements") or {})
            u2 = _max_horizontal(second.get("node_displacements") or {})
        except Exception as exc:
            cases.append({"case_id": case_id, "status": "PARSE_FAILED", "error": str(exc), "dat": _repo_ref(dat, repository)})
            continue
        amp = (u2/u1) if u1 is not None and u2 is not None and u1 > 0 else None
        cases.append({"case_id": case_id, "status": "PASSED" if amp is not None else "INCOMPLETE", "first_order_max_horizontal_displacement_m": u1, "second_order_max_horizontal_displacement_m": u2, "amplification_factor": amp, "source_first_order_dat": _repo_ref(source_dat, repository), "second_order_deck": _repo_ref(deck, repository), "second_order_dat": _repo_ref(dat, repository), "stdout": _repo_ref(target_dir/"solver_stdout.txt", repository), "stderr": _repo_ref(target_dir/"solver_stderr.txt", repository)})
    valid = [x for x in cases if x.get("status") == "PASSED" and _num(x.get("amplification_factor")) is not None]
    worst = max(valid, key=lambda x: x["amplification_factor"]) if valid else None
    return {"status": "PASSED" if valid else "BLOCKED", "evidence_class": "REAL_CALCULIX_NLGEOM_EVIDENCE", "executable": str(exe), "cases": cases, "worst_case": worst, "note": "NLGEOM is real CalculiX evidence; no acceptance limit is inferred by R9."}


def _extract_r9_input(candidates: Sequence[Any], forbidden_paths: Sequence[str]) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    accepted: list[tuple[int, str, dict[str, Any]]] = []
    for item in candidates:
        path, data = (item[0], item[1]) if isinstance(item, (list, tuple)) and len(item) >= 2 else (None, item)
        if not isinstance(data, Mapping):
            continue
        section = data.get("r9_global_stability_evidence_input")
        if not isinstance(section, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if any(ptext.endswith(x) for x in forbidden_paths):
            warnings.append({"reason": "R9_GENERIC_EXAMPLE_REJECTED", "source": ptext})
            continue
        value = dict(section)
        score = 0
        if isinstance(value.get("stability_basis"), Mapping) and value.get("stability_basis"):
            score += 100
        explicit = value.get("explicit_stability_checks") if isinstance(value.get("explicit_stability_checks"), list) else []
        score += 1000 * sum(1 for check in explicit if isinstance(check, Mapping) and check.get("check_type"))
        limits = value.get("normative_limits") if isinstance(value.get("normative_limits"), Mapping) else {}
        for record in limits.values():
            if isinstance(record, Mapping):
                score += sum(10 for key, val in record.items() if key != "normative_reference" and val is not None)
                if str(record.get("normative_reference") or "").strip():
                    score += 20
        score += sum(1 for key, val in value.items() if key.startswith("accept_model_derived_") and val is True)
        accepted.append((score, ptext, value))
    if not accepted:
        return {}, None, warnings
    accepted.sort(key=lambda item: (-item[0], item[1]))
    if len(accepted) > 1:
        warnings.append({"reason": "R9_MULTIPLE_INPUT_CANDIDATES_RANKED", "selected_source": accepted[0][1] or None, "candidate_count": len(accepted)})
    return accepted[0][2], accepted[0][1] or None, warnings


def _derived_basis(member_verification: Mapping[str, Any]) -> dict[str, Any] | None:
    basis = member_verification.get("code_basis") or member_verification.get("design_basis")
    if not isinstance(basis, Mapping) or not basis:
        return None
    jurisdiction = basis.get("jurisdiction") or basis.get("country") or "UNVERIFIED_PROJECT_BASIS"
    standard = basis.get("standard_set") or basis.get("standard") or basis.get("design_methodology") or basis.get("reference_basis") or "V8.5_MEMBER_VERIFICATION_CODE_BASIS"
    edition = basis.get("edition") or basis.get("version") or basis.get("reference_edition") or "NOT_SEPARATELY_VERIFIED_BY_R9"
    return {"jurisdiction": str(jurisdiction), "standard_set": str(standard), "edition": str(edition), "source_reference": "V8.5_MEMBER_VERIFICATION:code_basis", "status": "TRACEABLE_CANDIDATE_BASIS_NOT_LEGAL_STATUS_VERIFICATION"}


def _check_complete(check: Mapping[str, Any]) -> bool:
    ctype = str(check.get("check_type") or "")
    if ctype not in CHECK_TYPES or not str(check.get("normative_reference") or "").strip():
        return False
    required = {
        "SECOND_ORDER_AMPLIFICATION": ("first_order_displacement_m","second_order_displacement_m","max_amplification_factor"),
        "STOREY_STABILITY_INDEX": ("storey_id","gravity_load_kN","storey_drift_m","storey_shear_kN","storey_height_m","max_stability_index"),
        "GLOBAL_BUCKLING_FACTOR": ("critical_load_factor","minimum_critical_load_factor"),
        "TORSIONAL_DRIFT_RATIO": ("storey_id","max_edge_drift_m","average_edge_drift_m","max_torsional_drift_ratio"),
        "SOFT_STOREY_STIFFNESS_RATIO": ("storey_id","storey_stiffness_kN_per_m","reference_stiffness_kN_per_m","minimum_ratio"),
        "WEAK_STOREY_STRENGTH_RATIO": ("storey_id","storey_strength_kN","reference_strength_kN","minimum_ratio"),
        "DIAPHRAGM_CONTINUITY": ("continuity_verified",),
        "LOAD_PATH_CONTINUITY": ("loaded_nodes","load_path_edges"),
        "ALTERNATE_LOAD_PATH_EVIDENCE": ("alternate_path_verified","evidence_reference"),
    }[ctype]
    return all(check.get(k) is not None for k in required)


def _template(basis: Mapping[str, Any] | None, missing: Sequence[str], derived: Mapping[str, Any]) -> dict[str, Any]:
    limits = {}
    for ctype in missing:
        limits[ctype] = {"normative_reference": None}
    limits.get("SECOND_ORDER_AMPLIFICATION", {}).update({"max_amplification_factor": None})
    limits.get("STOREY_STABILITY_INDEX", {}).update({"max_stability_index": None})
    limits.get("GLOBAL_BUCKLING_FACTOR", {}).update({"minimum_critical_load_factor": None})
    limits.get("TORSIONAL_DRIFT_RATIO", {}).update({"max_torsional_drift_ratio": None})
    limits.get("SOFT_STOREY_STIFFNESS_RATIO", {}).update({"minimum_ratio": None})
    limits.get("WEAK_STOREY_STRENGTH_RATIO", {}).update({"minimum_ratio": None})
    return {"schema_version":"phoenix.r9-global-stability-engineering-input-template/1.0","r9_global_stability_evidence_input":{"stability_basis": dict(basis or {}),"normative_limits": limits,"explicit_stability_checks": [],"accept_base_lateral_cases_as_second_order_candidate_scope": False,"accept_model_derived_diaphragm_continuity_for_candidate_check": False,"accept_model_derived_load_path_continuity_for_candidate_check": False,"accept_model_derived_nodal_spread_as_torsional_evidence": False,"notes":["Fill only values backed by traceable project/standards/engineering evidence.","Do not copy generic example thresholds into this project without an explicit verified basis.","R9 will continue to derive real model/solver evidence automatically.","Base lateral load-case NLGEOM results are evidence only unless their use as the project second-order candidate scope is explicitly accepted."]},"derived_evidence_snapshot": derived}


def build_autonomous_global_stability_evidence(*, repository: Path, project_id: str, analytical_model: Mapping[str, Any], action_load_model: Mapping[str, Any], analysis_validation: Mapping[str, Any], member_verification: Mapping[str, Any], architecture: Mapping[str, Any] | None, candidates: Sequence[Any], v84_evidence_dir: Path, output_dir: Path, policy_path: Path) -> dict[str, Any]:
    repository = Path(repository).resolve(); output_dir = Path(output_dir).resolve()
    policy = _read_json(Path(policy_path))
    member_state = str(member_verification.get("verification_state") or "")
    blockers: list[dict[str, Any]] = []; warnings: list[dict[str, Any]] = []
    if member_state not in policy["accepted_member_verification_states"]:
        blockers.append({"reason":"R9_MEMBER_VERIFICATION_CANDIDATE_PASSED_REQUIRED","message":"R9 requires MEMBER_VERIFICATION_CANDIDATE_PASSED from the current v8.5 run.","observed_state":member_state})
    r9_input, input_source, input_warnings = _extract_r9_input(candidates, policy.get("forbidden_project_evidence_paths", [])); warnings.extend(input_warnings)
    basis = r9_input.get("stability_basis") if isinstance(r9_input.get("stability_basis"), Mapping) and r9_input.get("stability_basis") else _derived_basis(member_verification)
    if not basis:
        blockers.append({"reason":"R9_TRACEABLE_STABILITY_BASIS_REQUIRED","message":"A traceable project stability basis is required; R9 does not invent a normative basis."})

    tol = float(policy["derivation"].get("coordinate_tolerance_m", 1e-6))
    topology = derive_topology_evidence(analytical_model)
    diaphragm = derive_diaphragm_evidence(analytical_model, architecture or {}, tol)
    floor_response = derive_floor_response(analytical_model, architecture or {}, analysis_validation, tol)
    second_order = run_real_second_order(repository, Path(v84_evidence_dir), output_dir) if policy["derivation"].get("run_real_calculix_nlgeom_second_order") else {"status":"DISABLED","cases":[]}
    derived = {"topology_load_path": topology,"diaphragm_connectivity": diaphragm,"first_order_floor_response": floor_response,"second_order_calculix_nlgeom": second_order,"global_buckling":{"status":"EXPLICIT_EVIDENCE_REQUIRED","reason":policy["derivation"].get("global_buckling_reason")},"weak_storey_strength":{"status":"EXPLICIT_EVIDENCE_REQUIRED"},"alternate_load_path_capacity":{"status":"EXPLICIT_ENGINEERING_SCENARIO_EVIDENCE_REQUIRED","note":"Topological connectivity alone is not promoted to robustness-capacity evidence."}}

    explicit_checks = {}
    for c in r9_input.get("explicit_stability_checks", []) if isinstance(r9_input.get("explicit_stability_checks"), list) else []:
        if isinstance(c, Mapping) and str(c.get("check_type") or "") in CHECK_TYPES:
            explicit_checks[str(c["check_type"])] = dict(c)
    limits = r9_input.get("normative_limits") if isinstance(r9_input.get("normative_limits"), Mapping) else {}
    checks: dict[str, dict[str, Any]] = dict(explicit_checks)

    # Real NLGEOM can populate the measured pair, but never its acceptance limit.
    so_limit = limits.get("SECOND_ORDER_AMPLIFICATION") if isinstance(limits.get("SECOND_ORDER_AMPLIFICATION"), Mapping) else {}
    worst = second_order.get("worst_case") if isinstance(second_order, Mapping) else None
    if r9_input.get("accept_base_lateral_cases_as_second_order_candidate_scope") is True and "SECOND_ORDER_AMPLIFICATION" not in checks and isinstance(worst, Mapping) and worst.get("status") == "PASSED" and _num(so_limit.get("max_amplification_factor")) is not None and str(so_limit.get("normative_reference") or "").strip():
        checks["SECOND_ORDER_AMPLIFICATION"] = {"id":"R9-SECOND-ORDER","check_type":"SECOND_ORDER_AMPLIFICATION","first_order_displacement_m":worst["first_order_max_horizontal_displacement_m"],"second_order_displacement_m":worst["second_order_max_horizontal_displacement_m"],"max_amplification_factor":float(so_limit["max_amplification_factor"]),"mandatory":True,"normative_reference":str(so_limit["normative_reference"]),"evidence_reference":worst.get("second_order_dat")}

    if r9_input.get("accept_model_derived_diaphragm_continuity_for_candidate_check") is True and "DIAPHRAGM_CONTINUITY" not in checks:
        ref = limits.get("DIAPHRAGM_CONTINUITY") if isinstance(limits.get("DIAPHRAGM_CONTINUITY"), Mapping) else {}
        if str(ref.get("normative_reference") or "").strip():
            checks["DIAPHRAGM_CONTINUITY"] = {"id":"R9-DIAPHRAGM","check_type":"DIAPHRAGM_CONTINUITY","continuity_verified":bool(diaphragm.get("continuity_verified")),"evidence_reference":"R9:derived_evidence.diaphragm_connectivity","mandatory":True,"normative_reference":str(ref["normative_reference"])}

    if r9_input.get("accept_model_derived_load_path_continuity_for_candidate_check") is True and "LOAD_PATH_CONTINUITY" not in checks:
        ref = limits.get("LOAD_PATH_CONTINUITY") if isinstance(limits.get("LOAD_PATH_CONTINUITY"), Mapping) else {}
        if str(ref.get("normative_reference") or "").strip() and topology.get("all_loaded_nodes_reach_support"):
            checks["LOAD_PATH_CONTINUITY"] = {"id":"R9-LOAD-PATH","check_type":"LOAD_PATH_CONTINUITY","loaded_nodes":topology["loaded_nodes"],"load_path_edges":topology["load_path_edges"],"mandatory":True,"normative_reference":str(ref["normative_reference"]),"evidence_reference":"R9:derived_evidence.topology_load_path"}

    if r9_input.get("accept_model_derived_nodal_spread_as_torsional_evidence") is True and "TORSIONAL_DRIFT_RATIO" not in checks:
        ref = limits.get("TORSIONAL_DRIFT_RATIO") if isinstance(limits.get("TORSIONAL_DRIFT_RATIO"), Mapping) else {}
        rows = [r for r in floor_response.get("combinations", []) if _num(r.get("nodal_drift_spread_ratio")) is not None and _num(r.get("average_nodal_interstorey_drift_m")) and _num(r.get("average_nodal_interstorey_drift_m")) > 0]
        if rows and _num(ref.get("max_torsional_drift_ratio")) is not None and str(ref.get("normative_reference") or "").strip():
            worst_t = max(rows, key=lambda r: r["nodal_drift_spread_ratio"])
            checks["TORSIONAL_DRIFT_RATIO"] = {"id":"R9-TORSION","check_type":"TORSIONAL_DRIFT_RATIO","storey_id":worst_t["storey_id"],"max_edge_drift_m":worst_t["max_nodal_interstorey_drift_m"],"average_edge_drift_m":worst_t["average_nodal_interstorey_drift_m"],"max_torsional_drift_ratio":float(ref["max_torsional_drift_ratio"]),"mandatory":True,"normative_reference":str(ref["normative_reference"]),"evidence_reference":"R9:derived_evidence.first_order_floor_response","evidence_caveat":"Promoted only because the explicit R9 input opted in to nodal-spread-as-torsional candidate evidence."}

    complete_types = sorted(k for k, c in checks.items() if _check_complete(c))
    incomplete_explicit = sorted(k for k, c in checks.items() if not _check_complete(c))
    missing = sorted(set(policy["required_check_types"]) - set(complete_types))
    if incomplete_explicit:
        warnings.append({"reason":"R9_INCOMPLETE_EXPLICIT_CHECKS_IGNORED","check_types":incomplete_explicit})
    final_checks = [checks[k] for k in policy["required_check_types"] if k in complete_types]
    if missing:
        blockers.append({"reason":"R9_GLOBAL_STABILITY_EVIDENCE_INCOMPLETE","message":"R9 derived all safe available evidence but cannot fabricate missing normative limits or engineering evidence.","missing_check_types":missing})

    global_input = None
    if not blockers and basis and len(final_checks) == len(policy["required_check_types"]):
        global_input = {"stability_basis":dict(basis),"stability_checks":final_checks,"stability_policy":dict(policy["v8_6_policy"]),"release_policy":{"automatic_code_compliance_claim":False,"automatic_structural_approval":False,"automatic_robustness_approval":False,"structural_model_release":LOCKED_RELEASE}}

    template = _template(basis if isinstance(basis, Mapping) else None, missing, derived)
    return {"schema_version":SCHEMA,"engine":ENGINE_ID,"version":VERSION,"project_id":project_id,"status":"PASSED" if global_input is not None else "BLOCKED","source_states":{"member_verification_state":member_state,"analysis_validation_state":analysis_validation.get("validation_state"),"r9_explicit_input_source":input_source},"derived_evidence":derived,"completed_check_types":complete_types,"missing_check_types":missing,"global_stability_input":global_input,"required_input_template":template,"summary":{"required_check_type_count":len(policy["required_check_types"]),"completed_check_type_count":len(complete_types),"missing_check_type_count":len(missing),"blocker_count":len(blockers)},"blockers":blockers,"warnings":warnings,"safety":{"normative_limits_invented":False,"automatic_code_compliance_claim":False,"automatic_structural_approval":False,"automatic_robustness_approval":False,"professional_structural_review_required":True,"production_release":LOCKED_RELEASE}}
