from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ENGINE_ID = "PHX-PACKAGE-B-LICENSED-SOURCE-TRACEABILITY-R9.5.2.3"
VERSION = "R9.5.2.3"
PACKAGE_B = "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve(repo_root: Path, rel: str) -> Path:
    p = (Path(repo_root) / rel).resolve()
    root = Path(repo_root).resolve()
    try:
        p.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Source path escapes repository: {rel}") from exc
    return p


def validate_traceability_registry(*, repo_root: Path, registry_path: Path) -> dict[str, Any]:
    registry = _read_json(Path(registry_path))

    if registry.get("project_id") != "PHOENIX-PAT-001":
        raise ValueError("Package B traceability registry project mismatch")
    if not _mapping(registry.get("licensed_use")).get("confirmed"):
        raise ValueError("Licensed use is not explicitly confirmed")
    if not _mapping(registry.get("extraction_review")).get("reviewed"):
        raise ValueError("Source extraction review is not recorded")
    if _mapping(registry.get("extraction_review")).get("professional_structural_review"):
        raise ValueError("Source extraction review must not be promoted to professional structural review")

    bundle = _mapping(registry.get("bundle_source"))
    source_rel = str(bundle.get("source_file") or "").strip()
    expected_sha = str(bundle.get("sha256") or "").strip().lower()
    if not source_rel or len(expected_sha) != 64:
        raise ValueError("Bundle source path/SHA256 missing")
    source_path = _resolve(Path(repo_root), source_rel)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    actual_sha = _sha256(source_path)
    if actual_sha != expected_sha:
        raise ValueError(f"Bundle SHA256 mismatch: expected {expected_sha}, got {actual_sha}")

    raw = list(bundle.get("raw_evidence_files") or [])
    if len(raw) < 4:
        raise ValueError("At least four raw evidence screenshots are required")
    raw_results = []
    for row in raw:
        item = _mapping(row)
        rel = str(item.get("file") or "").strip()
        sha = str(item.get("sha256") or "").strip().lower()
        path = _resolve(Path(repo_root), rel)
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != sha:
            raise ValueError(f"Raw evidence SHA256 mismatch for {rel}")
        raw_results.append({"file": rel, "sha256": actual, "status": "VALIDATED"})

    criteria = _mapping(registry.get("criteria_traceability"))
    required = {
        "SECOND_ORDER_AMPLIFICATION": ("max_amplification_factor", 1.10),
        "GLOBAL_BUCKLING_FACTOR": ("minimum_critical_load_factor", 11.0),
        "STOREY_STABILITY_INDEX": ("max_stability_index", 0.10),
    }
    for check_id, (field, expected_value) in required.items():
        row = _mapping(criteria.get(check_id))
        if row.get("field") != field:
            raise ValueError(f"Traceability field mismatch for {check_id}")
        if float(row.get("value")) != float(expected_value):
            raise ValueError(f"Traceability value mismatch for {check_id}")
        if not str(row.get("clause_reference") or "").strip():
            raise ValueError(f"Clause reference missing for {check_id}")
        if row.get("literal_standard_limit_claim") is not False:
            raise ValueError(f"Literal standard-limit claim must remain false for {check_id}")

    return {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "VALIDATED",
        "bundle_source_file": source_rel,
        "bundle_sha256": actual_sha,
        "raw_evidence": raw_results,
        "criteria_count": 3,
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
        "professional_structural_review": False,
    }


