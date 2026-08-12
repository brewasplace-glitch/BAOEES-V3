from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .project_stability_design_basis_decision_r9_5 import (
    build_project_stability_design_basis_decision,
)

ENGINE_ID = "PHX-PACKAGE-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE-R9.5.2.5"
VERSION = "R9.5.2.5"
PACKAGE_ID = "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"
CHECK_TYPE = "ALTERNATE_LOAD_PATH_EVIDENCE"
INPUT_REL = Path("inputs") / "structural" / "package_e_alternate_path_independent_evidence_REQUIRED.json"
GLOBAL_INPUT_REL = Path("inputs") / "structural" / "global_stability_engineering_input_REQUIRED.json"
TEMPLATE_REL = Path("templates") / "structural" / "package_e_alternate_path_independent_evidence_REQUIRED.json"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(value)
    tmp = path.with_name(path.name + ".r9_5_2_5.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    readback = _read_json(path)
    if readback != dict(value):
        raise ValueError("R9.5.2.5 atomic JSON readback mismatch")
    return readback, hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_file(repository_root: Path, value: Any) -> Path | None:
    raw = _text(value).replace("\\", "/")
    if not raw:
        return None
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    root = Path(repository_root).resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def build_required_input_template(*, project_id: str, repository_root: Path) -> dict[str, Any]:
    value = _read_json(Path(repository_root) / TEMPLATE_REL)
    value["project_id"] = project_id
    return value


def _validate_independent_evidence(
    *,
    document: Mapping[str, Any],
    project_id: str,
    repository_root: Path,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    missing: list[str] = []
    errors: list[str] = []

    doc_project = _text(document.get("project_id"))
    if doc_project and doc_project != project_id:
        errors.append("project_id_mismatch")
    if _text(document.get("package_id")) != PACKAGE_ID:
        errors.append("package_id_mismatch")
    if _text(document.get("check_type")) != CHECK_TYPE:
        errors.append("check_type_mismatch")

    decision = _mapping(document.get("decision"))
    applicability = _text(decision.get("applicability"))
    if applicability not in set(policy.get("allowed_applicability") or []):
        missing.append("explicit_applicability_decision")

    if applicability == "NOT_APPLICABLE":
        missing.append("professional_v8_6_scope_waiver_or_policy_revision")

    evidence_trace: dict[str, Any] = {
        "resolved_file": None,
        "expected_sha256": None,
        "actual_sha256": None,
        "sha256_validated": False,
    }

    if applicability == "APPLICABLE":
        if decision.get("methodology_accepted") is not True:
            missing.append("methodology_accepted")
        if not _text(decision.get("methodology_acceptance_reference")):
            missing.append("methodology_acceptance_reference")

        primary_id = _text(decision.get("primary_source_record_id"))
        source_records = _mapping(document.get("source_records"))
        primary = _mapping(source_records.get(primary_id))
        if not primary_id:
            missing.append("primary_source_record_id")
        elif not primary:
            missing.append("primary_source_record")
        else:
            if _text(primary.get("reference_type")) not in set(
                policy.get("allowed_r9_5_source_record_types") or []
            ):
                missing.append("allowed_primary_source_reference_type")
            if not _text(primary.get("reference")):
                missing.append("primary_source_reference")

        criteria = _mapping(decision.get("acceptance_criteria"))
        ratio = _number(criteria.get("minimum_residual_capacity_proxy_ratio"))
        if ratio is None or ratio <= 0:
            missing.append("minimum_residual_capacity_proxy_ratio")

        trace = _mapping(
            _mapping(decision.get("criteria_traceability")).get(
                "minimum_residual_capacity_proxy_ratio"
            )
        )
        if not _text(trace.get("source_record_id")):
            missing.append("minimum_residual_capacity_proxy_ratio_source_record_id")
        if not _text(trace.get("clause_reference")):
            missing.append("minimum_residual_capacity_proxy_ratio_clause_reference")

        if not _text(decision.get("independent_engineering_evidence_reference")):
            missing.append("independent_engineering_evidence_reference")
        if _text(decision.get("independent_review_status")) != _text(
            policy.get("required_independent_review_status")
        ):
            missing.append("independent_review_status_REVIEWED")
        if not _text(decision.get("independent_review_reference")):
            missing.append("independent_review_reference")
        if decision.get("alternate_path_verified") is not True:
            missing.append("independently_verified_alternate_path")

        evidence_path = _repo_file(
            repository_root,
            decision.get("independent_engineering_evidence_file"),
        )
        expected_sha = _text(
            decision.get("independent_engineering_evidence_sha256")
        ).lower()
        actual_sha = None
        if evidence_path is None:
            missing.append("alternate_path_repository_relative_source_file_required")
        elif not evidence_path.is_file():
            missing.append("alternate_path_source_file_missing")
        elif len(expected_sha) != 64 or any(
            c not in "0123456789abcdef" for c in expected_sha
        ):
            missing.append("alternate_path_valid_sha256_required")
        else:
            actual_sha = _sha256(evidence_path)
            if actual_sha != expected_sha:
                errors.append("alternate_path_source_sha256_mismatch")

        attestation = _mapping(document.get("independence_attestation"))
        if _text(attestation.get("evidence_origin")) not in set(
            policy.get("required_evidence_origin") or []
        ):
            missing.append("independent_evidence_origin")
        if attestation.get("phoenix_generated") is not False:
            missing.append("phoenix_generated_must_be_false")
        if attestation.get("independent_from_phoenix_analysis") is not True:
            missing.append("independent_from_phoenix_analysis")
        if not _text(attestation.get("reviewer_or_organization")):
            missing.append("reviewer_or_organization")
        if not _text(attestation.get("attestation_reference")):
            missing.append("attestation_reference")

        evidence_trace = {
            "resolved_file": str(evidence_path) if evidence_path is not None else None,
            "expected_sha256": expected_sha or None,
            "actual_sha256": actual_sha,
            "sha256_validated": bool(
                evidence_path is not None
                and evidence_path.is_file()
                and actual_sha
                and actual_sha == expected_sha
            ),
            "evidence_origin": attestation.get("evidence_origin"),
            "phoenix_generated": attestation.get("phoenix_generated"),
            "independent_from_phoenix_analysis": attestation.get(
                "independent_from_phoenix_analysis"
            ),
        }

    return {
        "status": "VALIDATED" if not missing and not errors else "INCOMPLETE",
        "missing_requirements": sorted(set(missing)),
        "errors": sorted(set(errors)),
        "evidence_trace": evidence_trace,
    }


def _merge_into_r9_5_input(
    *,
    global_input: Mapping[str, Any],
    package_e_input: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    if validation.get("status") != "VALIDATED":
        raise ValueError("Package E evidence must validate before R9.5 merge")

    out = deepcopy(dict(global_input))
    root = _mapping(out.get("r9_5_project_stability_design_basis_decision"))
    if not root:
        raise ValueError("R9.5 decision input section missing")
    checks = _mapping(root.get("checks"))
    row = _mapping(checks.get(CHECK_TYPE))
    if not row:
        raise ValueError("ALTERNATE_LOAD_PATH_EVIDENCE R9.5 check missing")

    decision = _mapping(package_e_input.get("decision"))
    for field in (
        "applicability",
        "methodology_accepted",
        "methodology_acceptance_reference",
        "primary_source_record_id",
        "supporting_source_record_ids",
        "acceptance_criteria",
        "criteria_traceability",
        "evidence_reference",
        "alternate_path_verified",
        "independent_engineering_evidence_reference",
        "independent_engineering_evidence_file",
        "independent_engineering_evidence_sha256",
        "independent_review_status",
        "independent_review_reference",
    ):
        if field in decision:
            row[field] = deepcopy(decision[field])

    row["r9_5_2_5_package_e_validation"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "VALIDATED",
        "independent_evidence_sha256_validated": True,
        "phoenix_generated_independent_evidence": False,
        "professional_structural_review_required": True,
    }
    checks[CHECK_TYPE] = row
    root["checks"] = checks

    records = _mapping(root.get("source_records"))
    for source_id, source in _mapping(package_e_input.get("source_records")).items():
        candidate = _mapping(source)
        if not candidate or not _text(candidate.get("reference_type")) or not _text(candidate.get("reference")):
            continue
        existing = _mapping(records.get(source_id))
        if existing and existing != candidate:
            raise ValueError(f"Conflicting source record: {source_id}")
        records[str(source_id)] = deepcopy(candidate)
    root["source_records"] = records
    root["r9_5_2_5_package_e"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "INDEPENDENT_EVIDENCE_VALIDATED_FOR_R9_5_REQUALIFICATION",
        "independence_attestation": deepcopy(
            _mapping(package_e_input.get("independence_attestation"))
        ),
    }
    out["r9_5_project_stability_design_basis_decision"] = root
    return out


def _update_r9_5_2_package_e(
    *,
    r952: Mapping[str, Any],
    package_e_input: Mapping[str, Any],
    qualified: bool,
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    out = deepcopy(dict(r952))
    intake = _mapping(out.get("evidence_intake"))
    packages = _mapping(intake.get("package_inputs"))
    package = _mapping(packages.get(PACKAGE_ID))
    if not package:
        return out
    if qualified:
        decision = _mapping(package_e_input.get("decision"))
        package["status"] = "INDEPENDENT_EVIDENCE_COMPLETE_R9_5_QUALIFIED"
        package["inputs"] = {
            "independent_engineering_evidence_reference": decision.get(
                "independent_engineering_evidence_reference"
            ),
            "independent_engineering_evidence_file": decision.get(
                "independent_engineering_evidence_file"
            ),
            "independent_engineering_evidence_sha256": decision.get(
                "independent_engineering_evidence_sha256"
            ),
            "independent_review_status": decision.get("independent_review_status"),
            "independent_review_reference": decision.get(
                "independent_review_reference"
            ),
            "minimum_residual_capacity_proxy_ratio": _mapping(
                decision.get("acceptance_criteria")
            ).get("minimum_residual_capacity_proxy_ratio"),
        }
        package["validation"] = {
            "qualified": True,
            "independent_evidence_complete": True,
            "sha256_validated": _mapping(
                validation.get("evidence_trace")
            ).get("sha256_validated") is True,
            "independent_review_status": decision.get("independent_review_status"),
            "professional_structural_review": False,
        }
    packages[PACKAGE_ID] = package
    intake["package_inputs"] = packages
    out["evidence_intake"] = intake
    return out


def render_package_e_dossier_markdown(result: Mapping[str, Any]) -> str:
    summary = _mapping(result.get("summary"))
    lines = [
        "# PHOENIX R9.5.2.5 — Package E Alternate-Path Independent Evidence",
        "",
        f"- Project: `{result.get('project_id')}`",
        f"- Status: `{result.get('status')}`",
        f"- R9.5 qualified checks: `{summary.get('decision_qualified_check_count')}`",
        f"- R9.5 unresolved checks: `{summary.get('unresolved_decision_check_count')}`",
        f"- Technical analysis required: `{summary.get('technical_analysis_required_count')}`",
        f"- External independent evidence required: `{summary.get('external_independent_evidence_required_count')}`",
        "",
        "## Safety classification",
        "",
        "- R9.3 alternate-path result remains **INTERNAL SCREENING ONLY**.",
        "- It is not promoted to redistributed member-removal analysis.",
        "- Phoenix-generated evidence cannot satisfy the independence requirement.",
        "- Independent review and professional review are never claimed automatically.",
        "- Production / for-construction release remains **LOCKED**.",
        "",
    ]
    blockers = result.get("blockers") if isinstance(result.get("blockers"), list) else []
    if blockers:
        lines += ["## Current blocker", ""]
        for blocker in blockers:
            lines.append(f"- `{blocker.get('reason')}` — {blocker.get('message')}")
            for item in blocker.get("missing_requirements") or []:
                lines.append(f"  - `{item}`")
        lines.append("")
    return "\n".join(lines)


def build_package_e_alternate_path_independent_evidence(
    *,
    project_id: str,
    workspace: Path,
    repository_root: Path,
    r93_qualification: Mapping[str, Any],
    r94_initial: Mapping[str, Any],
    r9524_result: Mapping[str, Any],
    r952_result: Mapping[str, Any],
    r95_policy_path: Path,
    package_e_policy_path: Path,
    suriname_rule_registry_path: Path,
    suriname_source_registry_path: Path,
    r94_policy_path: Path,
    r94_public_source_registry_path: Path,
) -> dict[str, Any]:
    workspace = Path(workspace)
    repository_root = Path(repository_root)
    package_e_input_path = workspace / INPUT_REL
    global_input_path = workspace / GLOBAL_INPUT_REL
    policy = _read_json(Path(package_e_policy_path))

    safety = dict(policy.get("safety") or {})
    if not package_e_input_path.is_file():
        required = build_required_input_template(
            project_id=project_id,
            repository_root=repository_root,
        )
        _, template_sha = _atomic_write_json(package_e_input_path, required)
        blocker = {
            "reason": "R9_5_2_5_PACKAGE_E_INDEPENDENT_EVIDENCE_REQUIRED",
            "message": (
                "Package E evidence intake is ready. Existing R9.3 alternate-path screening "
                "is internal screening only and cannot be promoted to independent redistributed "
                "member-removal evidence. Supply actual independent engineering evidence, its "
                "SHA-256, a traceable acceptance criterion, and an independent review reference."
            ),
            "required_input_file": str(package_e_input_path),
            "missing_requirements": [
                "explicit_applicability_decision",
                "methodology_accepted",
                "primary_source_record_id",
                "minimum_residual_capacity_proxy_ratio",
                "independent_engineering_evidence_reference",
                "alternate_path_repository_relative_source_file_required",
                "alternate_path_valid_sha256_required",
                "independent_review_status_REVIEWED",
                "independent_review_reference",
                "independently_verified_alternate_path",
                "independence_attestation",
            ],
            "technical_analysis_required_count": 0,
            "external_independent_evidence_required_count": 1,
        }
        result = {
            "schema_version": "phoenix.r9-5-2-5-package-e-independent-evidence/1.0",
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "BLOCKED",
            "package_id": PACKAGE_ID,
            "input_template_created": True,
            "input_template_sha256": template_sha,
            "input_path": str(package_e_input_path),
            "r9_3_existing_screening": {
                "available": CHECK_TYPE in set(
                    r93_qualification.get("technical_evidence_available_for") or []
                ),
                "classification": "INTERNAL_SCREENING_ONLY",
                "sufficient_as_independent_evidence": False,
            },
            "r9_5_requalified": None,
            "r9_5_2_requalified": dict(r952_result),
            "resolved_package_ids": list(r9524_result.get("resolved_package_ids") or []),
            "unresolved_package_ids": list(r9524_result.get("unresolved_package_ids") or []),
            "blockers": [blocker],
            "summary": {
                "decision_qualified_check_count": _mapping(
                    r9524_result.get("summary")
                ).get("decision_qualified_check_count", 5),
                "unresolved_decision_check_count": _mapping(
                    r9524_result.get("summary")
                ).get("unresolved_decision_check_count", 4),
                "package_e_independent_evidence_complete": False,
                "technical_analysis_required_count": 0,
                "external_independent_evidence_required_count": 1,
            },
            "safety": safety,
        }
        result["dossier_markdown"] = render_package_e_dossier_markdown(result)
        return result

    package_e_input = _read_json(package_e_input_path)
    validation = _validate_independent_evidence(
        document=package_e_input,
        project_id=project_id,
        repository_root=repository_root,
        policy=policy,
    )
    if validation.get("status") != "VALIDATED":
        blocker = {
            "reason": "R9_5_2_5_PACKAGE_E_INDEPENDENT_EVIDENCE_INCOMPLETE",
            "message": (
                "Package E input exists but is not independently evidence-complete. Phoenix "
                "will not infer review, verification, independence, or a numeric residual-capacity criterion."
            ),
            "required_input_file": str(package_e_input_path),
            "missing_requirements": validation.get("missing_requirements") or [],
            "errors": validation.get("errors") or [],
            "technical_analysis_required_count": 0,
            "external_independent_evidence_required_count": 1,
        }
        result = {
            "schema_version": "phoenix.r9-5-2-5-package-e-independent-evidence/1.0",
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "BLOCKED",
            "package_id": PACKAGE_ID,
            "input_path": str(package_e_input_path),
            "validation": validation,
            "r9_5_requalified": None,
            "r9_5_2_requalified": dict(r952_result),
            "resolved_package_ids": list(r9524_result.get("resolved_package_ids") or []),
            "unresolved_package_ids": list(r9524_result.get("unresolved_package_ids") or []),
            "blockers": [blocker],
            "summary": {
                "decision_qualified_check_count": _mapping(
                    r9524_result.get("summary")
                ).get("decision_qualified_check_count", 5),
                "unresolved_decision_check_count": _mapping(
                    r9524_result.get("summary")
                ).get("unresolved_decision_check_count", 4),
                "package_e_independent_evidence_complete": False,
                "technical_analysis_required_count": 0,
                "external_independent_evidence_required_count": 1,
            },
            "safety": safety,
        }
        result["dossier_markdown"] = render_package_e_dossier_markdown(result)
        return result

    if not global_input_path.is_file():
        raise FileNotFoundError(global_input_path)

    global_input = _read_json(global_input_path)
    merged = _merge_into_r9_5_input(
        global_input=global_input,
        package_e_input=package_e_input,
        validation=validation,
    )
    readback, runtime_sha = _atomic_write_json(global_input_path, merged)

    r95 = build_project_stability_design_basis_decision(
        project_id=project_id,
        r93_qualification=r93_qualification,
        r94_initial=r94_initial,
        candidates=[(GLOBAL_INPUT_REL.as_posix(), readback)],
        policy_path=Path(r95_policy_path),
        suriname_rule_registry_path=Path(suriname_rule_registry_path),
        suriname_source_registry_path=Path(suriname_source_registry_path),
        r94_policy_path=Path(r94_policy_path),
        r94_public_source_registry_path=Path(r94_public_source_registry_path),
        repository_root=repository_root,
    )

    register = _mapping(r95.get("decision_register"))
    e_row = _mapping(register.get(CHECK_TYPE))
    e_qualified = (
        e_row.get("state") == "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
    )
    r952 = _update_r9_5_2_package_e(
        r952=r952_result,
        package_e_input=package_e_input,
        qualified=e_qualified,
        validation=validation,
    )

    qualified = sorted(
        check_id
        for check_id, row_value in register.items()
        if _mapping(row_value).get("state")
        == "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
    )
    unresolved = sorted(
        check_id
        for check_id, row_value in register.items()
        if _mapping(row_value).get("state")
        != "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
    )

    resolved_packages = list(r9524_result.get("resolved_package_ids") or [])
    unresolved_packages = list(r9524_result.get("unresolved_package_ids") or [])
    if e_qualified:
        if PACKAGE_ID not in resolved_packages:
            resolved_packages.append(PACKAGE_ID)
        unresolved_packages = [x for x in unresolved_packages if x != PACKAGE_ID]

    if e_qualified and unresolved:
        blocker = {
            "reason": "R9_5_2_5_PACKAGE_E_COMPLETE_REMAINING_C_D_REQUIRED",
            "message": (
                "Package E independent evidence is complete and ALTERNATE_LOAD_PATH_EVIDENCE "
                "is R9.5-qualified. Remaining structural decision inputs are the postponed "
                "seismic/weak-storey Packages C and D."
            ),
            "qualified_check_types": qualified,
            "unresolved_check_types": unresolved,
            "resolved_package_ids": sorted(set(resolved_packages)),
            "unresolved_package_ids": sorted(set(unresolved_packages)),
            "technical_analysis_required_count": 0,
            "external_independent_evidence_required_count": 0,
        }
    elif not e_qualified:
        blocker = {
            "reason": "R9_5_2_5_PACKAGE_E_R9_5_REQUALIFICATION_INCOMPLETE",
            "message": (
                "Package E evidence passed intake validation, but R9.5 did not qualify "
                "ALTERNATE_LOAD_PATH_EVIDENCE. The R9.5 decision register remains authoritative."
            ),
            "r9_5_missing_requirements": e_row.get("missing_requirements") or [],
            "technical_analysis_required_count": 0,
            "external_independent_evidence_required_count": 0,
        }
    else:
        blocker = None

    result = {
        "schema_version": "phoenix.r9-5-2-5-package-e-independent-evidence/1.0",
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if not unresolved and e_qualified else "BLOCKED",
        "package_id": PACKAGE_ID,
        "input_path": str(package_e_input_path),
        "validation": validation,
        "runtime_input_path": str(global_input_path),
        "runtime_input_sha256": runtime_sha,
        "r9_5_requalified": r95,
        "r9_5_2_requalified": r952,
        "resolved_package_ids": sorted(set(resolved_packages)),
        "unresolved_package_ids": sorted(set(unresolved_packages)),
        "blockers": [] if blocker is None else [blocker],
        "summary": {
            "required_check_type_count": len(register),
            "decision_qualified_check_count": len(qualified),
            "unresolved_decision_check_count": len(unresolved),
            "package_e_independent_evidence_complete": e_qualified,
            "technical_analysis_required_count": 0,
            "external_independent_evidence_required_count": 0,
        },
        "safety": safety,
    }
    result["dossier_markdown"] = render_package_e_dossier_markdown(result)
    return result
