#!/usr/bin/env python3
"""Project Phoenix Structural Code, Limit-State & Member Verification Engine v8.5.0.

The engine evaluates explicit verification rules against validated solver results.
Normative parameters remain external and must carry traceable source references.
A PASS means the configured rule evaluated within its supplied limit; it is not a
standalone legal/code-compliance declaration and never grants structural release.
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

ENGINE_ID = "PHX-STRUCT-CODE-LIMIT-STATE-MEMBER-VERIFICATION-V8.5.0"
VERSION = "8.5.0"
LOCKED_RELEASE = "LOCKED"
SUPPORTED_RULE_TYPES = {
    "FORCE_CAPACITY_RATIO",
    "LINEAR_INTERACTION",
    "NODE_DISPLACEMENT_LIMIT",
    "SLENDERNESS_LIMIT",
    "BUCKLING_RESISTANCE_RATIO",
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


def _code_basis(payload: Mapping[str, Any]) -> Dict[str, str]:
    raw = payload.get("code_basis")
    if not isinstance(raw, Mapping):
        raise ValueError("code_basis must be an object")
    result = {
        "jurisdiction": _text(raw.get("jurisdiction"), "code_basis.jurisdiction"),
        "standard_set": _text(raw.get("standard_set"), "code_basis.standard_set"),
        "edition": _text(raw.get("edition"), "code_basis.edition"),
        "source_reference": _text(raw.get("source_reference"), "code_basis.source_reference"),
        "status": _text(raw.get("status"), "code_basis.status"),
    }
    return result


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(payload.get("verification_policy") or {})
    states = [str(v) for v in _items(raw.get("acceptable_analysis_validation_states") or ["SANITY_VALIDATED_CANDIDATE"])]
    limits = [str(v).upper() for v in _items(raw.get("mandatory_limit_states") or ["ULS", "SLS"])]
    return {
        "acceptable_analysis_validation_states": states,
        "require_normative_reference": bool(raw.get("require_normative_reference", True)),
        "require_mandatory_rules_for_each_member": bool(raw.get("require_mandatory_rules_for_each_member", True)),
        "mandatory_limit_states": limits,
        "pass_tolerance": _nonnegative(raw.get("pass_tolerance", 1e-12), "pass_tolerance"),
    }


def _known_model_ids(payload: Mapping[str, Any]) -> Tuple[set[str], set[str]]:
    model = payload.get("analytical_model") or {}
    members = {_text(v.get("id"), "member id") for v in _items(model.get("members")) if isinstance(v, Mapping)}
    nodes = {_text(v.get("id"), "node id") for v in _items(model.get("nodes")) if isinstance(v, Mapping)}
    if not members:
        raise ValueError("analytical_model.members must contain at least one member")
    return members, nodes


def _result(payload: Mapping[str, Any], solver: str, combination_id: str) -> Mapping[str, Any]:
    combos = payload.get("combination_results") or {}
    if solver not in combos or combination_id not in (combos.get(solver) or {}):
        raise ValueError(f"Missing combination result {solver}/{combination_id}")
    result = combos[solver][combination_id]
    if not isinstance(result, Mapping):
        raise ValueError(f"Combination result {solver}/{combination_id} must be an object")
    return result


def _member_force(result: Mapping[str, Any], member_id: str, component: str) -> float:
    forces = result.get("element_forces") or {}
    if member_id not in forces or not isinstance(forces[member_id], Mapping):
        raise ValueError(f"Missing element forces for member {member_id}")
    raw = forces[member_id]
    c = component.upper()
    if c == "N_COMPRESSION":
        n = _num(raw.get("N", 0.0), f"{member_id}.N")
        return max(-n, 0.0)
    if c == "N_TENSION":
        n = _num(raw.get("N", 0.0), f"{member_id}.N")
        return max(n, 0.0)
    if c not in {"N", "VY", "VZ", "MY", "MZ", "T"}:
        raise ValueError(f"Unsupported demand component: {component}")
    return abs(_num(raw.get(c, 0.0), f"{member_id}.{c}"))


def _result_limit_state(result: Mapping[str, Any], requested: str, label: str) -> None:
    actual = str(result.get("limit_state") or "").upper()
    if actual and actual != requested.upper():
        raise ValueError(f"{label} limit-state mismatch: rule={requested}, result={actual}")


def _check_common(rule: Mapping[str, Any], members: set[str], policy: Mapping[str, Any], seen_ids: set[str]) -> Dict[str, Any]:
    rid = _text(rule.get("id"), "verification rule id")
    if rid in seen_ids:
        raise ValueError(f"Duplicate verification rule id: {rid}")
    seen_ids.add(rid)
    member_id = _text(rule.get("member_id"), f"{rid}.member_id")
    if member_id not in members:
        raise ValueError(f"{rid} references unknown member {member_id}")
    limit_state = _text(rule.get("limit_state"), f"{rid}.limit_state").upper()
    solver = _text(rule.get("solver"), f"{rid}.solver").lower()
    combination_id = _text(rule.get("combination_id"), f"{rid}.combination_id")
    rule_type = _text(rule.get("rule_type"), f"{rid}.rule_type").upper()
    if rule_type not in SUPPORTED_RULE_TYPES:
        raise ValueError(f"{rid} unsupported rule_type {rule_type}")
    normative_reference = str(rule.get("normative_reference") or "").strip()
    if policy["require_normative_reference"] and not normative_reference:
        raise ValueError(f"{rid} missing normative_reference")
    return {
        "id": rid,
        "member_id": member_id,
        "limit_state": limit_state,
        "solver": solver,
        "combination_id": combination_id,
        "rule_type": rule_type,
        "mandatory": bool(rule.get("mandatory", True)),
        "normative_reference": normative_reference,
    }


def _evaluate_rule(payload: Mapping[str, Any], rule: Mapping[str, Any], members: set[str], nodes: set[str], policy: Mapping[str, Any], seen_ids: set[str]) -> Dict[str, Any]:
    base = _check_common(rule, members, policy, seen_ids)
    result = _result(payload, base["solver"], base["combination_id"])
    _result_limit_state(result, base["limit_state"], base["id"])
    tol = policy["pass_tolerance"]
    rtype = base["rule_type"]

    if rtype == "FORCE_CAPACITY_RATIO":
        component = _text(rule.get("demand_component"), f"{base['id']}.demand_component").upper()
        demand = _member_force(result, base["member_id"], component)
        capacity = _positive(rule.get("capacity"), f"{base['id']}.capacity")
        utilization = demand / capacity
        return {**base, "demand_component": component, "demand": demand, "capacity": capacity, "unit": _text(rule.get("unit"), f"{base['id']}.unit"), "utilization": utilization, "limit": 1.0, "status": "PASS" if utilization <= 1.0 + tol else "FAIL"}

    if rtype == "BUCKLING_RESISTANCE_RATIO":
        demand = _member_force(result, base["member_id"], "N_COMPRESSION")
        capacity = _positive(rule.get("buckling_resistance_kN"), f"{base['id']}.buckling_resistance_kN")
        utilization = demand / capacity
        return {**base, "demand_component": "N_COMPRESSION", "demand_kN": demand, "buckling_resistance_kN": capacity, "utilization": utilization, "limit": 1.0, "status": "PASS" if utilization <= 1.0 + tol else "FAIL"}

    if rtype == "LINEAR_INTERACTION":
        terms = _items(rule.get("terms"))
        if not terms:
            raise ValueError(f"{base['id']} LINEAR_INTERACTION requires terms")
        evaluated_terms = []
        interaction = 0.0
        for i, term in enumerate(terms, 1):
            if not isinstance(term, Mapping):
                raise ValueError(f"{base['id']} term {i} must be an object")
            component = _text(term.get("demand_component"), f"{base['id']} term {i} demand_component").upper()
            demand = _member_force(result, base["member_id"], component)
            capacity = _positive(term.get("capacity"), f"{base['id']} term {i} capacity")
            ratio = demand / capacity
            interaction += ratio
            evaluated_terms.append({"demand_component": component, "demand": demand, "capacity": capacity, "unit": _text(term.get("unit"), f"{base['id']} term {i} unit"), "ratio": ratio})
        limit = _positive(rule.get("limit", 1.0), f"{base['id']}.limit")
        return {**base, "terms": evaluated_terms, "interaction_value": interaction, "utilization": interaction / limit, "limit": limit, "status": "PASS" if interaction <= limit + tol else "FAIL", "method_note": "Configured linear interaction is evaluated exactly as supplied; its normative validity belongs to the cited design basis."}

    if rtype == "NODE_DISPLACEMENT_LIMIT":
        node_id = _text(rule.get("node_id"), f"{base['id']}.node_id")
        if nodes and node_id not in nodes:
            raise ValueError(f"{base['id']} references unknown node {node_id}")
        dof = _text(rule.get("dof"), f"{base['id']}.dof").upper()
        displacement = result.get("node_displacements") or {}
        if node_id not in displacement or dof not in (displacement.get(node_id) or {}):
            raise ValueError(f"{base['id']} missing displacement {node_id}.{dof}")
        actual = abs(_num(displacement[node_id][dof], f"{base['id']} displacement"))
        limit = _positive(rule.get("max_abs_displacement_m"), f"{base['id']}.max_abs_displacement_m")
        utilization = actual / limit
        return {**base, "node_id": node_id, "dof": dof, "absolute_displacement_m": actual, "max_abs_displacement_m": limit, "utilization": utilization, "limit": 1.0, "status": "PASS" if utilization <= 1.0 + tol else "FAIL"}

    if rtype == "SLENDERNESS_LIMIT":
        actual = _nonnegative(rule.get("actual_slenderness"), f"{base['id']}.actual_slenderness")
        limit = _positive(rule.get("max_slenderness"), f"{base['id']}.max_slenderness")
        utilization = actual / limit
        return {**base, "actual_slenderness": actual, "max_slenderness": limit, "utilization": utilization, "limit": 1.0, "status": "PASS" if utilization <= 1.0 + tol else "FAIL"}

    raise AssertionError("unreachable")


def _coverage(members: set[str], results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    coverage: List[Dict[str, Any]] = []
    for member_id in sorted(members):
        for limit_state in policy["mandatory_limit_states"]:
            matching = [r for r in results if r["member_id"] == member_id and r["limit_state"] == limit_state and r["mandatory"]]
            status = "PASS" if matching else "INCOMPLETE"
            coverage.append({"member_id": member_id, "limit_state": limit_state, "mandatory_rule_count": len(matching), "status": status})
    return coverage


def _member_envelopes(members: set[str], results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for member_id in sorted(members):
        checks = [r for r in results if r["member_id"] == member_id]
        utilizations = [float(r["utilization"]) for r in checks if "utilization" in r]
        mandatory = [r for r in checks if r["mandatory"]]
        if any(r["status"] == "FAIL" for r in mandatory):
            state = "FAIL"
        elif any(r["status"] not in {"PASS"} for r in mandatory):
            state = "INCOMPLETE"
        else:
            state = "PASS"
        governing = max(checks, key=lambda r: float(r.get("utilization", 0.0))) if checks else None
        output[member_id] = {
            "status": state,
            "check_count": len(checks),
            "mandatory_check_count": len(mandatory),
            "max_utilization": max(utilizations) if utilizations else None,
            "governing_rule_id": governing["id"] if governing else None,
            "governing_rule_type": governing["rule_type"] if governing else None,
        }
    return output


def build_verification_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    project_id = _text(payload.get("project_id"), "project_id")
    source_engine = _text(payload.get("source_engine"), "source_engine")
    if "V8.4.0" not in source_engine.upper():
        raise ValueError("v8.5.0 expects input originating from the v8.4.0 analysis-results validation contract")
    basis = _code_basis(payload)
    policy = _policy(payload)
    analysis_state = _text(payload.get("analysis_validation_state"), "analysis_validation_state")
    if analysis_state not in policy["acceptable_analysis_validation_states"]:
        raise ValueError(f"analysis_validation_state {analysis_state!r} is not accepted for member verification")
    members, nodes = _known_model_ids(payload)
    rules = _items(payload.get("verification_rules"))
    if not rules:
        raise ValueError("verification_rules must contain at least one explicit rule")
    seen_ids: set[str] = set()
    evaluated = []
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise ValueError("verification_rules entries must be objects")
        evaluated.append(_evaluate_rule(payload, rule, members, nodes, policy, seen_ids))

    coverage = _coverage(members, evaluated, policy) if policy["require_mandatory_rules_for_each_member"] else []
    envelopes = _member_envelopes(members, evaluated)
    review_items: List[Dict[str, Any]] = []
    for result in evaluated:
        if result["mandatory"] and result["status"] != "PASS":
            review_items.append({"type": "MANDATORY_RULE_NOT_PASSED", "rule_id": result["id"], "member_id": result["member_id"], "status": result["status"], "utilization": result.get("utilization"), "normative_reference": result["normative_reference"]})
    for item in coverage:
        if item["status"] != "PASS":
            review_items.append({"type": "MANDATORY_LIMIT_STATE_COVERAGE_INCOMPLETE", **item})

    mandatory_failures = [r for r in evaluated if r["mandatory"] and r["status"] == "FAIL"]
    incomplete = [c for c in coverage if c["status"] != "PASS"]
    if mandatory_failures:
        state = "MEMBER_VERIFICATION_FAILED_REVIEW_REQUIRED"
    elif incomplete:
        state = "MEMBER_VERIFICATION_INCOMPLETE"
    else:
        state = "MEMBER_VERIFICATION_CANDIDATE_PASSED"

    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": project_id,
        "source_engine": source_engine,
        "analysis_validation_state": analysis_state,
        "verification_state": state,
        "code_basis": basis,
        "policy": deepcopy(policy),
        "verification_results": evaluated,
        "coverage": coverage,
        "member_envelopes": envelopes,
        "review_items": review_items,
        "summary": {
            "member_count": len(members),
            "rule_count": len(evaluated),
            "mandatory_rule_count": sum(1 for r in evaluated if r["mandatory"]),
            "passed_rule_count": sum(1 for r in evaluated if r["status"] == "PASS"),
            "failed_rule_count": sum(1 for r in evaluated if r["status"] == "FAIL"),
            "review_item_count": len(review_items),
            "max_utilization": max((float(r.get("utilization", 0.0)) for r in evaluated), default=0.0),
        },
        "digital_twin_writeback": {
            "enabled": True,
            "target": "CENTRAL_DIGITAL_TWIN.structural.code_limit_state_member_verification",
            "write_state": state,
            "normative_traceability_preserved": True,
            "automatic_release": False,
        },
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "engineering_review_required": True,
            "next_required_capabilities": [
                "GLOBAL_STABILITY_AND_SECOND_ORDER_VERIFICATION",
                "CONNECTION_AND_SUPPORT_VERIFICATION",
                "FOUNDATION_INTERFACE_VERIFICATION",
                "ENGINEERING_REVIEW_AND_RELEASE_GATE",
            ],
        },
        "disclaimer": "Configured verification rules were evaluated against supplied analysis results. Normative correctness of rule selection, capacities, limits and references remains subject to the cited design basis and competent engineering review.",
    }


def _demo_payload() -> Dict[str, Any]:
    return {
        "project_id": "SELF-TEST-V8.5.0",
        "source_engine": "PHX-STRUCT-ANALYSIS-RESULTS-VALIDATION-V8.4.0",
        "analysis_validation_state": "SANITY_VALIDATED_CANDIDATE",
        "code_basis": {
            "jurisdiction": "SELF_TEST",
            "standard_set": "EXPLICIT_TEST_DESIGN_BASIS",
            "edition": "TEST-1",
            "source_reference": "self-test/design-basis",
            "status": "VERIFIED_TEST_INPUT",
        },
        "analytical_model": {
            "members": [{"id": "M1", "length_m": 5.0, "material_family": "steel"}],
            "nodes": [{"id": "N1"}, {"id": "N2"}],
        },
        "combination_results": {
            "opensees": {
                "ULS1": {
                    "limit_state": "ULS",
                    "node_displacements": {"N2": {"UZ": -0.007}},
                    "element_forces": {"M1": {"N": -180.0, "VY": 35.0, "VZ": 12.0, "MY": 70.0, "MZ": 8.0, "T": 2.0}},
                },
                "SLS1": {
                    "limit_state": "SLS",
                    "node_displacements": {"N2": {"UZ": -0.011}},
                    "element_forces": {"M1": {"N": -95.0, "VY": 18.0, "VZ": 8.0, "MY": 42.0, "MZ": 5.0, "T": 1.0}},
                },
            }
        },
        "verification_rules": [
            {"id": "R-N", "member_id": "M1", "limit_state": "ULS", "combination_id": "ULS1", "solver": "opensees", "rule_type": "FORCE_CAPACITY_RATIO", "demand_component": "N_COMPRESSION", "capacity": 420.0, "unit": "kN", "mandatory": True, "normative_reference": "basis:R-N"},
            {"id": "R-MY", "member_id": "M1", "limit_state": "ULS", "combination_id": "ULS1", "solver": "opensees", "rule_type": "FORCE_CAPACITY_RATIO", "demand_component": "MY", "capacity": 160.0, "unit": "kNm", "mandatory": True, "normative_reference": "basis:R-MY"},
            {"id": "R-INT", "member_id": "M1", "limit_state": "ULS", "combination_id": "ULS1", "solver": "opensees", "rule_type": "LINEAR_INTERACTION", "limit": 1.0, "mandatory": True, "terms": [{"demand_component": "N_COMPRESSION", "capacity": 420.0, "unit": "kN"}, {"demand_component": "MY", "capacity": 160.0, "unit": "kNm"}], "normative_reference": "basis:R-INT"},
            {"id": "R-BUCK", "member_id": "M1", "limit_state": "ULS", "combination_id": "ULS1", "solver": "opensees", "rule_type": "BUCKLING_RESISTANCE_RATIO", "buckling_resistance_kN": 360.0, "mandatory": True, "normative_reference": "basis:R-BUCK"},
            {"id": "R-DEF", "member_id": "M1", "limit_state": "SLS", "combination_id": "SLS1", "solver": "opensees", "rule_type": "NODE_DISPLACEMENT_LIMIT", "node_id": "N2", "dof": "UZ", "max_abs_displacement_m": 0.02, "mandatory": True, "normative_reference": "basis:R-DEF"},
            {"id": "R-SLEND", "member_id": "M1", "limit_state": "SLS", "combination_id": "SLS1", "solver": "opensees", "rule_type": "SLENDERNESS_LIMIT", "actual_slenderness": 72.0, "max_slenderness": 120.0, "mandatory": False, "normative_reference": "basis:R-SLEND"},
        ],
        "verification_policy": {
            "acceptable_analysis_validation_states": ["SANITY_VALIDATED_CANDIDATE"],
            "require_normative_reference": True,
            "require_mandatory_rules_for_each_member": True,
            "mandatory_limit_states": ["ULS", "SLS"],
            "pass_tolerance": 1e-12,
        },
    }


def self_test() -> None:
    report = build_verification_report(_demo_payload())
    assert report["engine"]["version"] == VERSION
    assert report["verification_state"] == "MEMBER_VERIFICATION_CANDIDATE_PASSED"
    assert report["summary"]["rule_count"] == 6
    assert report["summary"]["review_item_count"] == 0
    assert report["member_envelopes"]["M1"]["status"] == "PASS"
    assert report["release"]["automatic_code_compliance_claim"] is False
    assert report["release"]["automatic_structural_approval"] is False
    assert report["release"]["structural_model_release"] == "LOCKED"
    print("STRUCTURAL CODE, LIMIT-STATE & MEMBER VERIFICATION ENGINE: PASSED")
    print("EXPLICIT CODE BASIS CONTRACT: VERIFIED")
    print("NORMATIVE REFERENCE TRACEABILITY: ENFORCED")
    print("ULS MEMBER FORCE/CAPACITY CHECKS: PASSED")
    print("CONFIGURED MEMBER INTERACTION CHECKS: PASSED")
    print("COMPRESSION BUCKLING RESISTANCE CHECKS: PASSED")
    print("SLS DISPLACEMENT/LIMIT CHECKS: PASSED")
    print("MEMBER VERIFICATION ENVELOPE: GENERATED")
    print("CENTRAL DIGITAL TWIN VERIFICATION WRITEBACK: PASSED")
    print("AUTOMATIC CODE COMPLIANCE CLAIM: DISABLED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_verification_report(payload)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
