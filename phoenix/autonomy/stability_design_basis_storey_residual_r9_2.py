"""Project Phoenix R9.2 stability design-basis, storey-completeness and residual-evidence engine.

R9.2 runs only after R9.1 remains blocked. It verifies architecturally
expected structural storey boundaries, reconstructs floor response on those
boundaries, filters base/support numerical noise from torsional candidates,
and accepts weak-storey or alternate-path capacity only from explicit
traceable engineering evidence.

R9.2 never invents normative limits, legal applicability, storey strength,
alternate-path capacity, professional approval, or for-construction release.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .advanced_global_stability_qualification_r9_1 import derive_storey_mechanics
from .autonomous_global_stability_evidence_r9 import derive_floor_response

ENGINE_ID = "PHX-STABILITY-DESIGN-BASIS-STOREY-COMPLETENESS-RESIDUAL-R9.2"
VERSION = "R9.2.0"
SCHEMA = "phoenix.stability-design-basis-storey-completeness-residual/1.0"
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


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _xyz(node: Mapping[str, Any]) -> tuple[float, float, float] | None:
    for key in ("coords", "coordinate"):
        raw = node.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) >= 3:
            values = tuple(_num(x) for x in raw[:3])
            if all(x is not None for x in values):
                return values  # type: ignore[return-value]
    values = (_num(node.get("x")), _num(node.get("y")), _num(node.get("z")))
    if any(x is None for x in values):
        return None
    return values  # type: ignore[return-value]


def _merge_z(values: Sequence[float], tol: float) -> list[float]:
    merged: list[float] = []
    for value in sorted(values):
        if not merged or abs(value - merged[-1]) > tol:
            merged.append(float(value))
    return merged


def expected_structural_levels(architecture: Mapping[str, Any], tol: float) -> dict[str, Any]:
    storeys: list[dict[str, Any]] = []
    for index, row in enumerate(architecture.get("storeys", []) if isinstance(architecture, Mapping) else []):
        if not isinstance(row, Mapping):
            continue
        z = _num(row.get("elevation_m"))
        if z is None:
            continue
        storeys.append({
            "storey_id": str(row.get("storey_id") or row.get("id") or f"L{index}"),
            "elevation_m": z,
            "height_m": _num(row.get("height_m")),
        })
    storeys.sort(key=lambda x: x["elevation_m"])
    if not storeys:
        return {
            "status": "UNAVAILABLE",
            "storeys": [],
            "levels": [],
            "reason": "ARCHITECTURAL_STOREY_ELEVATIONS_REQUIRED",
        }

    records: list[dict[str, Any]] = []
    for row in storeys:
        records.append({
            "level_id": row["storey_id"],
            "elevation_m": row["elevation_m"],
            "source": "ARCHITECTURAL_STOREY_ELEVATION",
        })
    top = storeys[-1]
    top_height = _num(top.get("height_m"))
    roof_known = top_height is not None and top_height > tol
    if roof_known:
        records.append({
            "level_id": f"{top['storey_id']}_TOP",
            "elevation_m": top["elevation_m"] + float(top_height),
            "source": "ARCHITECTURAL_TOP_STOREY_HEIGHT",
        })

    deduped: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda x: x["elevation_m"]):
        if deduped and abs(record["elevation_m"] - deduped[-1]["elevation_m"]) <= tol:
            if record["source"] == "ARCHITECTURAL_STOREY_ELEVATION":
                deduped[-1] = record
            continue
        deduped.append(record)
    return {
        "status": "AVAILABLE" if roof_known else "INCOMPLETE",
        "storeys": storeys,
        "levels": deduped,
        "top_boundary_known": roof_known,
        "reason": None if roof_known else "TOP_STOREY_HEIGHT_REQUIRED_TO_VERIFY_STRUCTURAL_STOREY_COMPLETENESS",
    }


def _member_nodes(member: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(member.get("node_i") or member.get("start_node") or member.get("node_start") or ""),
        str(member.get("node_j") or member.get("end_node") or member.get("node_end") or ""),
    )


def assess_storey_model_completeness(
    analytical_model: Mapping[str, Any],
    architecture: Mapping[str, Any],
    tol: float,
) -> dict[str, Any]:
    expected = expected_structural_levels(architecture, tol)
    nodes = {
        str(row.get("id")): _xyz(row)
        for row in analytical_model.get("nodes", [])
        if isinstance(row, Mapping) and row.get("id")
    }
    model_levels = _merge_z([point[2] for point in nodes.values() if point is not None], tol)
    if expected["status"] == "UNAVAILABLE":
        return {
            "status": "BLOCKED",
            "reason": "ARCHITECTURAL_STOREY_ELEVATIONS_REQUIRED",
            "expected": expected,
            "detected_model_levels_m": model_levels,
            "missing_expected_levels_m": [],
            "intervals": [],
        }

    level_rows = []
    missing: list[float] = []
    for level in expected["levels"]:
        z = float(level["elevation_m"])
        matching = sorted(nid for nid, point in nodes.items() if point is not None and abs(point[2] - z) <= tol)
        nearest = min(model_levels, key=lambda x: abs(x - z)) if model_levels else None
        matched = nearest is not None and abs(float(nearest) - z) <= tol and bool(matching)
        if not matched:
            missing.append(z)
        level_rows.append({
            **level,
            "matched": matched,
            "matching_node_count": len(matching),
            "matching_node_ids": matching,
            "matched_model_elevation_m": nearest if matched else None,
        })

    intervals: list[dict[str, Any]] = []
    expected_levels = expected["levels"]
    for index in range(1, len(expected_levels)):
        lower = expected_levels[index - 1]
        upper = expected_levels[index]
        z0 = float(lower["elevation_m"])
        z1 = float(upper["elevation_m"])
        vertical_members: list[str] = []
        for mindex, member in enumerate(analytical_model.get("members", [])):
            if not isinstance(member, Mapping):
                continue
            a, b = _member_nodes(member)
            pa, pb = nodes.get(a), nodes.get(b)
            if pa is None or pb is None:
                continue
            low, high = sorted((pa[2], pb[2]))
            if low <= z0 + tol and high >= z1 - tol and high - low > tol:
                vertical_members.append(str(member.get("id") or f"M{mindex + 1}"))
        vertical_shell_edges = 0
        for shell in analytical_model.get("shells", []):
            if not isinstance(shell, Mapping):
                continue
            ids = [str(x) for x in (shell.get("node_ids") or shell.get("nodes") or [])]
            for i, a in enumerate(ids):
                if len(ids) < 2:
                    break
                b = ids[(i + 1) % len(ids)]
                pa, pb = nodes.get(a), nodes.get(b)
                if pa is None or pb is None:
                    continue
                low, high = sorted((pa[2], pb[2]))
                if low <= z0 + tol and high >= z1 - tol and high - low > tol:
                    vertical_shell_edges += 1
        intervals.append({
            "interval_id": f"{lower['level_id']}->{upper['level_id']}",
            "lower_elevation_m": z0,
            "upper_elevation_m": z1,
            "height_m": z1 - z0,
            "vertical_member_count": len(vertical_members),
            "vertical_member_ids": vertical_members,
            "vertical_shell_edge_count": vertical_shell_edges,
            "vertical_load_path_candidate_present": bool(vertical_members or vertical_shell_edges),
        })

    missing_paths = [x["interval_id"] for x in intervals if not x["vertical_load_path_candidate_present"]]
    top_boundary_known = bool(expected.get("top_boundary_known"))
    passed = top_boundary_known and not missing and not missing_paths and len(intervals) >= 1
    reason = None
    if not top_boundary_known:
        reason = "TOP_STOREY_HEIGHT_REQUIRED_TO_VERIFY_STRUCTURAL_STOREY_COMPLETENESS"
    elif missing:
        reason = "EXPECTED_STRUCTURAL_STOREY_LEVEL_MISSING"
    elif missing_paths:
        reason = "STRUCTURAL_STOREY_VERTICAL_LOAD_PATH_MISSING"
    elif not intervals:
        reason = "STRUCTURAL_STOREY_INTERVAL_REQUIRED"
    return {
        "status": "PASSED" if passed else "BLOCKED",
        "reason": reason,
        "architecture_storey_count": len(expected.get("storeys", [])),
        "expected_structural_level_count": len(expected_levels),
        "expected_storey_interval_count": max(0, len(expected_levels) - 1),
        "detected_model_levels_m": model_levels,
        "levels": level_rows,
        "missing_expected_levels_m": missing,
        "intervals": intervals,
        "missing_vertical_path_intervals": missing_paths,
        "note": "The top of the top architectural storey is a required structural boundary when its height is explicit.",
    }


def augmented_architecture_from_completeness(completeness: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    levels = completeness.get("levels", []) if isinstance(completeness, Mapping) else []
    for index, level in enumerate(levels if isinstance(levels, list) else []):
        if not isinstance(level, Mapping):
            continue
        z = _num(level.get("elevation_m"))
        if z is None:
            continue
        next_z = _num(levels[index + 1].get("elevation_m")) if index + 1 < len(levels) and isinstance(levels[index + 1], Mapping) else None
        rows.append({
            "storey_id": str(level.get("level_id") or f"R92-L{index}"),
            "elevation_m": z,
            "height_m": (next_z - z) if next_z is not None and next_z > z else None,
        })
    return {"storeys": rows}


def corrected_torsional_response(
    floor_response: Mapping[str, Any],
    completeness: Mapping[str, Any],
    numerical_drift_floor_m: float,
) -> dict[str, Any]:
    rows = [dict(x) for x in floor_response.get("combinations", []) if isinstance(x, Mapping)] if isinstance(floor_response, Mapping) else []
    levels = completeness.get("levels", []) if isinstance(completeness, Mapping) else []
    base_values = [_num(x.get("elevation_m")) for x in levels if isinstance(x, Mapping)]
    base = min((x for x in base_values if x is not None), default=None)
    candidates: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        z = _num(row.get("elevation_m"))
        avg = _num(row.get("average_nodal_interstorey_drift_m"))
        mean = _num(row.get("mean_interstorey_drift_m"))
        ratio = _num(row.get("nodal_drift_spread_ratio"))
        count = int(row.get("node_count") or 0)
        reasons = []
        if base is not None and (z is None or z <= base + 1e-9):
            reasons.append("BASE_OR_SUPPORT_LEVEL_EXCLUDED")
        if avg is None or avg <= numerical_drift_floor_m:
            reasons.append("AVERAGE_DRIFT_BELOW_NUMERICAL_EVIDENCE_FLOOR")
        if mean is None or mean <= numerical_drift_floor_m:
            reasons.append("MEAN_DRIFT_BELOW_NUMERICAL_EVIDENCE_FLOOR")
        if ratio is None:
            reasons.append("FINITE_DRIFT_SPREAD_RATIO_REQUIRED")
        if count < 3:
            reasons.append("AT_LEAST_THREE_LEVEL_NODES_REQUIRED")
        if reasons:
            excluded.append({
                "combination_id": row.get("combination_id"),
                "storey_id": row.get("storey_id"),
                "elevation_m": z,
                "reasons": reasons,
            })
        else:
            candidates.append(row)
    governing = max(candidates, key=lambda x: float(x["nodal_drift_spread_ratio"])) if candidates else None
    return {
        "status": "AVAILABLE" if governing else "ANALYSIS_REQUIRED",
        "evidence_class": "R9_2_NUMERICALLY_FILTERED_TORSIONAL_DRIFT_CANDIDATE",
        "numerical_drift_floor_m": numerical_drift_floor_m,
        "candidate_count": len(candidates),
        "excluded_row_count": len(excluded),
        "governing_candidate": governing,
        "excluded_rows": excluded,
        "note": "The drift floor is a numerical evidence-quality filter, not a code acceptance limit. Base/support and near-zero drift rows are excluded.",
    }


def _explicit_strength_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    rows = value.get("storey_strength_evidence") or []
    valid = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        strength = _num(row.get("storey_strength_kN"))
        reference = _num(row.get("reference_strength_kN"))
        if strength is None or reference is None or reference <= 0:
            continue
        if not str(row.get("evidence_reference") or "").strip() or not str(row.get("methodology_reference") or "").strip():
            continue
        valid.append({**dict(row), "ratio": strength / reference})
    governing = min(valid, key=lambda x: x["ratio"]) if valid else None
    return {
        "status": "AVAILABLE" if governing else "ANALYSIS_REQUIRED",
        "evidence_class": "EXPLICIT_TRACEABLE_STOREY_STRENGTH_EVIDENCE",
        "rows": valid,
        "governing_candidate": governing,
        "invented_capacity": False,
    }


def _explicit_alternate_path_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    row = value.get("alternate_path_capacity_evidence")
    if isinstance(row, Mapping) and isinstance(row.get("alternate_path_verified"), bool):
        if str(row.get("evidence_reference") or "").strip() and str(row.get("methodology_reference") or "").strip():
            return {
                "status": "AVAILABLE",
                "evidence_class": "EXPLICIT_TRACEABLE_ALTERNATE_PATH_CAPACITY_EVIDENCE",
                **dict(row),
                "invented_capacity": False,
            }
    return {
        "status": "ANALYSIS_REQUIRED",
        "evidence_class": "EXPLICIT_TRACEABLE_ALTERNATE_PATH_CAPACITY_EVIDENCE",
        "invented_capacity": False,
    }


def _extract_input(candidates: Sequence[Any], forbidden_paths: Sequence[str]) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    inherited: list[tuple[int, str, dict[str, Any]]] = []
    direct: list[tuple[int, str, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    for item in candidates:
        path, data = (item[0], item[1]) if isinstance(item, (list, tuple)) and len(item) >= 2 else (None, item)
        if not isinstance(data, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if any(ptext.endswith(str(x)) for x in forbidden_paths):
            warnings.append({"reason": "R9_2_GENERIC_EXAMPLE_REJECTED", "source": ptext})
            continue
        for key, bucket, base_score in (
            ("r9_1_stability_qualification_input", inherited, 0),
            ("r9_2_stability_design_basis_input", direct, 100000),
        ):
            section = data.get(key)
            if not isinstance(section, Mapping):
                continue
            value = dict(section)
            explicit = value.get("explicit_stability_checks") if isinstance(value.get("explicit_stability_checks"), list) else []
            limits = value.get("normative_limits") if isinstance(value.get("normative_limits"), Mapping) else {}
            score = base_score + 1000 * len(explicit) + 100 * len(limits)
            bucket.append((score, ptext, value))
    merged: dict[str, Any] = {}
    source = None
    if inherited:
        inherited.sort(key=lambda x: (-x[0], x[1]))
        merged.update(inherited[0][2])
        source = inherited[0][1] or source
    if direct:
        direct.sort(key=lambda x: (-x[0], x[1]))
        merged.update(direct[0][2])
        source = direct[0][1] or source
    return merged, source, warnings


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


def _explicit_checks(value: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    rows = value.get("explicit_stability_checks") if isinstance(value.get("explicit_stability_checks"), list) else []
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("check_type") or "") in CHECK_TYPES:
            result[str(row["check_type"])] = dict(row)
    return result


def _q(state: str, evidence: Any, missing: Sequence[str], note: str | None = None) -> dict[str, Any]:
    result = {"qualification_state": state, "missing_requirements": list(missing), "evidence": evidence}
    if note:
        result["note"] = note
    return result


def _basis_from_r91(r91: Mapping[str, Any]) -> dict[str, Any]:
    template = r91.get("required_input_template") if isinstance(r91.get("required_input_template"), Mapping) else {}
    section = template.get("r9_1_stability_qualification_input") if isinstance(template, Mapping) else {}
    basis = section.get("stability_basis") if isinstance(section, Mapping) else None
    return dict(basis) if isinstance(basis, Mapping) else {}


def build_stability_design_basis_storey_residual(
    *,
    repository: Path,
    project_id: str,
    analytical_model: Mapping[str, Any],
    architecture: Mapping[str, Any] | None,
    solver_package: Mapping[str, Any],
    analysis_validation: Mapping[str, Any],
    r9_evidence: Mapping[str, Any],
    r91_qualification: Mapping[str, Any],
    candidates: Sequence[Any],
    policy_path: Path,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    tol = float(policy.get("derivation", {}).get("coordinate_tolerance_m", 1e-6))
    numerical_floor = float(policy.get("derivation", {}).get("torsional_numerical_drift_floor_m", 1e-10))
    input_value, input_source, warnings = _extract_input(candidates, policy.get("forbidden_project_evidence_paths", []))

    completeness = assess_storey_model_completeness(analytical_model, architecture or {}, tol)
    augmented_arch = augmented_architecture_from_completeness(completeness)
    floor = derive_floor_response(analytical_model, augmented_arch, analysis_validation, tol) if augmented_arch.get("storeys") else {"status": "UNAVAILABLE", "combinations": []}
    torsion = corrected_torsional_response(floor, completeness, numerical_floor)

    r9_aug = dict(r9_evidence)
    derived = dict(r9_evidence.get("derived_evidence") or {}) if isinstance(r9_evidence.get("derived_evidence"), Mapping) else {}
    derived["first_order_floor_response"] = floor
    r9_aug["derived_evidence"] = derived
    if augmented_arch.get("storeys"):
        storey_mechanics = derive_storey_mechanics(analytical_model, augmented_arch, solver_package, r9_aug, tol)
    else:
        storey_mechanics = {"status": "UNAVAILABLE", "rows": [], "adjacent_storey_stiffness_ratio_candidates": []}
    ratios = [dict(x) for x in storey_mechanics.get("adjacent_storey_stiffness_ratio_candidates", []) if isinstance(x, Mapping) and _num(x.get("ratio")) is not None]
    governing_soft = min(ratios, key=lambda x: x["ratio"]) if ratios else None

    strength = _explicit_strength_evidence(input_value)
    alternate = _explicit_alternate_path_evidence(input_value)
    r91_q = r91_qualification.get("qualification_register") if isinstance(r91_qualification.get("qualification_register"), Mapping) else {}
    topology = (r91_q.get("LOAD_PATH_CONTINUITY") or {}).get("evidence") if isinstance(r91_q.get("LOAD_PATH_CONTINUITY"), Mapping) else None
    diaphragm = (r91_q.get("DIAPHRAGM_CONTINUITY") or {}).get("evidence") if isinstance(r91_q.get("DIAPHRAGM_CONTINUITY"), Mapping) else None
    second = (r91_q.get("SECOND_ORDER_AMPLIFICATION") or {}).get("evidence") if isinstance(r91_q.get("SECOND_ORDER_AMPLIFICATION"), Mapping) else None
    buckling = (r91_q.get("GLOBAL_BUCKLING_FACTOR") or {}).get("evidence") if isinstance(r91_q.get("GLOBAL_BUCKLING_FACTOR"), Mapping) else None
    stability = (r91_q.get("STOREY_STABILITY_INDEX") or {}).get("evidence") if isinstance(r91_q.get("STOREY_STABILITY_INDEX"), Mapping) else None

    q: dict[str, dict[str, Any]] = {}
    q["SECOND_ORDER_AMPLIFICATION"] = _q("LIMIT_REFERENCE_REQUIRED", second, ["candidate_scope_acceptance", "max_amplification_factor", "normative_reference"]) if isinstance(second, Mapping) else _q("ANALYSIS_REQUIRED", second, ["real_second_order_result"])
    q["GLOBAL_BUCKLING_FACTOR"] = _q("LIMIT_REFERENCE_REQUIRED", buckling, ["minimum_critical_load_factor", "normative_reference"]) if isinstance(buckling, Mapping) else _q("ANALYSIS_REQUIRED", buckling, ["real_linear_eigenvalue_buckling_result"])
    q["STOREY_STABILITY_INDEX"] = _q("LIMIT_REFERENCE_REQUIRED", stability, ["max_stability_index", "normative_reference"]) if isinstance(stability, Mapping) else _q("ANALYSIS_REQUIRED", stability, ["P_delta_V_h_storey_mechanics"])
    if torsion.get("status") == "AVAILABLE":
        q["TORSIONAL_DRIFT_RATIO"] = _q("LIMIT_REFERENCE_REQUIRED", torsion["governing_candidate"], ["candidate_scope_acceptance", "max_torsional_drift_ratio", "normative_reference"], "Base/support and near-zero drift rows were excluded by R9.2.")
    else:
        q["TORSIONAL_DRIFT_RATIO"] = _q("ANALYSIS_REQUIRED", torsion, ["non_base_torsional_response_evidence"])
    if completeness.get("status") == "PASSED" and governing_soft:
        q["SOFT_STOREY_STIFFNESS_RATIO"] = _q("REFERENCE_METHOD_AND_LIMIT_REQUIRED", governing_soft, ["reference_storey_method_acceptance", "minimum_ratio", "normative_reference"])
    else:
        q["SOFT_STOREY_STIFFNESS_RATIO"] = _q("ANALYSIS_REQUIRED", {"storey_model_completeness": completeness, "storey_mechanics": storey_mechanics}, ["complete_multi_storey_structural_model", "comparable_storey_stiffness_evidence"])
    if strength.get("status") == "AVAILABLE":
        q["WEAK_STOREY_STRENGTH_RATIO"] = _q("LIMIT_REFERENCE_REQUIRED", strength["governing_candidate"], ["minimum_ratio", "normative_reference"])
    else:
        q["WEAK_STOREY_STRENGTH_RATIO"] = _q("ANALYSIS_REQUIRED", strength, ["traceable_storey_lateral_strength_capacity", "aggregation_methodology_reference"])
    if alternate.get("status") == "AVAILABLE":
        q["ALTERNATE_LOAD_PATH_EVIDENCE"] = _q("ENGINEERING_REFERENCE_REQUIRED", alternate, ["normative_reference"])
    else:
        q["ALTERNATE_LOAD_PATH_EVIDENCE"] = _q("ANALYSIS_REQUIRED", alternate, ["capacity_or_engineered_removal_scenario_evidence", "methodology_reference", "normative_reference"])
    q["DIAPHRAGM_CONTINUITY"] = _q("ENGINEERING_REFERENCE_REQUIRED", diaphragm, ["candidate_scope_acceptance", "normative_reference"], "Connectivity evidence is not diaphragm strength/stiffness adequacy.") if isinstance(diaphragm, Mapping) else _q("ANALYSIS_REQUIRED", diaphragm, ["diaphragm_connectivity_evidence"])
    q["LOAD_PATH_CONTINUITY"] = _q("ENGINEERING_REFERENCE_REQUIRED", topology, ["candidate_scope_acceptance", "normative_reference"], "Topology evidence is not member-capacity adequacy.") if isinstance(topology, Mapping) else _q("ANALYSIS_REQUIRED", topology, ["load_path_connectivity_evidence"])

    limits = input_value.get("normative_limits") if isinstance(input_value.get("normative_limits"), Mapping) else {}
    checks = _explicit_checks(input_value)
    accept = input_value.get("engineering_scope_acceptance") if isinstance(input_value.get("engineering_scope_acceptance"), Mapping) else {}

    def lim(ctype: str) -> Mapping[str, Any]:
        value = limits.get(ctype)
        return value if isinstance(value, Mapping) else {}

    if "SECOND_ORDER_AMPLIFICATION" not in checks and isinstance(second, Mapping) and accept.get("base_lateral_nlgeom_second_order_candidate_scope") is True:
        value = lim("SECOND_ORDER_AMPLIFICATION")
        if _num(value.get("max_amplification_factor")) is not None and str(value.get("normative_reference") or "").strip():
            checks["SECOND_ORDER_AMPLIFICATION"] = {"id": "R9.2-SECOND-ORDER", "check_type": "SECOND_ORDER_AMPLIFICATION", "first_order_displacement_m": second.get("first_order_max_horizontal_displacement_m"), "second_order_displacement_m": second.get("second_order_max_horizontal_displacement_m"), "max_amplification_factor": float(value["max_amplification_factor"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": second.get("second_order_dat")}
    if "GLOBAL_BUCKLING_FACTOR" not in checks and isinstance(buckling, Mapping) and accept.get("linear_eigenvalue_buckling_candidate_scope") is True:
        value = lim("GLOBAL_BUCKLING_FACTOR")
        if _num(value.get("minimum_critical_load_factor")) is not None and str(value.get("normative_reference") or "").strip():
            checks["GLOBAL_BUCKLING_FACTOR"] = {"id": "R9.2-BUCKLING", "check_type": "GLOBAL_BUCKLING_FACTOR", "critical_load_factor": buckling.get("lowest_positive_buckling_factor"), "minimum_critical_load_factor": float(value["minimum_critical_load_factor"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": buckling.get("dat")}
    if "STOREY_STABILITY_INDEX" not in checks and isinstance(stability, Mapping):
        value = lim("STOREY_STABILITY_INDEX")
        if _num(value.get("max_stability_index")) is not None and str(value.get("normative_reference") or "").strip():
            checks["STOREY_STABILITY_INDEX"] = {"id": "R9.2-STABILITY-INDEX", "check_type": "STOREY_STABILITY_INDEX", "storey_id": stability.get("storey_id"), "gravity_load_kN": stability.get("gravity_load_above_storey_kN"), "storey_drift_m": stability.get("mean_interstorey_drift_m"), "storey_shear_kN": stability.get("storey_shear_kN"), "storey_height_m": stability.get("storey_height_m"), "max_stability_index": float(value["max_stability_index"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": "R9.1:storey_mechanics"}
    if "TORSIONAL_DRIFT_RATIO" not in checks and torsion.get("status") == "AVAILABLE" and accept.get("filtered_nonbase_nodal_spread_torsional_candidate_scope") is True:
        value = lim("TORSIONAL_DRIFT_RATIO")
        row = torsion["governing_candidate"]
        if _num(value.get("max_torsional_drift_ratio")) is not None and str(value.get("normative_reference") or "").strip():
            checks["TORSIONAL_DRIFT_RATIO"] = {"id": "R9.2-TORSION", "check_type": "TORSIONAL_DRIFT_RATIO", "storey_id": row.get("storey_id"), "max_edge_drift_m": row.get("max_nodal_interstorey_drift_m"), "average_edge_drift_m": row.get("average_nodal_interstorey_drift_m"), "max_torsional_drift_ratio": float(value["max_torsional_drift_ratio"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": "R9.2:corrected_torsional_response"}
    if "SOFT_STOREY_STIFFNESS_RATIO" not in checks and completeness.get("status") == "PASSED" and governing_soft and accept.get("adjacent_storey_secant_stiffness_reference_method") is True:
        value = lim("SOFT_STOREY_STIFFNESS_RATIO")
        if _num(value.get("minimum_ratio")) is not None and str(value.get("normative_reference") or "").strip():
            checks["SOFT_STOREY_STIFFNESS_RATIO"] = {"id": "R9.2-SOFT-STOREY", "check_type": "SOFT_STOREY_STIFFNESS_RATIO", "storey_id": governing_soft.get("storey_id"), "storey_stiffness_kN_per_m": governing_soft.get("storey_stiffness_kN_per_m"), "reference_stiffness_kN_per_m": governing_soft.get("reference_stiffness_kN_per_m"), "minimum_ratio": float(value["minimum_ratio"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": "R9.2:storey_mechanics"}
    if "WEAK_STOREY_STRENGTH_RATIO" not in checks and strength.get("status") == "AVAILABLE":
        value = lim("WEAK_STOREY_STRENGTH_RATIO")
        row = strength["governing_candidate"]
        if _num(value.get("minimum_ratio")) is not None and str(value.get("normative_reference") or "").strip():
            checks["WEAK_STOREY_STRENGTH_RATIO"] = {"id": "R9.2-WEAK-STOREY", "check_type": "WEAK_STOREY_STRENGTH_RATIO", "storey_id": row.get("storey_id"), "storey_strength_kN": row.get("storey_strength_kN"), "reference_strength_kN": row.get("reference_strength_kN"), "minimum_ratio": float(value["minimum_ratio"]), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": row.get("evidence_reference")}
    if "ALTERNATE_LOAD_PATH_EVIDENCE" not in checks and alternate.get("status") == "AVAILABLE":
        value = lim("ALTERNATE_LOAD_PATH_EVIDENCE")
        if str(value.get("normative_reference") or "").strip():
            checks["ALTERNATE_LOAD_PATH_EVIDENCE"] = {"id": "R9.2-ALTERNATE-PATH", "check_type": "ALTERNATE_LOAD_PATH_EVIDENCE", "alternate_path_verified": alternate.get("alternate_path_verified"), "evidence_reference": alternate.get("evidence_reference"), "mandatory": True, "normative_reference": str(value["normative_reference"])}
    if "DIAPHRAGM_CONTINUITY" not in checks and isinstance(diaphragm, Mapping) and accept.get("model_derived_diaphragm_connectivity_candidate_scope") is True:
        value = lim("DIAPHRAGM_CONTINUITY")
        if str(value.get("normative_reference") or "").strip():
            checks["DIAPHRAGM_CONTINUITY"] = {"id": "R9.2-DIAPHRAGM", "check_type": "DIAPHRAGM_CONTINUITY", "continuity_verified": bool(diaphragm.get("continuity_verified")), "evidence_reference": "R9:diaphragm_connectivity", "mandatory": True, "normative_reference": str(value["normative_reference"])}
    if "LOAD_PATH_CONTINUITY" not in checks and isinstance(topology, Mapping) and topology.get("all_loaded_nodes_reach_support") and accept.get("model_derived_load_path_connectivity_candidate_scope") is True:
        value = lim("LOAD_PATH_CONTINUITY")
        if str(value.get("normative_reference") or "").strip():
            checks["LOAD_PATH_CONTINUITY"] = {"id": "R9.2-LOAD-PATH", "check_type": "LOAD_PATH_CONTINUITY", "loaded_nodes": topology.get("loaded_nodes"), "load_path_edges": topology.get("load_path_edges"), "mandatory": True, "normative_reference": str(value["normative_reference"]), "evidence_reference": "R9:topology_load_path"}

    complete = sorted(k for k, value in checks.items() if _complete(value))
    missing = sorted(set(policy["required_check_types"]) - set(complete))
    if isinstance(input_value.get("stability_basis"), Mapping) and input_value.get("stability_basis"):
        basis = dict(input_value["stability_basis"])
    else:
        basis = _basis_from_r91(r91_qualification)
    global_input = None
    if completeness.get("status") == "PASSED" and basis and len(complete) == len(policy["required_check_types"]):
        global_input = {
            "stability_basis": basis,
            "stability_checks": [checks[k] for k in policy["required_check_types"]],
            "stability_policy": dict(policy["v8_6_policy"]),
            "release_policy": {
                "automatic_code_compliance_claim": False,
                "automatic_structural_approval": False,
                "automatic_robustness_approval": False,
                "structural_model_release": LOCKED_RELEASE,
            },
        }

    technical_available = sorted(k for k, value in q.items() if value["qualification_state"] != "ANALYSIS_REQUIRED")
    blockers = []
    if completeness.get("status") != "PASSED":
        blockers.append({
            "reason": "R9_2_STRUCTURAL_STOREY_MODEL_INCOMPLETE",
            "message": "R9.2 cannot qualify storey stability until the analytical model contains all architectural storey boundaries and vertical load-path intervals.",
            "storey_model_reason": completeness.get("reason"),
            "missing_expected_levels_m": completeness.get("missing_expected_levels_m", []),
            "missing_vertical_path_intervals": completeness.get("missing_vertical_path_intervals", []),
            "expected_storey_interval_count": completeness.get("expected_storey_interval_count"),
            "detected_model_levels_m": completeness.get("detected_model_levels_m", []),
        })
    elif global_input is None:
        blockers.append({
            "reason": "R9_2_STABILITY_DESIGN_BASIS_OR_RESIDUAL_EVIDENCE_REQUIRED",
            "message": "R9.2 completed safe storey/torsion residual derivations, but v8.6 still requires explicit project limits/references and traceable residual capacity evidence.",
            "missing_check_types": missing,
            "technical_evidence_available_for": technical_available,
            "analysis_required_for": sorted(k for k, value in q.items() if value["qualification_state"] == "ANALYSIS_REQUIRED"),
        })

    template = {
        "schema_version": "phoenix.r9-2-stability-design-basis-input-template/1.0",
        "r9_2_stability_design_basis_input": {
            "stability_basis": dict(basis or {}),
            "normative_limits": {k: {"normative_reference": None} for k in missing},
            "engineering_scope_acceptance": {
                "base_lateral_nlgeom_second_order_candidate_scope": False,
                "linear_eigenvalue_buckling_candidate_scope": False,
                "filtered_nonbase_nodal_spread_torsional_candidate_scope": False,
                "adjacent_storey_secant_stiffness_reference_method": False,
                "model_derived_diaphragm_connectivity_candidate_scope": False,
                "model_derived_load_path_connectivity_candidate_scope": False,
            },
            "storey_strength_evidence": [],
            "alternate_path_capacity_evidence": {},
            "explicit_stability_checks": [],
            "notes": [
                "Provide only traceable project/standards/engineering values.",
                "Do not copy generic v8.6 example thresholds into the project.",
                "R9.2 numerical drift filtering is evidence-quality control, not a normative acceptance criterion.",
                "Weak-storey strength and alternate-path capacity remain explicit engineering evidence unless a verified future capacity engine supplies them.",
            ],
        },
        "storey_model_completeness_snapshot": completeness,
        "corrected_torsional_response_snapshot": torsion,
        "qualification_register_snapshot": q,
    }
    for key, field in (
        ("SECOND_ORDER_AMPLIFICATION", "max_amplification_factor"),
        ("GLOBAL_BUCKLING_FACTOR", "minimum_critical_load_factor"),
        ("STOREY_STABILITY_INDEX", "max_stability_index"),
        ("TORSIONAL_DRIFT_RATIO", "max_torsional_drift_ratio"),
        ("SOFT_STOREY_STIFFNESS_RATIO", "minimum_ratio"),
        ("WEAK_STOREY_STRENGTH_RATIO", "minimum_ratio"),
    ):
        if key in template["r9_2_stability_design_basis_input"]["normative_limits"]:
            template["r9_2_stability_design_basis_input"]["normative_limits"][key][field] = None

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if global_input is not None else "BLOCKED",
        "source_states": {
            "r9_status": r9_evidence.get("status"),
            "r9_1_status": r91_qualification.get("status"),
            "explicit_input_source": input_source,
        },
        "storey_model_completeness": completeness,
        "augmented_architecture": augmented_arch,
        "corrected_floor_response": floor,
        "corrected_torsional_response": torsion,
        "residual_storey_mechanics": storey_mechanics,
        "residual_storey_strength": strength,
        "residual_alternate_path_capacity": alternate,
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
            "analysis_required_check_type_count": sum(1 for value in q.values() if value["qualification_state"] == "ANALYSIS_REQUIRED"),
            "storey_model_complete": completeness.get("status") == "PASSED",
            "expected_storey_interval_count": completeness.get("expected_storey_interval_count", 0),
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            "normative_limits_invented": False,
            "generic_v8_6_example_limits_accepted_as_project_evidence": False,
            "storey_strength_invented": False,
            "alternate_path_capacity_invented": False,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
