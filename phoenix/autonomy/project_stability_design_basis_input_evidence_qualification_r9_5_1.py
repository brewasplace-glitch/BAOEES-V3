"""Project Phoenix R9.5.1 project stability design-basis input/evidence qualification.

R9.5.1 does not decide normative limits, seismic applicability, professional review,
or project policy approval. It turns the R9.5 required-input template into a
project-specific, traceable scaffold and consolidates the remaining evidence into
five source/review packages.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

ENGINE_ID = "PHX-PROJECT-STABILITY-DESIGN-BASIS-INPUT-EVIDENCE-QUALIFICATION-R9.5.1"
VERSION = "R9.5.1"
SCHEMA = "phoenix.project-stability-design-basis-input-evidence-qualification/1.0"
LOCKED_RELEASE = "LOCKED"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _clean_examples(source_records: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in source_records.items():
        name = str(key)
        if name.startswith("EXAMPLE_"):
            continue
        if isinstance(value, Mapping):
            out[name] = dict(value)
    return out


def _seed_source_records(existing: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    out = _clean_examples(existing)
    added = 0
    seeds = _mapping(policy.get("suriname_primary_records_to_seed"))
    for key, value in seeds.items():
        if key not in out and isinstance(value, Mapping):
            row = dict(value)
            row.pop("support_scope", None)
            out[str(key)] = row
            added += 1
    if "PROJECT_STABILITY_POLICY_REQUIRED" not in out:
        out["PROJECT_STABILITY_POLICY_REQUIRED"] = {
            "reference_type": "PROJECT_ENGINEERING_POLICY",
            "reference": "PROJECT STABILITY DESIGN BASIS - EXPLICIT APPROVAL REQUIRED",
            "project_policy_approved": False,
            "approval_reference": None,
            "scope": "R9.5/v8.6 project stability qualification; no numerical criteria are approved by this scaffold.",
        }
        added += 1
    if "LICENSED_STABILITY_SOURCE_REQUIRED" not in out:
        out["LICENSED_STABILITY_SOURCE_REQUIRED"] = {
            "reference_type": "LICENSED_STANDARD_SOURCE",
            "reference": "LICENSED STANDARD / CLAUSE INPUT REQUIRED",
            "source_file": None,
            "sha256": None,
            "clause_reference": None,
            "licensed_use_confirmed": False,
            "extraction_reviewed": False,
        }
        added += 1
    return out, added


def _seed_checks(checks: Mapping[str, Any], r95_register: Mapping[str, Any], policy: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    autofilled = 0
    prefill = _mapping(policy.get("check_prefill"))
    for check_type in policy.get("required_check_types", []):
        base = deepcopy(checks.get(check_type)) if isinstance(checks.get(check_type), Mapping) else {}
        register = _mapping(r95_register.get(check_type))
        snapshot = _mapping(register.get("decision_snapshot"))
        for key, value in snapshot.items():
            if value not in (None, "", [], {}):
                base[key] = deepcopy(value)
        row_prefill = _mapping(prefill.get(check_type))
        support_ids = row_prefill.get("supporting_source_record_ids")
        if isinstance(support_ids, list):
            current = base.get("supporting_source_record_ids")
            if not isinstance(current, list):
                current = []
            seen = set(str(x) for x in current)
            merged = list(current)
            for sid in support_ids:
                if str(sid) not in seen:
                    merged.append(str(sid))
                    seen.add(str(sid))
                    autofilled += 1
            base["supporting_source_record_ids"] = merged
        out[str(check_type)] = base
    return out, autofilled


def _matrix(required: list[str], r95_register: Mapping[str, Any], checks: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    numerical_names = {
        "max_amplification_factor", "minimum_critical_load_factor", "max_stability_index",
        "max_torsional_drift_ratio", "minimum_ratio", "minimum_residual_capacity_proxy_ratio",
    }
    for check_type in required:
        reg = _mapping(r95_register.get(check_type))
        missing = list(reg.get("missing_requirements") or [])
        row = _mapping(checks.get(check_type))
        result[check_type] = {
            "technical_evidence_reference": row.get("evidence_reference") or f"R9.3:{check_type}",
            "r9_5_state": reg.get("state") or "UNKNOWN",
            "remaining_requirements": missing,
            "suriname_primary_support": reg.get("available_surinaame_primary_support") or [],
            "decision_already_present": bool(_mapping(reg.get("decision_snapshot"))),
            "numerical_acceptance_criterion_still_required": any(str(name) in numerical_names for name in missing),
            "professional_or_independent_review_required": any(("review" in str(name).lower()) or ("independent" in str(name).lower()) for name in missing),
        }
    return result


def build_project_stability_design_basis_input_evidence_qualification(*, project_id: str, r95_result: Mapping[str, Any], policy_path: Path) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    required = [str(x) for x in policy.get("required_check_types", [])]
    if _text(r95_result.get("status")) == "PASSED":
        return {
            "schema_version": SCHEMA, "engine": ENGINE_ID, "version": VERSION, "project_id": project_id,
            "status": "PASSED", "prefilled_project_input": None, "evidence_requirement_matrix": {},
            "consolidated_input_packages": {}, "blockers": [],
            "summary": {"required_check_type_count": len(required), "r9_5_already_passed": True, "remaining_decision_check_count": 0, "autofilled_field_count": 0, "consolidated_input_package_count": 0, "technical_analysis_required_count": 0},
            "safety": dict(policy.get("safety", {})),
        }

    r95_register = _mapping(r95_result.get("decision_register"))
    template_root = _mapping(r95_result.get("required_input_template"))
    template = _mapping(template_root.get("r9_5_project_stability_design_basis_decision"))
    packages = dict(policy.get("consolidated_input_packages", {}))
    if not template:
        return {
            "schema_version": SCHEMA, "engine": ENGINE_ID, "version": VERSION, "project_id": project_id,
            "status": "BLOCKED", "prefilled_project_input": None, "evidence_requirement_matrix": {},
            "consolidated_input_packages": packages,
            "blockers": [{"reason": "R9_5_1_REQUIRED_TEMPLATE_MISSING", "message": "R9.5.1 cannot prepare a safe project input because the preserved R9.5 required-input template is missing."}],
            "summary": {"required_check_type_count": len(required), "r9_5_already_passed": False, "remaining_decision_check_count": len(required), "autofilled_field_count": 0, "consolidated_input_package_count": len(packages), "technical_analysis_required_count": 0},
            "safety": dict(policy.get("safety", {})),
        }

    scaffold = deepcopy(template)
    known = _mapping(policy.get("known_jurisdictional_basis"))
    jurisdictional = _mapping(scaffold.get("jurisdictional_basis"))
    changed = 0
    for key, value in known.items():
        if jurisdictional.get(key) in (None, ""):
            jurisdictional[key] = value
            changed += 1
    scaffold["jurisdictional_basis"] = jurisdictional

    records, seeded_records = _seed_source_records(_mapping(scaffold.get("source_records")), policy)
    scaffold["source_records"] = records
    checks, seeded_check_fields = _seed_checks(_mapping(scaffold.get("checks")), r95_register, policy)
    scaffold["checks"] = checks

    seismic = _mapping(scaffold.get("seismic_applicability"))
    if not _text(seismic.get("status")):
        seismic.update({
            "status": None, "reference_type": None, "reference": None, "source_record_id": None,
            "professional_scope_reviewed": False, "scope_review_reference": None,
            "r9_5_1_status": "EXPLICIT_SCOPE_DECISION_REQUIRED",
        })
    scaffold["seismic_applicability"] = seismic

    matrix = _matrix(required, r95_register, checks)
    unresolved = [check for check in required if _mapping(r95_register.get(check)).get("state") != "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"]
    blocker = {
        "reason": "R9_5_1_EXPLICIT_SOURCE_REVIEW_AND_DESIGN_BASIS_INPUT_REQUIRED",
        "message": "Technical stability evidence is complete. R9.5.1 generated a project-specific input scaffold and consolidated the remaining normative/source/review decisions. No numerical criterion, seismic scope decision, project-policy approval, or professional review was invented.",
        "unresolved_check_types": unresolved,
        "consolidated_input_package_ids": list(packages),
    }
    return {
        "schema_version": SCHEMA, "engine": ENGINE_ID, "version": VERSION, "project_id": project_id,
        "status": "BLOCKED",
        "source_states": {"r9_5_status": r95_result.get("status"), "r9_5_summary": r95_result.get("summary"), "r9_5_source": r95_result.get("source_states")},
        "prefilled_project_input": {
            "schema_version": "phoenix.r9-5-project-stability-design-basis-required-input/1.0",
            "r9_5_project_stability_design_basis_decision": scaffold,
            "r9_5_1_scaffold_metadata": {
                "engine": ENGINE_ID, "status": "DRAFT_INPUT_REQUIRING_EXPLICIT_DECISIONS",
                "automatic_normative_value_insertion": False, "automatic_seismic_applicability_decision": False,
                "automatic_project_policy_approval": False, "professional_review_required": True,
                "production_release": LOCKED_RELEASE,
            },
        },
        "evidence_requirement_matrix": matrix,
        "consolidated_input_packages": packages,
        "blockers": [blocker],
        "summary": {
            "required_check_type_count": len(required), "r9_5_already_passed": False,
            "remaining_decision_check_count": len(unresolved),
            "autofilled_field_count": changed + seeded_records + seeded_check_fields,
            "seeded_primary_surinaame_source_record_count": sum(1 for key in records if key.startswith("SURINAME_BOUWBESLUIT_")),
            "consolidated_input_package_count": len(packages), "technical_analysis_required_count": 0,
        },
        "safety": dict(policy.get("safety", {})),
    }
