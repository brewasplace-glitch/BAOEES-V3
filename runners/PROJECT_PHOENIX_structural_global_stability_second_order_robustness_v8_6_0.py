#!/usr/bin/env python3
"""Project Phoenix Global Stability, Second-Order & Structural Robustness Engine v8.6.0.

This engine consumes the member-verification candidate from v8.5.0 and evaluates
explicit, traceable global-stability / second-order / robustness screening rules.
All normative limits remain external project inputs. PASS therefore means the
supplied rule evaluated within its supplied limit; it is not a statutory code-
compliance declaration and never unlocks structural release.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-GLOBAL-STABILITY-SECOND-ORDER-ROBUSTNESS-V8.6.0"
VERSION = "8.6.0"
LOCKED_RELEASE = "LOCKED"
SUPPORTED_CHECK_TYPES = {
    "SECOND_ORDER_AMPLIFICATION",
    "STOREY_STABILITY_INDEX",
    "GLOBAL_BUCKLING_FACTOR",
    "TORSIONAL_DRIFT_RATIO",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
    "DIAPHRAGM_CONTINUITY",
    "LOAD_PATH_CONTINUITY",
    "ALTERNATE_LOAD_PATH_EVIDENCE",
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


def _nonnegative(value: Any, label: str) -> float:
    result = _num(value, label)
    if result < 0:
        raise ValueError(f"{label} must be >= 0")
    return result


def _basis(payload: Mapping[str, Any]) -> Dict[str, str]:
    raw = payload.get("stability_basis")
    if not isinstance(raw, Mapping):
        raise ValueError("stability_basis must be an object")
    return {
        "jurisdiction": _text(raw.get("jurisdiction"), "stability_basis.jurisdiction"),
        "standard_set": _text(raw.get("standard_set"), "stability_basis.standard_set"),
        "edition": _text(raw.get("edition"), "stability_basis.edition"),
        "source_reference": _text(raw.get("source_reference"), "stability_basis.source_reference"),
        "status": _text(raw.get("status"), "stability_basis.status"),
    }


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(payload.get("stability_policy") or {})
    acceptable = [str(v) for v in _items(raw.get("acceptable_member_verification_states") or ["MEMBER_VERIFICATION_CANDIDATE_PASSED"])]
    mandatory = [str(v).upper() for v in _items(raw.get("mandatory_check_types") or sorted(SUPPORTED_CHECK_TYPES))]
    unknown = [v for v in mandatory if v not in SUPPORTED_CHECK_TYPES]
    if unknown:
        raise ValueError(f"Unsupported mandatory_check_types: {', '.join(unknown)}")
    return {
        "acceptable_member_verification_states": acceptable,
        "require_normative_reference": bool(raw.get("require_normative_reference", True)),
        "mandatory_check_types": mandatory,
        "pass_tolerance": _nonnegative(raw.get("pass_tolerance", 1e-12), "pass_tolerance"),
    }


def _model_ids(payload: Mapping[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
    model = payload.get("analytical_model") or {}
    if not isinstance(model, Mapping):
        raise ValueError("analytical_model must be an object")
    nodes = {_text(v.get("id"), "node id") for v in _items(model.get("nodes")) if isinstance(v, Mapping)}
    supports = {_text(v.get("id"), "support id") for v in _items(model.get("supports")) if isinstance(v, Mapping)}
    storeys = {_text(v.get("id"), "storey id") for v in _items(model.get("storeys")) if isinstance(v, Mapping)}
    if not nodes:
        raise ValueError("analytical_model.nodes must contain at least one node")
    if not supports:
        raise ValueError("analytical_model.supports must contain at least one support")
    if not storeys:
        raise ValueError("analytical_model.storeys must contain at least one storey")
    return nodes, supports, storeys


def _source_gate(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    source = _text(payload.get("source_engine"), "source_engine")
    if "V8.5.0" not in source.upper():
        raise ValueError("source_engine must identify the v8.5.0 member verification engine")
    state = _text(payload.get("member_verification_state"), "member_verification_state")
    if state not in policy["acceptable_member_verification_states"]:
        raise ValueError(f"member_verification_state '{state}' is not accepted by stability_policy")


def _common(check: Mapping[str, Any], policy: Mapping[str, Any], seen: Set[str]) -> Dict[str, Any]:
    cid = _text(check.get("id"), "stability check id")
    if cid in seen:
        raise ValueError(f"Duplicate stability check id: {cid}")
    seen.add(cid)
    ctype = _text(check.get("check_type"), f"{cid}.check_type").upper()
    if ctype not in SUPPORTED_CHECK_TYPES:
        raise ValueError(f"{cid} unsupported check_type {ctype}")
    ref = str(check.get("normative_reference") or "").strip()
    if policy["require_normative_reference"] and not ref:
        raise ValueError(f"{cid} missing normative_reference")
    return {
        "id": cid,
        "check_type": ctype,
        "mandatory": bool(check.get("mandatory", True)),
        "normative_reference": ref,
    }


def _status_le(value: float, limit: float, tol: float) -> str:
    return "PASS" if value <= limit + tol else "FAIL"


def _status_ge(value: float, limit: float, tol: float) -> str:
    return "PASS" if value + tol >= limit else "FAIL"


def _eval_second_order(check: Mapping[str, Any], base: Dict[str, Any], tol: float) -> Dict[str, Any]:
    first = abs(_num(check.get("first_order_displacement_m"), f"{base['id']}.first_order_displacement_m"))
    second = abs(_num(check.get("second_order_displacement_m"), f"{base['id']}.second_order_displacement_m"))
    if first <= 0:
        raise ValueError(f"{base['id']}.first_order_displacement_m absolute value must be > 0")
    amplification = second / first
    limit = _positive(check.get("max_amplification_factor"), f"{base['id']}.max_amplification_factor")
    return {**base, "first_order_displacement_m": first, "second_order_displacement_m": second, "amplification_factor": amplification, "limit": limit, "utilization": amplification / limit, "status": _status_le(amplification, limit, tol)}


def _eval_storey_theta(check: Mapping[str, Any], base: Dict[str, Any], storeys: Set[str], tol: float) -> Dict[str, Any]:
    storey = _text(check.get("storey_id"), f"{base['id']}.storey_id")
    if storey not in storeys:
        raise ValueError(f"{base['id']} references unknown storey {storey}")
    p = _nonnegative(check.get("gravity_load_kN"), f"{base['id']}.gravity_load_kN")
    drift = abs(_num(check.get("storey_drift_m"), f"{base['id']}.storey_drift_m"))
    shear = _positive(check.get("storey_shear_kN"), f"{base['id']}.storey_shear_kN")
    height = _positive(check.get("storey_height_m"), f"{base['id']}.storey_height_m")
    theta = p * drift / (shear * height)
    limit = _positive(check.get("max_stability_index"), f"{base['id']}.max_stability_index")
    return {**base, "storey_id": storey, "gravity_load_kN": p, "storey_drift_m": drift, "storey_shear_kN": shear, "storey_height_m": height, "stability_index": theta, "limit": limit, "utilization": theta / limit, "status": _status_le(theta, limit, tol)}


def _eval_buckling(check: Mapping[str, Any], base: Dict[str, Any], tol: float) -> Dict[str, Any]:
    factor = _positive(check.get("critical_load_factor"), f"{base['id']}.critical_load_factor")
    minimum = _positive(check.get("minimum_critical_load_factor"), f"{base['id']}.minimum_critical_load_factor")
    return {**base, "critical_load_factor": factor, "minimum_critical_load_factor": minimum, "utilization": minimum / factor, "status": _status_ge(factor, minimum, tol), "method_note": "Critical-load-factor threshold is evaluated exactly as supplied; solver and normative validity remain external evidence."}


def _eval_torsion(check: Mapping[str, Any], base: Dict[str, Any], storeys: Set[str], tol: float) -> Dict[str, Any]:
    storey = _text(check.get("storey_id"), f"{base['id']}.storey_id")
    if storey not in storeys:
        raise ValueError(f"{base['id']} references unknown storey {storey}")
    max_drift = abs(_num(check.get("max_edge_drift_m"), f"{base['id']}.max_edge_drift_m"))
    avg_drift = abs(_num(check.get("average_edge_drift_m"), f"{base['id']}.average_edge_drift_m"))
    if avg_drift <= 0:
        raise ValueError(f"{base['id']}.average_edge_drift_m absolute value must be > 0")
    ratio = max_drift / avg_drift
    limit = _positive(check.get("max_torsional_drift_ratio"), f"{base['id']}.max_torsional_drift_ratio")
    return {**base, "storey_id": storey, "max_edge_drift_m": max_drift, "average_edge_drift_m": avg_drift, "torsional_drift_ratio": ratio, "limit": limit, "utilization": ratio / limit, "status": _status_le(ratio, limit, tol)}


def _eval_ratio_min(check: Mapping[str, Any], base: Dict[str, Any], storeys: Set[str], numerator_key: str, denominator_key: str, output_key: str, tol: float) -> Dict[str, Any]:
    storey = _text(check.get("storey_id"), f"{base['id']}.storey_id")
    if storey not in storeys:
        raise ValueError(f"{base['id']} references unknown storey {storey}")
    numerator = _positive(check.get(numerator_key), f"{base['id']}.{numerator_key}")
    denominator = _positive(check.get(denominator_key), f"{base['id']}.{denominator_key}")
    ratio = numerator / denominator
    minimum = _positive(check.get("minimum_ratio"), f"{base['id']}.minimum_ratio")
    return {**base, "storey_id": storey, numerator_key: numerator, denominator_key: denominator, output_key: ratio, "minimum_ratio": minimum, "utilization": minimum / ratio, "status": _status_ge(ratio, minimum, tol)}


def _eval_boolean_evidence(check: Mapping[str, Any], base: Dict[str, Any], evidence_key: str) -> Dict[str, Any]:
    evidence = check.get(evidence_key)
    if not isinstance(evidence, bool):
        raise ValueError(f"{base['id']}.{evidence_key} must be boolean")
    details = _text(check.get("evidence_reference"), f"{base['id']}.evidence_reference")
    return {**base, evidence_key: evidence, "evidence_reference": details, "status": "PASS" if evidence else "FAIL", "utilization": 0.0 if evidence else 1.0}


def _build_graph(edges: Iterable[Mapping[str, Any]], nodes: Set[str], supports: Set[str]) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = defaultdict(set)
    for i, edge in enumerate(edges, 1):
        a = _text(edge.get("from"), f"load_path_edges[{i}].from")
        b = _text(edge.get("to"), f"load_path_edges[{i}].to")
        known = nodes | supports
        if a not in known or b not in known:
            raise ValueError(f"load_path_edges[{i}] references unknown node/support {a}->{b}")
        graph[a].add(b)
        graph[b].add(a)
    return graph


def _reachable_support(start: str, graph: Mapping[str, Set[str]], supports: Set[str]) -> bool:
    q: deque[str] = deque([start])
    seen = {start}
    while q:
        current = q.popleft()
        if current in supports:
            return True
        for nxt in graph.get(current, set()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return False


def _eval_load_path(check: Mapping[str, Any], base: Dict[str, Any], nodes: Set[str], supports: Set[str]) -> Dict[str, Any]:
    starts = [_text(v, f"{base['id']}.loaded_nodes") for v in _items(check.get("loaded_nodes"))]
    if not starts:
        raise ValueError(f"{base['id']}.loaded_nodes must contain at least one node")
    unknown = [v for v in starts if v not in nodes]
    if unknown:
        raise ValueError(f"{base['id']} references unknown loaded nodes: {', '.join(unknown)}")
    edges = [e for e in _items(check.get("load_path_edges")) if isinstance(e, Mapping)]
    if not edges:
        raise ValueError(f"{base['id']}.load_path_edges must contain at least one edge")
    graph = _build_graph(edges, nodes, supports)
    disconnected = [n for n in starts if not _reachable_support(n, graph, supports)]
    return {**base, "loaded_nodes": starts, "edge_count": len(edges), "disconnected_loaded_nodes": disconnected, "status": "PASS" if not disconnected else "FAIL", "utilization": 0.0 if not disconnected else 1.0}


def _evaluate(check: Mapping[str, Any], policy: Mapping[str, Any], nodes: Set[str], supports: Set[str], storeys: Set[str], seen: Set[str]) -> Dict[str, Any]:
    base = _common(check, policy, seen)
    tol = policy["pass_tolerance"]
    ctype = base["check_type"]
    if ctype == "SECOND_ORDER_AMPLIFICATION":
        return _eval_second_order(check, base, tol)
    if ctype == "STOREY_STABILITY_INDEX":
        return _eval_storey_theta(check, base, storeys, tol)
    if ctype == "GLOBAL_BUCKLING_FACTOR":
        return _eval_buckling(check, base, tol)
    if ctype == "TORSIONAL_DRIFT_RATIO":
        return _eval_torsion(check, base, storeys, tol)
    if ctype == "SOFT_STOREY_STIFFNESS_RATIO":
        return _eval_ratio_min(check, base, storeys, "storey_stiffness_kN_per_m", "reference_stiffness_kN_per_m", "stiffness_ratio", tol)
    if ctype == "WEAK_STOREY_STRENGTH_RATIO":
        return _eval_ratio_min(check, base, storeys, "storey_strength_kN", "reference_strength_kN", "strength_ratio", tol)
    if ctype == "DIAPHRAGM_CONTINUITY":
        return _eval_boolean_evidence(check, base, "continuity_verified")
    if ctype == "ALTERNATE_LOAD_PATH_EVIDENCE":
        return _eval_boolean_evidence(check, base, "alternate_path_verified")
    if ctype == "LOAD_PATH_CONTINUITY":
        return _eval_load_path(check, base, nodes, supports)
    raise AssertionError(ctype)


def _coverage(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> List[str]:
    present = {str(r["check_type"]).upper() for r in results if r.get("mandatory")}
    return [ctype for ctype in policy["mandatory_check_types"] if ctype not in present]


def _review_items(results: Sequence[Mapping[str, Any]], missing: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for result in results:
        if result.get("mandatory") and result.get("status") != "PASS":
            items.append({
                "type": "MANDATORY_GLOBAL_STABILITY_CHECK_FAILED",
                "check_id": result["id"],
                "check_type": result["check_type"],
                "status": result["status"],
                "action": "Competent structural engineering review and corrective action required before release.",
            })
    if missing:
        items.append({
            "type": "MANDATORY_GLOBAL_STABILITY_COVERAGE_INCOMPLETE",
            "missing_check_types": list(missing),
            "action": "Provide explicit, traceable evidence for every mandatory global stability/robustness check type.",
        })
    return items


def build_stability_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    policy = _policy(payload)
    _source_gate(payload, policy)
    basis = _basis(payload)
    nodes, supports, storeys = _model_ids(payload)
    checks = [c for c in _items(payload.get("stability_checks")) if isinstance(c, Mapping)]
    if not checks:
        raise ValueError("stability_checks must contain at least one check")
    seen: Set[str] = set()
    results = [_evaluate(c, policy, nodes, supports, storeys, seen) for c in checks]
    missing = _coverage(results, policy)
    reviews = _review_items(results, missing)
    mandatory = [r for r in results if r["mandatory"]]
    if missing:
        state = "GLOBAL_STABILITY_VERIFICATION_INCOMPLETE"
    elif any(r["status"] != "PASS" for r in mandatory):
        state = "GLOBAL_STABILITY_REVIEW_REQUIRED"
    else:
        state = "GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED"
    numeric_utils = [float(r["utilization"]) for r in results if isinstance(r.get("utilization"), (int, float)) and math.isfinite(float(r["utilization"]))]
    report = {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": _text(payload.get("project_id"), "project_id"),
        "source_engine": _text(payload.get("source_engine"), "source_engine"),
        "source_member_verification_state": _text(payload.get("member_verification_state"), "member_verification_state"),
        "stability_basis": basis,
        "verification_state": state,
        "stability_checks": results,
        "summary": {
            "check_count": len(results),
            "mandatory_check_count": len(mandatory),
            "passed_count": sum(1 for r in results if r["status"] == "PASS"),
            "failed_count": sum(1 for r in results if r["status"] == "FAIL"),
            "missing_mandatory_check_types": missing,
            "review_item_count": len(reviews),
            "max_utilization_indicator": max(numeric_utils) if numeric_utils else None,
        },
        "review_items": reviews,
        "digital_twin_writeback": {
            "enabled": True,
            "target": "CENTRAL_DIGITAL_TWIN.structural.global_stability_second_order_robustness",
            "write_mode": "CANDIDATE_EVIDENCE_ONLY",
            "preserve_normative_references": True,
        },
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "remaining_gates": [
                "connection_and_support_verification",
                "foundation_interface_verification",
                "competent_engineering_review",
            ],
        },
    }
    return report


def _demo_payload() -> Dict[str, Any]:
    return {
        "project_id": "PHX-GENERIC-BUILDING-STABILITY-V8.6.0",
        "source_engine": "PHX-STRUCT-CODE-LIMIT-STATE-MEMBER-VERIFICATION-V8.5.0",
        "member_verification_state": "MEMBER_VERIFICATION_CANDIDATE_PASSED",
        "stability_basis": {
            "jurisdiction": "PROJECT_DEFINED",
            "standard_set": "PROJECT_DEFINED_STRUCTURAL_STANDARD",
            "edition": "PROJECT_DEFINED_EDITION",
            "source_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:GLOBAL_STABILITY",
            "status": "ENGINEER_OR_VERIFIED_STANDARDS_ENGINE_INPUT",
        },
        "analytical_model": {
            "nodes": [{"id": "N1"}, {"id": "N2"}, {"id": "N3"}, {"id": "N4"}],
            "supports": [{"id": "S1"}, {"id": "S2"}],
            "storeys": [{"id": "L1"}, {"id": "L2"}],
        },
        "stability_checks": [
            {
                "id": "GS-2ND",
                "check_type": "SECOND_ORDER_AMPLIFICATION",
                "first_order_displacement_m": 0.018,
                "second_order_displacement_m": 0.0207,
                "max_amplification_factor": 1.20,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:SECOND_ORDER_LIMIT",
            },
            {
                "id": "GS-THETA-L2",
                "check_type": "STOREY_STABILITY_INDEX",
                "storey_id": "L2",
                "gravity_load_kN": 5200.0,
                "storey_drift_m": 0.008,
                "storey_shear_kN": 680.0,
                "storey_height_m": 3.4,
                "max_stability_index": 0.10,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:STOREY_STABILITY_INDEX_LIMIT",
            },
            {
                "id": "GS-BUCKLING",
                "check_type": "GLOBAL_BUCKLING_FACTOR",
                "critical_load_factor": 8.2,
                "minimum_critical_load_factor": 5.0,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:GLOBAL_BUCKLING_FACTOR",
            },
            {
                "id": "GS-TORSION-L2",
                "check_type": "TORSIONAL_DRIFT_RATIO",
                "storey_id": "L2",
                "max_edge_drift_m": 0.0102,
                "average_edge_drift_m": 0.0085,
                "max_torsional_drift_ratio": 1.40,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:TORSIONAL_DRIFT_LIMIT",
            },
            {
                "id": "GS-SOFT-L1",
                "check_type": "SOFT_STOREY_STIFFNESS_RATIO",
                "storey_id": "L1",
                "storey_stiffness_kN_per_m": 125000.0,
                "reference_stiffness_kN_per_m": 150000.0,
                "minimum_ratio": 0.70,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:SOFT_STOREY_STIFFNESS_RATIO",
            },
            {
                "id": "GS-WEAK-L1",
                "check_type": "WEAK_STOREY_STRENGTH_RATIO",
                "storey_id": "L1",
                "storey_strength_kN": 1550.0,
                "reference_strength_kN": 1750.0,
                "minimum_ratio": 0.80,
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:WEAK_STOREY_STRENGTH_RATIO",
            },
            {
                "id": "GS-DIAPH",
                "check_type": "DIAPHRAGM_CONTINUITY",
                "continuity_verified": True,
                "evidence_reference": "PHX_ANALYTICAL_MODEL:DIAPHRAGM_CONNECTIVITY_EVIDENCE",
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:DIAPHRAGM_CONTINUITY",
            },
            {
                "id": "GS-LOADPATH",
                "check_type": "LOAD_PATH_CONTINUITY",
                "loaded_nodes": ["N3", "N4"],
                "load_path_edges": [
                    {"from": "N3", "to": "N2"},
                    {"from": "N4", "to": "N1"},
                    {"from": "N2", "to": "N1"},
                    {"from": "N1", "to": "S1"},
                ],
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:LOAD_PATH_CONTINUITY",
            },
            {
                "id": "GS-ALP",
                "check_type": "ALTERNATE_LOAD_PATH_EVIDENCE",
                "alternate_path_verified": True,
                "evidence_reference": "PROJECT_ROBUSTNESS_ASSESSMENT:ALTERNATE_PATH_CASES",
                "mandatory": True,
                "normative_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:ROBUSTNESS_ALTERNATE_LOAD_PATH",
            },
        ],
        "stability_policy": {
            "acceptable_member_verification_states": ["MEMBER_VERIFICATION_CANDIDATE_PASSED"],
            "require_normative_reference": True,
            "mandatory_check_types": sorted(SUPPORTED_CHECK_TYPES),
            "pass_tolerance": 1e-12,
        },
        "release_policy": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "structural_model_release": "LOCKED",
        },
    }


def _self_test() -> Dict[str, Any]:
    report = build_stability_report(_demo_payload())
    assert report["verification_state"] == "GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED"
    assert report["summary"]["review_item_count"] == 0
    assert report["summary"]["check_count"] == 9
    assert report["release"]["structural_model_release"] == "LOCKED"
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON stability-verification payload")
    parser.add_argument("--output", type=Path, help="Write JSON report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        report = _self_test()
        print("GLOBAL STABILITY / SECOND-ORDER / ROBUSTNESS SELF-TEST: PASSED")
        print(f"STABILITY CHECKS: {report['summary']['check_count']}")
        print(f"REVIEW ITEMS: {report['summary']['review_item_count']}")
        print(f"VERIFICATION STATE: {report['verification_state']}")
        print("AUTOMATIC CODE COMPLIANCE CLAIM: DISABLED")
        print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
        print("STRUCTURAL MODEL RELEASE: LOCKED")
        return 0

    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_stability_report(payload)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
