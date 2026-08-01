#!/usr/bin/env python3
"""Project Phoenix Structural Drawing, Calculation Package & Engineering QA/QC Engine v8.10.0.

This engine consolidates the structural evidence chain through v8.9.0 into an
engineering-package candidate. It validates source-layer provenance, drawing and
calculation registers, verification registers, assumptions, QA/QC evidence,
cross-document references and release-readiness metadata.

A technical PASS from this engine is NOT a code-compliance claim, professional
engineering approval, construction release, or structural-model release. Human
engineering review remains mandatory and all release gates remain locked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-DRAWING-CALC-PACKAGE-ENGINEERING-QAQC-V8.10.0"
VERSION = "8.10.0"
EXPECTED_SOURCE_ENGINE = "PHX-STRUCT-FOUNDATION-DESIGN-REINFORCEMENT-DETAILING-V8.9.0"
LOCKED_RELEASE = "LOCKED"

REQUIRED_SOURCE_LAYERS = {
    "v8.0.0": "ARCHITECTURAL_TO_STRUCTURAL_DERIVATION",
    "v8.1.0": "STRUCTURAL_ANALYTICAL_MODEL",
    "v8.2.0": "STRUCTURAL_ACTION_LOAD_MODEL",
    "v8.3.0": "STRUCTURAL_SOLVER_INPUT_ANALYSIS",
    "v8.4.0": "STRUCTURAL_ANALYSIS_RESULTS_VALIDATION",
    "v8.5.0": "STRUCTURAL_MEMBER_VERIFICATION",
    "v8.6.0": "STRUCTURAL_GLOBAL_STABILITY_ROBUSTNESS",
    "v8.7.0": "STRUCTURAL_CONNECTION_SUPPORT_JOINT_VERIFICATION",
    "v8.8.0": "STRUCTURAL_FOUNDATION_INTERFACE_SOIL_SUPPORT",
    "v8.9.0": "STRUCTURAL_FOUNDATION_DESIGN_REINFORCEMENT_DETAILING",
}

REQUIRED_VERIFICATION_REGISTERS = {
    "MEMBER_VERIFICATION",
    "GLOBAL_STABILITY_ROBUSTNESS",
    "CONNECTION_SUPPORT_JOINT",
    "FOUNDATION_INTERFACE_SOIL_SUPPORT",
    "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING",
}

SUPPORTED_QA_CHECK_TYPES = {
    "SOURCE_LAYER_COMPLETENESS",
    "DRAWING_CALCULATION_CROSS_REFERENCE",
    "DRAWING_REVISION_COHERENCE",
    "VERIFICATION_REGISTER_COMPLETENESS",
    "NORMATIVE_REFERENCE_COMPLETENESS",
    "ASSUMPTION_REGISTER_COMPLETENESS",
    "OPEN_REVIEW_ITEM_RECONCILIATION",
    "DIGITAL_TWIN_CROSS_REFERENCE",
    "QUANTITY_SCHEDULE_COHERENCE",
    "PACKAGE_IDENTIFIER_COHERENCE",
}

ALLOWED_DOCUMENT_STATUSES = {"ISSUED_FOR_ENGINEERING_QA", "CHECKED", "APPROVED_FOR_REVIEW"}
ALLOWED_ASSUMPTION_STATUSES = {"VALIDATED", "OPEN", "SUPERSEDED"}
ALLOWED_HUMAN_REVIEW_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


def _items(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be a non-empty string")
    return result


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


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


def _nonnegative(value: Any, label: str) -> float:
    result = _num(value, label)
    if result < 0:
        raise ValueError(f"{label} must be >= 0")
    return result


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("qaqc_policy")
    if not isinstance(raw, Mapping):
        raise ValueError("qaqc_policy must be an object")
    mandatory_qa = [str(x).strip().upper() for x in _items(raw.get("mandatory_qaqc_check_types")) if str(x).strip()]
    if not mandatory_qa:
        raise ValueError("mandatory_qaqc_check_types must not be empty")
    unknown = sorted(set(mandatory_qa) - SUPPORTED_QA_CHECK_TYPES)
    if unknown:
        raise ValueError(f"unsupported mandatory_qaqc_check_types: {', '.join(unknown)}")
    required_layers = [str(x).strip() for x in _items(raw.get("required_source_versions")) if str(x).strip()]
    if not required_layers:
        raise ValueError("required_source_versions must not be empty")
    return {
        "mandatory_qaqc_check_types": mandatory_qa,
        "required_source_versions": required_layers,
        "require_normative_reference": bool(raw.get("require_normative_reference", True)),
        "require_source_reference": bool(raw.get("require_source_reference", True)),
        "require_drawing_calc_cross_reference": bool(raw.get("require_drawing_calc_cross_reference", True)),
        "require_zero_open_verification_review_items": bool(raw.get("require_zero_open_verification_review_items", True)),
        "require_zero_open_assumptions_for_readiness": bool(raw.get("require_zero_open_assumptions_for_readiness", True)),
        "human_engineering_review_required": bool(raw.get("human_engineering_review_required", True)),
    }


def _source_gate(payload: Mapping[str, Any]) -> None:
    source = _text(payload.get("source_engine"), "source_engine")
    if source != EXPECTED_SOURCE_ENGINE:
        raise ValueError(f"v8.9.0 source engine required; received {source}")
    state = _text(payload.get("foundation_design_reinforcement_detailing_state"), "foundation_design_reinforcement_detailing_state")
    if state != "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED":
        raise ValueError(f"v8.9.0 candidate state not accepted: {state}")


def _basis(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("engineering_package_basis")
    if not isinstance(raw, Mapping):
        raise ValueError("engineering_package_basis must be an object")
    return {
        "project_id": _text(raw.get("project_id"), "engineering_package_basis.project_id"),
        "package_id": _text(raw.get("package_id"), "engineering_package_basis.package_id"),
        "package_revision": _text(raw.get("package_revision"), "engineering_package_basis.package_revision"),
        "jurisdiction": _text(raw.get("jurisdiction"), "engineering_package_basis.jurisdiction"),
        "standard_set": _text(raw.get("standard_set"), "engineering_package_basis.standard_set"),
        "edition": _text(raw.get("edition"), "engineering_package_basis.edition"),
        "source_reference": _text(raw.get("source_reference"), "engineering_package_basis.source_reference"),
        "status": _text(raw.get("status"), "engineering_package_basis.status"),
    }


def _source_layers(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    layers: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in _items(payload.get("source_layers")):
        if not isinstance(raw, Mapping):
            raise ValueError("source_layers entries must be objects")
        version = _text(raw.get("version"), "source layer version")
        if version in seen:
            raise ValueError(f"duplicate source layer version: {version}")
        seen.add(version)
        if version not in REQUIRED_SOURCE_LAYERS:
            raise ValueError(f"unsupported source layer version: {version}")
        layer_id = _text(raw.get("layer_id"), f"source_layers[{version}].layer_id")
        if layer_id != REQUIRED_SOURCE_LAYERS[version]:
            raise ValueError(f"source layer {version} expected layer_id {REQUIRED_SOURCE_LAYERS[version]} but received {layer_id}")
        state = _text(raw.get("state"), f"source_layers[{version}].state")
        evidence_reference = _text(raw.get("evidence_reference"), f"source_layers[{version}].evidence_reference")
        mandatory = _boolean(raw.get("mandatory"), f"source_layers[{version}].mandatory")
        layers.append({
            "version": version,
            "layer_id": layer_id,
            "state": state,
            "evidence_reference": evidence_reference,
            "mandatory": mandatory,
            "evidence_fingerprint_sha256": _canonical_sha256({"version": version, "layer_id": layer_id, "state": state, "evidence_reference": evidence_reference}),
        })
    missing = [v for v in policy["required_source_versions"] if v not in seen]
    return layers, missing


def _drawings(payload: Mapping[str, Any], basis: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    drawings: Dict[str, Dict[str, Any]] = {}
    for raw in _items(payload.get("drawings")):
        if not isinstance(raw, Mapping):
            raise ValueError("drawings entries must be objects")
        did = _text(raw.get("id"), "drawing id")
        if did in drawings:
            raise ValueError(f"duplicate drawing id: {did}")
        status = _text(raw.get("status"), f"drawing {did}.status").upper()
        if status not in ALLOWED_DOCUMENT_STATUSES:
            raise ValueError(f"drawing {did} has unsupported status: {status}")
        revision = _text(raw.get("revision"), f"drawing {did}.revision")
        source_reference = _text(raw.get("source_reference"), f"drawing {did}.source_reference")
        related_element_ids = [_text(x, f"drawing {did}.related_element_ids item") for x in _items(raw.get("related_element_ids"))]
        related_calculation_ids = [_text(x, f"drawing {did}.related_calculation_ids item") for x in _items(raw.get("related_calculation_ids"))]
        drawings[did] = {
            "id": did,
            "title": _text(raw.get("title"), f"drawing {did}.title"),
            "drawing_type": _text(raw.get("drawing_type"), f"drawing {did}.drawing_type"),
            "revision": revision,
            "status": status,
            "source_reference": source_reference,
            "related_element_ids": related_element_ids,
            "related_calculation_ids": related_calculation_ids,
            "package_revision_matches": revision == basis["package_revision"],
        }
    if not drawings:
        raise ValueError("at least one drawing is required")
    return drawings


def _calculations(payload: Mapping[str, Any], basis: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    calculations: Dict[str, Dict[str, Any]] = {}
    for raw in _items(payload.get("calculation_sections")):
        if not isinstance(raw, Mapping):
            raise ValueError("calculation_sections entries must be objects")
        cid = _text(raw.get("id"), "calculation section id")
        if cid in calculations:
            raise ValueError(f"duplicate calculation section id: {cid}")
        status = _text(raw.get("status"), f"calculation {cid}.status").upper()
        if status not in ALLOWED_DOCUMENT_STATUSES:
            raise ValueError(f"calculation {cid} has unsupported status: {status}")
        revision = _text(raw.get("revision"), f"calculation {cid}.revision")
        related_drawing_ids = [_text(x, f"calculation {cid}.related_drawing_ids item") for x in _items(raw.get("related_drawing_ids"))]
        calculations[cid] = {
            "id": cid,
            "title": _text(raw.get("title"), f"calculation {cid}.title"),
            "discipline": _text(raw.get("discipline"), f"calculation {cid}.discipline"),
            "revision": revision,
            "status": status,
            "source_reference": _text(raw.get("source_reference"), f"calculation {cid}.source_reference"),
            "normative_reference": _text(raw.get("normative_reference"), f"calculation {cid}.normative_reference"),
            "related_drawing_ids": related_drawing_ids,
            "package_revision_matches": revision == basis["package_revision"],
        }
    if not calculations:
        raise ValueError("at least one calculation section is required")
    return calculations


def _verification_registers(payload: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    registers: Dict[str, Dict[str, Any]] = {}
    for raw in _items(payload.get("verification_registers")):
        if not isinstance(raw, Mapping):
            raise ValueError("verification_registers entries must be objects")
        category = _text(raw.get("category"), "verification register category").upper()
        if category in registers:
            raise ValueError(f"duplicate verification register category: {category}")
        open_review_items = _nonnegative_int(raw.get("open_review_items"), f"verification {category}.open_review_items")
        max_util = raw.get("maximum_utilization")
        clean_util: Optional[float]
        if max_util is None:
            clean_util = None
        else:
            clean_util = _nonnegative(max_util, f"verification {category}.maximum_utilization")
        registers[category] = {
            "category": category,
            "status": _text(raw.get("status"), f"verification {category}.status"),
            "evidence_reference": _text(raw.get("evidence_reference"), f"verification {category}.evidence_reference"),
            "normative_reference": _text(raw.get("normative_reference"), f"verification {category}.normative_reference"),
            "open_review_items": open_review_items,
            "maximum_utilization": clean_util,
        }
    if not registers:
        raise ValueError("verification_registers must not be empty")
    return registers


def _assumptions(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    assumptions: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in _items(payload.get("assumptions")):
        if not isinstance(raw, Mapping):
            raise ValueError("assumptions entries must be objects")
        aid = _text(raw.get("id"), "assumption id")
        if aid in seen:
            raise ValueError(f"duplicate assumption id: {aid}")
        seen.add(aid)
        status = _text(raw.get("status"), f"assumption {aid}.status").upper()
        if status not in ALLOWED_ASSUMPTION_STATUSES:
            raise ValueError(f"assumption {aid} has unsupported status: {status}")
        assumptions.append({
            "id": aid,
            "statement": _text(raw.get("statement"), f"assumption {aid}.statement"),
            "status": status,
            "source_reference": _text(raw.get("source_reference"), f"assumption {aid}.source_reference"),
            "owner": _text(raw.get("owner"), f"assumption {aid}.owner"),
        })
    return assumptions


def _qa_checks(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in _items(payload.get("qaqc_checks")):
        if not isinstance(raw, Mapping):
            raise ValueError("qaqc_checks entries must be objects")
        check_type = _text(raw.get("check_type"), "qaqc check_type").upper()
        if check_type not in SUPPORTED_QA_CHECK_TYPES:
            raise ValueError(f"unsupported QA/QC check type: {check_type}")
        if check_type in seen:
            raise ValueError(f"duplicate QA/QC check type: {check_type}")
        seen.add(check_type)
        checks.append({
            "check_type": check_type,
            "verified": _boolean(raw.get("verified"), f"{check_type}.verified"),
            "evidence_reference": _text(raw.get("evidence_reference"), f"{check_type}.evidence_reference"),
            "comment": str(raw.get("comment") or "").strip(),
        })
    missing = [x for x in policy["mandatory_qaqc_check_types"] if x not in seen]
    return checks, missing


def _human_review(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("human_engineering_review_gate")
    if not isinstance(raw, Mapping):
        raise ValueError("human_engineering_review_gate must be an object")
    required = _boolean(raw.get("required"), "human_engineering_review_gate.required")
    if policy["human_engineering_review_required"] and not required:
        raise ValueError("human engineering review gate must remain required")
    status = _text(raw.get("status"), "human_engineering_review_gate.status").upper()
    if status not in ALLOWED_HUMAN_REVIEW_STATUSES:
        raise ValueError(f"unsupported human engineering review status: {status}")
    return {
        "required": required,
        "status": status,
        "reviewer_role": _text(raw.get("reviewer_role"), "human_engineering_review_gate.reviewer_role"),
        "review_reference": str(raw.get("review_reference") or "").strip() or None,
    }


def _cross_reference_findings(drawings: Mapping[str, Mapping[str, Any]], calculations: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    drawing_ids = set(drawings)
    calc_ids = set(calculations)
    for did, drawing in drawings.items():
        for cid in drawing["related_calculation_ids"]:
            if cid not in calc_ids:
                findings.append({"severity": "BLOCKER", "code": "DRAWING_UNKNOWN_CALCULATION_REFERENCE", "subject": did, "detail": cid})
    for cid, calc in calculations.items():
        for did in calc["related_drawing_ids"]:
            if did not in drawing_ids:
                findings.append({"severity": "BLOCKER", "code": "CALCULATION_UNKNOWN_DRAWING_REFERENCE", "subject": cid, "detail": did})
    return findings


def _build_evidence_index(
    layers: Sequence[Mapping[str, Any]],
    drawings: Mapping[str, Mapping[str, Any]],
    calculations: Mapping[str, Mapping[str, Any]],
    verification: Mapping[str, Mapping[str, Any]],
    assumptions: Sequence[Mapping[str, Any]],
    qaqc_checks: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for layer in layers:
        records.append({"kind": "SOURCE_LAYER", "id": layer["version"], "reference": layer["evidence_reference"]})
    for item in drawings.values():
        records.append({"kind": "DRAWING", "id": item["id"], "reference": item["source_reference"]})
    for item in calculations.values():
        records.append({"kind": "CALCULATION", "id": item["id"], "reference": item["source_reference"]})
    for item in verification.values():
        records.append({"kind": "VERIFICATION", "id": item["category"], "reference": item["evidence_reference"]})
    for item in assumptions:
        records.append({"kind": "ASSUMPTION", "id": item["id"], "reference": item["source_reference"]})
    for item in qaqc_checks:
        records.append({"kind": "QAQC", "id": item["check_type"], "reference": item["evidence_reference"]})
    for record in records:
        record["record_fingerprint_sha256"] = _canonical_sha256({"kind": record["kind"], "id": record["id"], "reference": record["reference"]})
    return records


def build_engineering_package_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    _source_gate(payload)
    policy = _policy(payload)
    basis = _basis(payload)
    layers, missing_layers = _source_layers(payload, policy)
    drawings = _drawings(payload, basis)
    calculations = _calculations(payload, basis)
    verification = _verification_registers(payload)
    assumptions = _assumptions(payload)
    qaqc_checks, missing_qa = _qa_checks(payload, policy)
    human_review = _human_review(payload, policy)

    findings: List[Dict[str, Any]] = []
    findings.extend(_cross_reference_findings(drawings, calculations))

    missing_verification = sorted(REQUIRED_VERIFICATION_REGISTERS - set(verification))
    for version in missing_layers:
        findings.append({"severity": "BLOCKER", "code": "MISSING_SOURCE_LAYER", "subject": version, "detail": "required source layer evidence missing"})
    for check_type in missing_qa:
        findings.append({"severity": "BLOCKER", "code": "MISSING_QAQC_CHECK", "subject": check_type, "detail": "mandatory QA/QC evidence missing"})
    for category in missing_verification:
        findings.append({"severity": "BLOCKER", "code": "MISSING_VERIFICATION_REGISTER", "subject": category, "detail": "required verification register missing"})

    for layer in layers:
        if layer["mandatory"] and "PASSED" not in layer["state"]:
            findings.append({"severity": "BLOCKER", "code": "SOURCE_LAYER_NOT_PASSED", "subject": layer["version"], "detail": layer["state"]})

    for item in drawings.values():
        if not item["package_revision_matches"]:
            findings.append({"severity": "BLOCKER", "code": "DRAWING_REVISION_MISMATCH", "subject": item["id"], "detail": item["revision"]})
    for item in calculations.values():
        if not item["package_revision_matches"]:
            findings.append({"severity": "BLOCKER", "code": "CALCULATION_REVISION_MISMATCH", "subject": item["id"], "detail": item["revision"]})

    for item in verification.values():
        if "PASSED" not in item["status"]:
            findings.append({"severity": "BLOCKER", "code": "VERIFICATION_REGISTER_NOT_PASSED", "subject": item["category"], "detail": item["status"]})
        if policy["require_zero_open_verification_review_items"] and item["open_review_items"] > 0:
            findings.append({"severity": "BLOCKER", "code": "OPEN_VERIFICATION_REVIEW_ITEMS", "subject": item["category"], "detail": str(item["open_review_items"])})

    open_assumptions = [x["id"] for x in assumptions if x["status"] == "OPEN"]
    if policy["require_zero_open_assumptions_for_readiness"]:
        for aid in open_assumptions:
            findings.append({"severity": "BLOCKER", "code": "OPEN_ENGINEERING_ASSUMPTION", "subject": aid, "detail": "assumption remains OPEN"})

    for check in qaqc_checks:
        if not check["verified"]:
            findings.append({"severity": "BLOCKER", "code": "QAQC_CHECK_FAILED", "subject": check["check_type"], "detail": check["comment"] or "verified=false"})

    evidence_index = _build_evidence_index(layers, drawings, calculations, verification, assumptions, qaqc_checks)
    maximum_utilizations = [x["maximum_utilization"] for x in verification.values() if x["maximum_utilization"] is not None]
    max_util = max(maximum_utilizations) if maximum_utilizations else None

    blocker_count = sum(1 for x in findings if x["severity"] == "BLOCKER")
    if missing_layers or missing_qa or missing_verification:
        state = "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_INCOMPLETE"
    elif blocker_count:
        state = "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_REVIEW_REQUIRED"
    else:
        state = "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_CANDIDATE_PASSED"

    package_core = {
        "basis": basis,
        "drawings": list(drawings.values()),
        "calculation_sections": list(calculations.values()),
        "verification_registers": list(verification.values()),
        "assumptions": assumptions,
        "source_layers": layers,
    }
    package_fingerprint = _canonical_sha256(package_core)

    technical_candidate_ready = state == "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_CANDIDATE_PASSED"
    human_review_complete = human_review["status"] == "APPROVED"

    report = {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "source_engine": EXPECTED_SOURCE_ENGINE,
        "engineering_package_basis": basis,
        "verification_state": state,
        "source_layers": layers,
        "drawing_register": list(drawings.values()),
        "calculation_register": list(calculations.values()),
        "verification_registers": list(verification.values()),
        "assumption_register": assumptions,
        "qaqc_checks": qaqc_checks,
        "qaqc_findings": findings,
        "engineering_evidence_index": evidence_index,
        "package_manifest": {
            "project_id": basis["project_id"],
            "package_id": basis["package_id"],
            "revision": basis["package_revision"],
            "drawing_count": len(drawings),
            "calculation_section_count": len(calculations),
            "verification_register_count": len(verification),
            "source_layer_count": len(layers),
            "evidence_record_count": len(evidence_index),
            "package_fingerprint_sha256": package_fingerprint,
        },
        "summary": {
            "missing_required_source_versions": missing_layers,
            "missing_mandatory_qaqc_check_types": missing_qa,
            "missing_verification_registers": missing_verification,
            "open_assumptions": open_assumptions,
            "qaqc_blocker_count": blocker_count,
            "maximum_reported_utilization": max_util,
            "technical_candidate_ready": technical_candidate_ready,
        },
        "release_readiness": {
            "technical_candidate_ready": technical_candidate_ready,
            "human_engineering_review_required": human_review["required"],
            "human_engineering_review_status": human_review["status"],
            "human_engineering_review_complete": human_review_complete,
            "professional_engineering_approval": False,
            "code_compliance_claim": False,
            "construction_release": LOCKED_RELEASE,
            "structural_model_release": LOCKED_RELEASE,
        },
        "human_engineering_review_gate": human_review,
        "digital_twin_writeback": {
            "enabled": True,
            "write_namespace": "structural.engineering_package_qaqc.v8_10_0",
            "write_fields": [
                "verification_state",
                "package_manifest",
                "drawing_register",
                "calculation_register",
                "verification_registers",
                "assumption_register",
                "qaqc_checks",
                "qaqc_findings",
                "engineering_evidence_index",
                "release_readiness",
            ],
        },
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_professional_engineering_approval": False,
            "automatic_structural_approval": False,
            "automatic_drawing_approval": False,
            "automatic_calculation_approval": False,
            "automatic_construction_release": False,
            "construction_release": LOCKED_RELEASE,
            "structural_model_release": LOCKED_RELEASE,
        },
    }
    return report


def _demo_payload() -> Dict[str, Any]:
    source_layers = []
    for version, layer_id in REQUIRED_SOURCE_LAYERS.items():
        source_layers.append({
            "version": version,
            "layer_id": layer_id,
            "state": f"{layer_id}_CANDIDATE_PASSED",
            "evidence_reference": f"outputs/runtime/{version.replace('.', '_')}/evidence.json",
            "mandatory": True,
        })

    verification_registers = [
        {"category": "MEMBER_VERIFICATION", "status": "MEMBER_VERIFICATION_CANDIDATE_PASSED", "evidence_reference": "outputs/structural/member_verification.json", "normative_reference": "Design basis / member verification clauses", "open_review_items": 0, "maximum_utilization": 0.8661},
        {"category": "GLOBAL_STABILITY_ROBUSTNESS", "status": "GLOBAL_STABILITY_ROBUSTNESS_CANDIDATE_PASSED", "evidence_reference": "outputs/structural/global_stability.json", "normative_reference": "Design basis / global stability clauses", "open_review_items": 0, "maximum_utilization": 0.9583},
        {"category": "CONNECTION_SUPPORT_JOINT", "status": "CONNECTION_SUPPORT_JOINT_CANDIDATE_PASSED", "evidence_reference": "outputs/structural/connections.json", "normative_reference": "Design basis / connection clauses", "open_review_items": 0, "maximum_utilization": 0.82},
        {"category": "FOUNDATION_INTERFACE_SOIL_SUPPORT", "status": "FOUNDATION_INTERFACE_SOIL_SUPPORT_CANDIDATE_PASSED", "evidence_reference": "outputs/structural/foundation_interface.json", "normative_reference": "Design basis / foundation and geotechnical clauses", "open_review_items": 0, "maximum_utilization": 0.74},
        {"category": "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING", "status": "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED", "evidence_reference": "outputs/structural/foundation_design.json", "normative_reference": "Design basis / reinforced foundation clauses", "open_review_items": 0, "maximum_utilization": 0.7821},
    ]

    qaqc_checks = [
        {"check_type": x, "verified": True, "evidence_reference": f"qa/{x.lower()}.json", "comment": "Demo evidence verified"}
        for x in sorted(SUPPORTED_QA_CHECK_TYPES)
    ]

    return {
        "source_engine": EXPECTED_SOURCE_ENGINE,
        "foundation_design_reinforcement_detailing_state": "FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED",
        "engineering_package_basis": {
            "project_id": "GENERIC-BUILDING-001",
            "package_id": "STRUCT-PKG-001",
            "package_revision": "P01",
            "jurisdiction": "PROJECT_DEFINED",
            "standard_set": "PROJECT DESIGN BASIS",
            "edition": "PROJECT_DEFINED",
            "source_reference": "configs/projects/generic_building_structural_drawing_calculation_package_engineering_qaqc_v8_10_0.json",
            "status": "ENGINEERING_QA_CANDIDATE",
        },
        "qaqc_policy": {
            "mandatory_qaqc_check_types": sorted(SUPPORTED_QA_CHECK_TYPES),
            "required_source_versions": list(REQUIRED_SOURCE_LAYERS),
            "require_normative_reference": True,
            "require_source_reference": True,
            "require_drawing_calc_cross_reference": True,
            "require_zero_open_verification_review_items": True,
            "require_zero_open_assumptions_for_readiness": True,
            "human_engineering_review_required": True,
        },
        "source_layers": source_layers,
        "drawings": [
            {"id": "S-001", "title": "Structural general arrangement", "drawing_type": "GENERAL_ARRANGEMENT", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "drawings/S-001.pdf", "related_element_ids": ["COL-01", "BEAM-01"], "related_calculation_ids": ["CALC-01", "CALC-02"]},
            {"id": "S-101", "title": "Foundation and reinforcement plan", "drawing_type": "FOUNDATION_REINFORCEMENT", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "drawings/S-101.pdf", "related_element_ids": ["F1", "FB1", "PC1"], "related_calculation_ids": ["CALC-03"]},
            {"id": "S-201", "title": "Connection and support details", "drawing_type": "CONNECTION_DETAILS", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "drawings/S-201.pdf", "related_element_ids": ["J1", "SUP-01"], "related_calculation_ids": ["CALC-02"]},
        ],
        "calculation_sections": [
            {"id": "CALC-01", "title": "Actions, analysis and member verification", "discipline": "STRUCTURAL_ANALYSIS", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "calculations/CALC-01.json", "normative_reference": "Project design basis / ULS-SLS", "related_drawing_ids": ["S-001"]},
            {"id": "CALC-02", "title": "Global stability and connection verification", "discipline": "STRUCTURAL_STABILITY_CONNECTIONS", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "calculations/CALC-02.json", "normative_reference": "Project design basis / stability and connections", "related_drawing_ids": ["S-001", "S-201"]},
            {"id": "CALC-03", "title": "Foundation and reinforcement verification", "discipline": "FOUNDATIONS", "revision": "P01", "status": "ISSUED_FOR_ENGINEERING_QA", "source_reference": "calculations/CALC-03.json", "normative_reference": "Project design basis / foundations", "related_drawing_ids": ["S-101"]},
        ],
        "verification_registers": verification_registers,
        "assumptions": [
            {"id": "ASM-001", "statement": "All project geometry used in the package is derived from the controlled Digital Twin snapshot.", "status": "VALIDATED", "source_reference": "digital_twin/snapshot_manifest.json", "owner": "PROJECT_QA"},
            {"id": "ASM-002", "statement": "Normative values are supplied by the controlled project design basis and are not invented by this engine.", "status": "VALIDATED", "source_reference": "design_basis/structural_basis.json", "owner": "STRUCTURAL_ENGINEERING"},
        ],
        "qaqc_checks": qaqc_checks,
        "human_engineering_review_gate": {
            "required": True,
            "status": "PENDING",
            "reviewer_role": "COMPETENT_STRUCTURAL_ENGINEER",
            "review_reference": "ENG-REVIEW-PENDING",
        },
    }


def _self_test() -> Dict[str, Any]:
    report = build_engineering_package_report(_demo_payload())
    assert report["verification_state"] == "ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_CANDIDATE_PASSED"
    assert report["summary"]["qaqc_blocker_count"] == 0
    assert report["summary"]["technical_candidate_ready"] is True
    assert report["release_readiness"]["human_engineering_review_complete"] is False
    assert report["release"]["construction_release"] == "LOCKED"
    assert report["release"]["structural_model_release"] == "LOCKED"
    assert len(report["source_layers"]) == 10
    assert report["package_manifest"]["drawing_count"] == 3
    assert report["package_manifest"]["calculation_section_count"] == 3
    assert len(report["package_manifest"]["package_fingerprint_sha256"]) == 64
    return {
        "engine": report["engine"],
        "verification_state": report["verification_state"],
        "source_layer_count": report["package_manifest"]["source_layer_count"],
        "drawing_count": report["package_manifest"]["drawing_count"],
        "calculation_section_count": report["package_manifest"]["calculation_section_count"],
        "verification_register_count": report["package_manifest"]["verification_register_count"],
        "evidence_record_count": report["package_manifest"]["evidence_record_count"],
        "qaqc_blocker_count": report["summary"]["qaqc_blocker_count"],
        "maximum_reported_utilization": report["summary"]["maximum_reported_utilization"],
        "human_engineering_review_status": report["human_engineering_review_gate"]["status"],
        "construction_release": report["release"]["construction_release"],
        "structural_model_release": report["release"]["structural_model_release"],
        "self_test": "PASSED",
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError("input JSON root must be an object")
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run embedded v8.10.0 validation scenario")
    parser.add_argument("--input", type=Path, help="Input engineering-package JSON")
    parser.add_argument("--output", type=Path, help="Write generated report JSON")
    args = parser.parse_args(argv)

    if args.self_test:
        result = _self_test()
    elif args.input:
        result = build_engineering_package_report(_load_json(args.input))
    else:
        parser.error("provide --self-test or --input")

    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
