"""Project Phoenix R9.1 advanced global-stability evidence completion engine.

R9.1 extends R9 after v8.5 has genuinely reached
MEMBER_VERIFICATION_CANDIDATE_PASSED. It separates technical evidence from
normative qualification, adds real CalculiX linear eigenvalue-buckling evidence,
derives storey mechanics from the v8.3 equivalent nodal-load ledger and v8.4
responses, and produces a granular qualification register.

R9.1 never fabricates normative limits, professional approval, robustness
capacity, legal status, or for-construction release.
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
from typing import Any, Mapping, Sequence

ENGINE_ID = "PHX-ADVANCED-GLOBAL-STABILITY-EVIDENCE-COMPLETION-R9.1"
VERSION = "R9.1.0"
SCHEMA = "phoenix.advanced-global-stability-evidence-qualification/1.0"
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
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(repository).resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _xyz(node: Mapping[str, Any]) -> tuple[float, float, float] | None:
    values = None
    for key in ("coords", "coordinate"):
        raw = node.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) >= 3:
            values = tuple(_num(x) for x in raw[:3])
            break
    if values is None:
        values = (_num(node.get("x")), _num(node.get("y")), _num(node.get("z")))
    if any(x is None for x in values):
        return None
    return values  # type: ignore[return-value]


def _levels(model: Mapping[str, Any], architecture: Mapping[str, Any], tol: float) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, row in enumerate(architecture.get("storeys", []) if isinstance(architecture, Mapping) else []):
        if not isinstance(row, Mapping):
            continue
        elevation = _num(row.get("elevation_m"))
        if elevation is None:
            continue
        result.append({
            "id": str(row.get("storey_id") or row.get("id") or f"L{index+1}"),
            "elevation_m": elevation,
            "height_m": _num(row.get("height_m")),
        })
    if result:
        result.sort(key=lambda x: x["elevation_m"])
        return result
    zs: list[float] = []
    for node in model.get("nodes", []):
        if isinstance(node, Mapping):
            point = _xyz(node)
            if point is not None:
                zs.append(point[2])
    merged: list[float] = []
    for z in sorted(set(zs)):
        if not merged or abs(z - merged[-1]) > tol:
            merged.append(z)
    return [{"id": f"Z{i+1}", "elevation_m": z, "height_m": None} for i, z in enumerate(merged)]


def _combination_nodal_loads(solver_package: Mapping[str, Any]) -> dict[str, dict[str, tuple[float, float, float]]]:
    base_raw = solver_package.get("equivalent_nodal_loads_kN") or {}
    base: dict[str, dict[str, tuple[float, float, float]]] = {}
    if isinstance(base_raw, Mapping):
        for case_id, node_map in base_raw.items():
            if not isinstance(node_map, Mapping):
                continue
            parsed: dict[str, tuple[float, float, float]] = {}
            for node_id, vector in node_map.items():
                if isinstance(vector, Mapping):
                    vals = (_num(vector.get("FX")), _num(vector.get("FY")), _num(vector.get("FZ")))
                elif isinstance(vector, (list, tuple)) and len(vector) >= 3:
                    vals = tuple(_num(x) for x in vector[:3])
                else:
                    continue
                if any(x is None for x in vals):
                    continue
                parsed[str(node_id)] = vals  # type: ignore[assignment]
            base[str(case_id)] = parsed

    out = dict(base)
    combinations = solver_package.get("load_combinations") or []
    for combo in combinations if isinstance(combinations, list) else []:
        if not isinstance(combo, Mapping) or not combo.get("id"):
            continue
        combo_id = str(combo["id"])
        totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
        terms = combo.get("terms") or []
        for term in terms if isinstance(terms, list) else []:
            if not isinstance(term, Mapping):
                continue
            case_id = str(term.get("case_id") or "")
            coeff = _num(term.get("coefficient"))
            if coeff is None or case_id not in base:
                continue
            for node_id, vector in base[case_id].items():
                for i in range(3):
                    totals[node_id][i] += coeff * vector[i]
        if totals:
            out[combo_id] = {n: (v[0], v[1], v[2]) for n, v in totals.items()}
    return out


def _response_rows(r9_evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    derived = r9_evidence.get("derived_evidence") or {}
    floor = derived.get("first_order_floor_response") if isinstance(derived, Mapping) else {}
    rows = floor.get("combinations") if isinstance(floor, Mapping) else []
    return [dict(x) for x in rows if isinstance(x, Mapping)] if isinstance(rows, list) else []


def derive_storey_mechanics(
    model: Mapping[str, Any],
    architecture: Mapping[str, Any],
    solver_package: Mapping[str, Any],
    r9_evidence: Mapping[str, Any],
    tol: float,
) -> dict[str, Any]:
    nodes = {str(n.get("id")): _xyz(n) for n in model.get("nodes", []) if isinstance(n, Mapping) and n.get("id")}
    levels = _levels(model, architecture, tol)
    if len(levels) < 2:
        return {"status": "UNAVAILABLE", "evidence_class": "MODEL_SOLVER_DERIVED_STOREY_MECHANICS", "rows": [], "reason": "AT_LEAST_TWO_LEVELS_REQUIRED"}
    nodal = _combination_nodal_loads(solver_package)
    responses = _response_rows(r9_evidence)
    response_index = {(str(r.get("combination_id")), str(r.get("storey_id"))): r for r in responses}
    rows: list[dict[str, Any]] = []
    for combo_id, loads in sorted(nodal.items()):
        fx_total = sum(v[0] for v in loads.values())
        fy_total = sum(v[1] for v in loads.values())
        if math.hypot(fx_total, fy_total) <= 1e-12 and "W" not in combo_id.upper() and "WIND" not in combo_id.upper():
            continue
        for i in range(1, len(levels)):
            lower = levels[i-1]
            upper = levels[i]
            h = upper.get("height_m") or (upper["elevation_m"] - lower["elevation_m"])
            h = _num(h)
            if h is None or h <= tol:
                continue
            above = [nid for nid, point in nodes.items() if point is not None and point[2] > lower["elevation_m"] + tol and nid in loads]
            fx = sum(loads[n][0] for n in above)
            fy = sum(loads[n][1] for n in above)
            fz = sum(loads[n][2] for n in above)
            shear = math.hypot(fx, fy)
            gravity = abs(fz)
            response = response_index.get((combo_id, str(upper["id"])))
            # If R9 response names do not match the exact v8.3 combination, keep mechanics evidence without drift.
            drift = _num((response or {}).get("mean_interstorey_drift_m"))
            theta = (gravity * drift / (shear * h)) if drift is not None and shear > 0 else None
            stiffness = (shear / drift) if drift is not None and drift > 0 else None
            rows.append({
                "combination_id": combo_id,
                "storey_id": str(upper["id"]),
                "lower_elevation_m": lower["elevation_m"],
                "upper_elevation_m": upper["elevation_m"],
                "storey_height_m": h,
                "loaded_node_count_above_storey": len(above),
                "horizontal_shear_components_kN": {"FX": fx, "FY": fy},
                "storey_shear_kN": shear,
                "gravity_load_above_storey_kN": gravity,
                "mean_interstorey_drift_m": drift,
                "storey_stability_index_candidate": theta,
                "secant_storey_stiffness_kN_per_m": stiffness,
                "interpretation": "MEASURED_CANDIDATE_ONLY_NO_ACCEPTANCE_LIMIT_INFERRED",
            })
    by_combo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _num(row.get("secant_storey_stiffness_kN_per_m")) is not None:
            by_combo[row["combination_id"]].append(row)
    ratios: list[dict[str, Any]] = []
    for combo_id, group in by_combo.items():
        ordered = sorted(group, key=lambda x: x["upper_elevation_m"])
        for i, row in enumerate(ordered):
            k = _num(row.get("secant_storey_stiffness_kN_per_m"))
            if k is None:
                continue
            for label, j in (("BELOW", i-1), ("ABOVE", i+1)):
                if 0 <= j < len(ordered):
                    ref = _num(ordered[j].get("secant_storey_stiffness_kN_per_m"))
                    if ref is not None and ref > 0:
                        ratios.append({
                            "combination_id": combo_id,
                            "storey_id": row["storey_id"],
                            "reference_storey_id": ordered[j]["storey_id"],
                            "reference_direction": label,
                            "storey_stiffness_kN_per_m": k,
                            "reference_stiffness_kN_per_m": ref,
                            "ratio": k/ref,
                            "interpretation": "ADJACENT_STOREY_RATIO_CANDIDATE_NO_NORMATIVE_REFERENCE_METHOD_SELECTED",
                        })
    available = bool(rows)
    return {
        "status": "AVAILABLE" if available else "UNAVAILABLE",
        "evidence_class": "MODEL_SOLVER_DERIVED_STOREY_MECHANICS",
        "rows": rows,
        "adjacent_storey_stiffness_ratio_candidates": ratios,
        "note": "P, V, drift, theta and secant stiffness are derived from the v8.3 nodal-load ledger and R9/v8.4 response evidence; no acceptance threshold is inferred.",
    }


def make_buckle_deck(text: str, mode_count: int = 1) -> str:
    if mode_count < 1:
        raise ValueError("mode_count must be >= 1")
    lines = text.splitlines()
    procedure = None
    for i, line in enumerate(lines):
        stripped = line.strip().upper()
        if stripped.startswith("*STATIC") and not stripped.startswith("**"):
            procedure = i
            break
    if procedure is None:
        raise ValueError("CalculiX source deck has no *STATIC procedure")
    lines[procedure] = "*BUCKLE"
    j = procedure + 1
    while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("**")):
        j += 1
    if j < len(lines) and not lines[j].lstrip().startswith("*"):
        # Replace *STATIC increment/control data with the number of requested buckling factors.
        lines[j] = str(mode_count)
    else:
        lines.insert(procedure + 1, str(mode_count))
    return "\n".join(lines) + "\n"


_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def parse_buckling_factors(text: str) -> list[float]:
    """Parse CalculiX buckling factors without confusing the MODE NO column.

    Native CalculiX .dat output uses a BUCKLING FACTOR OUTPUT table where each
    data row begins with the mode number followed by the buckling factor.
    A labelled single-line form is accepted as a fallback for test/adapter logs.
    """
    factors: list[float] = []
    lines = text.splitlines()
    in_table = False
    header_seen = False
    for line in lines:
        normalized = " ".join(line.upper().split())
        if "B U C K L I N G" in normalized and "F A C T O R" in normalized and "O U T P U T" in normalized:
            in_table = True
            header_seen = False
            continue
        if in_table:
            if "MODE NO" in normalized and "BUCKLING" in normalized:
                header_seen = True
                continue
            if header_seen:
                parts = line.replace(",", " ").split()
                if len(parts) >= 2:
                    try:
                        int(parts[0])
                        value = float(parts[1].replace("D", "E").replace("d", "e"))
                    except (ValueError, TypeError):
                        pass
                    else:
                        if math.isfinite(value):
                            factors.append(value)
                            continue
                if factors and normalized and not re.match(r"^[+-]?\d", normalized):
                    in_table = False
        match = re.search(r"BUCKLING\s+FACTOR\s*(?:=|:)\s*(" + _FLOAT + r")", line, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace("D", "E").replace("d", "e"))
            except ValueError:
                continue
            if math.isfinite(value):
                factors.append(value)
    result: list[float] = []
    for value in factors:
        if not any(abs(value-existing) <= max(1e-12, 1e-10*abs(existing)) for existing in result):
            result.append(value)
    return result

def _find_calculix() -> Path | None:
    explicit = os.environ.get("CALCULIX_EXE") or os.environ.get("CCX_EXE")
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    for name in ("ccx.exe", "ccx", "calculix.exe", "calculix"):
        found = shutil.which(name)
        if found and Path(found).is_file():
            return Path(found)
    for path in (
        Path(r"C:\Program Files\FreeCAD 1.1\bin\ccx.exe"),
        Path(r"C:\Program Files\FreeCAD 1.0\bin\ccx.exe"),
        Path(r"C:\CalculiX\ccx.exe"),
        Path(r"C:\ccx\ccx.exe"),
    ):
        if path.is_file():
            return path
    return None


def run_real_global_buckling(repository: Path, v84_evidence_dir: Path, output_dir: Path) -> dict[str, Any]:
    if os.environ.get("PHOENIX_TEST_MODE"):
        return {"status": "SKIPPED_TEST_MODE", "evidence_class": "REAL_CALCULIX_LINEAR_BUCKLING_EVIDENCE", "cases": []}
    exe = _find_calculix()
    if exe is None:
        return {"status": "BLOCKED", "reason": "CALCULIX_EXECUTABLE_REQUIRED_FOR_R9_1_BUCKLING", "evidence_class": "REAL_CALCULIX_LINEAR_BUCKLING_EVIDENCE", "cases": []}
    cases: list[dict[str, Any]] = []
    for case_dir in sorted(Path(v84_evidence_dir).glob("LC-W*")) if Path(v84_evidence_dir).is_dir() else []:
        source = case_dir / "phoenix_v8_4_case.inp"
        if not source.is_file():
            continue
        case_id = case_dir.name
        target = Path(output_dir) / "buckling" / "calculix" / case_id
        target.mkdir(parents=True, exist_ok=True)
        job = f"phoenix_r9_1_buckle_{case_id.replace('-', '_')}"
        deck = target / f"{job}.inp"
        try:
            deck.write_text(make_buckle_deck(source.read_text(encoding="utf-8", errors="replace")), encoding="utf-8", newline="\n")
        except Exception as exc:
            cases.append({"case_id": case_id, "status": "DECK_BUILD_FAILED", "error": str(exc)})
            continue
        cp = subprocess.run([str(exe), job], cwd=target, text=True, capture_output=True, check=False, timeout=180)
        stdout = target / "solver_stdout.txt"; stderr = target / "solver_stderr.txt"
        stdout.write_text(cp.stdout or "", encoding="utf-8"); stderr.write_text(cp.stderr or "", encoding="utf-8")
        dat = target / f"{job}.dat"
        if cp.returncode != 0 or not dat.is_file():
            cases.append({"case_id": case_id, "status": "FAILED", "return_code": cp.returncode, "deck": _repo_ref(deck, repository), "stdout": _repo_ref(stdout, repository), "stderr": _repo_ref(stderr, repository)})
            continue
        factors = parse_buckling_factors(dat.read_text(encoding="utf-8", errors="replace"))
        positive = sorted(v for v in factors if v > 0)
        cases.append({
            "case_id": case_id,
            "status": "PASSED" if positive else "PARSE_FAILED",
            "buckling_factors": factors,
            "positive_buckling_factors": positive,
            "lowest_positive_buckling_factor": positive[0] if positive else None,
            "deck": _repo_ref(deck, repository),
            "dat": _repo_ref(dat, repository),
            "stdout": _repo_ref(stdout, repository),
            "stderr": _repo_ref(stderr, repository),
            "interpretation": "LINEAR_EIGENVALUE_BUCKLING_CANDIDATE_NO_ACCEPTANCE_LIMIT_INFERRED",
        })
    valid = [x for x in cases if x.get("status") == "PASSED" and _num(x.get("lowest_positive_buckling_factor")) is not None]
    governing = min(valid, key=lambda x: x["lowest_positive_buckling_factor"]) if valid else None
    return {
        "status": "PASSED" if valid else "BLOCKED",
        "evidence_class": "REAL_CALCULIX_LINEAR_BUCKLING_EVIDENCE",
        "executable": str(exe),
        "cases": cases,
        "governing_case": governing,
        "note": "CalculiX linear eigenvalue buckling factors are technical evidence only; R9.1 does not infer the project minimum acceptable factor or legal applicability.",
    }


def derive_alternate_path_topology(model: Mapping[str, Any]) -> dict[str, Any]:
    nodes = {str(n.get("id")) for n in model.get("nodes", []) if isinstance(n, Mapping) and n.get("id")}
    supports = set()
    for s in model.get("supports", []) or model.get("support_candidates", []):
        if isinstance(s, Mapping):
            nid = s.get("node_id") or s.get("node") or s.get("node_ref")
            if nid:
                supports.add(str(nid))
    members = []
    shell_edges: list[tuple[str, str]] = []
    for m in model.get("members", []):
        if isinstance(m, Mapping):
            a = str(m.get("node_i") or m.get("start_node") or ""); b = str(m.get("node_j") or m.get("end_node") or "")
            if a in nodes and b in nodes and a != b:
                members.append((str(m.get("id") or f"M{len(members)+1}"), a, b))
    for s in model.get("shells", []):
        if isinstance(s, Mapping):
            ids = [str(x) for x in (s.get("node_ids") or s.get("nodes") or []) if str(x) in nodes]
            for i, a in enumerate(ids):
                if len(ids) > 1:
                    shell_edges.append((a, ids[(i+1) % len(ids)]))
    loaded = sorted(nodes - supports)

    def reaches_support(removed_member: str | None) -> bool:
        graph: dict[str, set[str]] = {n: set() for n in nodes}
        for mid, a, b in members:
            if mid == removed_member:
                continue
            graph[a].add(b); graph[b].add(a)
        for a, b in shell_edges:
            graph[a].add(b); graph[b].add(a)
        for start in loaded:
            q = deque([start]); seen = {start}; ok = False
            while q:
                cur = q.popleft()
                if cur in supports:
                    ok = True; break
                for nxt in graph[cur]:
                    if nxt not in seen:
                        seen.add(nxt); q.append(nxt)
            if not ok:
                return False
        return bool(supports) and bool(loaded)

    cases = []
    for mid, _, _ in members:
        cases.append({"removed_member_id": mid, "all_loaded_nodes_reach_support": reaches_support(mid)})
    successful = [x for x in cases if x["all_loaded_nodes_reach_support"]]
    return {
        "status": "AVAILABLE" if cases else "UNAVAILABLE",
        "evidence_class": "TOPOLOGICAL_MEMBER_REMOVAL_REDUNDANCY_EVIDENCE",
        "member_removal_case_count": len(cases),
        "topologically_redundant_case_count": len(successful),
        "all_single_member_removal_cases_topologically_connected": bool(cases) and len(successful) == len(cases),
        "cases": cases,
        "capacity_verified": False,
        "note": "Single-member removal graph connectivity is not promoted to alternate-load-path capacity or robustness approval.",
    }


def _extract_input(candidates: Sequence[Any], forbidden_paths: Sequence[str]) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    accepted: list[tuple[int, str, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    for item in candidates:
        path, data = (item[0], item[1]) if isinstance(item, (list, tuple)) and len(item) >= 2 else (None, item)
        if not isinstance(data, Mapping):
            continue
        section = data.get("r9_1_stability_qualification_input")
        if not isinstance(section, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if any(ptext.endswith(str(x)) for x in forbidden_paths):
            warnings.append({"reason": "R9_1_GENERIC_EXAMPLE_REJECTED", "source": ptext})
            continue
        value = dict(section)
        score = 1000 * len([x for x in value.get("explicit_stability_checks", []) if isinstance(x, Mapping)])
        limits = value.get("normative_limits") if isinstance(value.get("normative_limits"), Mapping) else {}
        score += 100 * len(limits)
        score += sum(1 for k, v in value.items() if k.startswith("accept_") and v is True)
        accepted.append((score, ptext, value))
    if not accepted:
        return {}, None, warnings
    accepted.sort(key=lambda x: (-x[0], x[1]))
    return accepted[0][2], accepted[0][1] or None, warnings


def _explicit_checks(value: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    rows = value.get("explicit_stability_checks") or []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, Mapping) and str(row.get("check_type") or "") in CHECK_TYPES:
            out[str(row["check_type"])] = dict(row)
    return out


def _complete(check: Mapping[str, Any]) -> bool:
    ctype = str(check.get("check_type") or "")
    if ctype not in CHECK_TYPES or not str(check.get("normative_reference") or "").strip():
        return False
    required = {
        "SECOND_ORDER_AMPLIFICATION": ("first_order_displacement_m", "second_order_displacement_m", "max_amplification_factor"),
        "STOREY_STABILITY_INDEX": ("storey_id", "gravity_load_kN", "storey_drift_m", "storey_shear_kN", "storey_height_m", "max_stability_index"),
        "GLOBAL_BUCKLING_FACTOR": ("critical_load_factor", "minimum_critical_load_factor"),
        "TORSIONAL_DRIFT_RATIO": ("storey_id", "max_edge_drift_m", "average_edge_drift_m", "max_torsional_drift_ratio"),
        "SOFT_STOREY_STIFFNESS_RATIO": ("storey_id", "storey_stiffness_kN_per_m", "reference_stiffness_kN_per_m", "minimum_ratio"),
        "WEAK_STOREY_STRENGTH_RATIO": ("storey_id", "storey_strength_kN", "reference_strength_kN", "minimum_ratio"),
        "DIAPHRAGM_CONTINUITY": ("continuity_verified",),
        "LOAD_PATH_CONTINUITY": ("loaded_nodes", "load_path_edges"),
        "ALTERNATE_LOAD_PATH_EVIDENCE": ("alternate_path_verified", "evidence_reference"),
    }[ctype]
    return all(check.get(k) is not None for k in required)


def _qualification(status: str, evidence: Any = None, missing: Sequence[str] = (), note: str | None = None) -> dict[str, Any]:
    result = {"qualification_state": status, "missing_requirements": list(missing)}
    if evidence is not None:
        result["evidence"] = evidence
    if note:
        result["note"] = note
    return result


def build_advanced_stability_qualification(
    *,
    repository: Path,
    project_id: str,
    analytical_model: Mapping[str, Any],
    architecture: Mapping[str, Any] | None,
    solver_package: Mapping[str, Any],
    r9_evidence: Mapping[str, Any],
    candidates: Sequence[Any],
    v84_evidence_dir: Path,
    output_dir: Path,
    policy_path: Path,
) -> dict[str, Any]:
    repository = Path(repository).resolve(); output_dir = Path(output_dir).resolve()
    policy = _read_json(Path(policy_path))
    r91_input, input_source, warnings = _extract_input(candidates, policy.get("forbidden_project_evidence_paths", []))
    tol = float(policy.get("derivation", {}).get("coordinate_tolerance_m", 1e-6))
    derived_r9 = r9_evidence.get("derived_evidence") if isinstance(r9_evidence.get("derived_evidence"), Mapping) else {}
    topology = derived_r9.get("topology_load_path") if isinstance(derived_r9, Mapping) else {}
    diaphragm = derived_r9.get("diaphragm_connectivity") if isinstance(derived_r9, Mapping) else {}
    floor = derived_r9.get("first_order_floor_response") if isinstance(derived_r9, Mapping) else {}
    second = derived_r9.get("second_order_calculix_nlgeom") if isinstance(derived_r9, Mapping) else {}

    storey = derive_storey_mechanics(analytical_model, architecture or {}, solver_package, r9_evidence, tol)
    buckling = run_real_global_buckling(repository, Path(v84_evidence_dir), output_dir) if policy.get("derivation", {}).get("run_real_calculix_linear_buckling") else {"status": "DISABLED", "cases": []}
    alternate = derive_alternate_path_topology(analytical_model)
    evidence = {
        "r9_source": {"status": r9_evidence.get("status"), "summary": r9_evidence.get("summary")},
        "topology_load_path": topology,
        "diaphragm_connectivity": diaphragm,
        "first_order_floor_response": floor,
        "second_order_calculix_nlgeom": second,
        "storey_mechanics": storey,
        "global_buckling_calculix": buckling,
        "alternate_path_topology": alternate,
        "weak_storey_strength": {"status": "ANALYSIS_REQUIRED", "reason": "NO_TRACEABLE_STOREY_LATERAL_STRENGTH_CAPACITY_ENGINE_AVAILABLE_IN_R9_1"},
    }

    q: dict[str, dict[str, Any]] = {}
    worst_second = second.get("worst_case") if isinstance(second, Mapping) else None
    if isinstance(worst_second, Mapping) and _num(worst_second.get("amplification_factor")) is not None:
        q["SECOND_ORDER_AMPLIFICATION"] = _qualification("LIMIT_REFERENCE_REQUIRED", worst_second, ["candidate_scope_acceptance", "max_amplification_factor", "normative_reference"])
    else:
        q["SECOND_ORDER_AMPLIFICATION"] = _qualification("ANALYSIS_REQUIRED", second, ["real_second_order_result"])

    governing_buckle = buckling.get("governing_case") if isinstance(buckling, Mapping) else None
    if isinstance(governing_buckle, Mapping) and _num(governing_buckle.get("lowest_positive_buckling_factor")) is not None:
        q["GLOBAL_BUCKLING_FACTOR"] = _qualification("LIMIT_REFERENCE_REQUIRED", governing_buckle, ["minimum_critical_load_factor", "normative_reference"])
    else:
        q["GLOBAL_BUCKLING_FACTOR"] = _qualification("ANALYSIS_REQUIRED", buckling, ["real_linear_eigenvalue_buckling_result"])

    storey_rows = [x for x in storey.get("rows", []) if isinstance(x, Mapping) and _num(x.get("storey_stability_index_candidate")) is not None]
    if storey_rows:
        worst_theta = max(storey_rows, key=lambda x: x["storey_stability_index_candidate"])
        q["STOREY_STABILITY_INDEX"] = _qualification("LIMIT_REFERENCE_REQUIRED", worst_theta, ["max_stability_index", "normative_reference"])
    else:
        q["STOREY_STABILITY_INDEX"] = _qualification("ANALYSIS_REQUIRED", storey, ["P_delta_V_h_storey_mechanics"])

    ratios = [x for x in storey.get("adjacent_storey_stiffness_ratio_candidates", []) if isinstance(x, Mapping) and _num(x.get("ratio")) is not None]
    if ratios:
        worst_ratio = min(ratios, key=lambda x: x["ratio"])
        q["SOFT_STOREY_STIFFNESS_RATIO"] = _qualification("REFERENCE_METHOD_AND_LIMIT_REQUIRED", worst_ratio, ["reference_storey_method_acceptance", "minimum_ratio", "normative_reference"])
    else:
        q["SOFT_STOREY_STIFFNESS_RATIO"] = _qualification("ANALYSIS_REQUIRED", storey, ["storey_stiffness_evidence"])

    floor_rows = [x for x in (floor.get("combinations", []) if isinstance(floor, Mapping) else []) if isinstance(x, Mapping) and _num(x.get("nodal_drift_spread_ratio")) is not None]
    if floor_rows:
        worst_t = max(floor_rows, key=lambda x: x["nodal_drift_spread_ratio"])
        q["TORSIONAL_DRIFT_RATIO"] = _qualification("LIMIT_REFERENCE_REQUIRED", worst_t, ["nodal_spread_candidate_scope_acceptance", "max_torsional_drift_ratio", "normative_reference"])
    else:
        q["TORSIONAL_DRIFT_RATIO"] = _qualification("ANALYSIS_REQUIRED", floor, ["torsional_response_evidence"])

    if isinstance(diaphragm, Mapping) and diaphragm.get("assessed_storey_count", 0):
        q["DIAPHRAGM_CONTINUITY"] = _qualification("ENGINEERING_REFERENCE_REQUIRED", diaphragm, ["candidate_scope_acceptance", "normative_reference"], "Connectivity evidence exists; strength/stiffness adequacy is not inferred.")
    else:
        q["DIAPHRAGM_CONTINUITY"] = _qualification("ANALYSIS_REQUIRED", diaphragm, ["diaphragm_connectivity_evidence"])

    if isinstance(topology, Mapping) and topology.get("loaded_node_count", 0):
        q["LOAD_PATH_CONTINUITY"] = _qualification("ENGINEERING_REFERENCE_REQUIRED", topology, ["candidate_scope_acceptance", "normative_reference"], "Topological support connectivity exists; member capacity adequacy is not inferred.")
    else:
        q["LOAD_PATH_CONTINUITY"] = _qualification("ANALYSIS_REQUIRED", topology, ["load_path_connectivity_evidence"])

    q["ALTERNATE_LOAD_PATH_EVIDENCE"] = _qualification("ANALYSIS_REQUIRED", alternate, ["capacity_or_engineered_removal_scenario_evidence", "normative_reference"], "Topology-only removal evidence is deliberately not promoted to robustness capacity.")
    q["WEAK_STOREY_STRENGTH_RATIO"] = _qualification("ANALYSIS_REQUIRED", evidence["weak_storey_strength"], ["storey_strength_kN", "reference_strength_kN", "minimum_ratio", "normative_reference"])

    limits = r91_input.get("normative_limits") if isinstance(r91_input.get("normative_limits"), Mapping) else {}
    checks = _explicit_checks(r91_input)

    # Promote only when technical evidence, explicit scope acceptance, numeric limit, and source reference all exist.
    if "SECOND_ORDER_AMPLIFICATION" not in checks and isinstance(worst_second, Mapping) and r91_input.get("accept_base_lateral_cases_as_second_order_candidate_scope") is True:
        lim = limits.get("SECOND_ORDER_AMPLIFICATION") if isinstance(limits.get("SECOND_ORDER_AMPLIFICATION"), Mapping) else {}
        if _num(lim.get("max_amplification_factor")) is not None and str(lim.get("normative_reference") or "").strip():
            checks["SECOND_ORDER_AMPLIFICATION"] = {"id":"R9.1-SECOND-ORDER","check_type":"SECOND_ORDER_AMPLIFICATION","first_order_displacement_m":worst_second.get("first_order_max_horizontal_displacement_m"),"second_order_displacement_m":worst_second.get("second_order_max_horizontal_displacement_m"),"max_amplification_factor":float(lim["max_amplification_factor"]),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":worst_second.get("second_order_dat")}

    if "GLOBAL_BUCKLING_FACTOR" not in checks and isinstance(governing_buckle, Mapping) and r91_input.get("accept_linear_eigenvalue_buckling_as_candidate_scope") is True:
        lim = limits.get("GLOBAL_BUCKLING_FACTOR") if isinstance(limits.get("GLOBAL_BUCKLING_FACTOR"), Mapping) else {}
        if _num(lim.get("minimum_critical_load_factor")) is not None and str(lim.get("normative_reference") or "").strip():
            checks["GLOBAL_BUCKLING_FACTOR"] = {"id":"R9.1-BUCKLING","check_type":"GLOBAL_BUCKLING_FACTOR","critical_load_factor":governing_buckle.get("lowest_positive_buckling_factor"),"minimum_critical_load_factor":float(lim["minimum_critical_load_factor"]),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":governing_buckle.get("dat")}

    if "STOREY_STABILITY_INDEX" not in checks and storey_rows:
        lim = limits.get("STOREY_STABILITY_INDEX") if isinstance(limits.get("STOREY_STABILITY_INDEX"), Mapping) else {}
        if _num(lim.get("max_stability_index")) is not None and str(lim.get("normative_reference") or "").strip():
            row = max(storey_rows, key=lambda x: x["storey_stability_index_candidate"])
            checks["STOREY_STABILITY_INDEX"] = {"id":"R9.1-STABILITY-INDEX","check_type":"STOREY_STABILITY_INDEX","storey_id":row["storey_id"],"gravity_load_kN":row["gravity_load_above_storey_kN"],"storey_drift_m":row["mean_interstorey_drift_m"],"storey_shear_kN":row["storey_shear_kN"],"storey_height_m":row["storey_height_m"],"max_stability_index":float(lim["max_stability_index"]),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":"R9.1:storey_mechanics"}

    if "TORSIONAL_DRIFT_RATIO" not in checks and floor_rows and r91_input.get("accept_model_derived_nodal_spread_as_torsional_candidate") is True:
        lim = limits.get("TORSIONAL_DRIFT_RATIO") if isinstance(limits.get("TORSIONAL_DRIFT_RATIO"), Mapping) else {}
        if _num(lim.get("max_torsional_drift_ratio")) is not None and str(lim.get("normative_reference") or "").strip():
            row = max(floor_rows, key=lambda x: x["nodal_drift_spread_ratio"])
            checks["TORSIONAL_DRIFT_RATIO"] = {"id":"R9.1-TORSION","check_type":"TORSIONAL_DRIFT_RATIO","storey_id":row["storey_id"],"max_edge_drift_m":row["max_nodal_interstorey_drift_m"],"average_edge_drift_m":row["average_nodal_interstorey_drift_m"],"max_torsional_drift_ratio":float(lim["max_torsional_drift_ratio"]),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":"R9:first_order_floor_response"}

    if "SOFT_STOREY_STIFFNESS_RATIO" not in checks and ratios and r91_input.get("accept_adjacent_storey_stiffness_reference_method") is True:
        lim = limits.get("SOFT_STOREY_STIFFNESS_RATIO") if isinstance(limits.get("SOFT_STOREY_STIFFNESS_RATIO"), Mapping) else {}
        if _num(lim.get("minimum_ratio")) is not None and str(lim.get("normative_reference") or "").strip():
            row = min(ratios, key=lambda x: x["ratio"])
            checks["SOFT_STOREY_STIFFNESS_RATIO"] = {"id":"R9.1-SOFT-STOREY","check_type":"SOFT_STOREY_STIFFNESS_RATIO","storey_id":row["storey_id"],"storey_stiffness_kN_per_m":row["storey_stiffness_kN_per_m"],"reference_stiffness_kN_per_m":row["reference_stiffness_kN_per_m"],"minimum_ratio":float(lim["minimum_ratio"]),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":"R9.1:storey_mechanics.adjacent_storey_stiffness_ratio_candidates"}

    if "DIAPHRAGM_CONTINUITY" not in checks and isinstance(diaphragm, Mapping) and r91_input.get("accept_model_derived_diaphragm_continuity_for_candidate_check") is True:
        lim = limits.get("DIAPHRAGM_CONTINUITY") if isinstance(limits.get("DIAPHRAGM_CONTINUITY"), Mapping) else {}
        if str(lim.get("normative_reference") or "").strip():
            checks["DIAPHRAGM_CONTINUITY"] = {"id":"R9.1-DIAPHRAGM","check_type":"DIAPHRAGM_CONTINUITY","continuity_verified":bool(diaphragm.get("continuity_verified")),"evidence_reference":"R9:diaphragm_connectivity","mandatory":True,"normative_reference":str(lim["normative_reference"])}

    if "LOAD_PATH_CONTINUITY" not in checks and isinstance(topology, Mapping) and topology.get("all_loaded_nodes_reach_support") and r91_input.get("accept_model_derived_load_path_continuity_for_candidate_check") is True:
        lim = limits.get("LOAD_PATH_CONTINUITY") if isinstance(limits.get("LOAD_PATH_CONTINUITY"), Mapping) else {}
        if str(lim.get("normative_reference") or "").strip():
            checks["LOAD_PATH_CONTINUITY"] = {"id":"R9.1-LOAD-PATH","check_type":"LOAD_PATH_CONTINUITY","loaded_nodes":topology.get("loaded_nodes"),"load_path_edges":topology.get("load_path_edges"),"mandatory":True,"normative_reference":str(lim["normative_reference"]),"evidence_reference":"R9:topology_load_path"}

    complete = sorted(k for k, v in checks.items() if _complete(v))
    missing = sorted(set(policy["required_check_types"]) - set(complete))
    final_checks = [checks[k] for k in policy["required_check_types"] if k in complete]
    basis = r91_input.get("stability_basis") if isinstance(r91_input.get("stability_basis"), Mapping) and r91_input.get("stability_basis") else None
    if basis is None:
        source_basis = r9_evidence.get("required_input_template") or {}
        source_input = source_basis.get("r9_global_stability_evidence_input") if isinstance(source_basis, Mapping) else {}
        candidate_basis = source_input.get("stability_basis") if isinstance(source_input, Mapping) else None
        if isinstance(candidate_basis, Mapping) and candidate_basis:
            basis = dict(candidate_basis)

    global_input = None
    if basis and len(final_checks) == len(policy["required_check_types"]):
        global_input = {
            "stability_basis": dict(basis),
            "stability_checks": final_checks,
            "stability_policy": dict(policy["v8_6_policy"]),
            "release_policy": {"automatic_code_compliance_claim":False,"automatic_structural_approval":False,"automatic_robustness_approval":False,"structural_model_release":LOCKED_RELEASE},
        }

    technical_available = sorted(k for k, v in q.items() if v["qualification_state"] not in {"ANALYSIS_REQUIRED"})
    blockers = []
    if global_input is None:
        blockers.append({
            "reason": "R9_1_GLOBAL_STABILITY_QUALIFICATION_INCOMPLETE",
            "message": "R9.1 completed all safe technical derivations available to this engine, but v8.6 still requires explicit project limits/references and/or engineering analyses for the remaining checks.",
            "missing_check_types": missing,
            "technical_evidence_available_for": technical_available,
            "analysis_required_for": sorted(k for k, v in q.items() if v["qualification_state"] == "ANALYSIS_REQUIRED"),
        })

    template = {
        "schema_version": "phoenix.r9-1-stability-qualification-input-template/1.0",
        "r9_1_stability_qualification_input": {
            "stability_basis": dict(basis or {}),
            "normative_limits": {k: {"normative_reference": None} for k in missing},
            "explicit_stability_checks": [],
            "accept_base_lateral_cases_as_second_order_candidate_scope": False,
            "accept_linear_eigenvalue_buckling_as_candidate_scope": False,
            "accept_model_derived_nodal_spread_as_torsional_candidate": False,
            "accept_adjacent_storey_stiffness_reference_method": False,
            "accept_model_derived_diaphragm_continuity_for_candidate_check": False,
            "accept_model_derived_load_path_continuity_for_candidate_check": False,
            "notes": [
                "Provide only traceable project/standards/engineering values.",
                "Do not copy generic v8.6 example thresholds into the project.",
                "R9.1 technical evidence does not constitute code compliance or professional approval.",
                "Weak-storey strength and alternate-load-path capacity require explicit engineering evidence unless a future verified engine supplies them.",
            ],
        },
        "qualification_register_snapshot": q,
    }
    # Add expected numeric fields only where they are still required, always null.
    nl = template["r9_1_stability_qualification_input"]["normative_limits"]
    for key, field in (
        ("SECOND_ORDER_AMPLIFICATION", "max_amplification_factor"),
        ("GLOBAL_BUCKLING_FACTOR", "minimum_critical_load_factor"),
        ("STOREY_STABILITY_INDEX", "max_stability_index"),
        ("TORSIONAL_DRIFT_RATIO", "max_torsional_drift_ratio"),
        ("SOFT_STOREY_STIFFNESS_RATIO", "minimum_ratio"),
        ("WEAK_STOREY_STRENGTH_RATIO", "minimum_ratio"),
    ):
        if key in nl:
            nl[key][field] = None

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if global_input is not None else "BLOCKED",
        "source_states": {"r9_status": r9_evidence.get("status"), "explicit_input_source": input_source},
        "technical_evidence": evidence,
        "qualification_register": q,
        "technical_evidence_available_for": technical_available,
        "completed_check_types": complete,
        "missing_check_types": missing,
        "global_stability_input": global_input,
        "required_input_template": template,
        "summary": {
            "required_check_type_count": len(policy["required_check_types"]),
            "technical_evidence_available_count": len(technical_available),
            "v8_6_completed_check_type_count": len(complete),
            "missing_check_type_count": len(missing),
            "analysis_required_check_type_count": sum(1 for v in q.values() if v["qualification_state"] == "ANALYSIS_REQUIRED"),
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            "normative_limits_invented": False,
            "generic_v8_6_example_limits_accepted_as_project_evidence": False,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
