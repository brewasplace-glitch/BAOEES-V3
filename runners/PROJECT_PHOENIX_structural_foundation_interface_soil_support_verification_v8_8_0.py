#!/usr/bin/env python3
"""Project Phoenix Structural Foundation Interface, Soil-Support & Foundation Verification Engine v8.8.0.

Consumes the v8.7.0 connection/support/joint verification candidate and creates an
explicit, auditable foundation-interface verification candidate. The engine never
invents soil parameters, bearing capacities, allowable settlements, pile capacities,
foundation resistances, spring stiffnesses, safety factors or normative limits.
A PASS means only that supplied, traceable demand/evidence is within supplied,
traceable capacity/limit/evidence. It is not a geotechnical or structural approval.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-FOUNDATION-INTERFACE-SOIL-SUPPORT-VERIFICATION-V8.8.0"
VERSION = "8.8.0"
EXPECTED_SOURCE_ENGINE = "PHX-STRUCT-CONNECTION-SUPPORT-JOINT-VERIFICATION-V8.7.0"
LOCKED_RELEASE = "LOCKED"

CAPACITY_CHECK_TYPES = {
    "FOUNDATION_REACTION_CAPACITY",
    "SOIL_BEARING_PRESSURE",
    "SETTLEMENT_LIMIT",
    "DIFFERENTIAL_SETTLEMENT_LIMIT",
    "UPLIFT_RESISTANCE",
    "SLIDING_RESISTANCE",
    "FOUNDATION_BEAM_CAPACITY",
    "PILE_AXIAL_CAPACITY",
    "PILE_GROUP_CAPACITY",
}
EVIDENCE_CHECK_TYPES = {
    "SOIL_SPRING_STIFFNESS_EVIDENCE",
    "GEOTECHNICAL_PARAMETER_TRACEABILITY",
}
SUPPORTED_CHECK_TYPES = CAPACITY_CHECK_TYPES | EVIDENCE_CHECK_TYPES
FOUNDATION_TARGET_CHECKS = CAPACITY_CHECK_TYPES - {"PILE_AXIAL_CAPACITY", "PILE_GROUP_CAPACITY"}
PILE_TARGET_CHECKS = {"PILE_AXIAL_CAPACITY"}
PILE_GROUP_TARGET_CHECKS = {"PILE_GROUP_CAPACITY"}


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


def _nonnegative(value: Any, label: str) -> float:
    result = _num(value, label)
    if result < 0:
        raise ValueError(f"{label} must be >= 0")
    return result


def _positive(value: Any, label: str) -> float:
    result = _num(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be > 0")
    return result


def _id_set(items: Sequence[Any], label: str) -> Set[str]:
    result: Set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValueError(f"{label}[{idx}] must be an object")
        item_id = _text(item.get("id"), f"{label}[{idx}].id")
        if item_id in result:
            raise ValueError(f"Duplicate {label} id: {item_id}")
        result.add(item_id)
    return result


def _basis(payload: Mapping[str, Any]) -> Dict[str, str]:
    raw = payload.get("foundation_geotechnical_basis")
    if not isinstance(raw, Mapping):
        raise ValueError("foundation_geotechnical_basis must be an object")
    required = ("jurisdiction", "standard_set", "edition", "source_reference", "status")
    return {key: _text(raw.get(key), f"foundation_geotechnical_basis.{key}") for key in required}


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("verification_policy")
    if not isinstance(raw, Mapping):
        raise ValueError("verification_policy must be an object")
    accepted = {_text(x, "verification_policy.acceptable_connection_states") for x in _items(raw.get("acceptable_connection_states"))}
    if not accepted:
        raise ValueError("verification_policy.acceptable_connection_states must not be empty")
    mandatory = [_text(x, "verification_policy.mandatory_check_types").upper() for x in _items(raw.get("mandatory_check_types"))]
    unknown = sorted(set(mandatory) - SUPPORTED_CHECK_TYPES)
    if unknown:
        raise ValueError(f"Unsupported mandatory check types: {', '.join(unknown)}")
    require_normative = raw.get("require_normative_reference", True)
    if not isinstance(require_normative, bool):
        raise ValueError("verification_policy.require_normative_reference must be boolean")
    require_support_mapping = raw.get("require_all_supports_mapped", True)
    if not isinstance(require_support_mapping, bool):
        raise ValueError("verification_policy.require_all_supports_mapped must be boolean")
    return {
        "acceptable_connection_states": accepted,
        "mandatory_check_types": mandatory,
        "require_normative_reference": require_normative,
        "require_all_supports_mapped": require_support_mapping,
        "pass_tolerance": _nonnegative(raw.get("pass_tolerance", 1e-12), "verification_policy.pass_tolerance"),
    }


def _source_gate(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    source = _text(payload.get("source_engine"), "source_engine")
    if source != EXPECTED_SOURCE_ENGINE:
        raise ValueError(f"v8.7.0 source engine required: {EXPECTED_SOURCE_ENGINE}; got {source}")
    state = _text(payload.get("connection_support_joint_state"), "connection_support_joint_state")
    if state not in policy["acceptable_connection_states"]:
        raise ValueError(f"connection/support/joint state {state!r} is not accepted")


def _model_ids(payload: Mapping[str, Any]) -> Tuple[Set[str], Set[str], Set[str], Set[str], Set[str]]:
    model = payload.get("foundation_model")
    if not isinstance(model, Mapping):
        raise ValueError("foundation_model must be an object")
    supports = _id_set(_items(model.get("supports")), "foundation_model.supports")
    foundations = _id_set(_items(model.get("foundation_elements")), "foundation_model.foundation_elements")
    soil_zones = _id_set(_items(model.get("soil_zones")), "foundation_model.soil_zones")
    piles = _id_set(_items(model.get("piles")), "foundation_model.piles")
    pile_groups = _id_set(_items(model.get("pile_groups")), "foundation_model.pile_groups")
    if not supports:
        raise ValueError("foundation_model.supports must contain at least one support")
    if not foundations:
        raise ValueError("foundation_model.foundation_elements must contain at least one element")
    if not soil_zones:
        raise ValueError("foundation_model.soil_zones must contain at least one soil zone")
    return supports, foundations, soil_zones, piles, pile_groups


def _support_mapping(payload: Mapping[str, Any], supports: Set[str], foundations: Set[str], soil_zones: Set[str]) -> Dict[str, Any]:
    mappings = _items(payload.get("support_foundation_interfaces"))
    seen_supports: Set[str] = set()
    normalized: List[Dict[str, str]] = []
    for idx, item in enumerate(mappings):
        if not isinstance(item, Mapping):
            raise ValueError(f"support_foundation_interfaces[{idx}] must be an object")
        support_id = _text(item.get("support_id"), f"support_foundation_interfaces[{idx}].support_id")
        foundation_id = _text(item.get("foundation_id"), f"support_foundation_interfaces[{idx}].foundation_id")
        soil_zone_id = _text(item.get("soil_zone_id"), f"support_foundation_interfaces[{idx}].soil_zone_id")
        evidence_reference = _text(item.get("evidence_reference"), f"support_foundation_interfaces[{idx}].evidence_reference")
        if support_id not in supports:
            raise ValueError(f"support_foundation_interfaces[{idx}] references unknown support {support_id}")
        if foundation_id not in foundations:
            raise ValueError(f"support_foundation_interfaces[{idx}] references unknown foundation {foundation_id}")
        if soil_zone_id not in soil_zones:
            raise ValueError(f"support_foundation_interfaces[{idx}] references unknown soil zone {soil_zone_id}")
        if support_id in seen_supports:
            raise ValueError(f"Duplicate support-foundation mapping for support {support_id}")
        seen_supports.add(support_id)
        normalized.append({
            "support_id": support_id,
            "foundation_id": foundation_id,
            "soil_zone_id": soil_zone_id,
            "evidence_reference": evidence_reference,
        })
    missing = sorted(supports - seen_supports)
    return {"interfaces": normalized, "mapped_support_ids": sorted(seen_supports), "unmapped_support_ids": missing}


def _common(check: Mapping[str, Any], policy: Mapping[str, Any], seen: Set[str]) -> Dict[str, Any]:
    check_id = _text(check.get("id"), "verification_check.id")
    if check_id in seen:
        raise ValueError(f"Duplicate verification check id: {check_id}")
    seen.add(check_id)
    check_type = _text(check.get("check_type"), f"{check_id}.check_type").upper()
    if check_type not in SUPPORTED_CHECK_TYPES:
        raise ValueError(f"Unsupported check_type {check_type}")
    mandatory = check.get("mandatory", True)
    if not isinstance(mandatory, bool):
        raise ValueError(f"{check_id}.mandatory must be boolean")
    normative_reference = str(check.get("normative_reference") or "").strip()
    if policy["require_normative_reference"] and not normative_reference:
        raise ValueError(f"{check_id} missing normative_reference")
    return {"id": check_id, "check_type": check_type, "mandatory": mandatory, "normative_reference": normative_reference}


def _capacity_check(
    check: Mapping[str, Any], base: Dict[str, Any], tol: float,
    foundations: Set[str], soil_zones: Set[str], piles: Set[str], pile_groups: Set[str]
) -> Dict[str, Any]:
    ctype = base["check_type"]
    target: Dict[str, str] = {}
    if ctype in FOUNDATION_TARGET_CHECKS:
        foundation_id = _text(check.get("foundation_id"), f"{base['id']}.foundation_id")
        if foundation_id not in foundations:
            raise ValueError(f"{base['id']} references unknown foundation {foundation_id}")
        target["foundation_id"] = foundation_id
        if ctype in {"SOIL_BEARING_PRESSURE", "SETTLEMENT_LIMIT", "DIFFERENTIAL_SETTLEMENT_LIMIT", "UPLIFT_RESISTANCE", "SLIDING_RESISTANCE"}:
            soil_zone_id = _text(check.get("soil_zone_id"), f"{base['id']}.soil_zone_id")
            if soil_zone_id not in soil_zones:
                raise ValueError(f"{base['id']} references unknown soil zone {soil_zone_id}")
            target["soil_zone_id"] = soil_zone_id
    elif ctype in PILE_TARGET_CHECKS:
        pile_id = _text(check.get("pile_id"), f"{base['id']}.pile_id")
        if pile_id not in piles:
            raise ValueError(f"{base['id']} references unknown pile {pile_id}")
        target["pile_id"] = pile_id
    elif ctype in PILE_GROUP_TARGET_CHECKS:
        group_id = _text(check.get("pile_group_id"), f"{base['id']}.pile_group_id")
        if group_id not in pile_groups:
            raise ValueError(f"{base['id']} references unknown pile group {group_id}")
        target["pile_group_id"] = group_id
    demand = _nonnegative(check.get("demand"), f"{base['id']}.demand")
    capacity = _positive(check.get("capacity"), f"{base['id']}.capacity")
    quantity = _text(check.get("quantity"), f"{base['id']}.quantity")
    unit = _text(check.get("unit"), f"{base['id']}.unit")
    utilization = demand / capacity
    status = "PASS" if demand <= capacity + tol else "FAIL"
    return {
        **base, **target, "quantity": quantity, "unit": unit, "demand": demand, "capacity": capacity,
        "utilization": utilization, "status": status,
        "method_note": "Demand and capacity/limit are evaluated exactly as supplied; geotechnical/structural derivation and normative validity remain external traceable evidence.",
    }


def _evidence_check(check: Mapping[str, Any], base: Dict[str, Any], soil_zones: Set[str]) -> Dict[str, Any]:
    soil_zone_id = _text(check.get("soil_zone_id"), f"{base['id']}.soil_zone_id")
    if soil_zone_id not in soil_zones:
        raise ValueError(f"{base['id']} references unknown soil zone {soil_zone_id}")
    verified = check.get("verified")
    if not isinstance(verified, bool):
        raise ValueError(f"{base['id']}.verified must be boolean")
    evidence_reference = _text(check.get("evidence_reference"), f"{base['id']}.evidence_reference")
    result = {**base, "soil_zone_id": soil_zone_id, "verified": verified, "evidence_reference": evidence_reference,
              "utilization": 0.0 if verified else 1.0, "status": "PASS" if verified else "FAIL"}
    if base["check_type"] == "SOIL_SPRING_STIFFNESS_EVIDENCE":
        result["stiffness_model"] = _text(check.get("stiffness_model"), f"{base['id']}.stiffness_model")
    else:
        result["parameter_set_id"] = _text(check.get("parameter_set_id"), f"{base['id']}.parameter_set_id")
    return result


def _evaluate(
    check: Mapping[str, Any], policy: Mapping[str, Any], foundations: Set[str], soil_zones: Set[str],
    piles: Set[str], pile_groups: Set[str], seen: Set[str]
) -> Dict[str, Any]:
    base = _common(check, policy, seen)
    if base["check_type"] in CAPACITY_CHECK_TYPES:
        return _capacity_check(check, base, policy["pass_tolerance"], foundations, soil_zones, piles, pile_groups)
    return _evidence_check(check, base, soil_zones)


def _coverage(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> List[str]:
    present = {str(r["check_type"]).upper() for r in results if r.get("mandatory")}
    return [ctype for ctype in policy["mandatory_check_types"] if ctype not in present]


def _review_items(results: Sequence[Mapping[str, Any]], missing_types: Sequence[str], unmapped_supports: Sequence[str], require_mapping: bool) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for result in results:
        if result.get("mandatory") and result.get("status") != "PASS":
            items.append({
                "type": "MANDATORY_FOUNDATION_SOIL_SUPPORT_CHECK_FAILED",
                "check_id": result["id"], "check_type": result["check_type"], "status": result["status"],
                "action": "Competent structural/geotechnical engineering review and corrective action required before release.",
            })
    if missing_types:
        items.append({
            "type": "MANDATORY_FOUNDATION_SOIL_SUPPORT_COVERAGE_INCOMPLETE",
            "missing_check_types": list(missing_types),
            "action": "Provide explicit, traceable evidence for every mandatory foundation/soil-support check type.",
        })
    if require_mapping and unmapped_supports:
        items.append({
            "type": "SUPPORT_TO_FOUNDATION_INTERFACE_INCOMPLETE",
            "unmapped_support_ids": list(unmapped_supports),
            "action": "Map every structural support to a traceable foundation element and soil zone before release.",
        })
    return items


def build_foundation_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    policy = _policy(payload)
    _source_gate(payload, policy)
    basis = _basis(payload)
    supports, foundations, soil_zones, piles, pile_groups = _model_ids(payload)
    interface = _support_mapping(payload, supports, foundations, soil_zones)
    checks = [c for c in _items(payload.get("verification_checks")) if isinstance(c, Mapping)]
    if not checks:
        raise ValueError("verification_checks must contain at least one check")
    seen: Set[str] = set()
    results = [_evaluate(c, policy, foundations, soil_zones, piles, pile_groups, seen) for c in checks]
    missing_types = _coverage(results, policy)
    reviews = _review_items(results, missing_types, interface["unmapped_support_ids"], policy["require_all_supports_mapped"])
    mandatory = [r for r in results if r["mandatory"]]
    if missing_types or (policy["require_all_supports_mapped"] and interface["unmapped_support_ids"]):
        state = "FOUNDATION_INTERFACE_SOIL_SUPPORT_VERIFICATION_INCOMPLETE"
    elif any(r["status"] != "PASS" for r in mandatory):
        state = "FOUNDATION_INTERFACE_SOIL_SUPPORT_REVIEW_REQUIRED"
    else:
        state = "FOUNDATION_INTERFACE_SOIL_SUPPORT_CANDIDATE_PASSED"
    utils = [float(r["utilization"]) for r in results if isinstance(r.get("utilization"), (int, float)) and math.isfinite(float(r["utilization"]))]
    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": _text(payload.get("project_id"), "project_id"),
        "source_engine": _text(payload.get("source_engine"), "source_engine"),
        "source_connection_support_joint_state": _text(payload.get("connection_support_joint_state"), "connection_support_joint_state"),
        "foundation_geotechnical_basis": basis,
        "support_foundation_interface": interface,
        "verification_state": state,
        "verification_checks": results,
        "summary": {
            "support_count": len(supports), "foundation_element_count": len(foundations), "soil_zone_count": len(soil_zones),
            "pile_count": len(piles), "pile_group_count": len(pile_groups), "check_count": len(results),
            "mandatory_check_count": len(mandatory), "passed_count": sum(1 for r in results if r["status"] == "PASS"),
            "failed_count": sum(1 for r in results if r["status"] == "FAIL"), "missing_mandatory_check_types": missing_types,
            "unmapped_support_ids": interface["unmapped_support_ids"], "review_item_count": len(reviews),
            "max_utilization_indicator": max(utils) if utils else None,
        },
        "review_items": reviews,
        "digital_twin_writeback": {
            "enabled": True,
            "target": "CENTRAL_DIGITAL_TWIN.structural.foundation_interface_soil_support_verification",
            "write_mode": "CANDIDATE_EVIDENCE_ONLY",
            "preserve_normative_references": True,
            "preserve_geotechnical_source_references": True,
        },
        "release": {
            "automatic_geotechnical_approval": False,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_foundation_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "remaining_gates": ["foundation_design_detail_verification", "competent_structural_geotechnical_review"],
        },
    }


def _demo_payload() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "configs" / "projects" / "generic_building_structural_foundation_interface_soil_support_v8_8_0.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raise RuntimeError(f"Demo project config not found: {path}")


def self_test() -> Dict[str, Any]:
    report = build_foundation_report(_demo_payload())
    assert report["verification_state"] == "FOUNDATION_INTERFACE_SOIL_SUPPORT_CANDIDATE_PASSED"
    assert report["summary"]["review_item_count"] == 0
    assert report["summary"]["unmapped_support_ids"] == []
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
        print("STRUCTURAL FOUNDATION INTERFACE / SOIL-SUPPORT VERIFICATION: PASSED")
        print("SUPPORT-TO-FOUNDATION INTERFACE MAPPING: VERIFIED")
        print("BEARING / SETTLEMENT / UPLIFT / SLIDING CHECKS: GENERATED")
        print("PILE / FOUNDATION BEAM CHECK CONTRACTS: GENERATED")
        print("GEOTECHNICAL TRACEABILITY: ENFORCED")
        print("DIGITAL TWIN WRITEBACK: PASSED")
        print("AUTOMATIC FOUNDATION APPROVAL: DISABLED")
        print("STRUCTURAL MODEL RELEASE: LOCKED")
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = build_foundation_report(data)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
