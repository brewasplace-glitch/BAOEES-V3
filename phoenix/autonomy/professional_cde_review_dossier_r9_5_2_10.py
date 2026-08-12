"""PROJECT PHOENIX R9.5.2.10 - Professional C/D/E review dossier and independent evidence request.

This layer prepares human-review material and validates review returns before existing
R9.5.2.9 / Package E / Package C / Package D / R9.5.2.8 logic runs.

It MUST NOT:
- decide seismic applicability;
- invent numerical acceptance criteria;
- accept the weak-storey proxy;
- fabricate reviewer identity or professional review;
- manufacture independent alternate-path evidence;
- claim code compliance, professional approval, R9.5 success, production release,
  or FOR-CONSTRUCTION release.

Mechanically complete, explicitly confirmed human submissions may be copied into the
existing combined intake. Existing package validators remain authoritative.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

VERSION = "R9.5.2.10"
ENGINE_ID = "PHX-R9.5.2.10-PROFESSIONAL-CDE-REVIEW-DOSSIER"
PACKAGE_ID = "PKG-R9.5-CDE-PROFESSIONAL-REVIEW-DOSSIER"

PACKAGE_C = "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
PACKAGE_D = "PKG-D-WEAK-STOREY-SCREENING-REVIEW"
PACKAGE_E = "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"

COMBINED_FILENAME = "r9_5_remaining_evidence_combined_intake_REQUIRED.json"
REVIEW_DIRNAME = "r9_5_2_10_review_pack"

C_RETURN = "package_c_professional_review_RETURN_REQUIRED.json"
D_RETURN = "package_d_weak_storey_review_RETURN_REQUIRED.json"
E_RETURN = "package_e_independent_evidence_RETURN_REQUIRED.json"

C_D_DOSSIER_JSON = "professional_C_D_review_dossier.json"
C_D_DOSSIER_MD = "professional_C_D_review_dossier.md"
E_REQUEST_JSON = "package_E_independent_evidence_request.json"
E_REQUEST_MD = "package_E_independent_evidence_request.md"
EVIDENCE_MANIFEST = "existing_evidence_manifest.json"
RETURN_VALIDATION = "review_return_validation.json"

UNRESOLVED_CHECKS = (
    "ALTERNATE_LOAD_PATH_EVIDENCE",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            value = json.loads(path.read_text(encoding=encoding))
            return value if isinstance(value, dict) else None
        except Exception:
            pass
    return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _write_if_missing(path: Path, value: Any) -> None:
    if path.exists():
        return
    if isinstance(value, str):
        _write_text(path, value)
    else:
        _write_json(path, value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nonempty(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _repo_relative(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except Exception:
        return str(path.resolve())


def _iter_dicts(value: Any, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 12:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child, depth + 1)


def _evidence_snapshots(value: Any, evidence_reference: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in _iter_dicts(value):
        if item.get("evidence_reference") == evidence_reference:
            matches.append(deepcopy(item))
            if len(matches) >= 5:
                break
    return matches


def _relevant_json_files(project_root: Path) -> list[Path]:
    structural = project_root / "results" / "session_adapters" / "structural_engineering"
    candidates: list[Path] = []
    if structural.is_dir():
        candidates.extend(structural.rglob("*.json"))
    input_structural = project_root / "inputs" / "structural"
    if input_structural.is_dir():
        candidates.extend(input_structural.glob("*.json"))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in sorted(candidates):
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique[:2500]


def _collect_existing_evidence(repository: Path, project_root: Path, combined: dict[str, Any]) -> dict[str, Any]:
    evidence_context = combined.get("evidence_context")
    if not isinstance(evidence_context, dict):
        evidence_context = {}

    known_refs = evidence_context.get("existing_r9_3_evidence_references")
    if not isinstance(known_refs, dict):
        known_refs = {}

    entries: dict[str, Any] = {}
    files = _relevant_json_files(project_root)

    for check in UNRESOLVED_CHECKS:
        ref = f"R9.3:{check}"
        locations: list[dict[str, Any]] = []
        for path in files:
            value = _read_json(path)
            if value is None:
                continue
            snapshots = _evidence_snapshots(value, ref)
            if not snapshots:
                continue
            locations.append({
                "source_file": _repo_relative(path, repository),
                "sha256": _sha256(path),
                "snapshots": snapshots,
            })
            if len(locations) >= 5:
                break
        entries[check] = {
            "check_type": check,
            "evidence_reference": ref,
            "existing_reference_flag": known_refs.get(ref) is True,
            "located_source_count": len(locations),
            "located_sources": locations,
            "interpretation": (
                "INTERNAL_SCREENING_ONLY"
                if check == "ALTERNATE_LOAD_PATH_EVIDENCE"
                else "TECHNICAL_EVIDENCE_REQUIRES_PROFESSIONAL_SCOPE_OR_CRITERION_DECISION"
            ),
        }

    source_manifest: list[dict[str, Any]] = []
    source_files = evidence_context.get("source_files")
    if isinstance(source_files, dict):
        for label, rel in source_files.items():
            if not _nonempty(rel):
                continue
            candidate = repository / str(rel)
            if candidate.is_file():
                source_manifest.append({
                    "label": label,
                    "source_file": str(rel).replace("\\", "/"),
                    "sha256": _sha256(candidate),
                })

    return {
        "schema_version": "phoenix.r9-5-2-10-existing-evidence-manifest/1.0",
        "project_id": combined.get("project_id"),
        "status": "EXISTING_EVIDENCE_INVENTORIED_NOT_PROFESSIONALLY_APPROVED",
        "source_manifest": source_manifest,
        "check_evidence": entries,
        "safety": {
            "technical_evidence_is_not_professional_approval": True,
            "weak_storey_screening_is_candidate_only": True,
            "alternate_path_screening_is_not_independent_evidence": True,
            "automatic_code_compliance_claim": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }


def _review_record_template(*, independent: bool = False) -> dict[str, Any]:
    value = {
        "reviewer_name": None,
        "reviewer_organization": None,
        "reviewer_role": None,
        "review_date": None,
        "signature_reference": None,
    }
    if independent:
        value["independence_confirmed"] = False
        value["independence_basis"] = None
    return value


def _package_c_return_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.r9-5-2-10-package-c-professional-review-return/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_C,
        "submission_confirmed": False,
        "review_record": _review_record_template(),
        "package_input": {
            "package_id": PACKAGE_C,
            "status": "INPUT_REQUIRED",
            "seismic_applicability_status": "INPUT_REQUIRED",
            "reference_type": None,
            "reference": None,
            "source_record_id": None,
            "professional_scope_reviewed": False,
            "scope_review_reference": None,
            "criteria_if_applicable": {
                "SOFT_STOREY_STIFFNESS_RATIO": {
                    "minimum_ratio": None,
                    "source_record_id": None,
                    "clause_reference": None,
                },
                "TORSIONAL_DRIFT_RATIO": {
                    "max_torsional_drift_ratio": None,
                    "source_record_id": None,
                    "clause_reference": None,
                },
                "WEAK_STOREY_STRENGTH_RATIO": {
                    "minimum_ratio": None,
                    "source_record_id": None,
                    "clause_reference": None,
                },
            },
            "review_note": None,
        },
        "declaration": "This file records explicit human/professional input. Phoenix does not author the decision.",
    }


def _package_d_return_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.r9-5-2-10-package-d-professional-review-return/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_D,
        "submission_confirmed": False,
        "review_record": _review_record_template(),
        "package_input": {
            "package_id": PACKAGE_D,
            "status": "INPUT_REQUIRED",
            "screening_proxy_accepted_for_candidate_gate": None,
            "screening_proxy_review_reference": None,
            "reviewer_scope": None,
            "review_status": "INPUT_REQUIRED",
            "review_note": None,
        },
        "declaration": "Acceptance or rejection must be explicitly recorded by the professional reviewer.",
    }


def _package_e_return_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.r9-5-2-10-package-e-independent-evidence-return/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_E,
        "submission_confirmed": False,
        "review_record": _review_record_template(independent=True),
        "package_input": {
            "package_id": PACKAGE_E,
            "status": "INPUT_REQUIRED",
            "independent_engineering_evidence_reference": None,
            "repository_relative_source_file": None,
            "sha256": None,
            "independent_review_status": "INPUT_REQUIRED",
            "independent_review_reference": None,
            "independently_verified_alternate_path": None,
            "acceptance_criterion_and_traceability": {
                "minimum_residual_capacity_proxy_ratio": None,
                "source_record_id": None,
                "clause_reference": None,
            },
            "review_note": None,
        },
        "declaration": "The evidence must be genuinely independent of the internal R9.3 screening path.",
    }


def _complete_review_record(value: Any, *, independent: bool = False) -> list[str]:
    missing: list[str] = []
    if not isinstance(value, dict):
        return ["review_record"]
    for key in ("reviewer_name", "reviewer_organization", "reviewer_role", "review_date", "signature_reference"):
        if not _nonempty(value.get(key)):
            missing.append(f"review_record.{key}")
    if independent:
        if value.get("independence_confirmed") is not True:
            missing.append("review_record.independence_confirmed")
        if not _nonempty(value.get("independence_basis")):
            missing.append("review_record.independence_basis")
    return missing


def _validate_c_submission(document: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing = _complete_review_record(document.get("review_record"))
    invalid: list[str] = []
    package = document.get("package_input")
    if not isinstance(package, dict):
        return missing + ["package_input"], invalid

    status = package.get("seismic_applicability_status")
    if status not in {"APPLICABLE", "NOT_APPLICABLE"}:
        missing.append("package_input.seismic_applicability_status")
    for key in ("reference_type", "reference", "source_record_id", "scope_review_reference"):
        if not _nonempty(package.get(key)):
            missing.append(f"package_input.{key}")
    if package.get("professional_scope_reviewed") is not True:
        missing.append("package_input.professional_scope_reviewed")

    if status == "APPLICABLE":
        criteria = package.get("criteria_if_applicable")
        if not isinstance(criteria, dict):
            missing.append("package_input.criteria_if_applicable")
        else:
            expected = {
                "SOFT_STOREY_STIFFNESS_RATIO": "minimum_ratio",
                "TORSIONAL_DRIFT_RATIO": "max_torsional_drift_ratio",
                "WEAK_STOREY_STRENGTH_RATIO": "minimum_ratio",
            }
            for check, numeric_key in expected.items():
                item = criteria.get(check)
                if not isinstance(item, dict):
                    missing.append(f"package_input.criteria_if_applicable.{check}")
                    continue
                if not _nonempty(item.get(numeric_key)):
                    missing.append(f"package_input.criteria_if_applicable.{check}.{numeric_key}")
                if not _nonempty(item.get("source_record_id")):
                    missing.append(f"package_input.criteria_if_applicable.{check}.source_record_id")
                if not _nonempty(item.get("clause_reference")):
                    missing.append(f"package_input.criteria_if_applicable.{check}.clause_reference")
    return missing, invalid


def _validate_d_submission(document: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing = _complete_review_record(document.get("review_record"))
    invalid: list[str] = []
    package = document.get("package_input")
    if not isinstance(package, dict):
        return missing + ["package_input"], invalid
    if not isinstance(package.get("screening_proxy_accepted_for_candidate_gate"), bool):
        missing.append("package_input.screening_proxy_accepted_for_candidate_gate")
    for key in ("screening_proxy_review_reference", "reviewer_scope", "review_status"):
        value = package.get(key)
        if not _nonempty(value) or str(value).upper() == "INPUT_REQUIRED":
            missing.append(f"package_input.{key}")
    return missing, invalid


def _validate_e_submission(document: dict[str, Any], repository: Path) -> tuple[list[str], list[str]]:
    missing = _complete_review_record(document.get("review_record"), independent=True)
    invalid: list[str] = []
    package = document.get("package_input")
    if not isinstance(package, dict):
        return missing + ["package_input"], invalid

    for key in (
        "independent_engineering_evidence_reference",
        "repository_relative_source_file",
        "sha256",
        "independent_review_reference",
        "independent_review_status",
    ):
        value = package.get(key)
        if not _nonempty(value) or (key == "independent_review_status" and str(value).upper() == "INPUT_REQUIRED"):
            missing.append(f"package_input.{key}")

    if package.get("independently_verified_alternate_path") is not True:
        missing.append("package_input.independently_verified_alternate_path")

    trace = package.get("acceptance_criterion_and_traceability")
    if not isinstance(trace, dict):
        missing.append("package_input.acceptance_criterion_and_traceability")
    else:
        for key in ("minimum_residual_capacity_proxy_ratio", "source_record_id", "clause_reference"):
            if not _nonempty(trace.get(key)):
                missing.append(f"package_input.acceptance_criterion_and_traceability.{key}")

    rel = package.get("repository_relative_source_file")
    expected_sha = package.get("sha256")
    if _nonempty(rel):
        rel_path = Path(str(rel))
        if rel_path.is_absolute() or ".." in rel_path.parts:
            invalid.append("package_input.repository_relative_source_file:UNSAFE_PATH")
        else:
            source = repository / rel_path
            if not source.is_file():
                invalid.append("package_input.repository_relative_source_file:FILE_NOT_FOUND")
            elif _nonempty(expected_sha):
                if _sha256(source).lower() != str(expected_sha).strip().lower():
                    invalid.append("package_input.sha256:MISMATCH")
    return missing, invalid


def _merge_package_input(combined: dict[str, Any], package_id: str, package_input: dict[str, Any]) -> None:
    package_inputs = combined.setdefault("package_inputs", {})
    if not isinstance(package_inputs, dict):
        raise ValueError("Combined intake package_inputs is invalid.")
    current = package_inputs.get(package_id)
    if not isinstance(current, dict):
        current = {}
    merged = deepcopy(current)
    for key, value in package_input.items():
        if key == "package_id":
            continue
        merged[key] = deepcopy(value)
    merged["package_id"] = package_id
    package_inputs[package_id] = merged


def _submission_validation(
    path: Path,
    package_id: str,
    repository: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    doc = _read_json(path)
    if doc is None:
        return {
            "package_id": package_id,
            "status": "RETURN_FILE_MISSING_OR_INVALID",
            "submission_confirmed": False,
            "missing_requirements": ["return_file"],
            "invalid_requirements": [],
            "mechanical_merge_performed": False,
        }, None

    confirmed = doc.get("submission_confirmed") is True
    if not confirmed:
        return {
            "package_id": package_id,
            "status": "NOT_SUBMITTED",
            "submission_confirmed": False,
            "missing_requirements": [],
            "invalid_requirements": [],
            "mechanical_merge_performed": False,
        }, None

    if package_id == PACKAGE_C:
        missing, invalid = _validate_c_submission(doc)
    elif package_id == PACKAGE_D:
        missing, invalid = _validate_d_submission(doc)
    elif package_id == PACKAGE_E:
        missing, invalid = _validate_e_submission(doc, repository)
    else:
        raise ValueError(package_id)

    if missing or invalid:
        return {
            "package_id": package_id,
            "status": "INCOMPLETE_OR_INVALID_SUBMISSION",
            "submission_confirmed": True,
            "missing_requirements": missing,
            "invalid_requirements": invalid,
            "mechanical_merge_performed": False,
        }, None

    package_input = doc.get("package_input")
    assert isinstance(package_input, dict)
    return {
        "package_id": package_id,
        "status": "READY_FOR_EXISTING_PACKAGE_VALIDATOR",
        "submission_confirmed": True,
        "missing_requirements": [],
        "invalid_requirements": [],
        "mechanical_merge_performed": True,
        "review_record": deepcopy(doc.get("review_record")),
    }, deepcopy(package_input)


def _dossier_markdown(project_id: str, manifest: dict[str, Any]) -> str:
    lines = [
        f"# {project_id} — Professional Package C/D Review Dossier",
        "",
        "## Purpose",
        "",
        "This dossier presents existing Phoenix technical evidence for professional review.",
        "It does not contain a Phoenix-authored professional decision.",
        "",
        "## Package C — Seismic scope & criteria",
        "",
        "Reviewer action:",
        "- explicitly decide `APPLICABLE` or `NOT_APPLICABLE`;",
        "- provide traceable source/reference and scope-review reference;",
        "- if APPLICABLE, provide traceable criteria for soft-storey, torsional drift and weak-storey checks.",
        "",
        "Existing technical evidence references:",
    ]
    for check in ("SOFT_STOREY_STIFFNESS_RATIO", "TORSIONAL_DRIFT_RATIO", "WEAK_STOREY_STRENGTH_RATIO"):
        item = manifest["check_evidence"][check]
        lines.append(
            f"- `{item['evidence_reference']}` — located sources: `{item['located_source_count']}`; "
            f"existing reference flag: `{item['existing_reference_flag']}`"
        )
    lines += [
        "",
        "## Package D — Weak-storey screening review",
        "",
        "Reviewer action:",
        "- review the existing R8/R9.3 weak-storey candidate-screening proxy;",
        "- explicitly accept or reject it for the candidate gate;",
        "- provide review reference and reviewer scope.",
        "",
        "Boundary: acceptance for the candidate gate is not a code-compliance or FOR-CONSTRUCTION approval.",
        "",
        "## Required return files",
        "",
        f"- `{C_RETURN}`",
        f"- `{D_RETURN}`",
        "",
        "Production and FOR-CONSTRUCTION remain `LOCKED`.",
    ]
    return "\n".join(lines)


def _e_request(project_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    alt = manifest["check_evidence"]["ALTERNATE_LOAD_PATH_EVIDENCE"]
    return {
        "schema_version": "phoenix.r9-5-2-10-package-e-independent-evidence-request/1.0",
        "project_id": project_id,
        "package_id": PACKAGE_E,
        "status": "INDEPENDENT_EVIDENCE_REQUIRED",
        "existing_internal_screening": {
            "evidence_reference": alt["evidence_reference"],
            "existing_reference_flag": alt["existing_reference_flag"],
            "located_source_count": alt["located_source_count"],
            "classification": "INTERNAL_SCREENING_ONLY",
            "may_be_used_as_independent_evidence": False,
        },
        "required_external_deliverables": [
            "independent engineering evidence reference",
            "repository-relative evidence source file",
            "SHA-256 of the exact submitted source file",
            "independent review status and review reference",
            "explicit independently_verified_alternate_path decision",
            "acceptance criterion plus source-record and clause/reference traceability",
            "reviewer identity, role, organization, date and signature reference",
            "independence confirmation and independence basis",
        ],
        "acceptance_boundary": {
            "phoenix_does_not_define_the_engineering_criterion": True,
            "phoenix_does_not_claim_independence_without_returned_evidence": True,
            "existing_package_e_validator_remains_authoritative": True,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
        "return_file": E_RETURN,
    }


def _e_request_markdown(project_id: str, request: dict[str, Any]) -> str:
    return "\n".join([
        f"# {project_id} — Package E Independent Alternate-Path Evidence Request",
        "",
        "The existing R9.3 alternate-path result is internal screening only and is not independent redistributed/nonlinear alternate-path proof.",
        "",
        "The independent engineer/reviewer must return:",
        "",
        "- an independent engineering evidence reference;",
        "- the exact evidence source file stored under the Phoenix repository/project tree;",
        "- SHA-256 of that exact file;",
        "- independent review status and review reference;",
        "- explicit confirmation whether the alternate path is independently verified;",
        "- the acceptance criterion and its source/clause traceability;",
        "- reviewer identity, organization, role, date and signature reference;",
        "- an explicit independence confirmation and basis.",
        "",
        f"Complete `{E_RETURN}` only after the evidence source file is present.",
        "",
        "Phoenix verifies path safety, file existence and SHA-256 mechanically. Package E remains the engineering validator.",
        "",
        "Production and FOR-CONSTRUCTION remain `LOCKED`.",
    ])


def prepare_review_pack(repository: Path, project_id: str) -> dict[str, Any]:
    repository = repository.resolve()
    project_root = repository / "projects" / "runtime" / project_id
    input_root = project_root / "inputs" / "structural"
    combined_path = input_root / COMBINED_FILENAME
    combined = _read_json(combined_path)
    if combined is None:
        raise FileNotFoundError(f"Combined R9.5.2.9 intake not found: {combined_path}")

    review_root = input_root / REVIEW_DIRNAME
    review_root.mkdir(parents=True, exist_ok=True)

    manifest = _collect_existing_evidence(repository, project_root, combined)
    _write_json(review_root / EVIDENCE_MANIFEST, manifest)

    dossier = {
        "schema_version": "phoenix.r9-5-2-10-professional-cd-review-dossier/1.0",
        "project_id": project_id,
        "status": "PROFESSIONAL_REVIEW_REQUIRED",
        "packages": [PACKAGE_C, PACKAGE_D],
        "evidence_manifest": EVIDENCE_MANIFEST,
        "package_c_required_decision": {
            "seismic_applicability_status": ["APPLICABLE", "NOT_APPLICABLE"],
            "traceable_scope_review_required": True,
            "criteria_required_only_if_applicable": True,
        },
        "package_d_required_decision": {
            "weak_storey_candidate_proxy_review_required": True,
            "explicit_accept_or_reject_required": True,
            "candidate_gate_only": True,
        },
        "return_files": [C_RETURN, D_RETURN],
        "automatic_professional_approval": False,
        "automatic_code_compliance_claim": False,
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }
    _write_json(review_root / C_D_DOSSIER_JSON, dossier)
    _write_text(review_root / C_D_DOSSIER_MD, _dossier_markdown(project_id, manifest))

    request = _e_request(project_id, manifest)
    _write_json(review_root / E_REQUEST_JSON, request)
    _write_text(review_root / E_REQUEST_MD, _e_request_markdown(project_id, request))

    _write_if_missing(review_root / C_RETURN, _package_c_return_template())
    _write_if_missing(review_root / D_RETURN, _package_d_return_template())
    _write_if_missing(review_root / E_RETURN, _package_e_return_template())

    validations = {}
    merges: dict[str, dict[str, Any]] = {}
    for package_id, filename in (
        (PACKAGE_C, C_RETURN),
        (PACKAGE_D, D_RETURN),
        (PACKAGE_E, E_RETURN),
    ):
        validation, package_input = _submission_validation(review_root / filename, package_id, repository)
        validations[package_id] = validation
        if package_input is not None:
            merges[package_id] = package_input

    combined_changed = False
    if merges:
        for package_id, package_input in merges.items():
            _merge_package_input(combined, package_id, package_input)
        combined["r9_5_2_10_review_return_processing"] = {
            "status": "MECHANICALLY_MERGED_FOR_EXISTING_PACKAGE_VALIDATION",
            "merged_package_ids": sorted(merges),
            "automatic_gate_promotion": False,
            "existing_package_validators_remain_authoritative": True,
        }
        _write_json(combined_path, combined)
        combined_changed = True

    validation_document = {
        "schema_version": "phoenix.r9-5-2-10-review-return-validation/1.0",
        "project_id": project_id,
        "status": (
            "SUBMISSIONS_MERGED_FOR_EXISTING_VALIDATORS"
            if merges
            else "AWAITING_CONFIRMED_PROFESSIONAL_OR_INDEPENDENT_RETURNS"
        ),
        "submissions": validations,
        "merged_package_ids": sorted(merges),
        "combined_intake_changed": combined_changed,
        "automatic_r9_5_requalification_started": False,
        "automatic_gate_promotion": False,
        "next_runtime_authorities": [
            "R9.5.2.9 combined intake normalization",
            "Package E R9.5.2.5",
            "Package C R9.5.2.6",
            "Package D R9.5.2.7",
            "R9.5.2.8 remaining evidence gate and controlled R9.5 requalification",
        ],
        "safety": {
            "automatic_professional_approval": False,
            "automatic_code_compliance_claim": False,
            "automatic_seismic_applicability_decision": False,
            "automatic_numerical_criteria_generation": False,
            "automatic_screening_proxy_acceptance": False,
            "automatic_independent_evidence_generation": False,
            "automatic_r9_5_success_claim": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }
    _write_json(review_root / RETURN_VALIDATION, validation_document)

    return {
        "schema_version": "phoenix.r9-5-2-10-result/1.0",
        "engine_version": VERSION,
        "engine_id": ENGINE_ID,
        "package_id": PACKAGE_ID,
        "status": validation_document["status"],
        "project_id": project_id,
        "review_root": str(review_root),
        "generated_files": [
            str(review_root / C_D_DOSSIER_JSON),
            str(review_root / C_D_DOSSIER_MD),
            str(review_root / E_REQUEST_JSON),
            str(review_root / E_REQUEST_MD),
            str(review_root / EVIDENCE_MANIFEST),
            str(review_root / C_RETURN),
            str(review_root / D_RETURN),
            str(review_root / E_RETURN),
            str(review_root / RETURN_VALIDATION),
        ],
        "merged_package_ids": sorted(merges),
        "combined_intake_changed": combined_changed,
        "automatic_r9_5_requalification_started": False,
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }


def run_professional_cde_review_dossier_r9_5_2_10(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context if isinstance(context, dict) else {}
    repository = context.get("repository")
    project_id = context.get("project_id")
    workspace = context.get("workspace")

    if repository is None:
        return {
            "status": "RUNTIME_CONTEXT_INCOMPLETE",
            "missing_runtime_context": ["repository"],
            "automatic_r9_5_requalification_started": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        }
    repository_path = Path(repository)

    if not _nonempty(project_id):
        if workspace is not None:
            try:
                project_id = Path(workspace).name
            except Exception:
                project_id = None
    if not _nonempty(project_id):
        return {
            "status": "RUNTIME_CONTEXT_INCOMPLETE",
            "missing_runtime_context": ["project_id"],
            "automatic_r9_5_requalification_started": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        }

    return prepare_review_pack(repository_path, str(project_id))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=r"C:\PROJECT-PHOENIX")
    parser.add_argument("--project-id", default="PHOENIX-PAT-001")
    args = parser.parse_args()
    result = prepare_review_pack(Path(args.repository), args.project_id)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