def _source_record(registry: Mapping[str, Any]) -> dict[str, Any]:
    bundle = _mapping(registry.get("bundle_source"))
    identity = _mapping(registry.get("standard_identity"))
    licensed = _mapping(registry.get("licensed_use"))
    review = _mapping(registry.get("extraction_review"))
    return {
        "reference_type": "LICENSED_STANDARD_EXTRACT",
        "reference": identity.get("displayed_title"),
        "source_class": bundle.get("source_class"),
        "source_file": bundle.get("source_file"),
        "local_file": bundle.get("local_file"),
        "file_path": bundle.get("file_path"),
        "repo_relative_path": bundle.get("repo_relative_path"),
        "sha256": bundle.get("sha256"),
        "checksum_sha256": bundle.get("checksum_sha256"),
        "source_sha256": bundle.get("source_sha256"),
        "clause_reference": bundle.get("clause_reference"),
        "clause_references": deepcopy(bundle.get("clause_references") or []),
        "licensed_use_confirmed": bool(bundle.get("licensed_use_confirmed")),
        "licensed_use_confirmation_reference": licensed.get("confirmation_text"),
        "licensed_use_confirmation_date": licensed.get("confirmed_date"),
        "extraction_reviewed": bool(bundle.get("extraction_reviewed")),
        "extraction_review_status": bundle.get("review_status"),
        "extraction_review_scope": review.get("scope"),
        "professional_structural_review": False,
        "legal_status_in_suriname": identity.get("legal_status_in_suriname"),
        "project_use_status": identity.get("project_use_status"),
        "raw_evidence_files": deepcopy(bundle.get("raw_evidence_files") or []),
    }


def _set_criterion(row: dict[str, Any], *, field: str, value: float, trace: Mapping[str, Any]) -> None:
    acceptance = _mapping(row.get("acceptance_criteria"))
    existing = acceptance.get(field)
    if existing not in (None, "") and float(existing) != float(value):
        raise ValueError(f"Existing R9.5 criterion conflict for {field}: {existing} != {value}")
    acceptance[field] = value
    row["acceptance_criteria"] = acceptance

    criteria_traceability = _mapping(row.get("criteria_traceability"))
    criteria_traceability[field] = {
        "source_record_id": trace.get("source_record_id"),
        "clause_reference": trace.get("clause_reference"),
        "traceability_status": "LICENSED_SOURCE_VALIDATED",
        "classification": trace.get("classification"),
        "literal_standard_limit_claim": False,
    }
    row["criteria_traceability"] = criteria_traceability


def apply_package_b_traceability_to_r9_5_required_input_document(
    document: Mapping[str, Any],
    *,
    repo_root: Path,
    registry_path: Path,
) -> dict[str, Any]:
    validation = validate_traceability_registry(repo_root=Path(repo_root), registry_path=Path(registry_path))
    registry = _read_json(Path(registry_path))

    out = deepcopy(dict(document))
    if str(out.get("project_id") or "") != str(registry.get("project_id") or ""):
        return out

    root = _mapping(out.get("r9_5_project_stability_design_basis_decision"))
    if not root:
        return out

    source_record_id = str(registry.get("source_record_id"))
    source_records = _mapping(root.get("source_records"))
    source_records[source_record_id] = _source_record(registry)
    root["source_records"] = source_records

    checks = _mapping(root.get("checks"))
    criteria = _mapping(registry.get("criteria_traceability"))
    for check_id, trace_value in criteria.items():
        row = _mapping(checks.get(check_id))
        if not row:
            continue
        trace = _mapping(trace_value)
        _set_criterion(
            row,
            field=str(trace.get("field")),
            value=float(trace.get("value")),
            trace=trace,
        )
        row["r9_5_2_3_package_b_traceability"] = {
            "status": "LICENSED_SOURCE_VALIDATED",
            "source_record_id": source_record_id,
            "bundle_sha256": validation.get("bundle_sha256"),
            "licensed_use_confirmed": True,
            "extraction_reviewed": True,
            "professional_structural_review": False,
        }
        checks[check_id] = row
    root["checks"] = checks

    root["r9_5_2_3_package_b_traceability"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "PACKAGE_B_TRACEABILITY_COMPLETE",
        "source_record_id": source_record_id,
        "bundle_source_file": validation.get("bundle_source_file"),
        "bundle_sha256": validation.get("bundle_sha256"),
        "criteria_promoted_to_r9_5_input": True,
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
        "professional_structural_review": False,
        "automatic_code_compliance_claim": False,
        "production_release": "LOCKED",
    }
    out["r9_5_project_stability_design_basis_decision"] = root
    return out


