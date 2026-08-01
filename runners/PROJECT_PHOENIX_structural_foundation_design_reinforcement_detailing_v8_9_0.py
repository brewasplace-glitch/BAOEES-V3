#!/usr/bin/env python3
"""Project Phoenix Structural Foundation Design, Reinforcement & Detailing Engine v8.9.0.

Consumes the v8.8.0 foundation-interface / soil-support verification candidate and
creates an auditable reinforced-foundation design/detailing candidate.

The engine deliberately does NOT invent code values, material strengths, cover,
minimum/maximum reinforcement, anchorage lengths, shear/punching resistances,
pile-cap strut-and-tie resistances, safety factors, or detailing limits. Such data
must be explicit and traceable to project design input, a verified standards engine,
or competent engineering input.

A PASS from this engine is a candidate-verification state only. It is not a code
compliance claim, structural approval, geotechnical approval, foundation approval,
or construction release.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-FOUNDATION-DESIGN-REINFORCEMENT-DETAILING-V8.9.0"
VERSION = "8.9.0"
EXPECTED_SOURCE_ENGINE = "PHX-STRUCT-FOUNDATION-INTERFACE-SOIL-SUPPORT-VERIFICATION-V8.8.0"
LOCKED_RELEASE = "LOCKED"

SUPPORTED_FOUNDATION_TYPES = {
    "PAD_FOUNDATION",
    "STRIP_FOUNDATION",
    "FOUNDATION_BEAM",
    "PILE_CAP",
}

CAPACITY_CHECK_TYPES = {
    "PAD_FLEXURAL_CAPACITY",
    "PAD_ONE_WAY_SHEAR_CAPACITY",
    "PAD_PUNCHING_SHEAR_CAPACITY",
    "STRIP_FLEXURAL_CAPACITY",
    "STRIP_ONE_WAY_SHEAR_CAPACITY",
    "FOUNDATION_BEAM_FLEXURAL_CAPACITY",
    "FOUNDATION_BEAM_SHEAR_CAPACITY",
    "PILE_CAP_STRUT_TIE_CAPACITY",
}

EVIDENCE_CHECK_TYPES = {
    "MINIMUM_REINFORCEMENT_EVIDENCE",
    "MAXIMUM_REINFORCEMENT_EVIDENCE",
    "CONCRETE_COVER_EVIDENCE",
    "BAR_SPACING_EVIDENCE",
    "ANCHORAGE_DEVELOPMENT_EVIDENCE",
    "DOWEL_STARTER_BAR_EVIDENCE",
    "MATERIAL_TRACEABILITY",
    "DRAWING_DETAIL_COMPLETENESS",
}
SUPPORTED_CHECK_TYPES = CAPACITY_CHECK_TYPES | EVIDENCE_CHECK_TYPES

TYPE_REQUIRED_DIMENSIONS = {
    "PAD_FOUNDATION": ("length_m", "width_m", "thickness_m"),
    "STRIP_FOUNDATION": ("length_m", "width_m", "thickness_m"),
    "FOUNDATION_BEAM": ("length_m", "width_m", "height_m"),
    "PILE_CAP": ("length_m", "width_m", "thickness_m"),
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
        raise ValueError(f"{label} must be numeric") from exc
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


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _integer_positive(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("verification_policy")
    if not isinstance(raw, Mapping):
        raise ValueError("verification_policy must be an object")
    accepted = [_text(x, "acceptable_foundation_interface_states item") for x in _items(raw.get("acceptable_foundation_interface_states"))]
    if not accepted:
        raise ValueError("acceptable_foundation_interface_states must not be empty")
    mandatory = [str(x).strip().upper() for x in _items(raw.get("mandatory_check_types")) if str(x).strip()]
    if not mandatory:
        raise ValueError("mandatory_check_types must not be empty")
    unknown = sorted(set(mandatory) - SUPPORTED_CHECK_TYPES)
    if unknown:
        raise ValueError(f"unsupported mandatory_check_types: {', '.join(unknown)}")
    return {
        "acceptable_foundation_interface_states": accepted,
        "mandatory_check_types": mandatory,
        "require_normative_reference": bool(raw.get("require_normative_reference", True)),
        "require_reinforcement_for_all_foundations": bool(raw.get("require_reinforcement_for_all_foundations", True)),
        "require_detail_for_all_foundations": bool(raw.get("require_detail_for_all_foundations", True)),
        "pass_tolerance": _nonnegative(raw.get("pass_tolerance", 1e-12), "verification_policy.pass_tolerance"),
    }


def _source_gate(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    source = _text(payload.get("source_engine"), "source_engine")
    if source != EXPECTED_SOURCE_ENGINE:
        raise ValueError(f"v8.8.0 source engine required; received {source}")
    state = _text(payload.get("foundation_interface_soil_support_state"), "foundation_interface_soil_support_state")
    if state not in policy["acceptable_foundation_interface_states"]:
        raise ValueError(f"v8.8.0 foundation interface / soil-support state not accepted: {state}")


def _basis(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("foundation_design_basis")
    if not isinstance(raw, Mapping):
        raise ValueError("foundation_design_basis must be an object")
    return {
        "jurisdiction": _text(raw.get("jurisdiction"), "foundation_design_basis.jurisdiction"),
        "standard_set": _text(raw.get("standard_set"), "foundation_design_basis.standard_set"),
        "edition": _text(raw.get("edition"), "foundation_design_basis.edition"),
        "source_reference": _text(raw.get("source_reference"), "foundation_design_basis.source_reference"),
        "status": _text(raw.get("status"), "foundation_design_basis.status"),
    }


def _materials(payload: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    raw = payload.get("materials")
    if not isinstance(raw, Mapping):
        raise ValueError("materials must be an object")
    concrete: Dict[str, Dict[str, Any]] = {}
    reinforcement: Dict[str, Dict[str, Any]] = {}
    for item in _items(raw.get("concrete")):
        if not isinstance(item, Mapping):
            raise ValueError("materials.concrete entries must be objects")
        mid = _text(item.get("id"), "concrete material id")
        if mid in concrete:
            raise ValueError(f"duplicate concrete material id: {mid}")
        concrete[mid] = {
            "id": mid,
            "design_strength": _positive(item.get("design_strength"), f"{mid}.design_strength"),
            "strength_unit": _text(item.get("strength_unit"), f"{mid}.strength_unit"),
            "source_reference": _text(item.get("source_reference"), f"{mid}.source_reference"),
        }
    for item in _items(raw.get("reinforcement")):
        if not isinstance(item, Mapping):
            raise ValueError("materials.reinforcement entries must be objects")
        mid = _text(item.get("id"), "reinforcement material id")
        if mid in reinforcement:
            raise ValueError(f"duplicate reinforcement material id: {mid}")
        reinforcement[mid] = {
            "id": mid,
            "design_strength": _positive(item.get("design_strength"), f"{mid}.design_strength"),
            "strength_unit": _text(item.get("strength_unit"), f"{mid}.strength_unit"),
            "density_kg_m3": _positive(item.get("density_kg_m3"), f"{mid}.density_kg_m3"),
            "source_reference": _text(item.get("source_reference"), f"{mid}.source_reference"),
        }
    if not concrete:
        raise ValueError("at least one concrete material is required")
    if not reinforcement:
        raise ValueError("at least one reinforcement material is required")
    return concrete, reinforcement


def _foundation_elements(payload: Mapping[str, Any], concrete: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    elements: Dict[str, Dict[str, Any]] = {}
    for raw in _items(payload.get("foundation_elements")):
        if not isinstance(raw, Mapping):
            raise ValueError("foundation_elements entries must be objects")
        eid = _text(raw.get("id"), "foundation element id")
        if eid in elements:
            raise ValueError(f"duplicate foundation element id: {eid}")
        etype = _text(raw.get("type"), f"{eid}.type").upper()
        if etype not in SUPPORTED_FOUNDATION_TYPES:
            raise ValueError(f"unsupported foundation type for {eid}: {etype}")
        material_id = _text(raw.get("concrete_material_id"), f"{eid}.concrete_material_id")
        if material_id not in concrete:
            raise ValueError(f"{eid} references unknown concrete material: {material_id}")
        dimensions = raw.get("dimensions")
        if not isinstance(dimensions, Mapping):
            raise ValueError(f"{eid}.dimensions must be an object")
        clean_dims: Dict[str, float] = {}
        for key in TYPE_REQUIRED_DIMENSIONS[etype]:
            clean_dims[key] = _positive(dimensions.get(key), f"{eid}.dimensions.{key}")
        if etype == "FOUNDATION_BEAM":
            volume = clean_dims["length_m"] * clean_dims["width_m"] * clean_dims["height_m"]
        else:
            volume = clean_dims["length_m"] * clean_dims["width_m"] * clean_dims["thickness_m"]
        elements[eid] = {
            "id": eid,
            "type": etype,
            "concrete_material_id": material_id,
            "dimensions": clean_dims,
            "concrete_volume_m3": volume,
            "source_reference": _text(raw.get("source_reference"), f"{eid}.source_reference"),
        }
    if not elements:
        raise ValueError("foundation_elements must contain at least one element")
    return elements


def _reinforcement_groups(payload: Mapping[str, Any], elements: Mapping[str, Any], reinforcement_materials: Mapping[str, Any]) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in _items(payload.get("reinforcement_groups")):
        if not isinstance(raw, Mapping):
            raise ValueError("reinforcement_groups entries must be objects")
        gid = _text(raw.get("id"), "reinforcement group id")
        if gid in seen:
            raise ValueError(f"duplicate reinforcement group id: {gid}")
        seen.add(gid)
        element_id = _text(raw.get("foundation_element_id"), f"{gid}.foundation_element_id")
        if element_id not in elements:
            raise ValueError(f"{gid} references unknown foundation element: {element_id}")
        material_id = _text(raw.get("material_id"), f"{gid}.material_id")
        if material_id not in reinforcement_materials:
            raise ValueError(f"{gid} references unknown reinforcement material: {material_id}")
        count = _integer_positive(raw.get("count"), f"{gid}.count")
        diameter_mm = _positive(raw.get("diameter_mm"), f"{gid}.diameter_mm")
        bar_length_m = _positive(raw.get("bar_length_m"), f"{gid}.bar_length_m")
        cover_mm = _positive(raw.get("cover_mm"), f"{gid}.cover_mm")
        spacing_mm = _positive(raw.get("spacing_mm"), f"{gid}.spacing_mm")
        one_bar_area_mm2 = math.pi * diameter_mm ** 2 / 4.0
        provided_area_mm2 = count * one_bar_area_mm2
        one_bar_area_m2 = one_bar_area_mm2 * 1e-6
        total_length_m = count * bar_length_m
        mass_kg = one_bar_area_m2 * total_length_m * reinforcement_materials[material_id]["density_kg_m3"]
        groups.append({
            "id": gid,
            "bar_mark": _text(raw.get("bar_mark"), f"{gid}.bar_mark"),
            "foundation_element_id": element_id,
            "role": _text(raw.get("role"), f"{gid}.role"),
            "material_id": material_id,
            "count": count,
            "diameter_mm": diameter_mm,
            "bar_length_m": bar_length_m,
            "cover_mm": cover_mm,
            "spacing_mm": spacing_mm,
            "shape_code": _text(raw.get("shape_code"), f"{gid}.shape_code"),
            "source_reference": _text(raw.get("source_reference"), f"{gid}.source_reference"),
            "one_bar_area_mm2": one_bar_area_mm2,
            "provided_area_mm2": provided_area_mm2,
            "total_length_m": total_length_m,
            "estimated_mass_kg": mass_kg,
        })
    if not groups:
        raise ValueError("reinforcement_groups must contain at least one group")
    return groups


def _drawing_details(payload: Mapping[str, Any], elements: Mapping[str, Any]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in _items(payload.get("drawing_details")):
        if not isinstance(raw, Mapping):
            raise ValueError("drawing_details entries must be objects")
        did = _text(raw.get("id"), "drawing detail id")
        if did in seen:
            raise ValueError(f"duplicate drawing detail id: {did}")
        seen.add(did)
        element_id = _text(raw.get("foundation_element_id"), f"{did}.foundation_element_id")
        if element_id not in elements:
            raise ValueError(f"{did} references unknown foundation element: {element_id}")
        details.append({
            "id": did,
            "foundation_element_id": element_id,
            "view_type": _text(raw.get("view_type"), f"{did}.view_type"),
            "scale": _text(raw.get("scale"), f"{did}.scale"),
            "status": _text(raw.get("status"), f"{did}.status"),
            "source_reference": _text(raw.get("source_reference"), f"{did}.source_reference"),
        })
    if not details:
        raise ValueError("drawing_details must contain at least one detail")
    return details


def _common_check(check: Mapping[str, Any], policy: Mapping[str, Any], elements: Mapping[str, Any], seen: Set[str]) -> Dict[str, Any]:
    cid = _text(check.get("id"), "verification check id")
    if cid in seen:
        raise ValueError(f"duplicate verification check id: {cid}")
    seen.add(cid)
    ctype = _text(check.get("check_type"), f"{cid}.check_type").upper()
    if ctype not in SUPPORTED_CHECK_TYPES:
        raise ValueError(f"unsupported verification check type: {ctype}")
    element_id = _text(check.get("foundation_element_id"), f"{cid}.foundation_element_id")
    if element_id not in elements:
        raise ValueError(f"{cid} references unknown foundation element: {element_id}")
    normative = str(check.get("normative_reference") or "").strip()
    if policy["require_normative_reference"] and not normative:
        raise ValueError(f"{cid} missing normative_reference")
    return {
        "id": cid,
        "check_type": ctype,
        "foundation_element_id": element_id,
        "mandatory": bool(check.get("mandatory", True)),
        "normative_reference": normative,
    }


def _capacity_check(check: Mapping[str, Any], base: Mapping[str, Any], tolerance: float) -> Dict[str, Any]:
    demand = _nonnegative(check.get("demand"), f"{base['id']}.demand")
    capacity = _positive(check.get("capacity"), f"{base['id']}.capacity")
    utilization = demand / capacity
    status = "PASS" if utilization <= 1.0 + tolerance else "FAIL"
    return {
        **base,
        "quantity": _text(check.get("quantity"), f"{base['id']}.quantity"),
        "unit": _text(check.get("unit"), f"{base['id']}.unit"),
        "demand": demand,
        "capacity": capacity,
        "utilization": utilization,
        "status": status,
    }


def _evidence_check(check: Mapping[str, Any], base: Mapping[str, Any]) -> Dict[str, Any]:
    verified = _boolean(check.get("verified"), f"{base['id']}.verified")
    evidence_reference = _text(check.get("evidence_reference"), f"{base['id']}.evidence_reference")
    return {
        **base,
        "verified": verified,
        "evidence_reference": evidence_reference,
        "status": "PASS" if verified else "FAIL",
    }


def _verification_results(payload: Mapping[str, Any], policy: Mapping[str, Any], elements: Mapping[str, Any]) -> List[Dict[str, Any]]:
    checks = [x for x in _items(payload.get("verification_checks")) if isinstance(x, Mapping)]
    if not checks:
        raise ValueError("verification_checks must contain at least one check")
    seen: Set[str] = set()
    results: List[Dict[str, Any]] = []
    for check in checks:
        base = _common_check(check, policy, elements, seen)
        if base["check_type"] in CAPACITY_CHECK_TYPES:
            results.append(_capacity_check(check, base, policy["pass_tolerance"]))
        else:
            results.append(_evidence_check(check, base))
    return results


def _coverage(results: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> List[str]:
    present = {str(r["check_type"]).upper() for r in results if r.get("mandatory")}
    return [ctype for ctype in policy["mandatory_check_types"] if ctype not in present]


def _missing_reinforcement(elements: Mapping[str, Any], groups: Sequence[Mapping[str, Any]]) -> List[str]:
    represented = {str(g["foundation_element_id"]) for g in groups}
    return sorted([eid for eid in elements if eid not in represented])


def _missing_details(elements: Mapping[str, Any], details: Sequence[Mapping[str, Any]]) -> List[str]:
    represented = {str(d["foundation_element_id"]) for d in details if str(d.get("status", "")).upper() == "DEFINED"}
    return sorted([eid for eid in elements if eid not in represented])


def _element_envelopes(results: Sequence[Mapping[str, Any]], elements: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for eid in elements:
        checks = [r for r in results if r["foundation_element_id"] == eid]
        ratios = [float(r["utilization"]) for r in checks if "utilization" in r]
        out.append({
            "foundation_element_id": eid,
            "maximum_utilization": max(ratios) if ratios else None,
            "check_count": len(checks),
            "failed_check_count": sum(1 for r in checks if r["status"] != "PASS"),
        })
    return out


def _reinforcement_schedule(groups: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for g in groups:
        rows.append({
            "bar_mark": g["bar_mark"],
            "foundation_element_id": g["foundation_element_id"],
            "role": g["role"],
            "material_id": g["material_id"],
            "diameter_mm": g["diameter_mm"],
            "count": g["count"],
            "bar_length_m": g["bar_length_m"],
            "total_length_m": g["total_length_m"],
            "estimated_mass_kg": g["estimated_mass_kg"],
            "shape_code": g["shape_code"],
        })
    return {
        "rows": rows,
        "total_bar_count": sum(int(g["count"]) for g in groups),
        "total_length_m": sum(float(g["total_length_m"]) for g in groups),
        "estimated_reinforcement_mass_kg": sum(float(g["estimated_mass_kg"]) for g in groups),
    }


def _quantity_takeoff(elements: Mapping[str, Any], groups: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    element_rows = []
    for eid, e in elements.items():
        mass = sum(float(g["estimated_mass_kg"]) for g in groups if g["foundation_element_id"] == eid)
        element_rows.append({
            "foundation_element_id": eid,
            "foundation_type": e["type"],
            "concrete_volume_m3": e["concrete_volume_m3"],
            "estimated_reinforcement_mass_kg": mass,
        })
    return {
        "elements": element_rows,
        "total_concrete_volume_m3": sum(float(e["concrete_volume_m3"]) for e in elements.values()),
        "estimated_total_reinforcement_mass_kg": sum(float(g["estimated_mass_kg"]) for g in groups),
        "quantity_status": "GEOMETRY_DERIVED_FROM_EXPLICIT_INPUT",
    }


def _review_items(
    results: Sequence[Mapping[str, Any]],
    missing_types: Sequence[str],
    missing_reinf: Sequence[str],
    missing_details: Sequence[str],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for r in results:
        if r.get("mandatory") and r.get("status") != "PASS":
            items.append({
                "type": "MANDATORY_FOUNDATION_DESIGN_DETAIL_CHECK_FAILED",
                "check_id": r["id"],
                "check_type": r["check_type"],
                "foundation_element_id": r["foundation_element_id"],
                "status": r["status"],
                "action": "Competent structural engineering review and corrective action required before release.",
            })
    if missing_types:
        items.append({
            "type": "MANDATORY_FOUNDATION_DESIGN_DETAIL_COVERAGE_INCOMPLETE",
            "missing_check_types": list(missing_types),
            "action": "Provide explicit, traceable evidence for every mandatory foundation design/detail check type.",
        })
    if missing_reinf:
        items.append({
            "type": "FOUNDATION_REINFORCEMENT_DEFINITION_INCOMPLETE",
            "foundation_element_ids": list(missing_reinf),
            "action": "Define traceable reinforcement groups for every required foundation element.",
        })
    if missing_details:
        items.append({
            "type": "FOUNDATION_DRAWING_DETAIL_DEFINITION_INCOMPLETE",
            "foundation_element_ids": list(missing_details),
            "action": "Provide defined drawing/detail data for every required foundation element.",
        })
    return items


def build_foundation_design_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    policy = _policy(payload)
    _source_gate(payload, policy)
    basis = _basis(payload)
    concrete, reinforcement_materials = _materials(payload)
    elements = _foundation_elements(payload, concrete)
    groups = _reinforcement_groups(payload, elements, reinforcement_materials)
    details = _drawing_details(payload, elements)
    results = _verification_results(payload, policy, elements)

    missing_types = _coverage(results, policy)
    missing_reinf = _missing_reinforcement(elements, groups) if policy["require_reinforcement_for_all_foundations"] else []
    missing_details = _missing_details(elements, details) if policy["require_detail_for_all_foundations"] else []
    reviews = _review_items(results, missing_types, missing_reinf, missing_details)
    mandatory = [r for r in results if r["mandatory"]]

    if missing_types or missing_reinf or missing_details:
        state = "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_INCOMPLETE"
    elif any(r["status"] != "PASS" for r in mandatory):
        state = "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_REVIEW_REQUIRED"
    else:
        state = "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED"

    envelopes = _element_envelopes(results, elements)
    max_util = max([e["maximum_utilization"] for e in envelopes if e["maximum_utilization"] is not None], default=None)
    schedule = _reinforcement_schedule(groups)
    quantities = _quantity_takeoff(elements, groups)

    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "source": {
            "engine_id": EXPECTED_SOURCE_ENGINE,
            "foundation_interface_soil_support_state": payload["foundation_interface_soil_support_state"],
        },
        "foundation_design_basis": basis,
        "materials": {
            "concrete": list(concrete.values()),
            "reinforcement": list(reinforcement_materials.values()),
        },
        "foundation_elements": list(elements.values()),
        "reinforcement_groups": groups,
        "reinforcement_schedule": schedule,
        "drawing_details": details,
        "verification_checks": results,
        "foundation_utilization_envelope": envelopes,
        "quantity_takeoff": quantities,
        "review_items": reviews,
        "verification_state": state,
        "summary": {
            "foundation_element_count": len(elements),
            "reinforcement_group_count": len(groups),
            "drawing_detail_count": len(details),
            "verification_check_count": len(results),
            "mandatory_check_count": len(mandatory),
            "failed_mandatory_check_count": sum(1 for r in mandatory if r["status"] != "PASS"),
            "missing_mandatory_check_types": missing_types,
            "foundation_elements_without_reinforcement": missing_reinf,
            "foundation_elements_without_defined_detail": missing_details,
            "review_item_count": len(reviews),
            "maximum_utilization": max_util,
        },
        "digital_twin_writeback": {
            "enabled": True,
            "namespace": "structural.foundation.design_reinforcement_detailing.v8_9_0",
            "state": state,
            "write_fields": [
                "foundation_geometry",
                "reinforcement_groups",
                "reinforcement_schedule",
                "verification_results",
                "utilization_envelope",
                "drawing_details",
                "quantity_takeoff",
                "normative_traceability",
                "review_items",
            ],
        },
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_geotechnical_approval": False,
            "automatic_structural_approval": False,
            "automatic_foundation_approval": False,
            "automatic_detailing_approval": False,
            "construction_release": LOCKED_RELEASE,
            "structural_model_release": LOCKED_RELEASE,
        },
    }


def _demo_payload() -> Dict[str, Any]:
    return {
        "project_id": "PHX-GENERIC-BUILDING-FOUNDATION-DESIGN-V8.9.0",
        "source_engine": EXPECTED_SOURCE_ENGINE,
        "foundation_interface_soil_support_state": "FOUNDATION_INTERFACE_SOIL_SUPPORT_CANDIDATE_PASSED",
        "foundation_design_basis": {
            "jurisdiction": "PROJECT_DEFINED",
            "standard_set": "PROJECT_DEFINED_REINFORCED_CONCRETE_FOUNDATION_STANDARD",
            "edition": "PROJECT_DEFINED_EDITION",
            "source_reference": "PROJECT_STRUCTURAL_DESIGN_BASIS:FOUNDATION_DESIGN_DETAILING",
            "status": "ENGINEER_OR_VERIFIED_STANDARDS_ENGINE_INPUT",
        },
        "materials": {
            "concrete": [
                {"id": "CONC-1", "design_strength": 20.0, "strength_unit": "MPa", "source_reference": "MAT:CONC-1"}
            ],
            "reinforcement": [
                {"id": "REBAR-1", "design_strength": 435.0, "strength_unit": "MPa", "density_kg_m3": 7850.0, "source_reference": "MAT:REBAR-1"}
            ],
        },
        "foundation_elements": [
            {"id": "F1", "type": "PAD_FOUNDATION", "concrete_material_id": "CONC-1", "dimensions": {"length_m": 2.0, "width_m": 2.0, "thickness_m": 0.45}, "source_reference": "GEOM:F1"},
            {"id": "SF1", "type": "STRIP_FOUNDATION", "concrete_material_id": "CONC-1", "dimensions": {"length_m": 6.0, "width_m": 1.5, "thickness_m": 0.40}, "source_reference": "GEOM:SF1"},
            {"id": "FB1", "type": "FOUNDATION_BEAM", "concrete_material_id": "CONC-1", "dimensions": {"length_m": 6.0, "width_m": 0.50, "height_m": 0.60}, "source_reference": "GEOM:FB1"},
            {"id": "PC1", "type": "PILE_CAP", "concrete_material_id": "CONC-1", "dimensions": {"length_m": 2.2, "width_m": 2.2, "thickness_m": 0.80}, "source_reference": "GEOM:PC1"},
        ],
        "reinforcement_groups": [
            {"id": "RG1", "bar_mark": "F1-B1", "foundation_element_id": "F1", "role": "BOTTOM_X", "material_id": "REBAR-1", "count": 11, "diameter_mm": 16, "bar_length_m": 1.80, "cover_mm": 50, "spacing_mm": 150, "shape_code": "STRAIGHT", "source_reference": "REINF:F1-B1"},
            {"id": "RG2", "bar_mark": "SF1-B1", "foundation_element_id": "SF1", "role": "BOTTOM_LONGITUDINAL", "material_id": "REBAR-1", "count": 6, "diameter_mm": 16, "bar_length_m": 5.80, "cover_mm": 50, "spacing_mm": 200, "shape_code": "STRAIGHT", "source_reference": "REINF:SF1-B1"},
            {"id": "RG3", "bar_mark": "FB1-B1", "foundation_element_id": "FB1", "role": "BOTTOM_LONGITUDINAL", "material_id": "REBAR-1", "count": 4, "diameter_mm": 20, "bar_length_m": 5.80, "cover_mm": 40, "spacing_mm": 120, "shape_code": "STRAIGHT", "source_reference": "REINF:FB1-B1"},
            {"id": "RG4", "bar_mark": "PC1-B1", "foundation_element_id": "PC1", "role": "BOTTOM_X", "material_id": "REBAR-1", "count": 12, "diameter_mm": 20, "bar_length_m": 2.00, "cover_mm": 60, "spacing_mm": 160, "shape_code": "STRAIGHT", "source_reference": "REINF:PC1-B1"},
        ],
        "drawing_details": [
            {"id": "D-F1", "foundation_element_id": "F1", "view_type": "PLAN_AND_SECTION", "scale": "1:20", "status": "DEFINED", "source_reference": "DETAIL:F1"},
            {"id": "D-SF1", "foundation_element_id": "SF1", "view_type": "PLAN_AND_SECTION", "scale": "1:20", "status": "DEFINED", "source_reference": "DETAIL:SF1"},
            {"id": "D-FB1", "foundation_element_id": "FB1", "view_type": "LONGITUDINAL_AND_CROSS_SECTION", "scale": "1:20", "status": "DEFINED", "source_reference": "DETAIL:FB1"},
            {"id": "D-PC1", "foundation_element_id": "PC1", "view_type": "PLAN_AND_SECTION", "scale": "1:20", "status": "DEFINED", "source_reference": "DETAIL:PC1"},
        ],
        "verification_checks": [
            {"id": "FD01", "check_type": "PAD_FLEXURAL_CAPACITY", "foundation_element_id": "F1", "demand": 85, "capacity": 120, "quantity": "design_moment", "unit": "kNm", "mandatory": True, "normative_reference": "REF:PAD_FLEXURE"},
            {"id": "FD02", "check_type": "PAD_ONE_WAY_SHEAR_CAPACITY", "foundation_element_id": "F1", "demand": 110, "capacity": 160, "quantity": "design_shear", "unit": "kN", "mandatory": True, "normative_reference": "REF:PAD_ONE_WAY_SHEAR"},
            {"id": "FD03", "check_type": "PAD_PUNCHING_SHEAR_CAPACITY", "foundation_element_id": "F1", "demand": 330, "capacity": 430, "quantity": "punching_shear", "unit": "kN", "mandatory": True, "normative_reference": "REF:PAD_PUNCHING"},
            {"id": "FD04", "check_type": "STRIP_FLEXURAL_CAPACITY", "foundation_element_id": "SF1", "demand": 72, "capacity": 105, "quantity": "design_moment", "unit": "kNm/m", "mandatory": True, "normative_reference": "REF:STRIP_FLEXURE"},
            {"id": "FD05", "check_type": "STRIP_ONE_WAY_SHEAR_CAPACITY", "foundation_element_id": "SF1", "demand": 88, "capacity": 125, "quantity": "design_shear", "unit": "kN/m", "mandatory": True, "normative_reference": "REF:STRIP_SHEAR"},
            {"id": "FD06", "check_type": "FOUNDATION_BEAM_FLEXURAL_CAPACITY", "foundation_element_id": "FB1", "demand": 135, "capacity": 180, "quantity": "design_moment", "unit": "kNm", "mandatory": True, "normative_reference": "REF:FOUNDATION_BEAM_FLEXURE"},
            {"id": "FD07", "check_type": "FOUNDATION_BEAM_SHEAR_CAPACITY", "foundation_element_id": "FB1", "demand": 145, "capacity": 190, "quantity": "design_shear", "unit": "kN", "mandatory": True, "normative_reference": "REF:FOUNDATION_BEAM_SHEAR"},
            {"id": "FD08", "check_type": "PILE_CAP_STRUT_TIE_CAPACITY", "foundation_element_id": "PC1", "demand": 610, "capacity": 780, "quantity": "strut_tie_design_action", "unit": "kN", "mandatory": True, "normative_reference": "REF:PILE_CAP_STRUT_TIE"},
            {"id": "FD09", "check_type": "MINIMUM_REINFORCEMENT_EVIDENCE", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:MIN_REINF", "mandatory": True, "normative_reference": "REF:MIN_REINF"},
            {"id": "FD10", "check_type": "MAXIMUM_REINFORCEMENT_EVIDENCE", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:MAX_REINF", "mandatory": True, "normative_reference": "REF:MAX_REINF"},
            {"id": "FD11", "check_type": "CONCRETE_COVER_EVIDENCE", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:COVER", "mandatory": True, "normative_reference": "REF:COVER"},
            {"id": "FD12", "check_type": "BAR_SPACING_EVIDENCE", "foundation_element_id": "SF1", "verified": True, "evidence_reference": "EVIDENCE:SPACING", "mandatory": True, "normative_reference": "REF:SPACING"},
            {"id": "FD13", "check_type": "ANCHORAGE_DEVELOPMENT_EVIDENCE", "foundation_element_id": "FB1", "verified": True, "evidence_reference": "EVIDENCE:ANCHORAGE", "mandatory": True, "normative_reference": "REF:ANCHORAGE"},
            {"id": "FD14", "check_type": "DOWEL_STARTER_BAR_EVIDENCE", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:DOWELS", "mandatory": True, "normative_reference": "REF:DOWELS"},
            {"id": "FD15", "check_type": "MATERIAL_TRACEABILITY", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:MATERIALS", "mandatory": True, "normative_reference": "REF:MATERIALS"},
            {"id": "FD16", "check_type": "DRAWING_DETAIL_COMPLETENESS", "foundation_element_id": "F1", "verified": True, "evidence_reference": "EVIDENCE:DRAWINGS", "mandatory": True, "normative_reference": "REF:DRAWINGS"},
        ],
        "verification_policy": {
            "acceptable_foundation_interface_states": ["FOUNDATION_INTERFACE_SOIL_SUPPORT_CANDIDATE_PASSED"],
            "require_normative_reference": True,
            "require_reinforcement_for_all_foundations": True,
            "require_detail_for_all_foundations": True,
            "mandatory_check_types": sorted(SUPPORTED_CHECK_TYPES),
            "pass_tolerance": 1e-12,
        },
    }


def _self_test() -> int:
    report = build_foundation_design_report(_demo_payload())
    summary = {
        "engine": report["engine"],
        "verification_state": report["verification_state"],
        "foundation_elements": report["summary"]["foundation_element_count"],
        "reinforcement_groups": report["summary"]["reinforcement_group_count"],
        "verification_checks": report["summary"]["verification_check_count"],
        "review_items": report["summary"]["review_item_count"],
        "maximum_utilization": report["summary"]["maximum_utilization"],
        "concrete_volume_m3": report["quantity_takeoff"]["total_concrete_volume_m3"],
        "reinforcement_mass_kg": report["quantity_takeoff"]["estimated_total_reinforcement_mass_kg"],
        "structural_model_release": report["release"]["structural_model_release"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if report["verification_state"] == "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        return _self_test()
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_foundation_design_report(payload)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
