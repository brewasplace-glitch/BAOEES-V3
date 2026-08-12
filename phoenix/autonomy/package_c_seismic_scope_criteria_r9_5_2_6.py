"""PROJECT PHOENIX R9.5.2.6 — Package C seismic scope & criteria framework.

This module is intentionally evidence-driven.  It does not decide seismic
applicability, invent numerical criteria, claim code compliance, perform a
professional review, or unlock production release.

It may only:
- discover Package-C intake already supplied by the project;
- validate completeness and internal consistency;
- mark a complete intake as eligible for later R9.5 promotion;
- write a runtime evidence record when an output directory is explicitly
  supplied by the structural session chain.

Package D remains the independent/professional weak-storey screening review
gate where that review is applicable.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

ENGINE_ID = "PHX-PACKAGE-C-SEISMIC-SCOPE-CRITERIA-R9.5.2.6"
VERSION = "R9.5.2.6"
PACKAGE_ID = "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
CHECKS = (
    "SOFT_STOREY_STIFFNESS_RATIO",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
)

_REQUIRED_CRITERIA = {
    "SOFT_STOREY_STIFFNESS_RATIO": "minimum_ratio",
    "TORSIONAL_DRIFT_RATIO": "max_torsional_drift_ratio",
    "WEAK_STOREY_STRENGTH_RATIO": "minimum_ratio",
}


def required_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.package-c-seismic-scope-criteria-input/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_ID,
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
    }


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _iter_dicts(value: Any, *, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 6:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_dicts(child, depth=depth + 1)


def discover_package_c_input(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return Package-C input if present; otherwise a pristine REQUIRED template."""
    roots: list[Any] = list(args) + list(kwargs.values())
    aliases = {
        PACKAGE_ID,
        "package_c",
        "package_c_input",
        "package_c_seismic_scope_and_criteria",
        "package_c_seismic_scope_criteria",
    }

    for root in roots:
        for document in _iter_dicts(root):
            if document.get("package_id") == PACKAGE_ID:
                return deepcopy(document)

            for key in aliases:
                value = document.get(key)
                if isinstance(value, dict):
                    return deepcopy(value)

            package_inputs = document.get("package_inputs")
            if isinstance(package_inputs, dict):
                value = package_inputs.get(PACKAGE_ID)
                if isinstance(value, dict):
                    return deepcopy(value)

    return required_template()


def validate_package_c_input(value: dict[str, Any] | None) -> dict[str, Any]:
    payload = deepcopy(value) if isinstance(value, dict) else required_template()
    missing: list[str] = []
    invalid: list[str] = []

    status = str(payload.get("seismic_applicability_status") or "INPUT_REQUIRED").upper()
    allowed = {"INPUT_REQUIRED", "APPLICABLE", "NOT_APPLICABLE"}
    if status not in allowed:
        invalid.append("seismic_applicability_status")
        status = "INPUT_REQUIRED"

    for field in ("reference_type", "reference", "source_record_id", "scope_review_reference"):
        if status != "INPUT_REQUIRED" and not _is_nonempty(payload.get(field)):
            missing.append(field)

    if status != "INPUT_REQUIRED" and payload.get("professional_scope_reviewed") is not True:
        missing.append("professional_scope_reviewed")

    criteria_summary: dict[str, Any] = {}
    if status == "APPLICABLE":
        criteria = payload.get("criteria_if_applicable")
        if not isinstance(criteria, dict):
            missing.append("criteria_if_applicable")
            criteria = {}

        for check, field in _REQUIRED_CRITERIA.items():
            item = criteria.get(check)
            if not isinstance(item, dict):
                missing.append(f"criteria_if_applicable.{check}")
                criteria_summary[check] = {"complete": False}
                continue

            complete = True
            if not _positive_number(item.get(field)):
                missing.append(f"criteria_if_applicable.{check}.{field}")
                complete = False
            if not _is_nonempty(item.get("source_record_id")):
                missing.append(f"criteria_if_applicable.{check}.source_record_id")
                complete = False
            if not _is_nonempty(item.get("clause_reference")):
                missing.append(f"criteria_if_applicable.{check}.clause_reference")
                complete = False
            criteria_summary[check] = {"complete": complete, "criterion_field": field}
    else:
        for check, field in _REQUIRED_CRITERIA.items():
            criteria_summary[check] = {
                "complete": status == "NOT_APPLICABLE",
                "criterion_field": field,
                "required": False,
            }

    eligible = (
        status in {"APPLICABLE", "NOT_APPLICABLE"}
        and not missing
        and not invalid
        and payload.get("professional_scope_reviewed") is True
    )

    if status == "INPUT_REQUIRED":
        result_status = "INPUT_REQUIRED"
    elif eligible:
        result_status = "ELIGIBLE_FOR_LATER_R9_5_PROMOTION"
    else:
        result_status = "INCOMPLETE_REVIEWED_INPUT"

    return {
        "engine": ENGINE_ID,
        "version": VERSION,
        "package_id": PACKAGE_ID,
        "checks": list(CHECKS),
        "status": result_status,
        "seismic_applicability_status": status,
        "eligible_for_r9_5_promotion": eligible,
        "missing_requirements": sorted(set(missing)),
        "invalid_requirements": sorted(set(invalid)),
        "criteria_summary": criteria_summary,
        "validated_input": payload,
        "safety": {
            "automatic_seismic_applicability_decision": False,
            "automatic_normative_value_insertion": False,
            "automatic_r9_5_promotion": False,
            "automatic_professional_review": False,
            "automatic_code_compliance_claim": False,
            "weak_storey_package_d_review_gate_preserved": True,
            "existing_r9_5_r9_4_v8_6_gates_preserved": True,
            "professional_structural_review_required": True,
            "production_release": "LOCKED",
        },
    }


def _path_from_value(value: Any) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return Path(value)
        except (TypeError, ValueError):
            return None
    return None


def _explicit_output_dir(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Path | None:
    for key in (
        "output_dir",
        "structural_output_dir",
        "validated_output_dir",
        "evidence_output_dir",
    ):
        path = _path_from_value(kwargs.get(key))
        if path is not None:
            return path

    # Do not guess from arbitrary positional paths.  Runtime mutation is only
    # permitted when the caller explicitly labels an output directory.
    return None


def run_package_c_seismic_scope_criteria_r9_5_2_6(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Structural-chain-compatible entry point.

    The permissive signature deliberately allows the chain to pass the same
    context arguments used by the preceding Package-E framework.  Package C
    consumes only evidence it can positively identify.
    """
    payload = discover_package_c_input(*args, **kwargs)
    result = validate_package_c_input(payload)

    output_dir = _explicit_output_dir(args, kwargs)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "r9_5_2_6_package_c_seismic_scope_criteria.json"
        output_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result["output_file"] = str(output_file)

    return result


# Stable alias for future orchestration code.
run_package_c = run_package_c_seismic_scope_criteria_r9_5_2_6
