"""PROJECT PHOENIX R9.5.2.9 - Combined C/D/E Evidence Intake & Controlled Requalification Trigger.

R9.5.2.9 is an intake-normalization layer. It does not approve evidence and does not
perform R9.5 requalification itself. Its normalized package_inputs are intentionally
placed in the structural runtime context before Package E, Package C and Package D run.
Those existing package engines remain authoritative for package-specific validation.
R9.5.2.8 remains authoritative for the evidence gate and controlled requalification.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

VERSION = "R9.5.2.9"
ENGINE_ID = "PHX-R9.5.2.9-COMBINED-CDE-EVIDENCE-INTAKE"
PACKAGE_ID = "PKG-R9.5-CDE-COMBINED-EVIDENCE-INTAKE"

PACKAGE_C_ID = "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
PACKAGE_D_ID = "PKG-D-WEAK-STOREY-SCREENING-REVIEW"
PACKAGE_E_ID = "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"

INPUT_REQUIRED = "INPUT_REQUIRED"
READY_FOR_PACKAGE_VALIDATION = "READY_FOR_PACKAGE_VALIDATION"
INVALID_INTAKE = "INVALID_INTAKE"

DEFAULT_WORKSPACE_FILENAME = "r9_5_remaining_evidence_combined_intake_REQUIRED.json"


def required_combined_intake_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.r9-5-cde-combined-evidence-intake/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_ID,
        "status": INPUT_REQUIRED,
        "project_id": None,
        "bundle_reference": None,
        "package_inputs": {
            PACKAGE_C_ID: {
                "schema_version": "phoenix.package-c-seismic-scope-criteria-input/1.0",
                "engine_version": "R9.5.2.6",
                "package_id": PACKAGE_C_ID,
                "status": INPUT_REQUIRED,
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
            PACKAGE_D_ID: {
                "schema_version": "phoenix.package-d-weak-storey-screening-review-input/1.0",
                "engine_version": "R9.5.2.7",
                "package_id": PACKAGE_D_ID,
                "check": "WEAK_STOREY_STRENGTH_RATIO",
                "status": INPUT_REQUIRED,
                "screening_proxy_accepted_for_candidate_gate": None,
                "screening_proxy_review_reference": None,
                "reviewer_scope": None,
                "review_status": "INPUT_REQUIRED",
                "review_note": None,
            },
            PACKAGE_E_ID: {
                "schema_version": "phoenix.package-e-alternate-path-independent-evidence-input/1.0",
                "engine_version": "R9.5.2.5",
                "package_id": PACKAGE_E_ID,
                "status": INPUT_REQUIRED,
                "independent_engineering_evidence_reference": None,
                "repository_relative_source_file": None,
                "sha256": None,
                "independent_review_status": "INPUT_REQUIRED",
                "independent_review_reference": None,
                "independently_verified_alternate_path": None,
                "acceptance_criterion_and_traceability": None,
                "review_note": None,
            },
        },
        "declarations": {
            "no_automatic_professional_approval": True,
            "no_automatic_code_compliance_claim": True,
            "no_automatic_seismic_applicability_decision": True,
            "no_automatic_numerical_criteria_generation": True,
            "no_automatic_screening_proxy_acceptance": True,
            "no_automatic_independent_evidence_generation": True,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }


def _is_nonempty(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _iter_dicts(value: Any, *, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 8:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_dicts(child, depth=depth + 1)


def _workspace_from_context(context: dict[str, Any]) -> Path | None:
    value = context.get("workspace")
    if value is None:
        return None
    try:
        return Path(value)
    except Exception:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return value if isinstance(value, dict) else None


def discover_combined_intake(context: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    context = context if isinstance(context, dict) else {}

    direct_aliases = (
        "_phoenix_r9_5_2_9_intake_input",
        "r9_5_remaining_evidence_combined_intake",
        "combined_cde_evidence_intake",
        "combined_remaining_evidence_intake",
    )
    for key in direct_aliases:
        value = context.get(key)
        if isinstance(value, dict):
            return deepcopy(value), f"context:{key}"

    workspace = _workspace_from_context(context)
    if workspace is not None:
        candidate = workspace / "inputs" / "structural" / DEFAULT_WORKSPACE_FILENAME
        loaded = _load_json(candidate)
        if loaded is not None:
            return loaded, str(candidate)

    for document in _iter_dicts(context):
        if document.get("package_id") == PACKAGE_ID:
            return deepcopy(document), "context:recursive-package-id"
        package_inputs = document.get("package_inputs")
        if isinstance(package_inputs, dict):
            ids = {PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID}
            if ids.intersection(package_inputs.keys()):
                return {
                    "schema_version": "phoenix.r9-5-cde-combined-evidence-intake/1.0",
                    "engine_version": VERSION,
                    "package_id": PACKAGE_ID,
                    "status": document.get("status", INPUT_REQUIRED),
                    "project_id": document.get("project_id"),
                    "bundle_reference": document.get("bundle_reference"),
                    "package_inputs": deepcopy(package_inputs),
                    "declarations": deepcopy(document.get("declarations") or {}),
                }, "context:recursive-package-inputs"

    return None, None


def _normalize_package_input(package_id: str, value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return deepcopy(fallback)
    merged = deepcopy(fallback)
    for key, item in value.items():
        if key == "package_id":
            continue
        merged[key] = deepcopy(item)
    merged["package_id"] = package_id
    return merged


def normalize_combined_intake(value: dict[str, Any] | None) -> dict[str, Any]:
    template = required_combined_intake_template()
    if not isinstance(value, dict):
        return template

    result = deepcopy(template)
    for key in ("project_id", "bundle_reference"):
        if key in value:
            result[key] = deepcopy(value[key])

    supplied_inputs = value.get("package_inputs")
    if not isinstance(supplied_inputs, dict):
        supplied_inputs = {}

    for package_id in (PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID):
        result["package_inputs"][package_id] = _normalize_package_input(
            package_id,
            supplied_inputs.get(package_id),
            template["package_inputs"][package_id],
        )

    declarations = value.get("declarations")
    if isinstance(declarations, dict):
        result["declarations"].update(deepcopy(declarations))

    return result


def validate_combined_intake_structure(value: dict[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_combined_intake(value)
    supplied = value if isinstance(value, dict) else {}
    supplied_inputs = supplied.get("package_inputs") if isinstance(supplied.get("package_inputs"), dict) else {}

    missing_packages = [
        package_id
        for package_id in (PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID)
        if not isinstance(supplied_inputs.get(package_id), dict)
    ]

    invalid = []
    for package_id in (PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID):
        package = normalized["package_inputs"][package_id]
        if package.get("package_id") != package_id:
            invalid.append(f"{package_id}:PACKAGE_ID_MISMATCH")

    if missing_packages:
        status = INPUT_REQUIRED
    elif invalid:
        status = INVALID_INTAKE
    else:
        status = READY_FOR_PACKAGE_VALIDATION

    normalized["status"] = status
    normalized["intake_validation"] = {
        "status": status,
        "missing_packages": missing_packages,
        "invalid_requirements": invalid,
        "package_specific_validation_delegated_to_existing_engines": True,
        "package_c_validator_authoritative": "R9.5.2.6",
        "package_d_validator_authoritative": "R9.5.2.7",
        "package_e_validator_authoritative": "R9.5.2.5",
        "remaining_evidence_gate_authoritative": "R9.5.2.8",
    }
    return normalized


def run_combined_cde_evidence_intake_r9_5_2_9(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context if isinstance(context, dict) else {}
    discovered, source = discover_combined_intake(context)
    result = validate_combined_intake_structure(discovered)
    result["intake_source"] = source
    result["workspace_expected_input_path"] = (
        str(_workspace_from_context(context) / "inputs" / "structural" / DEFAULT_WORKSPACE_FILENAME)
        if _workspace_from_context(context) is not None
        else None
    )
    result["controlled_requalification_trigger"] = {
        "performed_by_r9_5_2_9": False,
        "trigger_path": "PACKAGE_E -> PACKAGE_C -> PACKAGE_D -> R9.5.2.8",
        "condition": "ONLY_AFTER_EXISTING_PACKAGE_VALIDATORS_REPORT_ELIGIBLE",
        "r9_5_2_8_remains_authoritative": True,
    }
    result["safety"] = {
        "automatic_professional_approval": False,
        "automatic_code_compliance_claim": False,
        "automatic_seismic_applicability_decision": False,
        "automatic_numerical_criteria_generation": False,
        "automatic_screening_proxy_acceptance": False,
        "automatic_independent_evidence_generation": False,
        "automatic_r9_5_success_claim": False,
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }
    return result


run_r9_5_2_9 = run_combined_cde_evidence_intake_r9_5_2_9
