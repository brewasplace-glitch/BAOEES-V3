"""Project Phoenix R9.3 residual-capacity and stability design-basis qualification engine.

R9.3 runs only after R9.2 has proved the structural storey model complete but
v8.6 remains blocked on residual capacity and/or explicit project
qualification data.

It derives:
- a traceable weak-storey lateral-capacity *screening proxy* from the R8 RC
  candidate member screening resistances;
- a traceable single-member-removal residual-capacity *screening register*
  combined with R9.1 topology evidence;
- a unified project stability design-basis contract for all nine v8.6 checks.

The screening proxies are engineering candidates, not code resistance claims.
They may only be promoted into the v8.6 candidate check set when an explicit
project input accepts the methodology and supplies the required traceable
reference/limit. No normative limits, legal applicability, professional
approval, robustness approval, or construction release are invented.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

ENGINE_ID = "PHX-RESIDUAL-CAPACITY-STABILITY-DESIGN-BASIS-QUALIFICATION-R9.3"
VERSION = "R9.3.0"
SCHEMA = "phoenix.residual-capacity-stability-design-basis-qualification/1.0"
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
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _q(state: str, evidence: Any, missing: Sequence[str], note: str | None = None) -> dict[str, Any]:
    out = {
        "qualification_state": state,
        "missing_requirements": list(missing),
        "evidence": evidence,
    }
    if note:
        out["note"] = note
    return out


def _member_candidate_map(rc_candidate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    rows = rc_candidate.get("candidate_members")
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        mid = _text(row.get("member_id"))
        if mid:
            result[mid] = dict(row)
    return result


def _screening_lateral_capacity_proxy(member: Mapping[str, Any], interval_height_m: float) -> dict[str, Any] | None:
    """Return a conservative traceable screening proxy; never a normative resistance."""
    resist = member.get("screening_resistances")
    if not isinstance(resist, Mapping) or interval_height_m <= 0:
        return None
    vy = _num(resist.get("VY_Rd_kN"))
    vz = _num(resist.get("VZ_Rd_kN"))
    my = _num(resist.get("MY_Rd_kNm"))
    mz = _num(resist.get("MZ_Rd_kNm"))
    candidates: dict[str, float] = {}
    if vy is not None and vy > 0:
        candidates["VY_Rd_kN"] = vy
    if vz is not None and vz > 0:
        candidates["VZ_Rd_kN"] = vz
    # M/h is deliberately a conservative single-curvature screening proxy.
    # It is not promoted to a code lateral-resistance method without explicit
    # engineering-scope acceptance.
    if my is not None and my > 0:
        candidates["MY_Rd_over_h_kN"] = my / interval_height_m
    if mz is not None and mz > 0:
        candidates["MZ_Rd_over_h_kN"] = mz / interval_height_m
    if not candidates:
        return None
    governing_key = min(candidates, key=candidates.get)
    return {
        "member_id": _text(member.get("member_id")),
        "member_role": _text(member.get("member_role")),
        "section_id": _text(member.get("section_id")),
        "material_id": _text(member.get("material_id")),
        "interval_height_m": interval_height_m,
        "component_candidates_kN": candidates,
        "lateral_capacity_proxy_kN": candidates[governing_key],
        "governing_component": governing_key,
        "source_status": _text(member.get("candidate_status")),
        "source_parameter_status": _text(member.get("normative_parameter_status")),
        "methodology": "MIN(VY_Rd,VZ_Rd,MY_Rd/h,MZ_Rd/h)_R8_SCREENING_PROXY",
    }


def derive_weak_storey_capacity_screening(
    r92: Mapping[str, Any],
    rc_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    completeness = r92.get("storey_model_completeness")
    if not isinstance(completeness, Mapping) or completeness.get("status") != "PASSED":
        return {
            "status": "ANALYSIS_REQUIRED",
            "reason": "R9_2_STOREY_MODEL_COMPLETENESS_REQUIRED",
            "evidence_class": "R8_RC_SCREENING_RESISTANCE_DERIVED_STOREY_CAPACITY_PROXY",
            "invented_capacity": False,
        }
    cmap = _member_candidate_map(rc_candidate)
    rows: list[dict[str, Any]] = []
    intervals = completeness.get("intervals")
    for interval in intervals if isinstance(intervals, list) else []:
        if not isinstance(interval, Mapping):
            continue
        h = _num(interval.get("height_m"))
        if h is None or h <= 0:
            continue
        member_rows: list[dict[str, Any]] = []
        missing_members: list[str] = []
        ids = interval.get("vertical_member_ids")
        for member_id in ids if isinstance(ids, list) else []:
            mid = str(member_id)
            candidate = cmap.get(mid)
            if not candidate:
                missing_members.append(mid)
                continue
            proxy = _screening_lateral_capacity_proxy(candidate, h)
            if proxy is None:
                missing_members.append(mid)
                continue
            member_rows.append(proxy)
        total = sum(float(x["lateral_capacity_proxy_kN"]) for x in member_rows)
        rows.append({
            "interval_id": _text(interval.get("interval_id")),
            "lower_elevation_m": _num(interval.get("lower_elevation_m")),
            "upper_elevation_m": _num(interval.get("upper_elevation_m")),
            "height_m": h,
            "source_vertical_member_count": len(ids) if isinstance(ids, list) else 0,
            "capacity_proxy_member_count": len(member_rows),
            "missing_capacity_member_ids": sorted(missing_members),
            "member_capacity_proxy": member_rows,
            "storey_lateral_capacity_proxy_kN": total if member_rows and not missing_members else None,
        })

    valid = [x for x in rows if _num(x.get("storey_lateral_capacity_proxy_kN")) not in (None, 0.0)]
    valid.sort(key=lambda x: float(x.get("upper_elevation_m") or 0.0))
    ratios: list[dict[str, Any]] = []
    for i in range(1, len(valid)):
        current = valid[i]
        below = valid[i - 1]
        a = _num(current.get("storey_lateral_capacity_proxy_kN"))
        b = _num(below.get("storey_lateral_capacity_proxy_kN"))
        if a is None or b is None or b <= 0:
            continue
        ratios.append({
            "storey_id": current["interval_id"],
            "reference_storey_id": below["interval_id"],
            "reference_direction": "BELOW",
            "storey_strength_proxy_kN": a,
            "reference_strength_proxy_kN": b,
            "ratio": a / b,
            "methodology": "ADJACENT_STOREY_R8_SCREENING_CAPACITY_PROXY_RATIO",
        })
    governing = min(ratios, key=lambda x: x["ratio"]) if ratios else None
    complete = bool(rows) and len(valid) == len(rows) and governing is not None
    return {
        "status": "AVAILABLE" if complete else "ANALYSIS_REQUIRED",
        "evidence_class": "R8_RC_SCREENING_RESISTANCE_DERIVED_STOREY_CAPACITY_PROXY",
        "source_rc_candidate_status": rc_candidate.get("status"),
        "source_rc_candidate_member_count": rc_candidate.get("member_count"),
        "storey_rows": rows,
        "adjacent_storey_strength_proxy_ratios": ratios,
        "governing_candidate": governing,
        "invented_capacity": False,
        "candidate_methodology_only": True,
        "note": (
            "The proxy is derived from traceable R8 screening resistances using "
            "MIN(VY_Rd,VZ_Rd,MY_Rd/h,MZ_Rd/h). It is not a normative storey "
            "strength method and may not be used by v8.6 unless explicitly "
            "accepted in the project stability design basis."
        ),
    }


def _topology_cases(r91: Mapping[str, Any]) -> list[dict[str, Any]]:
    q = r91.get("qualification_register")
    if not isinstance(q, Mapping):
        return []
    alt = q.get("ALTERNATE_LOAD_PATH_EVIDENCE")
    evidence = alt.get("evidence") if isinstance(alt, Mapping) else None
    cases = evidence.get("cases") if isinstance(evidence, Mapping) else None
    return [dict(x) for x in cases if isinstance(x, Mapping)] if isinstance(cases, list) else []


def derive_alternate_path_capacity_screening(
    r91: Mapping[str, Any],
    weak_storey: Mapping[str, Any],
) -> dict[str, Any]:
    cases = _topology_cases(r91)
    storeys = weak_storey.get("storey_rows")
    if not cases or not isinstance(storeys, list) or not storeys:
        return {
            "status": "ANALYSIS_REQUIRED",
            "reason": "TOPOLOGY_AND_STOREY_CAPACITY_PROXY_REQUIRED",
            "evidence_class": "TOPOLOGY_PLUS_TRACEABLE_CAPACITY_RESERVE_SCREENING",
            "alternate_path_verified": False,
            "invented_capacity": False,
        }

    base_capacity: dict[str, float] = {}
    member_to_storey: dict[str, tuple[str, float]] = {}
    for storey in storeys:
        if not isinstance(storey, Mapping):
            continue
        sid = _text(storey.get("interval_id"))
        total = _num(storey.get("storey_lateral_capacity_proxy_kN"))
        members = storey.get("member_capacity_proxy")
        if not sid or total is None or total <= 0 or not isinstance(members, list):
            continue
        base_capacity[sid] = total
        for row in members:
            if not isinstance(row, Mapping):
                continue
            mid = _text(row.get("member_id"))
            cap = _num(row.get("lateral_capacity_proxy_kN"))
            if mid and cap is not None and cap >= 0:
                member_to_storey[mid] = (sid, cap)

    result_cases: list[dict[str, Any]] = []
    for case in cases:
        mid = _text(case.get("removed_member_id"))
        topology_ok = case.get("all_loaded_nodes_reach_support") is True
        ratios = {sid: 1.0 for sid in base_capacity}
        affected = member_to_storey.get(mid)
        if affected:
            sid, cap = affected
            base = base_capacity.get(sid, 0.0)
            ratios[sid] = max(0.0, (base - cap) / base) if base > 0 else 0.0
        governing_ratio = min(ratios.values()) if ratios else None
        result_cases.append({
            "removed_member_id": mid,
            "all_loaded_nodes_reach_support": topology_ok,
            "storey_residual_capacity_proxy_ratios": ratios,
            "governing_residual_capacity_proxy_ratio": governing_ratio,
            "screening_only_no_load_redistribution_analysis": True,
        })
    valid = [x for x in result_cases if _num(x.get("governing_residual_capacity_proxy_ratio")) is not None]
    governing = min(valid, key=lambda x: x["governing_residual_capacity_proxy_ratio"]) if valid else None
    topology_all = bool(result_cases) and all(x["all_loaded_nodes_reach_support"] for x in result_cases)
    return {
        "status": "AVAILABLE" if governing is not None and topology_all else "ANALYSIS_REQUIRED",
        "evidence_class": "TOPOLOGY_PLUS_TRACEABLE_CAPACITY_RESERVE_SCREENING",
        "member_removal_case_count": len(result_cases),
        "all_single_member_removal_cases_topologically_connected": topology_all,
        "cases": result_cases,
        "governing_candidate": governing,
        "minimum_residual_capacity_proxy_ratio": governing.get("governing_residual_capacity_proxy_ratio") if governing else None,
        "alternate_path_verified": False,
        "invented_capacity": False,
        "candidate_methodology_only": True,
        "note": (
            "This is a residual-capacity screening register, not a redistributed "
            "member-removal nonlinear analysis. It may only be promoted into the "
            "v8.6 candidate check set after explicit project methodology acceptance."
        ),
    }


def _extract_input(
    candidates: Sequence[Any],
    forbidden_paths: Sequence[str],
) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    inherited: list[tuple[int, str, dict[str, Any]]] = []
    direct: list[tuple[int, str, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    for item in candidates:
        path, data = (item[0], item[1]) if isinstance(item, (list, tuple)) and len(item) >= 2 else (None, item)
        if not isinstance(data, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if any(ptext.endswith(str(x)) for x in forbidden_paths):
            warnings.append({"reason": "R9_3_GENERIC_EXAMPLE_REJECTED", "source": ptext})
            continue
        for key, bucket, base_score in (
            ("r9_2_stability_design_basis_input", inherited, 0),
            ("r9_3_stability_design_basis_input", direct, 100000),
        ):
            section = data.get(key)
            if not isinstance(section, Mapping):
                continue
            value = dict(section)
            explicit = value.get("explicit_stability_checks") if isinstance(value.get("explicit_stability_checks"), list) else []
            limits = value.get("normative_limits") if isinstance(value.get("normative_limits"), Mapping) else {}
            acceptance = value.get("engineering_scope_acceptance") if isinstance(value.get("engineering_scope_acceptance"), Mapping) else {}
            score = base_score + 1000 * len(explicit) + 100 * len(limits) + sum(1 for v in acceptance.values() if v is True)
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


def _explicit_checks(value: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    rows = value.get("explicit_stability_checks") if isinstance(value.get("explicit_stability_checks"), list) else []
    for row in rows:
        if isinstance(row, Mapping) and _text(row.get("check_type")) in CHECK_TYPES:
            out[_text(row["check_type"])] = dict(row)
    return out


def _complete(check: Mapping[str, Any]) -> bool:
    ctype = _text(check.get("check_type"))
    if ctype not in CHECK_TYPES or not _text(check.get("normative_reference")):
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
    return all(check.get(key) is not None for key in required)


def _basis_from_r92(r92: Mapping[str, Any]) -> dict[str, Any]:
    template = r92.get("required_input_template")
    section = template.get("r9_2_stability_design_basis_input") if isinstance(template, Mapping) else None
    basis = section.get("stability_basis") if isinstance(section, Mapping) else None
    return dict(basis) if isinstance(basis, Mapping) else {}


def _r92_evidence(r92: Mapping[str, Any], check_type: str) -> Any:
    q = r92.get("qualification_register")
    row = q.get(check_type) if isinstance(q, Mapping) else None
    return row.get("evidence") if isinstance(row, Mapping) else None


def build_residual_capacity_stability_design_basis(
    *,
    project_id: str,
    r91_qualification: Mapping[str, Any],
    r92_qualification: Mapping[str, Any],
    rc_design_candidate: Mapping[str, Any],
    member_verification: Mapping[str, Any],
    candidates: Sequence[Any],
    policy_path: Path,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    input_value, input_source, warnings = _extract_input(candidates, policy.get("forbidden_project_evidence_paths", []))

    weak = derive_weak_storey_capacity_screening(r92_qualification, rc_design_candidate)
    alternate = derive_alternate_path_capacity_screening(r91_qualification, weak)

    q: dict[str, dict[str, Any]] = {}
    for ctype in (
        "SECOND_ORDER_AMPLIFICATION",
        "GLOBAL_BUCKLING_FACTOR",
        "STOREY_STABILITY_INDEX",
        "TORSIONAL_DRIFT_RATIO",
        "SOFT_STOREY_STIFFNESS_RATIO",
        "DIAPHRAGM_CONTINUITY",
        "LOAD_PATH_CONTINUITY",
    ):
        evidence = _r92_evidence(r92_qualification, ctype)
        prior = (r92_qualification.get("qualification_register") or {}).get(ctype) if isinstance(r92_qualification.get("qualification_register"), Mapping) else None
        state = _text((prior or {}).get("qualification_state")) or ("EVIDENCE_AVAILABLE" if evidence is not None else "ANALYSIS_REQUIRED")
        missing = list((prior or {}).get("missing_requirements") or [])
        q[ctype] = _q(state, evidence, missing, (prior or {}).get("note") if isinstance(prior, Mapping) else None)

    if weak.get("status") == "AVAILABLE":
        q["WEAK_STOREY_STRENGTH_RATIO"] = _q(
            "REFERENCE_METHOD_AND_LIMIT_REQUIRED",
            weak,
            ["rc_screening_storey_capacity_proxy_method_acceptance", "minimum_ratio", "normative_reference"],
            "Technical evidence is a traceable R8 screening-capacity proxy, not a code storey-strength claim.",
        )
    else:
        q["WEAK_STOREY_STRENGTH_RATIO"] = _q(
            "ANALYSIS_REQUIRED",
            weak,
            ["traceable_storey_lateral_capacity_evidence"],
        )

    if alternate.get("status") == "AVAILABLE":
        q["ALTERNATE_LOAD_PATH_EVIDENCE"] = _q(
            "ENGINEERING_METHOD_AND_REFERENCE_REQUIRED",
            alternate,
            [
                "topology_capacity_reserve_screening_method_acceptance",
                "minimum_residual_capacity_proxy_ratio",
                "normative_reference",
            ],
            "Screening does not include redistributed member-removal demand unless a future solver-removal engine supplies it.",
        )
    else:
        q["ALTERNATE_LOAD_PATH_EVIDENCE"] = _q(
            "ANALYSIS_REQUIRED",
            alternate,
            ["traceable_residual_capacity_screening_evidence"],
        )

    limits = input_value.get("normative_limits") if isinstance(input_value.get("normative_limits"), Mapping) else {}
    accept = input_value.get("engineering_scope_acceptance") if isinstance(input_value.get("engineering_scope_acceptance"), Mapping) else {}
    checks = _explicit_checks(input_value)

    def lim(ctype: str) -> Mapping[str, Any]:
        value = limits.get(ctype)
        return value if isinstance(value, Mapping) else {}

    def ref(value: Mapping[str, Any]) -> str:
        return _text(value.get("normative_reference"))

    second = _r92_evidence(r92_qualification, "SECOND_ORDER_AMPLIFICATION")
    if "SECOND_ORDER_AMPLIFICATION" not in checks and isinstance(second, Mapping) and accept.get("base_lateral_nlgeom_second_order_candidate_scope") is True:
        value = lim("SECOND_ORDER_AMPLIFICATION")
        if _num(value.get("max_amplification_factor")) is not None and ref(value):
            checks["SECOND_ORDER_AMPLIFICATION"] = {
                "id": "R9.3-SECOND-ORDER",
                "check_type": "SECOND_ORDER_AMPLIFICATION",
                "first_order_displacement_m": second.get("first_order_max_horizontal_displacement_m"),
                "second_order_displacement_m": second.get("second_order_max_horizontal_displacement_m"),
                "max_amplification_factor": float(value["max_amplification_factor"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": second.get("second_order_dat"),
            }

    buckling = _r92_evidence(r92_qualification, "GLOBAL_BUCKLING_FACTOR")
    if "GLOBAL_BUCKLING_FACTOR" not in checks and isinstance(buckling, Mapping) and accept.get("linear_eigenvalue_buckling_candidate_scope") is True:
        value = lim("GLOBAL_BUCKLING_FACTOR")
        if _num(value.get("minimum_critical_load_factor")) is not None and ref(value):
            checks["GLOBAL_BUCKLING_FACTOR"] = {
                "id": "R9.3-BUCKLING",
                "check_type": "GLOBAL_BUCKLING_FACTOR",
                "critical_load_factor": buckling.get("lowest_positive_buckling_factor"),
                "minimum_critical_load_factor": float(value["minimum_critical_load_factor"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": buckling.get("dat"),
            }

    stability = _r92_evidence(r92_qualification, "STOREY_STABILITY_INDEX")
    if "STOREY_STABILITY_INDEX" not in checks and isinstance(stability, Mapping):
        value = lim("STOREY_STABILITY_INDEX")
        if _num(value.get("max_stability_index")) is not None and ref(value):
            checks["STOREY_STABILITY_INDEX"] = {
                "id": "R9.3-STABILITY-INDEX",
                "check_type": "STOREY_STABILITY_INDEX",
                "storey_id": stability.get("storey_id"),
                "gravity_load_kN": stability.get("gravity_load_above_storey_kN"),
                "storey_drift_m": stability.get("mean_interstorey_drift_m"),
                "storey_shear_kN": stability.get("storey_shear_kN"),
                "storey_height_m": stability.get("storey_height_m"),
                "max_stability_index": float(value["max_stability_index"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9.1:R9.2_STOREY_MECHANICS",
            }

    torsion = _r92_evidence(r92_qualification, "TORSIONAL_DRIFT_RATIO")
    if "TORSIONAL_DRIFT_RATIO" not in checks and isinstance(torsion, Mapping) and accept.get("filtered_nonbase_nodal_spread_torsional_candidate_scope") is True:
        value = lim("TORSIONAL_DRIFT_RATIO")
        if _num(value.get("max_torsional_drift_ratio")) is not None and ref(value):
            checks["TORSIONAL_DRIFT_RATIO"] = {
                "id": "R9.3-TORSION",
                "check_type": "TORSIONAL_DRIFT_RATIO",
                "storey_id": torsion.get("storey_id"),
                "max_edge_drift_m": torsion.get("max_nodal_interstorey_drift_m"),
                "average_edge_drift_m": torsion.get("average_nodal_interstorey_drift_m"),
                "max_torsional_drift_ratio": float(value["max_torsional_drift_ratio"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9.2:FILTERED_NONBASE_TORSIONAL_RESPONSE",
            }

    soft = _r92_evidence(r92_qualification, "SOFT_STOREY_STIFFNESS_RATIO")
    if "SOFT_STOREY_STIFFNESS_RATIO" not in checks and isinstance(soft, Mapping) and accept.get("adjacent_storey_secant_stiffness_reference_method") is True:
        value = lim("SOFT_STOREY_STIFFNESS_RATIO")
        if _num(value.get("minimum_ratio")) is not None and ref(value):
            checks["SOFT_STOREY_STIFFNESS_RATIO"] = {
                "id": "R9.3-SOFT-STOREY",
                "check_type": "SOFT_STOREY_STIFFNESS_RATIO",
                "storey_id": soft.get("storey_id"),
                "storey_stiffness_kN_per_m": soft.get("storey_stiffness_kN_per_m"),
                "reference_stiffness_kN_per_m": soft.get("reference_stiffness_kN_per_m"),
                "minimum_ratio": float(value["minimum_ratio"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9.2:ADJACENT_STOREY_SECANT_STIFFNESS",
            }

    diaphragm = _r92_evidence(r92_qualification, "DIAPHRAGM_CONTINUITY")
    if "DIAPHRAGM_CONTINUITY" not in checks and isinstance(diaphragm, Mapping) and accept.get("model_derived_diaphragm_connectivity_candidate_scope") is True:
        value = lim("DIAPHRAGM_CONTINUITY")
        if ref(value):
            checks["DIAPHRAGM_CONTINUITY"] = {
                "id": "R9.3-DIAPHRAGM",
                "check_type": "DIAPHRAGM_CONTINUITY",
                "continuity_verified": bool(diaphragm.get("continuity_verified")),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9:R9.2_DIAPHRAGM_CONNECTIVITY",
            }

    load_path = _r92_evidence(r92_qualification, "LOAD_PATH_CONTINUITY")
    if "LOAD_PATH_CONTINUITY" not in checks and isinstance(load_path, Mapping) and load_path.get("all_loaded_nodes_reach_support") is True and accept.get("model_derived_load_path_connectivity_candidate_scope") is True:
        value = lim("LOAD_PATH_CONTINUITY")
        if ref(value):
            checks["LOAD_PATH_CONTINUITY"] = {
                "id": "R9.3-LOAD-PATH",
                "check_type": "LOAD_PATH_CONTINUITY",
                "loaded_nodes": load_path.get("loaded_nodes"),
                "load_path_edges": load_path.get("load_path_edges"),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9:R9.2_LOAD_PATH_CONNECTIVITY",
            }

    weak_gov = weak.get("governing_candidate") if isinstance(weak, Mapping) else None
    if "WEAK_STOREY_STRENGTH_RATIO" not in checks and isinstance(weak_gov, Mapping) and accept.get("rc_screening_storey_capacity_proxy_method") is True:
        value = lim("WEAK_STOREY_STRENGTH_RATIO")
        if _num(value.get("minimum_ratio")) is not None and ref(value):
            checks["WEAK_STOREY_STRENGTH_RATIO"] = {
                "id": "R9.3-WEAK-STOREY-SCREENING",
                "check_type": "WEAK_STOREY_STRENGTH_RATIO",
                "storey_id": weak_gov.get("storey_id"),
                "storey_strength_kN": weak_gov.get("storey_strength_proxy_kN"),
                "reference_strength_kN": weak_gov.get("reference_strength_proxy_kN"),
                "minimum_ratio": float(value["minimum_ratio"]),
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9.3:R8_RC_SCREENING_STOREY_CAPACITY_PROXY",
                "candidate_methodology_status": "EXPLICITLY_ACCEPTED_ENGINEERING_SCREENING_METHOD",
            }

    alt_gov = alternate.get("governing_candidate") if isinstance(alternate, Mapping) else None
    if "ALTERNATE_LOAD_PATH_EVIDENCE" not in checks and isinstance(alt_gov, Mapping) and accept.get("topology_capacity_reserve_screening_as_alternate_path_method") is True:
        value = lim("ALTERNATE_LOAD_PATH_EVIDENCE")
        threshold = _num(value.get("minimum_residual_capacity_proxy_ratio"))
        measured = _num(alternate.get("minimum_residual_capacity_proxy_ratio"))
        if threshold is not None and measured is not None and ref(value):
            verified = bool(alternate.get("all_single_member_removal_cases_topologically_connected")) and measured >= threshold
            checks["ALTERNATE_LOAD_PATH_EVIDENCE"] = {
                "id": "R9.3-ALTERNATE-PATH-SCREENING",
                "check_type": "ALTERNATE_LOAD_PATH_EVIDENCE",
                "alternate_path_verified": verified,
                "mandatory": True,
                "normative_reference": ref(value),
                "evidence_reference": "R9.3:TOPOLOGY_PLUS_CAPACITY_RESERVE_SCREENING",
                "minimum_residual_capacity_proxy_ratio": threshold,
                "measured_residual_capacity_proxy_ratio": measured,
                "candidate_methodology_status": "EXPLICITLY_ACCEPTED_ENGINEERING_SCREENING_METHOD",
            }

    complete = sorted(k for k, row in checks.items() if _complete(row))
    required = list(policy["required_check_types"])
    missing = sorted(set(required) - set(complete))

    basis = dict(input_value.get("stability_basis")) if isinstance(input_value.get("stability_basis"), Mapping) else _basis_from_r92(r92_qualification)
    global_input = None
    if basis and len(complete) == len(required):
        global_input = {
            "stability_basis": basis,
            "stability_checks": [checks[k] for k in required],
            "stability_policy": dict(policy["v8_6_policy"]),
            "release_policy": {
                "automatic_code_compliance_claim": False,
                "automatic_structural_approval": False,
                "automatic_robustness_approval": False,
                "structural_model_release": LOCKED_RELEASE,
            },
        }

    technical_available = sorted(k for k, row in q.items() if row["qualification_state"] != "ANALYSIS_REQUIRED")
    analysis_required = sorted(k for k, row in q.items() if row["qualification_state"] == "ANALYSIS_REQUIRED")

    blockers = []
    if global_input is None:
        blockers.append({
            "reason": "R9_3_STABILITY_DESIGN_BASIS_QUALIFICATION_REQUIRED",
            "message": (
                "R9.3 generated all safe residual-capacity screening evidence available "
                "from the R8/R9 chain, but v8.6 still requires explicit project methodology "
                "acceptance, limits and traceable references for the remaining checks."
            ),
            "missing_check_types": missing,
            "technical_evidence_available_for": technical_available,
            "analysis_required_for": analysis_required,
        })

    normative_template = {k: {"normative_reference": None} for k in required}
    for key, field in (
        ("SECOND_ORDER_AMPLIFICATION", "max_amplification_factor"),
        ("GLOBAL_BUCKLING_FACTOR", "minimum_critical_load_factor"),
        ("STOREY_STABILITY_INDEX", "max_stability_index"),
        ("TORSIONAL_DRIFT_RATIO", "max_torsional_drift_ratio"),
        ("SOFT_STOREY_STIFFNESS_RATIO", "minimum_ratio"),
        ("WEAK_STOREY_STRENGTH_RATIO", "minimum_ratio"),
        ("ALTERNATE_LOAD_PATH_EVIDENCE", "minimum_residual_capacity_proxy_ratio"),
    ):
        normative_template[key][field] = None

    template = {
        "schema_version": "phoenix.r9-3-stability-design-basis-input-template/1.0",
        "r9_3_stability_design_basis_input": {
            "stability_basis": dict(basis or {}),
            "normative_limits": normative_template,
            "engineering_scope_acceptance": {
                "base_lateral_nlgeom_second_order_candidate_scope": False,
                "linear_eigenvalue_buckling_candidate_scope": False,
                "filtered_nonbase_nodal_spread_torsional_candidate_scope": False,
                "adjacent_storey_secant_stiffness_reference_method": False,
                "model_derived_diaphragm_connectivity_candidate_scope": False,
                "model_derived_load_path_connectivity_candidate_scope": False,
                "rc_screening_storey_capacity_proxy_method": False,
                "topology_capacity_reserve_screening_as_alternate_path_method": False,
            },
            "explicit_stability_checks": [],
            "notes": [
                "Provide only traceable project/standards/engineering values.",
                "Do not copy generic v8.6 example thresholds into the project.",
                "R8 RC screening resistances are engineering candidate values, not automatically verified NDP/code resistances.",
                "Weak-storey and alternate-path screening proxies require explicit engineering methodology acceptance before v8.6 use.",
                "Production release remains locked and professional structural review remains mandatory.",
            ],
        },
        "weak_storey_capacity_screening_snapshot": weak,
        "alternate_path_capacity_screening_snapshot": alternate,
        "qualification_register_snapshot": q,
    }

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if global_input is not None else "BLOCKED",
        "source_states": {
            "r9_1_status": r91_qualification.get("status"),
            "r9_2_status": r92_qualification.get("status"),
            "rc_design_candidate_status": rc_design_candidate.get("status"),
            "member_verification_state": member_verification.get("verification_state"),
            "explicit_input_source": input_source,
        },
        "weak_storey_capacity_screening": weak,
        "alternate_path_capacity_screening": alternate,
        "qualification_register": q,
        "technical_evidence_available_for": technical_available,
        "analysis_required_for": analysis_required,
        "completed_check_types": complete,
        "missing_check_types": missing,
        "global_stability_input": global_input,
        "required_input_template": template,
        "summary": {
            "required_check_type_count": len(required),
            "technical_evidence_available_count": len(technical_available),
            "v8_6_completed_check_type_count": len(complete),
            "missing_check_type_count": len(missing),
            "analysis_required_check_type_count": len(analysis_required),
            "weak_storey_capacity_screening_available": weak.get("status") == "AVAILABLE",
            "alternate_path_capacity_screening_available": alternate.get("status") == "AVAILABLE",
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            "normative_limits_invented": False,
            "generic_v8_6_example_limits_accepted_as_project_evidence": False,
            "r8_screening_resistance_promoted_to_code_strength_without_acceptance": False,
            "load_redistribution_after_member_removal_invented": False,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
