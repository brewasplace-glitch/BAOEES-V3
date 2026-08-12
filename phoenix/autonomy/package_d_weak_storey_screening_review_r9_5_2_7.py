"""PROJECT PHOENIX R9.5.2.7 - Package D weak-storey screening review framework.

Package D records and validates a professional review decision that is supplied
by the project for the existing WEAK_STOREY_STRENGTH_RATIO candidate screening
proxy.  The review is limited to candidate-gate use.

This module does not:
- accept or reject the screening proxy by itself;
- invent a reviewer, review reference, reviewer scope, or review status;
- claim code compliance or final professional approval;
- validate or invent normative numerical criteria;
- replace Package-E independent alternate-path evidence;
- automatically promote the project to R9.5;
- unlock production or FOR-CONSTRUCTION release.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

ENGINE_ID = "PHX-PACKAGE-D-WEAK-STOREY-SCREENING-REVIEW-R9.5.2.7"
VERSION = "R9.5.2.7"
PACKAGE_ID = "PKG-D-WEAK-STOREY-SCREENING-REVIEW"
CHECK = "WEAK_STOREY_STRENGTH_RATIO"

REVIEW_INPUT_REQUIRED = "INPUT_REQUIRED"
REVIEW_ACCEPTED = "REVIEWED_ACCEPTED_FOR_CANDIDATE_GATE"
REVIEW_NOT_ACCEPTED = "REVIEWED_NOT_ACCEPTED_FOR_CANDIDATE_GATE"
_ALLOWED_REVIEW_STATUS = {
    REVIEW_INPUT_REQUIRED,
    REVIEW_ACCEPTED,
    REVIEW_NOT_ACCEPTED,
}


def required_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.package-d-weak-storey-screening-review-input/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_ID,
        "check": CHECK,
        "status": "INPUT_REQUIRED",
        "screening_proxy_accepted_for_candidate_gate": None,
        "screening_proxy_review_reference": None,
        "reviewer_scope": None,
        "review_status": REVIEW_INPUT_REQUIRED,
        "review_note": None,
    }


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


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


def discover_package_d_input(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return supplied Package-D input, otherwise a pristine REQUIRED template."""
    roots: list[Any] = list(args) + list(kwargs.values())
    aliases = {
        PACKAGE_ID,
        "package_d",
        "package_d_input",
        "package_d_weak_storey_screening_review",
        "weak_storey_screening_review",
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


def validate_package_d_input(value: dict[str, Any] | None) -> dict[str, Any]:
    payload = deepcopy(value) if isinstance(value, dict) else required_template()
    missing: list[str] = []
    invalid: list[str] = []

    raw_status = payload.get("review_status")
    review_status = str(raw_status or REVIEW_INPUT_REQUIRED).upper()
    if review_status not in _ALLOWED_REVIEW_STATUS:
        invalid.append("review_status")
        review_status = REVIEW_INPUT_REQUIRED

    accepted_value = payload.get("screening_proxy_accepted_for_candidate_gate")
    reference = payload.get("screening_proxy_review_reference")
    reviewer_scope = payload.get("reviewer_scope")

    supplied_review_fields = any(
        item not in (None, "", REVIEW_INPUT_REQUIRED)
        for item in (accepted_value, reference, reviewer_scope, raw_status)
    )

    if review_status != REVIEW_INPUT_REQUIRED:
        if not isinstance(accepted_value, bool):
            missing.append("screening_proxy_accepted_for_candidate_gate")
        if not _is_nonempty(reference):
            missing.append("screening_proxy_review_reference")
        if not _is_nonempty(reviewer_scope):
            missing.append("reviewer_scope")

        if isinstance(accepted_value, bool):
            expected_status = REVIEW_ACCEPTED if accepted_value else REVIEW_NOT_ACCEPTED
            if review_status != expected_status:
                invalid.append("review_status_vs_screening_proxy_accepted_for_candidate_gate")
    elif isinstance(accepted_value, bool) or _is_nonempty(reference) or _is_nonempty(reviewer_scope):
        missing.append("review_status")

    review_complete = (
        review_status != REVIEW_INPUT_REQUIRED
        and not missing
        and not invalid
        and isinstance(accepted_value, bool)
        and _is_nonempty(reference)
        and _is_nonempty(reviewer_scope)
    )
    accepted_for_candidate_gate = (
        review_complete
        and accepted_value is True
        and review_status == REVIEW_ACCEPTED
    )

    if not supplied_review_fields and review_status == REVIEW_INPUT_REQUIRED:
        result_status = "INPUT_REQUIRED"
    elif review_complete and accepted_for_candidate_gate:
        result_status = "ELIGIBLE_FOR_LATER_R9_5_PROMOTION"
    elif review_complete:
        result_status = "REVIEWED_NOT_ACCEPTED_FOR_CANDIDATE_GATE"
    else:
        result_status = "INCOMPLETE_REVIEWED_INPUT"

    return {
        "engine": ENGINE_ID,
        "version": VERSION,
        "package_id": PACKAGE_ID,
        "check": CHECK,
        "status": result_status,
        "review_status": review_status,
        "review_complete": review_complete,
        "screening_proxy_accepted_for_candidate_gate": accepted_for_candidate_gate,
        "eligible_for_r9_5_promotion": accepted_for_candidate_gate,
        "missing_requirements": sorted(set(missing)),
        "invalid_requirements": sorted(set(invalid)),
        "validated_input": payload,
        "safety": {
            "candidate_gate_only": True,
            "automatic_screening_proxy_acceptance": False,
            "automatic_reviewer_identity_generation": False,
            "automatic_professional_review": False,
            "automatic_professional_approval": False,
            "automatic_normative_value_insertion": False,
            "automatic_code_compliance_claim": False,
            "automatic_r9_5_promotion": False,
            "package_c_gate_preserved": True,
            "package_e_gate_preserved": True,
            "existing_r9_5_r9_4_v8_6_gates_preserved": True,
            "professional_structural_review_required": True,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
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


def _explicit_output_dir(kwargs: dict[str, Any]) -> Path | None:
    for key in (
        "output_dir",
        "structural_output_dir",
        "validated_output_dir",
        "evidence_output_dir",
    ):
        path = _path_from_value(kwargs.get(key))
        if path is not None:
            return path
    return None


def run_package_d_weak_storey_screening_review_r9_5_2_7(*args: Any, **kwargs: Any) -> dict[str, Any]:
    payload = discover_package_d_input(*args, **kwargs)
    result = validate_package_d_input(payload)

    output_dir = _explicit_output_dir(kwargs)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "r9_5_2_7_package_d_weak_storey_screening_review.json"
        output_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result["output_file"] = str(output_file)

    return result


run_package_d = run_package_d_weak_storey_screening_review_r9_5_2_7
