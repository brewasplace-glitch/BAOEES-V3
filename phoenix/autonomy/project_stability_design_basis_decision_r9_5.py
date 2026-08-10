"""Project Phoenix R9.5 project stability design-basis decision and source qualification.

R9.5 is a decision/source-integrity layer between the R9.4 applicability register
and the existing v8.6 verifier. It does not invent limits or waive checks.

It validates explicit project decisions and the provenance of the source used to
justify methodology/acceptance criteria. It can use the Phoenix Suriname BIB as
primary-source support where the uploaded law/regulation actually supports a
point, but it never promotes background AI text to normative evidence and never
claims current 2026 legal status or Eurocode legal adoption in Suriname.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .normative_applicability_stability_design_basis_r9_4 import (
    build_normative_applicability_stability_design_basis,
)

ENGINE_ID = "PHX-PROJECT-STABILITY-DESIGN-BASIS-DECISION-LICENSED-SOURCE-QUALIFICATION-R9.5"
VERSION = "R9.5.0"
SCHEMA = "phoenix.project-stability-design-basis-decision-licensed-source-qualification/1.0"
LOCKED_RELEASE = "LOCKED"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _text(value: Any) -> str:
    return str(value or "").strip()


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_file(repository_root: Path, relative_path: str) -> Path | None:
    rel = _text(relative_path).replace("\\", "/")
    if not rel or rel.startswith("/") or ":" in rel.split("/")[0]:
        return None
    root = Path(repository_root).resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def _extract_input(
    candidates: Sequence[Any],
    forbidden_paths: Sequence[str],
) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    rows: list[tuple[int, str, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    forbidden = {str(x).replace("\\", "/") for x in forbidden_paths}
    for item in candidates:
        path, data = (
            (item[0], item[1])
            if isinstance(item, (list, tuple)) and len(item) >= 2
            else (None, item)
        )
        if not isinstance(data, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if ptext in forbidden or any(ptext.endswith(x) for x in forbidden):
            warnings.append({"reason": "R9_5_FORBIDDEN_INPUT_SOURCE_REJECTED", "source": ptext})
            continue
        section = data.get("r9_5_project_stability_design_basis_decision")
        if not isinstance(section, Mapping):
            continue
        value = dict(section)
        checks = value.get("checks") if isinstance(value.get("checks"), Mapping) else {}
        sources = value.get("source_records") if isinstance(value.get("source_records"), Mapping) else {}
        score = 10000 * len(checks) + 100 * len(sources)
        if _text(value.get("decision_id")):
            score += 1
        rows.append((score, ptext, value))
    if not rows:
        return {}, None, warnings
    rows.sort(key=lambda x: (-x[0], x[1]))
    return rows[0][2], rows[0][1], warnings


def _bib_source_map(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    values = registry.get("sources")
    if not isinstance(values, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in values:
        if isinstance(row, Mapping) and _text(row.get("source_id")):
            out[_text(row["source_id"])] = dict(row)
    return out


def _bib_rule_map(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    values = registry.get("rules")
    if not isinstance(values, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in values:
        if isinstance(row, Mapping) and _text(row.get("rule_id")):
            out[_text(row["rule_id"])] = dict(row)
    return out


def _validate_sha_file(
    repository_root: Path,
    source_file: Any,
    expected_sha: Any,
) -> tuple[bool, list[str], str | None]:
    errors: list[str] = []
    path = _repo_file(repository_root, _text(source_file))
    if path is None:
        return False, ["repository_relative_source_file_required"], None
    if not path.is_file():
        return False, ["source_file_missing"], path.as_posix()
    expected = _text(expected_sha).lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        errors.append("valid_sha256_required")
        return False, errors, path.as_posix()
    actual = _sha256(path)
    if actual != expected:
        errors.append("source_sha256_mismatch")
    return not errors, errors, path.as_posix()


def _validate_source_record(
    *,
    source_id: str,
    record: Mapping[str, Any],
    repository_root: Path,
    allowed_reference_types: Sequence[str],
    bib_sources: Mapping[str, Mapping[str, Any]],
    forbidden_primary_source_paths: Sequence[str],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    ref_type = _text(record.get("reference_type"))
    reference = _text(record.get("reference"))
    if ref_type not in set(allowed_reference_types):
        errors.append("allowed_reference_type_required")
    if not reference:
        errors.append("reference_required")

    source_file = _text(record.get("source_file")).replace("\\", "/")
    forbidden = {str(x).replace("\\", "/") for x in forbidden_primary_source_paths}
    if source_file and (source_file in forbidden or any(source_file.endswith(x) for x in forbidden)):
        errors.append("forbidden_primary_source_path")

    trace: dict[str, Any] = {
        "source_record_id": source_id,
        "reference_type": ref_type or None,
        "reference": reference or None,
        "source_file": source_file or None,
    }

    if ref_type == "LICENSED_STANDARD_SOURCE":
        if record.get("licensed_use_confirmed") is not True:
            errors.append("licensed_use_confirmed_required")
        if record.get("extraction_reviewed") is not True:
            errors.append("extraction_reviewed_required")
        if not _text(record.get("clause_reference")):
            errors.append("clause_reference_required")
        ok, file_errors, resolved = _validate_sha_file(
            repository_root,
            record.get("source_file"),
            record.get("sha256"),
        )
        errors.extend(file_errors)
        trace["resolved_file"] = resolved
        trace["sha256_validated"] = ok

    elif ref_type == "PROJECT_ENGINEERING_POLICY":
        if record.get("project_policy_approved") is not True:
            errors.append("project_policy_approved_required")
        if not _text(record.get("approval_reference")):
            errors.append("approval_reference_required")
        if not _text(record.get("scope")):
            errors.append("scope_required")
        trace["approval_reference"] = _text(record.get("approval_reference")) or None
        trace["scope"] = _text(record.get("scope")) or None

    elif ref_type == "AUTHORITY_APPROVED_PROJECT_BASIS":
        bib_id = _text(record.get("bib_source_id"))
        if bib_id:
            source = bib_sources.get(bib_id)
            if not isinstance(source, Mapping):
                errors.append("registered_bib_source_required")
            else:
                source_class = _text(source.get("source_class"))
                if not source_class.startswith("PRIMARY_"):
                    errors.append("primary_bib_source_required")
                trace["bib_source_id"] = bib_id
                trace["bib_source_class"] = source_class
                trace["bib_source_file"] = source.get("file")
            if not _text(record.get("source_pointer")):
                errors.append("source_pointer_required")
        else:
            if record.get("authority_basis_confirmed") is not True:
                errors.append("authority_basis_confirmed_required")
            if not _text(record.get("source_pointer")):
                errors.append("source_pointer_required")
            ok, file_errors, resolved = _validate_sha_file(
                repository_root,
                record.get("source_file"),
                record.get("sha256"),
            )
            errors.extend(file_errors)
            trace["resolved_file"] = resolved
            trace["sha256_validated"] = ok

    return {
        "source_record_id": source_id,
        "status": "QUALIFIED" if not errors else "REJECTED",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "trace": trace,
    }


def _local_support_snapshot(
    *,
    check_type: str,
    policy: Mapping[str, Any],
    bib_sources: Mapping[str, Mapping[str, Any]],
    bib_rules: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    support = policy.get("suriname_bib_support")
    row = support.get(check_type) if isinstance(support, Mapping) else None
    if not isinstance(row, Mapping):
        return []
    source_id = _text(row.get("source_id"))
    rule_id = _text(row.get("rule_id"))
    source = bib_sources.get(source_id)
    rule = bib_rules.get(rule_id)
    if not isinstance(source, Mapping) or not isinstance(rule, Mapping):
        return [{
            "status": "CONFIGURED_SUPPORT_SOURCE_MISSING",
            "source_id": source_id or None,
            "rule_id": rule_id or None,
        }]
    return [{
        "status": "AVAILABLE",
        "source_id": source_id,
        "source_class": source.get("source_class"),
        "source_file": source.get("file"),
        "rule_id": rule_id,
        "source_pointer": row.get("source_pointer") or rule.get("source_pointer"),
        "support_scope": row.get("support_scope"),
        "exact_v8_6_acceptance_limit_available": bool(
            row.get("exact_v8_6_acceptance_limit_available")
        ),
        "rule_summary": rule.get("summary"),
    }]


def _criteria_fields(
    policy: Mapping[str, Any],
    check_type: str,
) -> list[str]:
    table = policy.get("acceptance_criteria_fields")
    values = table.get(check_type) if isinstance(table, Mapping) else None
    return [str(x) for x in values] if isinstance(values, list) else []


def _validate_check_decision(
    *,
    check_type: str,
    decision: Mapping[str, Any],
    policy: Mapping[str, Any],
    source_qualifications: Mapping[str, Mapping[str, Any]],
    repository_root: Path,
) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
    missing: list[str] = []
    applicability = _text(decision.get("applicability"))
    allowed_app = set(policy.get("allowed_applicability_states", []))
    if applicability not in allowed_app:
        missing.append("explicit_applicability_decision")

    if decision.get("methodology_accepted") is not True:
        missing.append("methodology_accepted")

    primary_id = _text(decision.get("primary_source_record_id"))
    primary = source_qualifications.get(primary_id)
    if not primary_id:
        missing.append("primary_source_record_id")
    elif not isinstance(primary, Mapping) or primary.get("status") != "QUALIFIED":
        missing.append("qualified_primary_source_record")

    supporting_ids = decision.get("supporting_source_record_ids")
    if not isinstance(supporting_ids, list):
        supporting_ids = []
    bad_supporting = [
        sid for sid in supporting_ids
        if not isinstance(source_qualifications.get(str(sid)), Mapping)
        or source_qualifications[str(sid)].get("status") != "QUALIFIED"
    ]
    if bad_supporting:
        missing.append("qualified_supporting_source_records")

    criteria = (
        decision.get("acceptance_criteria")
        if isinstance(decision.get("acceptance_criteria"), Mapping)
        else {}
    )
    traceability = (
        decision.get("criteria_traceability")
        if isinstance(decision.get("criteria_traceability"), Mapping)
        else {}
    )
    for field in _criteria_fields(policy, check_type):
        if _num(criteria.get(field)) is None:
            missing.append(field)
            continue
        trace = traceability.get(field)
        if not isinstance(trace, Mapping):
            missing.append(f"{field}_traceability")
            continue
        trace_sid = _text(trace.get("source_record_id"))
        if not trace_sid:
            missing.append(f"{field}_source_record_id")
        elif not isinstance(source_qualifications.get(trace_sid), Mapping) or (
            source_qualifications[trace_sid].get("status") != "QUALIFIED"
        ):
            missing.append(f"{field}_qualified_source_record")
        if not _text(trace.get("clause_reference")):
            missing.append(f"{field}_clause_reference")

    if applicability == "NOT_APPLICABLE":
        missing.append("professional_v8_6_scope_waiver_or_policy_revision")

    if check_type == "WEAK_STOREY_STRENGTH_RATIO":
        if decision.get("screening_proxy_accepted_for_candidate_gate") is not True:
            missing.append("explicit_candidate_screening_proxy_acceptance")
        if not _text(decision.get("screening_proxy_review_reference")):
            missing.append("screening_proxy_review_reference")

    if check_type == "ALTERNATE_LOAD_PATH_EVIDENCE":
        if decision.get("alternate_path_verified") is not True:
            missing.append("independently_verified_alternate_path")
        if _text(decision.get("independent_review_status")) != "REVIEWED":
            missing.append("independent_review_status_REVIEWED")
        if not _text(decision.get("independent_review_reference")):
            missing.append("independent_review_reference")
        if not _text(decision.get("independent_engineering_evidence_reference")):
            missing.append("independent_engineering_evidence_reference")
        ok, file_errors, resolved = _validate_sha_file(
            repository_root,
            decision.get("independent_engineering_evidence_file"),
            decision.get("independent_engineering_evidence_sha256"),
        )
        if not ok:
            missing.extend(f"alternate_path_{x}" for x in file_errors)
        alternate_trace = {
            "resolved_file": resolved,
            "sha256_validated": ok,
        }
    else:
        alternate_trace = {}

    if missing or not isinstance(primary, Mapping):
        return None, sorted(set(missing)), alternate_trace

    primary_trace = primary.get("trace") if isinstance(primary.get("trace"), Mapping) else {}
    reference = _text(primary_trace.get("reference"))
    ref_type = _text(primary_trace.get("reference_type"))
    r94_row: dict[str, Any] = {
        "applicability": applicability,
        "methodology_accepted": True,
        "methodology_acceptance_reference": (
            _text(decision.get("methodology_acceptance_reference"))
            or reference
        ),
        "reference_type": ref_type,
        "reference": reference,
        "acceptance_criteria": dict(criteria),
        "evidence_reference": _text(decision.get("evidence_reference")) or f"R9.3:{check_type}",
    }
    if check_type == "ALTERNATE_LOAD_PATH_EVIDENCE":
        r94_row["alternate_path_verified"] = True
        r94_row["independent_engineering_evidence_reference"] = _text(
            decision.get("independent_engineering_evidence_reference")
        )
    return r94_row, [], alternate_trace


def _required_template(
    *,
    project_id: str,
    policy: Mapping[str, Any],
    r94_initial: Mapping[str, Any],
    local_support: Mapping[str, Any],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for check_type in policy["required_check_types"]:
        criteria = {field: None for field in _criteria_fields(policy, check_type)}
        row: dict[str, Any] = {
            "applicability": None,
            "methodology_accepted": False,
            "methodology_acceptance_reference": None,
            "primary_source_record_id": None,
            "supporting_source_record_ids": [],
            "acceptance_criteria": criteria,
            "criteria_traceability": {
                field: {
                    "source_record_id": None,
                    "clause_reference": None,
                }
                for field in criteria
            },
            "evidence_reference": f"R9.3:{check_type}",
            "available_surinaame_primary_support": local_support.get(check_type, []),
        }
        if check_type == "WEAK_STOREY_STRENGTH_RATIO":
            row.update(
                screening_proxy_accepted_for_candidate_gate=False,
                screening_proxy_review_reference=None,
            )
        if check_type == "ALTERNATE_LOAD_PATH_EVIDENCE":
            row.update(
                alternate_path_verified=False,
                independent_engineering_evidence_reference=None,
                independent_engineering_evidence_file=None,
                independent_engineering_evidence_sha256=None,
                independent_review_status=None,
                independent_review_reference=None,
            )
        checks[check_type] = row

    return {
        "schema_version": "phoenix.r9-5-project-stability-design-basis-required-input/1.0",
        "r9_5_project_stability_design_basis_decision": {
            "decision_id": f"{project_id}-STABILITY-DESIGN-BASIS-DECISION",
            "jurisdictional_basis": {
                "project_jurisdiction": "Suriname / Paramaribo",
                "engineering_design_methodology": "Eurocode 2 based",
                "current_2026_surinaame_legal_status": "NOT_EXTERNALLY_VERIFIED",
                "eurocode_2_legal_adoption": "NOT_ESTABLISHED_BY_UPLOADED_PRIMARY_SOURCES",
                "legal_status_source_record_id": None,
            },
            "seismic_applicability": {
                "status": None,
                "reference_type": None,
                "reference": None,
                "source_record_id": None,
                "professional_scope_reviewed": False,
                "scope_review_reference": None,
                "note": (
                    "If NOT_APPLICABLE is selected, the existing mandatory v8.6 check set is "
                    "not automatically waived; a professional scope decision/policy revision remains required."
                ),
            },
            "source_records": {
                "EXAMPLE_PROJECT_POLICY_RECORD": {
                    "reference_type": "PROJECT_ENGINEERING_POLICY",
                    "reference": None,
                    "project_policy_approved": False,
                    "approval_reference": None,
                    "scope": None,
                },
                "EXAMPLE_LICENSED_STANDARD_RECORD": {
                    "reference_type": "LICENSED_STANDARD_SOURCE",
                    "reference": None,
                    "source_file": None,
                    "sha256": None,
                    "clause_reference": None,
                    "licensed_use_confirmed": False,
                    "extraction_reviewed": False,
                },
                "EXAMPLE_SURINAME_PRIMARY_RECORD": {
                    "reference_type": "AUTHORITY_APPROVED_PROJECT_BASIS",
                    "reference": "Suriname Bouwbesluit no. 1",
                    "bib_source_id": "SR-SUR-BB1-1956-001",
                    "source_pointer": None,
                },
            },
            "checks": checks,
        },
        "r9_4_initial_summary": r94_initial.get("summary"),
        "safety_notes": [
            "No default numerical acceptance limits are supplied.",
            "Do not enter values copied from a generic v8.6 example as project evidence.",
            "The Suriname background AI text is not a normative source.",
            "Bouwbesluit Article 27 supports the need for a buckling check but does not establish the R9/v8.6 eigenvalue acceptance limit.",
            "R8/R9.3 weak-storey strength remains a candidate screening proxy unless explicitly accepted for the candidate gate.",
            "R9.3 alternate-path screening is not redistributed nonlinear alternate-path proof.",
            "Professional structural review is required and production release remains locked.",
        ],
    }


def build_project_stability_design_basis_decision(
    *,
    project_id: str,
    r93_qualification: Mapping[str, Any],
    r94_initial: Mapping[str, Any],
    candidates: Sequence[Any],
    policy_path: Path,
    suriname_rule_registry_path: Path,
    suriname_source_registry_path: Path,
    r94_policy_path: Path,
    r94_public_source_registry_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    bib_rules_registry = _read_json(Path(suriname_rule_registry_path))
    bib_source_registry = _read_json(Path(suriname_source_registry_path))
    bib_sources = _bib_source_map(bib_source_registry)
    bib_rules = _bib_rule_map(bib_rules_registry)
    required = list(policy["required_check_types"])

    value, input_source, warnings = _extract_input(
        candidates,
        policy.get("forbidden_primary_source_paths", []),
    )
    source_records = (
        value.get("source_records")
        if isinstance(value.get("source_records"), Mapping)
        else {}
    )
    decisions = value.get("checks") if isinstance(value.get("checks"), Mapping) else {}
    seismic = (
        value.get("seismic_applicability")
        if isinstance(value.get("seismic_applicability"), Mapping)
        else {}
    )

    local_support = {
        check_type: _local_support_snapshot(
            check_type=check_type,
            policy=policy,
            bib_sources=bib_sources,
            bib_rules=bib_rules,
        )
        for check_type in required
    }

    source_qualifications: dict[str, dict[str, Any]] = {}
    for source_id, record in source_records.items():
        if isinstance(record, Mapping):
            source_qualifications[str(source_id)] = _validate_source_record(
                source_id=str(source_id),
                record=record,
                repository_root=Path(repository_root),
                allowed_reference_types=policy.get("allowed_reference_types", []),
                bib_sources=bib_sources,
                forbidden_primary_source_paths=policy.get("forbidden_primary_source_paths", []),
            )

    seismic_missing: list[str] = []
    seismic_status = _text(seismic.get("status"))
    if seismic_status not in set(policy.get("allowed_seismic_scope_states", [])):
        seismic_missing.append("explicit_seismic_applicability_decision")
    seismic_source_id = _text(seismic.get("source_record_id"))
    if seismic_status:
        if not seismic_source_id:
            seismic_missing.append("seismic_source_record_id")
        elif not isinstance(source_qualifications.get(seismic_source_id), Mapping) or (
            source_qualifications[seismic_source_id].get("status") != "QUALIFIED"
        ):
            seismic_missing.append("qualified_seismic_source_record")
    if seismic_status == "NOT_APPLICABLE":
        if seismic.get("professional_scope_reviewed") is not True:
            seismic_missing.append("professional_scope_review")
        if not _text(seismic.get("scope_review_reference")):
            seismic_missing.append("scope_review_reference")
        seismic_missing.append("mandatory_v8_6_scope_waiver_or_policy_revision")

    check_register: dict[str, dict[str, Any]] = {}
    r94_checks: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []

    for check_type in required:
        decision = decisions.get(check_type) if isinstance(decisions.get(check_type), Mapping) else {}
        row, missing, alternate_trace = _validate_check_decision(
            check_type=check_type,
            decision=decision,
            policy=policy,
            source_qualifications=source_qualifications,
            repository_root=Path(repository_root),
        )
        if check_type in set(policy.get("seismic_style_check_types", [])) and seismic_missing:
            missing = sorted(set(missing + seismic_missing))
            row = None
        if row is not None:
            r94_checks[check_type] = row
            state = "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
        else:
            unresolved.append(check_type)
            state = "DECISION_OR_SOURCE_INPUT_REQUIRED"
        check_register[check_type] = {
            "state": state,
            "missing_requirements": missing,
            "available_surinaame_primary_support": local_support.get(check_type, []),
            "decision_snapshot": dict(decision) if isinstance(decision, Mapping) else {},
            "alternate_path_evidence_trace": alternate_trace,
        }

    jurisdictional = (
        value.get("jurisdictional_basis")
        if isinstance(value.get("jurisdictional_basis"), Mapping)
        else {}
    )
    generated_r94_input = {
        "r9_4_normative_applicability_input": {
            "jurisdictional_basis": {
                "project_jurisdiction": (
                    _text(jurisdictional.get("project_jurisdiction"))
                    or "Suriname / Paramaribo"
                ),
                "engineering_design_methodology": (
                    _text(jurisdictional.get("engineering_design_methodology"))
                    or "Eurocode 2 based"
                ),
                "legal_applicability_in_suriname": "NOT_VERIFIED",
                "professional_review_status": "REQUIRED",
                "surinaame_primary_source_text_available": True,
                "surinaame_current_2026_legal_status": "NOT_EXTERNALLY_VERIFIED",
                "eurocode_2_legal_adoption": "NOT_ESTABLISHED_BY_UPLOADED_PRIMARY_SOURCES",
            },
            "seismic_applicability": {
                "status": seismic_status or None,
                "reference_type": (
                    source_qualifications.get(seismic_source_id, {})
                    .get("trace", {})
                    .get("reference_type")
                    if seismic_source_id
                    else None
                ),
                "reference": (
                    source_qualifications.get(seismic_source_id, {})
                    .get("trace", {})
                    .get("reference")
                    if seismic_source_id
                    else None
                ),
            },
            "checks": r94_checks,
        }
    }

    r94_recheck = None
    if value and not unresolved and not seismic_missing and len(r94_checks) == len(required):
        r94_recheck = build_normative_applicability_stability_design_basis(
            project_id=project_id,
            r93_qualification=r93_qualification,
            candidates=[("R9.5_GENERATED_EXPLICIT_DECISION", generated_r94_input)],
            policy_path=Path(r94_policy_path),
            source_registry_path=Path(r94_public_source_registry_path),
        )

    global_input = (
        r94_recheck.get("global_stability_input")
        if isinstance(r94_recheck, Mapping) and r94_recheck.get("status") == "PASSED"
        else None
    )

    blockers: list[dict[str, Any]] = []
    if not value:
        blockers.append({
            "reason": "R9_5_PROJECT_STABILITY_DESIGN_BASIS_DECISION_REQUIRED",
            "message": (
                "R9.3 technical evidence is complete and R9.4 applicability mapping exists, "
                "but an explicit project stability design-basis decision with qualified "
                "licensed/authority/project-policy sources is required."
            ),
            "unresolved_check_types": required,
        })
    elif unresolved or seismic_missing:
        blockers.append({
            "reason": "R9_5_DECISION_OR_SOURCE_QUALIFICATION_INCOMPLETE",
            "message": (
                "The R9.5 decision package is present, but one or more checks or the seismic "
                "scope decision lack complete source qualification, traceable criteria, "
                "independent evidence, or required professional scope review."
            ),
            "unresolved_check_types": sorted(set(unresolved)),
            "seismic_missing_requirements": sorted(set(seismic_missing)),
        })
    elif global_input is None:
        blockers.append({
            "reason": "R9_5_R9_4_REQUALIFICATION_NOT_PASSED",
            "message": (
                "R9.5 source qualification completed, but the preserved R9.4 gate did not "
                "produce a complete v8.6 input. No verifier rule was weakened."
            ),
            "r9_4_recheck_blockers": (
                r94_recheck.get("blockers")
                if isinstance(r94_recheck, Mapping)
                else None
            ),
        })

    template = _required_template(
        project_id=project_id,
        policy=policy,
        r94_initial=r94_initial,
        local_support=local_support,
    )

    source_summary = {
        "declared_source_record_count": len(source_records),
        "qualified_source_record_count": sum(
            1 for row in source_qualifications.values() if row.get("status") == "QUALIFIED"
        ),
        "rejected_source_record_count": sum(
            1 for row in source_qualifications.values() if row.get("status") == "REJECTED"
        ),
        "suriname_primary_source_count": sum(
            1 for row in bib_sources.values()
            if _text(row.get("source_class")).startswith("PRIMARY_")
        ),
        "background_source_used_as_normative_input": False,
    }

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if global_input is not None else "BLOCKED",
        "source_states": {
            "r9_3_status": r93_qualification.get("status"),
            "r9_4_initial_status": r94_initial.get("status"),
            "r9_4_initial_summary": r94_initial.get("summary"),
            "explicit_r9_5_input_source": input_source,
            "suriname_bib_source_registry": str(suriname_source_registry_path),
            "suriname_bib_rule_registry": str(suriname_rule_registry_path),
        },
        "source_qualification_register": source_qualifications,
        "source_qualification_summary": source_summary,
        "local_surinaame_primary_support": local_support,
        "decision_register": check_register,
        "seismic_scope_decision": {
            "status": seismic_status or None,
            "source_record_id": seismic_source_id or None,
            "missing_requirements": sorted(set(seismic_missing)),
        },
        "generated_r9_4_input": generated_r94_input if value else None,
        "r9_4_requalification": r94_recheck,
        "global_stability_input": global_input,
        "qualified_check_types": (
            list(r94_recheck.get("qualified_check_types", []))
            if isinstance(r94_recheck, Mapping)
            else []
        ),
        "unresolved_check_types": (
            list(r94_recheck.get("unresolved_check_types", []))
            if isinstance(r94_recheck, Mapping)
            else sorted(set(unresolved))
        ),
        "required_input_template": template,
        "blockers": blockers,
        "warnings": warnings,
        "summary": {
            "required_check_type_count": len(required),
            "r9_3_technical_evidence_count": (
                r94_initial.get("summary", {}).get("technical_evidence_available_count")
                if isinstance(r94_initial.get("summary"), Mapping)
                else None
            ),
            "decision_qualified_check_count": len(r94_checks),
            "unresolved_decision_check_count": len(set(unresolved)),
            "qualified_source_record_count": source_summary["qualified_source_record_count"],
            "r9_4_requalified_check_count": (
                len(r94_recheck.get("qualified_check_types", []))
                if isinstance(r94_recheck, Mapping)
                else 0
            ),
            "blocker_count": len(blockers),
        },
        "safety": {
            "normative_limits_invented": False,
            "copyrighted_national_annex_values_embedded": False,
            "background_ai_source_used_as_normative_input": False,
            "current_2026_surinaame_legal_status_invented": False,
            "eurocode_2_legal_adoption_invented": False,
            "not_applicable_auto_waives_v8_6": False,
            "r8_screening_promoted_to_code_strength": False,
            "r9_3_alternate_path_screening_promoted_to_redistributed_analysis": False,
            "existing_r9_4_gate_preserved": True,
            "existing_v8_6_verifier_preserved": True,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
