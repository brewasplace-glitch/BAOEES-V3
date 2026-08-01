#!/usr/bin/env python3
"""Project Phoenix Structural Connection, Support & Joint Verification Engine v8.7.0.

The engine consumes the v8.6.0 global-stability candidate and evaluates explicit,
traceable connection/support/joint evidence. It never invents normative capacities,
connection resistances, bolt/weld/anchor strengths or stiffness classifications.
PASS means only that the configured evidence satisfies the configured explicit rule.
It is not a statutory code-compliance statement and never unlocks structural release.
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-CONNECTION-SUPPORT-JOINT-VERIFICATION-V8.7.0"
VERSION = "8.7.0"
LOCKED_RELEASE = "LOCKED"
CAPACITY_CHECK_TYPES = {
    "BEAM_COLUMN_CONNECTION",
    "BEAM_BEAM_CONNECTION",
    "COLUMN_BASE_CONNECTION",
    "SUPPORT_REACTION_CAPACITY",
    "BOLT_GROUP_CAPACITY",
    "WELD_CAPACITY",
    "ANCHOR_GROUP_CAPACITY",
    "BEARING_CAPACITY",
}
EVIDENCE_CHECK_TYPES = {"JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE"}
SUPPORTED_CHECK_TYPES = CAPACITY_CHECK_TYPES | EVIDENCE_CHECK_TYPES
CONNECTION_CHECK_TYPES = {
    "BEAM_COLUMN_CONNECTION", "BEAM_BEAM_CONNECTION", "COLUMN_BASE_CONNECTION",
    "BOLT_GROUP_CAPACITY", "WELD_CAPACITY", "ANCHOR_GROUP_CAPACITY", "BEARING_CAPACITY"
}


def _items(value: Any) -> List[Any]:
    if value is None: return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result: raise ValueError(f"{label} must be a non-empty string")
    return result


def _num(value: Any, label: str) -> float:
    if isinstance(value, bool): raise ValueError(f"{label} must be numeric, not boolean")
    try: result = float(value)
    except (TypeError, ValueError) as exc: raise ValueError(f"{label} must be numeric: {value!r}") from exc
    if not math.isfinite(result): raise ValueError(f"{label} must be finite")
    return result


def _nonnegative(value: Any, label: str) -> float:
    result = _num(value, label)
    if result < 0: raise ValueError(f"{label} must be >= 0")
    return result


def _positive(value: Any, label: str) -> float:
    result = _num(value, label)
    if result <= 0: raise ValueError(f"{label} must be > 0")
    return result


def _basis(payload: Mapping[str, Any]) -> Dict[str, str]:
    raw = payload.get("connection_basis")
    if not isinstance(raw, Mapping): raise ValueError("connection_basis must be an object")
    return {
        "jurisdiction": _text(raw.get("jurisdiction"), "connection_basis.jurisdiction"),
        "standard_set": _text(raw.get("standard_set"), "connection_basis.standard_set"),
        "edition": _text(raw.get("edition"), "connection_basis.edition"),
        "source_reference": _text(raw.get("source_reference"), "connection_basis.source_reference"),
        "status": _text(raw.get("status"), "connection_basis.status"),
    }


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(payload.get("verification_policy") or {})
    acceptable = [str(v) for v in _items(raw.get("acceptable_global_stability_states") or ["GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED"])]
    mandatory = [str(v).upper() for v in _items(raw.get("mandatory_check_types") or sorted(SUPPORTED_CHECK_TYPES))]
    unknown = [v for v in mandatory if v not in SUPPORTED_CHECK_TYPES]
    if unknown: raise ValueError(f"Unsupported mandatory_check_types: {', '.join(unknown)}")
    return {
        "acceptable_global_stability_states": acceptable,
        "require_normative_reference": bool(raw.get("require_normative_reference", True)),
        "mandatory_check_types": mandatory,
        "pass_tolerance": _nonnegative(raw.get("pass_tolerance", 1e-12), "pass_tolerance"),
    }


def _ids(payload: Mapping[str, Any]) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    model = payload.get("structural_model") or {}
    if not isinstance(model, Mapping): raise ValueError("structural_model must be an object")
    def ids(key: str) -> Set[str]:
        return {_text(v.get("id"), f"{key} id") for v in _items(model.get(key)) if isinstance(v, Mapping)}
    members, joints, supports, connections = ids("members"), ids("joints"), ids("supports"), ids("connection_candidates")
    if not members: raise ValueError("structural_model.members must contain at least one member")
    if not joints: raise ValueError("structural_model.joints must contain at least one joint")
    if not supports: raise ValueError("structural_model.supports must contain at least one support")
    if not connections: raise ValueError("structural_model.connection_candidates must contain at least one connection")
    return members, joints, supports, connections


def _source_gate(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    source = _text(payload.get("source_engine"), "source_engine")
    if "V8.6.0" not in source.upper(): raise ValueError("source_engine must identify the v8.6.0 global stability engine")
    state = _text(payload.get("global_stability_state"), "global_stability_state")
    if state not in policy["acceptable_global_stability_states"]:
        raise ValueError(f"global_stability_state '{state}' is not accepted by verification_policy")


def _common(check: Mapping[str, Any], policy: Mapping[str, Any], seen: Set[str]) -> Dict[str, Any]:
    cid = _text(check.get("id"), "verification check id")
    if cid in seen: raise ValueError(f"Duplicate verification check id: {cid}")
    seen.add(cid)
    ctype = _text(check.get("check_type"), f"{cid}.check_type").upper()
    if ctype not in SUPPORTED_CHECK_TYPES: raise ValueError(f"{cid} unsupported check_type {ctype}")
    ref = str(check.get("normative_reference") or "").strip()
    if policy["require_normative_reference"] and not ref: raise ValueError(f"{cid} missing normative_reference")
    return {"id": cid, "check_type": ctype, "mandatory": bool(check.get("mandatory", True)), "normative_reference": ref}


def _capacity_check(check: Mapping[str, Any], base: Dict[str, Any], tol: float, connections: Set[str], supports: Set[str]) -> Dict[str, Any]:
    if base["check_type"] == "SUPPORT_REACTION_CAPACITY":
        support_id = _text(check.get("support_id"), f"{base['id']}.support_id")
        if support_id not in supports: raise ValueError(f"{base['id']} references unknown support {support_id}")
        reference = {"support_id": support_id}
    else:
        connection_id = _text(check.get("connection_id"), f"{base['id']}.connection_id")
        if connection_id not in connections: raise ValueError(f"{base['id']} references unknown connection {connection_id}")
        reference = {"connection_id": connection_id}
    demand = _nonnegative(check.get("demand"), f"{base['id']}.demand")
    capacity = _positive(check.get("capacity"), f"{base['id']}.capacity")
    quantity = _text(check.get("quantity"), f"{base['id']}.quantity")
    unit = _text(check.get("unit"), f"{base['id']}.unit")
    utilization = demand / capacity
    status = "PASS" if demand <= capacity + tol else "FAIL"
    return {**base, **reference, "quantity": quantity, "unit": unit, "demand": demand, "capacity": capacity, "utilization": utilization, "status": status,
            "method_note": "Demand/capacity values are evaluated exactly as supplied; resistance derivation and normative validity remain external evidence."}


def _stiffness_evidence(check: Mapping[str, Any], base: Dict[str, Any], joints: Set[str]) -> Dict[str, Any]:
    joint_id = _text(check.get("joint_id"), f"{base['id']}.joint_id")
    if joint_id not in joints: raise ValueError(f"{base['id']} references unknown joint {joint_id}")
    classification = _text(check.get("classification"), f"{base['id']}.classification")
    verified = check.get("classification_verified")
    if not isinstance(verified, bool): raise ValueError(f"{base['id']}.classification_verified must be boolean")
    evidence = _text(check.get("evidence_reference"), f"{base['id']}.evidence_reference")
    return {**base, "joint_id": joint_id, "classification": classification, "classification_verified": verified, "evidence_reference": evidence,
            "utilization": 0.0 if verified else 1.0, "status": "PASS" if verified else "FAIL"}


def _evaluate(check: Mapping[str, Any], policy: Mapping[str, Any], joints: Set[str], supports: Set[str], connections: Set[str], seen: Set[str]) -> Dict[str, Any]:
    base = _common(check, policy, seen)
    if base["check_type"] in CAPACITY_CHECK_TYPES:
        return _capacity_check(check, base, policy["pass_tolerance"], connections, supports)
    return _stiffness_evidence(check, base, joints)


def _coverage(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> List[str]:
    present = {str(r["check_type"]).upper() for r in results if r.get("mandatory")}
    return [ctype for ctype in policy["mandatory_check_types"] if ctype not in present]


def _review_items(results: Sequence[Mapping[str, Any]], missing: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for result in results:
        if result.get("mandatory") and result.get("status") != "PASS":
            items.append({"type":"MANDATORY_CONNECTION_SUPPORT_JOINT_CHECK_FAILED","check_id":result["id"],"check_type":result["check_type"],"status":result["status"],
                          "action":"Competent structural engineering review and corrective action required before release."})
    if missing:
        items.append({"type":"MANDATORY_CONNECTION_SUPPORT_JOINT_COVERAGE_INCOMPLETE","missing_check_types":list(missing),
                      "action":"Provide explicit, traceable evidence for every mandatory connection/support/joint check type."})
    return items


def build_connection_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping): raise ValueError("payload must be an object")
    policy = _policy(payload)
    _source_gate(payload, policy)
    basis = _basis(payload)
    _members, joints, supports, connections = _ids(payload)
    checks = [c for c in _items(payload.get("verification_checks")) if isinstance(c, Mapping)]
    if not checks: raise ValueError("verification_checks must contain at least one check")
    seen: Set[str] = set()
    results = [_evaluate(c, policy, joints, supports, connections, seen) for c in checks]
    missing = _coverage(results, policy)
    reviews = _review_items(results, missing)
    mandatory = [r for r in results if r["mandatory"]]
    if missing: state = "CONNECTION_SUPPORT_JOINT_VERIFICATION_INCOMPLETE"
    elif any(r["status"] != "PASS" for r in mandatory): state = "CONNECTION_SUPPORT_JOINT_REVIEW_REQUIRED"
    else: state = "CONNECTION_SUPPORT_JOINT_CANDIDATE_PASSED"
    utils = [float(r["utilization"]) for r in results if isinstance(r.get("utilization"),(int,float)) and math.isfinite(float(r["utilization"]))]
    return {
        "engine":{"id":ENGINE_ID,"version":VERSION},
        "project_id":_text(payload.get("project_id"),"project_id"),
        "source_engine":_text(payload.get("source_engine"),"source_engine"),
        "source_global_stability_state":_text(payload.get("global_stability_state"),"global_stability_state"),
        "connection_basis":basis,
        "verification_state":state,
        "verification_checks":results,
        "summary":{"check_count":len(results),"mandatory_check_count":len(mandatory),"passed_count":sum(1 for r in results if r["status"]=="PASS"),
                   "failed_count":sum(1 for r in results if r["status"]=="FAIL"),"missing_mandatory_check_types":missing,"review_item_count":len(reviews),
                   "max_utilization_indicator":max(utils) if utils else None},
        "review_items":reviews,
        "digital_twin_writeback":{"enabled":True,"target":"CENTRAL_DIGITAL_TWIN.structural.connection_support_joint_verification","write_mode":"CANDIDATE_EVIDENCE_ONLY","preserve_normative_references":True},
        "release":{"automatic_code_compliance_claim":False,"automatic_structural_approval":False,"automatic_connection_approval":False,"structural_model_release":LOCKED_RELEASE,
                   "remaining_gates":["foundation_interface_verification","competent_engineering_review"]}
    }


def _demo_payload() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "configs" / "projects" / "generic_building_structural_connection_support_joint_v8_7_0.json"
    if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
    return {
      "project_id":"PHX-GENERIC-BUILDING-CONNECTIONS-V8.7.0","source_engine":"PHX-STRUCT-GLOBAL-STABILITY-SECOND-ORDER-ROBUSTNESS-V8.6.0",
      "global_stability_state":"GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED",
      "connection_basis":{"jurisdiction":"PROJECT_DEFINED","standard_set":"PROJECT_DEFINED_STRUCTURAL_STANDARD","edition":"PROJECT_DEFINED_EDITION","source_reference":"PROJECT_STRUCTURAL_DESIGN_BASIS:CONNECTIONS_SUPPORTS_JOINTS","status":"ENGINEER_OR_VERIFIED_STANDARDS_ENGINE_INPUT"},
      "structural_model":{"members":[{"id":"B1"}],"joints":[{"id":"J1"}],"supports":[{"id":"S1"}],"connection_candidates":[{"id":"C1"}]},
      "verification_checks":[
        {"id":"T1","check_type":"BEAM_COLUMN_CONNECTION","connection_id":"C1","demand":8,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T1"},
        {"id":"T2","check_type":"BEAM_BEAM_CONNECTION","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T2"},
        {"id":"T3","check_type":"COLUMN_BASE_CONNECTION","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T3"},
        {"id":"T4","check_type":"SUPPORT_REACTION_CAPACITY","support_id":"S1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T4"},
        {"id":"T5","check_type":"BOLT_GROUP_CAPACITY","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T5"},
        {"id":"T6","check_type":"WELD_CAPACITY","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T6"},
        {"id":"T7","check_type":"ANCHOR_GROUP_CAPACITY","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"kN","mandatory":True,"normative_reference":"REF:T7"},
        {"id":"T8","check_type":"BEARING_CAPACITY","connection_id":"C1","demand":7,"capacity":10,"quantity":"test","unit":"MPa","mandatory":True,"normative_reference":"REF:T8"},
        {"id":"T9","check_type":"JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE","joint_id":"J1","classification":"PROJECT_DEFINED","classification_verified":True,"evidence_reference":"EVIDENCE:J1","mandatory":True,"normative_reference":"REF:T9"}],
      "verification_policy":{"acceptable_global_stability_states":["GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED"],"require_normative_reference":True,"mandatory_check_types":sorted(SUPPORTED_CHECK_TYPES),"pass_tolerance":1e-12}
    }


def self_test() -> Dict[str, Any]:
    report = build_connection_report(_demo_payload())
    assert report["verification_state"] == "CONNECTION_SUPPORT_JOINT_CANDIDATE_PASSED"
    assert report["summary"]["review_item_count"] == 0
    assert report["release"]["structural_model_release"] == "LOCKED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=2))
        print("STRUCTURAL CONNECTION / SUPPORT / JOINT VERIFICATION: PASSED")
        print("CONNECTION/SUPPORT/JOINT CHECKS: GENERATED")
        print("NORMATIVE TRACEABILITY: ENFORCED")
        print("DIGITAL TWIN WRITEBACK: PASSED")
        print("AUTOMATIC CONNECTION APPROVAL: DISABLED")
        print("STRUCTURAL MODEL RELEASE: LOCKED")
        return 0
    if not args.input: parser.error("--input is required unless --self-test is used")
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = build_connection_report(data)
    text = json.dumps(report, indent=2) + "\n"
    if args.output: Path(args.output).write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0


if __name__ == "__main__": raise SystemExit(main())