def apply_package_b_traceability_to_r9_5_2_result(
    result: Mapping[str, Any],
    *,
    repo_root: Path,
    registry_path: Path,
) -> dict[str, Any]:
    validation = validate_traceability_registry(repo_root=Path(repo_root), registry_path=Path(registry_path))
    registry = _read_json(Path(registry_path))
    out = deepcopy(dict(result))

    if str(out.get("project_id") or "") != str(registry.get("project_id") or ""):
        return out

    intake = _mapping(out.get("evidence_intake"))
    source_record_id = str(registry.get("source_record_id"))
    source_records = _mapping(intake.get("source_records"))
    source_records[source_record_id] = _source_record(registry)
    intake["source_records"] = source_records

    packages = _mapping(intake.get("package_inputs"))
    package_b = _mapping(packages.get(PACKAGE_B))
    inputs = _mapping(package_b.get("inputs"))
    bundle = _mapping(registry.get("bundle_source"))
    inputs.update({
        "source_record_id": source_record_id,
        "source_file": bundle.get("source_file"),
        "sha256": bundle.get("sha256"),
        "clause_reference": bundle.get("clause_reference"),
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
    })
    criteria_inputs = _mapping(inputs.get("criteria"))
    for check_id, trace_value in _mapping(registry.get("criteria_traceability")).items():
        trace = _mapping(trace_value)
        row = _mapping(criteria_inputs.get(check_id))
        row[str(trace.get("field"))] = float(trace.get("value"))
        criteria_inputs[check_id] = row
    inputs["criteria"] = criteria_inputs
    inputs["licensed_source_traceability_validation"] = deepcopy(validation)
    package_b["inputs"] = inputs
    package_b["status"] = "LICENSED_SOURCE_TRACEABILITY_COMPLETE_R9_5_REQUALIFICATION_REQUIRED"
    package_b["validation"] = {
        "qualified": False,
        "project_policy_criteria_approved": True,
        "licensed_source_traceability_complete": True,
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
        "professional_structural_review": False,
        "qualification_message": (
            "Package B licensed source traceability is complete. "
            "R9.5/R9.4/v8.6 remain the qualification gates; professional structural review remains required."
        ),
    }
    packages[PACKAGE_B] = package_b
    intake["package_inputs"] = packages

    metadata = _mapping(intake.get("intake_metadata"))
    metadata["r9_5_2_3_package_b_traceability"] = {
        "status": "COMPLETE",
        "source_record_id": source_record_id,
        "bundle_sha256": validation.get("bundle_sha256"),
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
        "professional_structural_review": False,
        "automatic_code_compliance_claim": False,
        "production_release": "LOCKED",
    }
    intake["intake_metadata"] = metadata
    out["evidence_intake"] = intake

    out["r9_5_2_3"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "PACKAGE_B_LICENSED_SOURCE_TRACEABILITY_COMPLETE",
        "source_record_id": source_record_id,
        "bundle_source_file": validation.get("bundle_source_file"),
        "bundle_sha256": validation.get("bundle_sha256"),
        "criteria_promoted_to_r9_5_input": True,
        "licensed_use_confirmed": True,
        "extraction_reviewed": True,
        "professional_structural_review": False,
        "automatic_code_compliance_claim": False,
        "production_release": "LOCKED",
    }

    blockers = list(out.get("blockers") or [])
    if blockers and isinstance(blockers[0], Mapping):
        blocker = dict(blockers[0])
        blocker["message"] = (
            "Technical stability analysis is complete. Package A project policy is recorded and Package B "
            "licensed source traceability is complete. R9.5/R9.4/v8.6 must requalify the populated criteria. "
            "No automatic code-compliance or professional approval claim is made."
        )
        blocker["r9_5_2_3_package_b_traceability_status"] = "COMPLETE"
        blockers[0] = blocker
        out["blockers"] = blockers

    return out
