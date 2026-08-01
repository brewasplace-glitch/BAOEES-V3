#!/usr/bin/env python3
"""PROJECT PHOENIX v8.12.0
Structural Revision, Change Impact & Issued-for-Construction Package Engine.

This engine controls revisions after v8.11.0 release. It detects engineering
changes by SHA256 fingerprints, propagates impact through structural
dependencies, generates re-analysis/re-verification requirements, manages
superseded-document evidence, and creates an immutable IFC package manifest.

It NEVER fabricates engineering approval. A revision can become IFC only when
an exact v8.11.0 construction-release record exists for the current revision
fingerprint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Set

ENGINE_ID = "PHX-STRUCT-REVISION-CHANGE-IMPACT-IFC-PACKAGE-V8.12.0"
VERSION = "8.12.0"
EXPECTED_SOURCE_ENGINE = "PHX-STRUCT-ENGINEERING-REVIEW-APPROVAL-RELEASE-CONTROL-V8.11.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REVISION_STATES = {"DRAFT", "FOR_REVIEW", "APPROVED", "IFC", "SUPERSEDED", "AS_BUILT"}

COMPONENTS = (
    "architectural_model",
    "structural_model",
    "load_model",
    "analysis_results",
    "member_verification",
    "global_stability",
    "connections",
    "foundation_soil",
    "foundation_design",
    "calculation_package",
    "drawing_package",
    "engineering_evidence_index",
)

DEPENDENCIES = {
    "architectural_model": {
        "structural_model", "load_model", "analysis_results", "member_verification",
        "global_stability", "connections", "foundation_soil", "foundation_design",
        "calculation_package", "drawing_package", "engineering_evidence_index"
    },
    "structural_model": {
        "load_model", "analysis_results", "member_verification", "global_stability",
        "connections", "foundation_soil", "foundation_design",
        "calculation_package", "drawing_package", "engineering_evidence_index"
    },
    "load_model": {
        "analysis_results", "member_verification", "global_stability", "connections",
        "foundation_soil", "foundation_design", "calculation_package",
        "drawing_package", "engineering_evidence_index"
    },
    "analysis_results": {
        "member_verification", "global_stability", "connections", "foundation_soil",
        "foundation_design", "calculation_package", "drawing_package",
        "engineering_evidence_index"
    },
    "member_verification": {"calculation_package", "drawing_package", "engineering_evidence_index"},
    "global_stability": {"calculation_package", "drawing_package", "engineering_evidence_index"},
    "connections": {"calculation_package", "drawing_package", "engineering_evidence_index"},
    "foundation_soil": {"foundation_design", "calculation_package", "drawing_package", "engineering_evidence_index"},
    "foundation_design": {"calculation_package", "drawing_package", "engineering_evidence_index"},
    "calculation_package": {"engineering_evidence_index"},
    "drawing_package": {"engineering_evidence_index"},
    "engineering_evidence_index": set(),
}

SCOPES = {
    "architectural_model": {"ARCHITECTURAL_COORDINATION", "STRUCTURAL_DERIVATION"},
    "structural_model": {"ANALYTICAL_MODEL", "SOLVER_MODEL"},
    "load_model": {"ACTIONS_LOADS", "LOAD_COMBINATIONS"},
    "analysis_results": {"ANALYSIS_RESULTS", "SANITY_EQUILIBRIUM"},
    "member_verification": {"ULS_SLS_MEMBER_VERIFICATION"},
    "global_stability": {"GLOBAL_STABILITY_ROBUSTNESS"},
    "connections": {"CONNECTION_SUPPORT_JOINT_VERIFICATION"},
    "foundation_soil": {"FOUNDATION_SOIL_SUPPORT_VERIFICATION"},
    "foundation_design": {"FOUNDATION_DESIGN_REINFORCEMENT_DETAILING"},
    "calculation_package": {"CALCULATION_PACKAGE_QAQC"},
    "drawing_package": {"DRAWING_PACKAGE_QAQC"},
    "engineering_evidence_index": {"EVIDENCE_TRACEABILITY_QAQC"},
}


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be a non-empty string")
    return text


def _sha(value: Any, label: str) -> str:
    text = _text(value, label).lower()
    if not SHA256_RE.fullmatch(text):
        raise ValueError(f"{label} must be a 64-character SHA256 digest")
    return text


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _component_fingerprints(raw: Mapping[str, Any], label: str) -> Dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be an object")
    return {c: _sha(raw.get(c), f"{label}.{c}") for c in COMPONENTS}


def compute_revision_fingerprint(project_id: str, revision_id: str, components: Mapping[str, str]) -> str:
    return _canonical_hash({
        "project_id": _text(project_id, "project_id"),
        "revision_id": _text(revision_id, "revision_id"),
        "components": {c: _sha(components[c], f"components.{c}") for c in COMPONENTS},
    })


def transitive_affected(changed: Iterable[str]) -> Set[str]:
    affected = set(changed)
    frontier = list(changed)
    while frontier:
        current = frontier.pop()
        for downstream in DEPENDENCIES.get(current, set()):
            if downstream not in affected:
                affected.add(downstream)
                frontier.append(downstream)
    return affected


def required_scopes(affected: Iterable[str]) -> List[str]:
    affected = list(affected)
    scopes: Set[str] = set()
    for component in affected:
        scopes.update(SCOPES.get(component, set()))
    if affected:
        scopes.update({"ENGINEERING_PACKAGE_QAQC", "HUMAN_ENGINEERING_REVIEW", "RELEASE_AUTHORIZATION"})
    return sorted(scopes)


def compare_revisions(baseline: Mapping[str, str], current: Mapping[str, str]) -> Dict[str, Any]:
    changed = sorted(c for c in COMPONENTS if baseline[c] != current[c])
    affected = sorted(transitive_affected(changed))
    return {
        "engineering_change_detected": bool(changed),
        "changed_components": changed,
        "affected_components": affected,
        "required_validation_scopes": required_scopes(affected),
    }


def parse_documents(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("documents must be a non-empty list")
    result = []
    seen = set()
    for i, item in enumerate(raw, 1):
        if not isinstance(item, Mapping):
            raise ValueError(f"documents[{i}] must be an object")
        doc_id = _text(item.get("document_id"), f"documents[{i}].document_id")
        if doc_id in seen:
            raise ValueError(f"duplicate document_id: {doc_id}")
        seen.add(doc_id)
        result.append({
            "document_id": doc_id,
            "title": _text(item.get("title"), f"documents[{i}].title"),
            "revision": _text(item.get("revision"), f"documents[{i}].revision"),
            "sha256": _sha(item.get("sha256"), f"documents[{i}].sha256"),
            "required_for_ifc": _bool(item.get("required_for_ifc"), f"documents[{i}].required_for_ifc"),
            "status": _text(item.get("status"), f"documents[{i}].status").upper(),
        })
    return result


def parse_release_record(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {
            "present": False,
            "engine_id": "",
            "package_fingerprint_sha256": "",
            "structural_model_release": "LOCKED",
            "construction_release": "LOCKED",
            "release_id": "",
        }
    if not isinstance(raw, Mapping):
        raise ValueError("current_v8_11_release_record must be object or null")
    return {
        "present": True,
        "engine_id": _text(raw.get("engine_id"), "release_record.engine_id"),
        "package_fingerprint_sha256": _sha(raw.get("package_fingerprint_sha256"), "release_record.package_fingerprint_sha256"),
        "structural_model_release": _text(raw.get("structural_model_release"), "release_record.structural_model_release").upper(),
        "construction_release": _text(raw.get("construction_release"), "release_record.construction_release").upper(),
        "release_id": _text(raw.get("release_id"), "release_record.release_id"),
    }


def evaluate(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if _text(payload.get("source_engine"), "source_engine") != EXPECTED_SOURCE_ENGINE:
        raise ValueError("v8.11.0 source engine required")

    project_id = _text(payload.get("project_id"), "project_id")

    policy_raw = payload.get("revision_policy")
    if not isinstance(policy_raw, Mapping):
        raise ValueError("revision_policy must be an object")
    policy = {
        "require_release_record_for_ifc": bool(policy_raw.get("require_release_record_for_ifc", True)),
        "invalidate_release_on_any_engineering_change": bool(policy_raw.get("invalidate_release_on_any_engineering_change", True)),
        "require_all_ifc_documents_complete": bool(policy_raw.get("require_all_ifc_documents_complete", True)),
    }

    baseline_raw = payload.get("baseline_release")
    if not isinstance(baseline_raw, Mapping):
        raise ValueError("baseline_release must be an object")
    baseline_revision = _text(baseline_raw.get("revision_id"), "baseline_release.revision_id")
    baseline_state = _text(baseline_raw.get("revision_state"), "baseline_release.revision_state").upper()
    if baseline_state not in REVISION_STATES:
        raise ValueError("unsupported baseline revision_state")
    baseline_components = _component_fingerprints(
        baseline_raw.get("component_fingerprints"), "baseline_release.component_fingerprints"
    )
    baseline_declared = _sha(
        baseline_raw.get("revision_fingerprint_sha256"), "baseline_release.revision_fingerprint_sha256"
    )
    baseline_computed = compute_revision_fingerprint(project_id, baseline_revision, baseline_components)

    current_raw = payload.get("current_revision")
    if not isinstance(current_raw, Mapping):
        raise ValueError("current_revision must be an object")
    current_revision = _text(current_raw.get("revision_id"), "current_revision.revision_id")
    requested_state = _text(current_raw.get("requested_state"), "current_revision.requested_state").upper()
    if requested_state not in REVISION_STATES:
        raise ValueError("unsupported current requested_state")
    current_components = _component_fingerprints(
        current_raw.get("component_fingerprints"), "current_revision.component_fingerprints"
    )
    current_declared = _sha(
        current_raw.get("revision_fingerprint_sha256"), "current_revision.revision_fingerprint_sha256"
    )
    current_computed = compute_revision_fingerprint(project_id, current_revision, current_components)

    change = compare_revisions(baseline_components, current_components)
    documents = parse_documents(payload.get("documents"))
    release = parse_release_record(payload.get("current_v8_11_release_record"))

    blockers: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    def block(code: str, message: str) -> None:
        blockers.append({"code": code, "message": message})

    def warn(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    if baseline_declared != baseline_computed:
        block("BASELINE_FINGERPRINT_INVALID", "Baseline revision fingerprint does not match component fingerprints")

    if current_declared != current_computed:
        block("CURRENT_FINGERPRINT_INVALID", "Current revision fingerprint does not match component fingerprints")

    if baseline_revision == current_revision and change["engineering_change_detected"]:
        block("REVISION_ID_NOT_INCREMENTED", "Engineering changed but revision_id was not incremented")

    if baseline_revision != current_revision and not change["engineering_change_detected"]:
        warn("REVISION_WITHOUT_ENGINEERING_CHANGE", "Revision changed while engineering component fingerprints are unchanged")

    required_ifc = [d for d in documents if d["required_for_ifc"]]
    incomplete = [d["document_id"] for d in required_ifc if d["status"] not in {"APPROVED", "IFC"}]
    if policy["require_all_ifc_documents_complete"] and incomplete:
        block("IFC_DOCUMENTS_INCOMPLETE", "Required IFC documents are incomplete: " + ", ".join(incomplete))

    exact_release_match = (
        release["present"]
        and release["engine_id"] == EXPECTED_SOURCE_ENGINE
        and release["package_fingerprint_sha256"] == current_computed
    )

    if release["present"] and release["engine_id"] != EXPECTED_SOURCE_ENGINE:
        block("INVALID_RELEASE_RECORD_ENGINE", "Release record was not produced by v8.11.0")

    if release["present"] and release["package_fingerprint_sha256"] != current_computed:
        block("RELEASE_RECORD_FINGERPRINT_MISMATCH", "Release record does not match exact current revision fingerprint")

    if requested_state == "IFC" and policy["require_release_record_for_ifc"]:
        if not exact_release_match:
            block("EXACT_V8_11_RELEASE_RECORD_REQUIRED", "IFC requires exact v8.11.0 release record")
        elif release["construction_release"] != "RELEASED":
            block("CONSTRUCTION_RELEASE_NOT_RELEASED", "v8.11 construction release is not RELEASED")

    if requested_state in {"APPROVED", "IFC"} and change["engineering_change_detected"] and not exact_release_match:
        block("CHANGED_REVISION_REQUIRES_REVIEW_AND_RELEASE", "Changed revision requires fresh v8.10 QA/QC and v8.11 human review/release")

    if requested_state == "AS_BUILT" and release["construction_release"] != "RELEASED":
        block("AS_BUILT_WITHOUT_RELEASED_CONSTRUCTION_BASE", "AS_BUILT requires a released construction baseline")

    prior_release_invalidated_for_current_revision = (
        policy["invalidate_release_on_any_engineering_change"]
        and change["engineering_change_detected"]
        and not exact_release_match
    )

    can_issue_ifc = (
        requested_state == "IFC"
        and not blockers
        and exact_release_match
        and release["construction_release"] == "RELEASED"
    )

    effective_state = requested_state
    if change["engineering_change_detected"] and not exact_release_match:
        effective_state = "FOR_REVIEW"
    elif requested_state == "IFC" and not can_issue_ifc:
        effective_state = "APPROVED"

    baseline_control_state = "CURRENT_RELEASED_BASELINE"
    if can_issue_ifc and baseline_revision != current_revision:
        baseline_control_state = "SUPERSEDED_BY_NEW_IFC_REVISION"

    change_register = [
        {
            "component": component,
            "baseline_sha256": baseline_components[component],
            "current_sha256": current_components[component],
            "affected_downstream": sorted(transitive_affected([component]) - {component}),
        }
        for component in change["changed_components"]
    ]

    document_register = []
    for d in documents:
        item = dict(d)
        item["superseded_by_revision"] = (
            current_revision
            if can_issue_ifc and d["revision"] == baseline_revision and baseline_revision != current_revision
            else None
        )
        document_register.append(item)

    transmittal = [
        {
            "document_id": d["document_id"],
            "title": d["title"],
            "revision": d["revision"],
            "sha256": d["sha256"],
            "status": d["status"],
        }
        for d in documents
        if (not d["required_for_ifc"]) or d["status"] in {"APPROVED", "IFC"}
    ]

    manifest_basis = {
        "project_id": project_id,
        "revision_id": current_revision,
        "revision_fingerprint_sha256": current_computed,
        "release_id": release["release_id"] if exact_release_match else None,
        "documents": sorted(transmittal, key=lambda x: x["document_id"]),
    }
    manifest_sha = _canonical_hash(manifest_basis)

    status = (
        "IFC_PACKAGE_ISSUED" if can_issue_ifc
        else "REVISION_REVIEW_REQUIRED" if change["engineering_change_detected"]
        else "REVISION_CONTROLLED"
    )

    return {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": status,
        "baseline": {
            "revision_id": baseline_revision,
            "declared_fingerprint_sha256": baseline_declared,
            "computed_fingerprint_sha256": baseline_computed,
            "control_state": baseline_control_state,
        },
        "current_revision": {
            "revision_id": current_revision,
            "requested_state": requested_state,
            "effective_state": effective_state,
            "declared_fingerprint_sha256": current_declared,
            "computed_fingerprint_sha256": current_computed,
        },
        "change_impact": change,
        "change_register": change_register,
        "required_rework": {
            "components": change["affected_components"] if change["engineering_change_detected"] else [],
            "validation_scopes": change["required_validation_scopes"],
            "fresh_v8_10_qaqc_required": bool(change["engineering_change_detected"] and not exact_release_match),
            "fresh_v8_11_review_release_required": bool(change["engineering_change_detected"] and not exact_release_match),
        },
        "release_binding": {
            "release_record_present": release["present"],
            "exact_release_match": exact_release_match,
            "release_id": release["release_id"] or None,
            "structural_model_release": release["structural_model_release"],
            "construction_release": release["construction_release"],
            "prior_release_invalidated_for_current_revision": prior_release_invalidated_for_current_revision,
        },
        "document_control": {
            "documents": document_register,
            "required_ifc_documents": [d["document_id"] for d in required_ifc],
            "incomplete_ifc_documents": incomplete,
        },
        "ifc_package": {
            "can_issue_ifc": can_issue_ifc,
            "transmittal_index": transmittal if can_issue_ifc else [],
            "immutable_manifest_sha256": manifest_sha if can_issue_ifc else None,
            "manifest_basis": manifest_basis if can_issue_ifc else None,
        },
        "blockers": blockers,
        "warnings": warnings,
        "digital_twin_writeback": {
            "structural.revision_control.current_revision": current_revision,
            "structural.revision_control.effective_state": effective_state,
            "structural.revision_control.changed_components": change["changed_components"],
            "structural.revision_control.affected_components": change["affected_components"],
            "structural.revision_control.current_revision_fingerprint_sha256": current_computed,
            "structural.revision_control.ifc_package_state": "ISSUED" if can_issue_ifc else "LOCKED",
            "structural.revision_control.ifc_manifest_sha256": manifest_sha if can_issue_ifc else None,
            "structural.revision_control.release_id": release["release_id"] if exact_release_match else None,
        },
        "safety": {
            "automatic_professional_engineering_approval": "DISABLED",
            "automatic_human_review_fabrication": "DISABLED",
            "automatic_release_without_v8_11_authorization": "DISABLED",
            "changed_revision_auto_ifc": "DISABLED",
        },
    }


def self_test_payload() -> Dict[str, Any]:
    def h(seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    baseline_components = {c: h("baseline:" + c) for c in COMPONENTS}
    current_components = dict(baseline_components)
    for c in (
        "structural_model", "analysis_results", "member_verification",
        "calculation_package", "drawing_package", "engineering_evidence_index"
    ):
        current_components[c] = h("current:" + c)

    project_id = "PHX-GENERIC-BUILDING"
    baseline_revision = "C01"
    current_revision = "C02"
    baseline_fp = compute_revision_fingerprint(project_id, baseline_revision, baseline_components)
    current_fp = compute_revision_fingerprint(project_id, current_revision, current_components)

    return {
        "source_engine": EXPECTED_SOURCE_ENGINE,
        "project_id": project_id,
        "revision_policy": {
            "require_release_record_for_ifc": True,
            "invalidate_release_on_any_engineering_change": True,
            "require_all_ifc_documents_complete": True,
        },
        "baseline_release": {
            "revision_id": baseline_revision,
            "revision_state": "IFC",
            "component_fingerprints": baseline_components,
            "revision_fingerprint_sha256": baseline_fp,
        },
        "current_revision": {
            "revision_id": current_revision,
            "requested_state": "IFC",
            "component_fingerprints": current_components,
            "revision_fingerprint_sha256": current_fp,
        },
        "current_v8_11_release_record": {
            "engine_id": EXPECTED_SOURCE_ENGINE,
            "package_fingerprint_sha256": current_fp,
            "structural_model_release": "RELEASED",
            "construction_release": "RELEASED",
            "release_id": "PHX-REL-C02-0001",
        },
        "documents": [
            {
                "document_id": "STR-CALC-001",
                "title": "Structural Calculation Package",
                "revision": current_revision,
                "sha256": h("calc-document"),
                "required_for_ifc": True,
                "status": "APPROVED",
            },
            {
                "document_id": "STR-DWG-001",
                "title": "Structural Drawing Package",
                "revision": current_revision,
                "sha256": h("drawing-document"),
                "required_for_ifc": True,
                "status": "IFC",
            },
            {
                "document_id": "STR-QAQC-001",
                "title": "Engineering QA/QC Evidence Index",
                "revision": current_revision,
                "sha256": h("qaqc-document"),
                "required_for_ifc": True,
                "status": "APPROVED",
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        result = evaluate(self_test_payload())
        if result["status"] != "IFC_PACKAGE_ISSUED":
            raise SystemExit("self-test failed: IFC package not issued")
        if result["blockers"]:
            raise SystemExit("self-test failed: unexpected blockers")
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if not args.input:
        parser.error("--input is required unless --self-test is used")

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(data)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
