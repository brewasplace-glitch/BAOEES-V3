#!/usr/bin/env python3
"""Project Phoenix Structural Engineering Review, Approval & Release Control Engine v8.11.0.

This engine formalizes the transition from a v8.10.0 QA/QC engineering package
candidate to controlled structural-model and/or construction release states.

It NEVER fabricates human approval. A release is possible only when explicit,
traceable human engineering review evidence and explicit human release
authorization are supplied, all fingerprints still match the reviewed package,
and the configured release gates pass.

The engine is a workflow/evidence control mechanism. It does not determine who
is legally competent to approve engineering work in a jurisdiction; that must be
established by project governance and applicable law.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

ENGINE_ID = "PHX-STRUCT-ENGINEERING-REVIEW-APPROVAL-RELEASE-CONTROL-V8.11.0"
VERSION = "8.11.0"
EXPECTED_SOURCE_ENGINE = "PHX-STRUCT-DRAWING-CALC-PACKAGE-ENGINEERING-QAQC-V8.10.0"
EXPECTED_QAQC_STATE = "ENGINEERING_PACKAGE_QAQC_CANDIDATE_PASSED"

REVIEW_STATUSES = {
    "PENDING", "APPROVED", "APPROVED_WITH_COMMENTS", "REJECTED", "RETURNED_FOR_REVISION"
}
RELEASE_DECISIONS = {"HOLD", "REJECT", "RELEASE_STRUCTURAL_MODEL", "RELEASE_CONSTRUCTION"}
SIGNATURE_STATES = {"VERIFIED_EXTERNALLY", "NOT_VERIFIED"}
REVIEW_SCOPES = {"STRUCTURAL_MODEL", "CONSTRUCTION_DOCUMENTS"}
RELEASE_SCOPES = {"STRUCTURAL_MODEL", "CONSTRUCTION"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _items(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be a non-empty string")
    return result


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _sha(value: Any, label: str) -> str:
    result = _text(value, label).lower()
    if not SHA256_RE.fullmatch(result):
        raise ValueError(f"{label} must be a 64-character SHA256 hex digest")
    return result


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_timestamp(value: Any, label: str) -> datetime:
    text = _text(value, label)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return dt


def compute_package_fingerprint(package: Mapping[str, Any]) -> str:
    """Fingerprint the immutable package identity and component fingerprints."""
    basis = {
        "project_id": _text(package.get("project_id"), "engineering_package.project_id"),
        "package_id": _text(package.get("package_id"), "engineering_package.package_id"),
        "package_revision": _text(package.get("package_revision"), "engineering_package.package_revision"),
        "structural_model_fingerprint_sha256": _sha(package.get("structural_model_fingerprint_sha256"), "engineering_package.structural_model_fingerprint_sha256"),
        "calculation_package_fingerprint_sha256": _sha(package.get("calculation_package_fingerprint_sha256"), "engineering_package.calculation_package_fingerprint_sha256"),
        "drawing_package_fingerprint_sha256": _sha(package.get("drawing_package_fingerprint_sha256"), "engineering_package.drawing_package_fingerprint_sha256"),
        "engineering_evidence_index_fingerprint_sha256": _sha(package.get("engineering_evidence_index_fingerprint_sha256"), "engineering_package.engineering_evidence_index_fingerprint_sha256"),
    }
    return _canonical_hash(basis)


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("release_policy")
    if not isinstance(raw, Mapping):
        raise ValueError("release_policy must be an object")
    reviewer_roles = {_text(x, "allowed reviewer role").upper() for x in _items(raw.get("allowed_reviewer_roles"))}
    authority_roles = {_text(x, "allowed release authority role").upper() for x in _items(raw.get("allowed_release_authority_roles"))}
    if not reviewer_roles or not authority_roles:
        raise ValueError("release_policy reviewer and release-authority roles must not be empty")
    return {
        "allowed_reviewer_roles": reviewer_roles,
        "allowed_release_authority_roles": authority_roles,
        "require_external_signature_validation": bool(raw.get("require_external_signature_validation", True)),
        "require_professional_responsibility_acknowledgement": bool(raw.get("require_professional_responsibility_acknowledgement", True)),
        "require_separation_of_duties": bool(raw.get("require_separation_of_duties", True)),
        "require_zero_qaqc_blockers": bool(raw.get("require_zero_qaqc_blockers", True)),
        "require_complete_verification_registers": bool(raw.get("require_complete_verification_registers", True)),
        "require_complete_documents_for_construction_release": bool(raw.get("require_complete_documents_for_construction_release", True)),
        "invalidate_approval_on_any_fingerprint_change": bool(raw.get("invalidate_approval_on_any_fingerprint_change", True)),
        "allow_approved_with_comments": bool(raw.get("allow_approved_with_comments", True)),
    }


def _package(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("engineering_package")
    if not isinstance(raw, Mapping):
        raise ValueError("engineering_package must be an object")
    package = {
        "project_id": _text(raw.get("project_id"), "engineering_package.project_id"),
        "package_id": _text(raw.get("package_id"), "engineering_package.package_id"),
        "package_revision": _text(raw.get("package_revision"), "engineering_package.package_revision"),
        "structural_model_fingerprint_sha256": _sha(raw.get("structural_model_fingerprint_sha256"), "engineering_package.structural_model_fingerprint_sha256"),
        "calculation_package_fingerprint_sha256": _sha(raw.get("calculation_package_fingerprint_sha256"), "engineering_package.calculation_package_fingerprint_sha256"),
        "drawing_package_fingerprint_sha256": _sha(raw.get("drawing_package_fingerprint_sha256"), "engineering_package.drawing_package_fingerprint_sha256"),
        "engineering_evidence_index_fingerprint_sha256": _sha(raw.get("engineering_evidence_index_fingerprint_sha256"), "engineering_package.engineering_evidence_index_fingerprint_sha256"),
        "package_fingerprint_sha256": _sha(raw.get("package_fingerprint_sha256"), "engineering_package.package_fingerprint_sha256"),
        "qaqc_blockers": raw.get("qaqc_blockers"),
        "required_documents_complete": _bool(raw.get("required_documents_complete"), "engineering_package.required_documents_complete"),
        "verification_registers_complete": _bool(raw.get("verification_registers_complete"), "engineering_package.verification_registers_complete"),
        "evidence_reference": _text(raw.get("evidence_reference"), "engineering_package.evidence_reference"),
    }
    if isinstance(package["qaqc_blockers"], bool) or not isinstance(package["qaqc_blockers"], int) or package["qaqc_blockers"] < 0:
        raise ValueError("engineering_package.qaqc_blockers must be a non-negative integer")
    package["computed_package_fingerprint_sha256"] = compute_package_fingerprint(package)
    return package


def _review(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("human_engineering_review")
    if not isinstance(raw, Mapping):
        raise ValueError("human_engineering_review must be an object")
    status = _text(raw.get("status"), "human_engineering_review.status").upper()
    if status not in REVIEW_STATUSES:
        raise ValueError(f"unsupported human engineering review status: {status}")
    scopes = {_text(x, "human_engineering_review.approved_scopes item").upper() for x in _items(raw.get("approved_scopes"))}
    unknown = scopes - REVIEW_SCOPES
    if unknown:
        raise ValueError(f"unsupported human review scopes: {', '.join(sorted(unknown))}")
    comments = []
    for item in _items(raw.get("comments")):
        if not isinstance(item, Mapping):
            raise ValueError("human_engineering_review.comments entries must be objects")
        comments.append({
            "id": _text(item.get("id"), "review comment id"),
            "text": _text(item.get("text"), "review comment text"),
            "blocking": _bool(item.get("blocking"), "review comment blocking"),
            "resolved": _bool(item.get("resolved"), "review comment resolved"),
        })
    review = {
        "status": status,
        "reviewer_id": _text(raw.get("reviewer_id"), "human_engineering_review.reviewer_id"),
        "reviewer_name": _text(raw.get("reviewer_name"), "human_engineering_review.reviewer_name"),
        "reviewer_role": _text(raw.get("reviewer_role"), "human_engineering_review.reviewer_role").upper(),
        "review_timestamp": _text(raw.get("review_timestamp"), "human_engineering_review.review_timestamp"),
        "approved_package_fingerprint_sha256": _sha(raw.get("approved_package_fingerprint_sha256"), "human_engineering_review.approved_package_fingerprint_sha256"),
        "approved_structural_model_fingerprint_sha256": _sha(raw.get("approved_structural_model_fingerprint_sha256"), "human_engineering_review.approved_structural_model_fingerprint_sha256"),
        "approved_calculation_package_fingerprint_sha256": _sha(raw.get("approved_calculation_package_fingerprint_sha256"), "human_engineering_review.approved_calculation_package_fingerprint_sha256"),
        "approved_drawing_package_fingerprint_sha256": _sha(raw.get("approved_drawing_package_fingerprint_sha256"), "human_engineering_review.approved_drawing_package_fingerprint_sha256"),
        "approved_scopes": scopes,
        "professional_responsibility_acknowledged": _bool(raw.get("professional_responsibility_acknowledged"), "human_engineering_review.professional_responsibility_acknowledged"),
        "identity_evidence_reference": _text(raw.get("identity_evidence_reference"), "human_engineering_review.identity_evidence_reference"),
        "signature_evidence_reference": _text(raw.get("signature_evidence_reference"), "human_engineering_review.signature_evidence_reference"),
        "signature_validation_state": _text(raw.get("signature_validation_state"), "human_engineering_review.signature_validation_state").upper(),
        "comments": comments,
    }
    if review["signature_validation_state"] not in SIGNATURE_STATES:
        raise ValueError("unsupported human engineering review signature validation state")
    _parse_timestamp(review["review_timestamp"], "human_engineering_review.review_timestamp")
    return review


def _authorization(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = payload.get("release_authorization")
    if not isinstance(raw, Mapping):
        raise ValueError("release_authorization must be an object")
    decision = _text(raw.get("decision"), "release_authorization.decision").upper()
    if decision not in RELEASE_DECISIONS:
        raise ValueError(f"unsupported release decision: {decision}")
    scopes = {_text(x, "release_authorization.authorized_scopes item").upper() for x in _items(raw.get("authorized_scopes"))}
    unknown = scopes - RELEASE_SCOPES
    if unknown:
        raise ValueError(f"unsupported release authorization scopes: {', '.join(sorted(unknown))}")
    auth = {
        "decision": decision,
        "authority_id": _text(raw.get("authority_id"), "release_authorization.authority_id"),
        "authority_name": _text(raw.get("authority_name"), "release_authorization.authority_name"),
        "authority_role": _text(raw.get("authority_role"), "release_authorization.authority_role").upper(),
        "authorization_timestamp": _text(raw.get("authorization_timestamp"), "release_authorization.authorization_timestamp"),
        "authorized_package_fingerprint_sha256": _sha(raw.get("authorized_package_fingerprint_sha256"), "release_authorization.authorized_package_fingerprint_sha256"),
        "authorized_scopes": scopes,
        "identity_evidence_reference": _text(raw.get("identity_evidence_reference"), "release_authorization.identity_evidence_reference"),
        "signature_evidence_reference": _text(raw.get("signature_evidence_reference"), "release_authorization.signature_evidence_reference"),
        "signature_validation_state": _text(raw.get("signature_validation_state"), "release_authorization.signature_validation_state").upper(),
        "release_note": _text(raw.get("release_note"), "release_authorization.release_note"),
    }
    if auth["signature_validation_state"] not in SIGNATURE_STATES:
        raise ValueError("unsupported release authorization signature validation state")
    _parse_timestamp(auth["authorization_timestamp"], "release_authorization.authorization_timestamp")
    return auth


def _add(blockers: List[Dict[str, str]], code: str, message: str) -> None:
    blockers.append({"code": code, "message": message})


def evaluate_release(payload: Mapping[str, Any]) -> Dict[str, Any]:
    source_engine = _text(payload.get("source_engine"), "source_engine")
    if source_engine != EXPECTED_SOURCE_ENGINE:
        raise ValueError(f"v8.10.0 source engine required; received {source_engine}")
    qaqc_state = _text(payload.get("engineering_package_qaqc_state"), "engineering_package_qaqc_state")
    policy = _policy(payload)
    package = _package(payload)
    review = _review(payload)
    auth = _authorization(payload)
    blockers: List[Dict[str, str]] = []

    if qaqc_state != EXPECTED_QAQC_STATE:
        _add(blockers, "QAQC_STATE_NOT_PASSED", f"Expected {EXPECTED_QAQC_STATE}; received {qaqc_state}")
    if package["package_fingerprint_sha256"] != package["computed_package_fingerprint_sha256"]:
        _add(blockers, "PACKAGE_FINGERPRINT_INVALID", "Declared package fingerprint does not match current component fingerprints")
    if policy["require_zero_qaqc_blockers"] and package["qaqc_blockers"] != 0:
        _add(blockers, "QAQC_BLOCKERS_OPEN", f"QA/QC blocker count is {package['qaqc_blockers']}")
    if policy["require_complete_verification_registers"] and not package["verification_registers_complete"]:
        _add(blockers, "VERIFICATION_REGISTERS_INCOMPLETE", "Verification registers are incomplete")

    if review["status"] not in {"APPROVED", "APPROVED_WITH_COMMENTS"}:
        _add(blockers, "HUMAN_REVIEW_NOT_APPROVED", f"Human engineering review state is {review['status']}")
    if review["status"] == "APPROVED_WITH_COMMENTS":
        if not policy["allow_approved_with_comments"]:
            _add(blockers, "APPROVED_WITH_COMMENTS_NOT_ALLOWED", "Policy does not allow release from APPROVED_WITH_COMMENTS")
        if not review["comments"]:
            _add(blockers, "APPROVAL_COMMENTS_MISSING", "APPROVED_WITH_COMMENTS requires a comment register")
    unresolved_blocking = [x["id"] for x in review["comments"] if x["blocking"] and not x["resolved"]]
    if unresolved_blocking:
        _add(blockers, "UNRESOLVED_BLOCKING_REVIEW_COMMENTS", ", ".join(unresolved_blocking))
    if review["reviewer_role"] not in policy["allowed_reviewer_roles"]:
        _add(blockers, "REVIEWER_ROLE_NOT_AUTHORIZED", review["reviewer_role"])
    if policy["require_professional_responsibility_acknowledgement"] and not review["professional_responsibility_acknowledged"]:
        _add(blockers, "PROFESSIONAL_RESPONSIBILITY_NOT_ACKNOWLEDGED", "Human reviewer did not acknowledge professional responsibility")
    if policy["require_external_signature_validation"] and review["signature_validation_state"] != "VERIFIED_EXTERNALLY":
        _add(blockers, "REVIEW_SIGNATURE_NOT_VERIFIED", review["signature_validation_state"])

    exact_review_hash_match = (
        review["approved_package_fingerprint_sha256"] == package["package_fingerprint_sha256"]
        and review["approved_structural_model_fingerprint_sha256"] == package["structural_model_fingerprint_sha256"]
        and review["approved_calculation_package_fingerprint_sha256"] == package["calculation_package_fingerprint_sha256"]
        and review["approved_drawing_package_fingerprint_sha256"] == package["drawing_package_fingerprint_sha256"]
    )
    if not exact_review_hash_match:
        _add(blockers, "APPROVAL_INVALIDATED_HASH_MISMATCH", "Current package/model/calculation/drawing fingerprints differ from the approved fingerprints")

    if auth["decision"] in {"HOLD", "REJECT"}:
        _add(blockers, "RELEASE_AUTHORIZATION_NOT_RELEASE", f"Release decision is {auth['decision']}")
    if auth["authority_role"] not in policy["allowed_release_authority_roles"]:
        _add(blockers, "RELEASE_AUTHORITY_ROLE_NOT_AUTHORIZED", auth["authority_role"])
    if policy["require_external_signature_validation"] and auth["signature_validation_state"] != "VERIFIED_EXTERNALLY":
        _add(blockers, "RELEASE_AUTHORIZATION_SIGNATURE_NOT_VERIFIED", auth["signature_validation_state"])
    if auth["authorized_package_fingerprint_sha256"] != package["package_fingerprint_sha256"]:
        _add(blockers, "RELEASE_AUTHORIZATION_HASH_MISMATCH", "Release authorization is bound to a different package fingerprint")
    if policy["require_separation_of_duties"] and review["reviewer_id"] == auth["authority_id"]:
        _add(blockers, "SEPARATION_OF_DUTIES_VIOLATION", "Reviewer and release authority must be different persons under current policy")
    if _parse_timestamp(auth["authorization_timestamp"], "release_authorization.authorization_timestamp") < _parse_timestamp(review["review_timestamp"], "human_engineering_review.review_timestamp"):
        _add(blockers, "AUTHORIZATION_PRECEDES_REVIEW", "Release authorization timestamp precedes engineering review")

    structural_scope_ok = "STRUCTURAL_MODEL" in review["approved_scopes"] and "STRUCTURAL_MODEL" in auth["authorized_scopes"]
    construction_scope_ok = "CONSTRUCTION_DOCUMENTS" in review["approved_scopes"] and "CONSTRUCTION" in auth["authorized_scopes"]
    if not structural_scope_ok and auth["decision"] in {"RELEASE_STRUCTURAL_MODEL", "RELEASE_CONSTRUCTION"}:
        _add(blockers, "STRUCTURAL_MODEL_SCOPE_NOT_APPROVED", "Structural model release scope is not approved and authorized")
    if auth["decision"] == "RELEASE_CONSTRUCTION":
        if not construction_scope_ok:
            _add(blockers, "CONSTRUCTION_SCOPE_NOT_APPROVED", "Construction-document release scope is not approved and authorized")
        if policy["require_complete_documents_for_construction_release"] and not package["required_documents_complete"]:
            _add(blockers, "CONSTRUCTION_DOCUMENTS_INCOMPLETE", "Required construction-release documents are incomplete")

    blocker_codes = {b["code"] for b in blockers}
    invalidated = bool({"PACKAGE_FINGERPRINT_INVALID", "APPROVAL_INVALIDATED_HASH_MISMATCH", "RELEASE_AUTHORIZATION_HASH_MISMATCH"} & blocker_codes)
    can_structural = not blockers and auth["decision"] in {"RELEASE_STRUCTURAL_MODEL", "RELEASE_CONSTRUCTION"} and structural_scope_ok
    can_construction = not blockers and auth["decision"] == "RELEASE_CONSTRUCTION" and construction_scope_ok and package["required_documents_complete"]

    structural_state = "RELEASED" if can_structural else "LOCKED"
    construction_state = "RELEASED" if can_construction else "LOCKED"
    if invalidated:
        overall = "APPROVAL_INVALIDATED_REVIEW_REQUIRED"
    elif can_construction:
        overall = "CONSTRUCTION_RELEASED"
    elif can_structural:
        overall = "STRUCTURAL_MODEL_RELEASED"
    elif review["status"] in {"PENDING", "RETURNED_FOR_REVISION", "REJECTED"}:
        overall = "HUMAN_REVIEW_REQUIRED"
    else:
        overall = "RELEASE_LOCKED"

    release_identity_basis = {
        "engine_id": ENGINE_ID,
        "project_id": package["project_id"],
        "package_id": package["package_id"],
        "package_revision": package["package_revision"],
        "package_fingerprint_sha256": package["package_fingerprint_sha256"],
        "reviewer_id": review["reviewer_id"],
        "review_timestamp": review["review_timestamp"],
        "authority_id": auth["authority_id"],
        "authorization_timestamp": auth["authorization_timestamp"],
        "decision": auth["decision"],
    }
    release_id = "PHX-REL-" + _canonical_hash(release_identity_basis)[:16].upper()
    previous_event_hash = str(payload.get("previous_release_event_hash_sha256") or "").strip().lower()
    if previous_event_hash and not SHA256_RE.fullmatch(previous_event_hash):
        raise ValueError("previous_release_event_hash_sha256 must be blank or SHA256 hex")
    ledger_basis = {
        "release_id": release_id,
        "previous_event_hash_sha256": previous_event_hash,
        "overall_release_state": overall,
        "structural_model_release": structural_state,
        "construction_release": construction_state,
        "package_fingerprint_sha256": package["package_fingerprint_sha256"],
        "review_status": review["status"],
        "release_decision": auth["decision"],
        "blocker_codes": sorted(blocker_codes),
    }
    event_hash = _canonical_hash(ledger_basis)

    return {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "project_id": package["project_id"],
        "package_id": package["package_id"],
        "package_revision": package["package_revision"],
        "package_fingerprint_sha256": package["package_fingerprint_sha256"],
        "computed_package_fingerprint_sha256": package["computed_package_fingerprint_sha256"],
        "human_review": {
            "status": review["status"],
            "reviewer_id": review["reviewer_id"],
            "reviewer_name": review["reviewer_name"],
            "reviewer_role": review["reviewer_role"],
            "review_timestamp": review["review_timestamp"],
            "approved_scopes": sorted(review["approved_scopes"]),
            "signature_validation_state": review["signature_validation_state"],
            "blocking_comments_unresolved": unresolved_blocking,
        },
        "release_authorization": {
            "decision": auth["decision"],
            "authority_id": auth["authority_id"],
            "authority_name": auth["authority_name"],
            "authority_role": auth["authority_role"],
            "authorization_timestamp": auth["authorization_timestamp"],
            "authorized_scopes": sorted(auth["authorized_scopes"]),
            "signature_validation_state": auth["signature_validation_state"],
            "release_note": auth["release_note"],
        },
        "approval_binding": {
            "exact_review_hash_match": exact_review_hash_match,
            "approval_invalidated": invalidated,
            "change_requires_new_review": invalidated and policy["invalidate_approval_on_any_fingerprint_change"],
        },
        "release_gates": {
            "qaqc_gate": qaqc_state == EXPECTED_QAQC_STATE and package["qaqc_blockers"] == 0,
            "human_engineering_review_gate": review["status"] in {"APPROVED", "APPROVED_WITH_COMMENTS"} and not unresolved_blocking,
            "fingerprint_binding_gate": exact_review_hash_match and auth["authorized_package_fingerprint_sha256"] == package["package_fingerprint_sha256"],
            "human_release_authorization_gate": auth["decision"] in {"RELEASE_STRUCTURAL_MODEL", "RELEASE_CONSTRUCTION"},
            "separation_of_duties_gate": (not policy["require_separation_of_duties"]) or review["reviewer_id"] != auth["authority_id"],
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "overall_release_state": overall,
        "structural_model_release": structural_state,
        "construction_release": construction_state,
        "release_record": {
            "release_id": release_id,
            "release_record_fingerprint_sha256": _canonical_hash({**release_identity_basis, "overall_release_state": overall}),
            "package_revision": package["package_revision"],
            "package_fingerprint_sha256": package["package_fingerprint_sha256"],
        },
        "release_ledger_entry": {
            "release_id": release_id,
            "previous_event_hash_sha256": previous_event_hash,
            "event_hash_sha256": event_hash,
            "state": overall,
        },
        "digital_twin_writeback": {
            "structural.engineering_release.version": VERSION,
            "structural.engineering_release.package_revision": package["package_revision"],
            "structural.engineering_release.package_fingerprint_sha256": package["package_fingerprint_sha256"],
            "structural.engineering_release.human_review_status": review["status"],
            "structural.engineering_release.release_decision": auth["decision"],
            "structural.engineering_release.structural_model_release": structural_state,
            "structural.engineering_release.construction_release": construction_state,
            "structural.engineering_release.release_id": release_id,
            "structural.engineering_release.event_hash_sha256": event_hash,
        },
        "safety": {
            "automatic_human_approval_fabrication": "DISABLED",
            "automatic_professional_engineering_approval": "DISABLED",
            "release_without_explicit_human_authorization": "DISABLED",
            "approval_reuse_after_package_change": "DISABLED",
        },
    }


def build_demo_payload() -> Dict[str, Any]:
    h = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    package = {
        "project_id": "GENERIC-BUILDING-001",
        "package_id": "STRUCT-PKG-001",
        "package_revision": "P01",
        "structural_model_fingerprint_sha256": h("structural-model-p01"),
        "calculation_package_fingerprint_sha256": h("calculations-p01"),
        "drawing_package_fingerprint_sha256": h("drawings-p01"),
        "engineering_evidence_index_fingerprint_sha256": h("evidence-index-p01"),
        "qaqc_blockers": 0,
        "required_documents_complete": True,
        "verification_registers_complete": True,
        "evidence_reference": "outputs/structural/v8_10_0/engineering_package_qaqc.json",
    }
    package["package_fingerprint_sha256"] = compute_package_fingerprint(package)
    payload = {
        "source_engine": EXPECTED_SOURCE_ENGINE,
        "engineering_package_qaqc_state": EXPECTED_QAQC_STATE,
        "release_policy": {
            "allowed_reviewer_roles": ["COMPETENT_STRUCTURAL_ENGINEER", "LICENSED_STRUCTURAL_ENGINEER", "CHARTERED_STRUCTURAL_ENGINEER"],
            "allowed_release_authority_roles": ["STRUCTURAL_RELEASE_AUTHORITY", "PROJECT_ENGINEER", "PRINCIPAL_STRUCTURAL_ENGINEER"],
            "require_external_signature_validation": True,
            "require_professional_responsibility_acknowledgement": True,
            "require_separation_of_duties": True,
            "require_zero_qaqc_blockers": True,
            "require_complete_verification_registers": True,
            "require_complete_documents_for_construction_release": True,
            "invalidate_approval_on_any_fingerprint_change": True,
            "allow_approved_with_comments": True,
        },
        "engineering_package": package,
        "human_engineering_review": {
            "status": "APPROVED",
            "reviewer_id": "ENG-REV-001",
            "reviewer_name": "Demo Structural Reviewer",
            "reviewer_role": "COMPETENT_STRUCTURAL_ENGINEER",
            "review_timestamp": "2026-08-01T10:00:00+00:00",
            "approved_package_fingerprint_sha256": package["package_fingerprint_sha256"],
            "approved_structural_model_fingerprint_sha256": package["structural_model_fingerprint_sha256"],
            "approved_calculation_package_fingerprint_sha256": package["calculation_package_fingerprint_sha256"],
            "approved_drawing_package_fingerprint_sha256": package["drawing_package_fingerprint_sha256"],
            "approved_scopes": ["STRUCTURAL_MODEL", "CONSTRUCTION_DOCUMENTS"],
            "professional_responsibility_acknowledged": True,
            "identity_evidence_reference": "reviews/ENG-REV-001.identity.json",
            "signature_evidence_reference": "reviews/ENG-REV-001.signature.p7s",
            "signature_validation_state": "VERIFIED_EXTERNALLY",
            "comments": [],
        },
        "release_authorization": {
            "decision": "RELEASE_CONSTRUCTION",
            "authority_id": "REL-AUTH-001",
            "authority_name": "Demo Release Authority",
            "authority_role": "STRUCTURAL_RELEASE_AUTHORITY",
            "authorization_timestamp": "2026-08-01T10:30:00+00:00",
            "authorized_package_fingerprint_sha256": package["package_fingerprint_sha256"],
            "authorized_scopes": ["STRUCTURAL_MODEL", "CONSTRUCTION"],
            "identity_evidence_reference": "release/REL-AUTH-001.identity.json",
            "signature_evidence_reference": "release/REL-AUTH-001.signature.p7s",
            "signature_validation_state": "VERIFIED_EXTERNALLY",
            "release_note": "Demo release after engineering review",
        },
        "previous_release_event_hash_sha256": "",
    }
    return payload


def _self_test() -> Dict[str, Any]:
    payload = build_demo_payload()
    result = evaluate_release(payload)
    assert result["construction_release"] == "RELEASED"
    assert result["structural_model_release"] == "RELEASED"
    assert result["blocker_count"] == 0
    tampered = deepcopy(payload)
    tampered["engineering_package"]["drawing_package_fingerprint_sha256"] = hashlib.sha256(b"changed-drawing").hexdigest()
    tampered_result = evaluate_release(tampered)
    assert tampered_result["construction_release"] == "LOCKED"
    assert tampered_result["approval_binding"]["approval_invalidated"] is True
    return {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "controlled_release_candidate": result["overall_release_state"],
        "human_review_gate": result["release_gates"]["human_engineering_review_gate"],
        "human_release_authorization_gate": result["release_gates"]["human_release_authorization_gate"],
        "exact_fingerprint_binding": result["release_gates"]["fingerprint_binding_gate"],
        "tamper_invalidation": tampered_result["overall_release_state"],
        "automatic_professional_approval": "DISABLED",
        "default_release_without_explicit_evidence": "LOCKED",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(_self_test(), indent=2, sort_keys=True))
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = evaluate_release(payload)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
