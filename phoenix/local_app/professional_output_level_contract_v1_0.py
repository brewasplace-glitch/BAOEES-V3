"""Project Phoenix professional A/B output-level contract v1.0.

This is a routing/state contract over existing Phoenix capabilities. It does not
replace architecture, structural, cost, document, CAD, QA/QC, or release engines.

A = professional project output, not formally released for construction.
B = formal-control target. B remains pending until existing Phoenix professional
review/release gates are positively evidenced. A relevant revision after release
invalidates B-RELEASED and returns the project to B-REVIEW-REQUIRED.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

LEVEL_A = "A"
LEVEL_B = "B"

STATE_A_PROFESSIONAL = "A-PROFESSIONAL"
STATE_B_PENDING = "B-PENDING"
STATE_B_RELEASED = "B-RELEASED"
STATE_B_REVIEW_REQUIRED = "B-REVIEW-REQUIRED"

WORKFLOW_ID = "PHX.PROFESSIONAL_COUNTRY_AWARE_DESIGN_TO_CONSTRUCTION_COST_V1"
SCHEMA_VERSION = "phoenix.professional-output-level-contract/1.0"

A_CAPABILITIES = (
    "PROJECT_INTAKE",
    "ARCHITECTURAL_DESIGN",
    "DRAWINGS_2D",
    "BIM_IFC",
    "STRUCTURAL_ANALYSIS",
    "STRUCTURAL_REPORT",
    "SPECIFICATION",
    "SPECIFICATION_DRAWINGS",
    "QUANTITIES",
    "COST_ESTIMATION",
    "COUNTRY_AWARE_COSTING",
    "DOCX_PDF_EXPORT",
    "CAD_EXPORT",
    "XLSX_EXPORT",
    "QA_QC",
    "SOURCE_TRACEABILITY",
    "FINAL_PACKAGE",
)

B_ADDITIONAL_CAPABILITIES = (
    "PROFESSIONAL_REVIEW",
    "RELEASE_GATE_CONTROL",
    "REVISION_CHANGE_IMPACT",
)

REQUIRED_B_EVIDENCE = (
    "professional_review_complete",
    "release_gates_closed",
    "materials_and_project_inputs_verified",
    "revision_fingerprint_current",
)


class OutputLevelContractError(ValueError):
    pass


def normalize_target_level(value: Any) -> str:
    raw = str(value or LEVEL_A).strip().upper()
    aliases = {
        "A": LEVEL_A,
        "PROFESSIONAL": LEVEL_A,
        "PROFESSIONAL_PROJECT_OUTPUT": LEVEL_A,
        "B": LEVEL_B,
        "FORMAL": LEVEL_B,
        "FOR_CONSTRUCTION": LEVEL_B,
        "FORMALLY_CONTROLLED": LEVEL_B,
    }
    if raw not in aliases:
        raise OutputLevelContractError(f"unsupported output level: {value!r}")
    return aliases[raw]


def _fingerprint_changed(
    revision_fingerprint: str | None,
    released_revision_fingerprint: str | None,
) -> bool:
    current = str(revision_fingerprint or "").strip()
    released = str(released_revision_fingerprint or "").strip()
    return bool(current and released and current != released)


def resolve_output_state(
    target_level: Any,
    *,
    previous_state: str | None = None,
    professional_review_complete: bool = False,
    release_gates_closed: bool = False,
    materials_and_project_inputs_verified: bool = False,
    revision_fingerprint: str | None = None,
    released_revision_fingerprint: str | None = None,
) -> str:
    """Resolve A/B state without fabricating formal approval."""
    target = normalize_target_level(target_level)

    if target == LEVEL_A:
        return STATE_A_PROFESSIONAL

    previous = str(previous_state or "").strip().upper()
    if (
        previous == STATE_B_RELEASED
        and _fingerprint_changed(revision_fingerprint, released_revision_fingerprint)
    ):
        return STATE_B_REVIEW_REQUIRED

    evidence_complete = all(
        (
            professional_review_complete,
            release_gates_closed,
            materials_and_project_inputs_verified,
            bool(str(revision_fingerprint or "").strip()),
        )
    )
    return STATE_B_RELEASED if evidence_complete else STATE_B_PENDING


def build_output_level_contract(
    target_level: Any = LEVEL_A,
    *,
    project_id: str | None = None,
    country_code: str | None = None,
) -> dict[str, Any]:
    target = normalize_target_level(target_level)
    capabilities = list(A_CAPABILITIES)
    if target == LEVEL_B:
        capabilities.extend(B_ADDITIONAL_CAPABILITIES)

    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": WORKFLOW_ID,
        "project_id": str(project_id or "").strip() or None,
        "target_level": target,
        "initial_state": (
            STATE_A_PROFESSIONAL if target == LEVEL_A else STATE_B_PENDING
        ),
        "country_code": str(country_code or "").strip().upper() or None,
        "country_aware_costing_required": True,
        "capabilities": capabilities,
        "formal_release": {
            "automatic_professional_approval": False,
            "automatic_for_construction_release": False,
            "fail_closed": True,
            "required_evidence": list(REQUIRED_B_EVIDENCE),
        },
        "same_project_transition": {
            "A_to_B": True,
            "new_project_required": False,
        },
        "revision_invalidation": {
            "from": STATE_B_RELEASED,
            "to": STATE_B_REVIEW_REQUIRED,
            "when": "relevant_project_revision_changes",
        },
    }


def append_brief_markers(
    brief: Any,
    *,
    target_level: Any,
) -> str:
    target = normalize_target_level(target_level)
    raw = str(brief or "")
    lines = [
        line
        for line in raw.splitlines()
        if not line.strip().startswith("[PHOENIX_PROFESSIONAL_OUTPUT_LEVEL_TARGET=")
        and not line.strip().startswith("[PHOENIX_COUNTRY_AWARE_COSTING=")
        and not line.strip().startswith("[PHOENIX_END_TO_END_MASTER_WORKFLOW=")
    ]
    cleaned = "\n".join(lines).rstrip()
    markers = (
        f"[PHOENIX_PROFESSIONAL_OUTPUT_LEVEL_TARGET={target}]",
        "[PHOENIX_COUNTRY_AWARE_COSTING=REQUIRED]",
        "[PHOENIX_END_TO_END_MASTER_WORKFLOW=v1.0]",
    )
    return (cleaned + "\n\n" if cleaned else "") + "\n".join(markers)


def normalize_project_start_payload(
    payload: dict[str, Any],
    *,
    target_level: Any = None,
) -> dict[str, Any]:
    """Return a copy of a project-start payload with the routing contract attached."""
    result = dict(payload)
    target = normalize_target_level(
        target_level
        if target_level is not None
        else result.get("professional_output_level_target", LEVEL_A)
    )
    result["professional_output_level_target"] = target
    result["professional_output_state"] = (
        STATE_A_PROFESSIONAL if target == LEVEL_A else STATE_B_PENDING
    )
    result["professional_end_to_end_workflow"] = WORKFLOW_ID
    result["country_aware_costing_required"] = True
    result["formal_release_fail_closed"] = True
    result["automatic_professional_approval"] = False
    result["automatic_for_construction_release"] = False
    result["brief"] = append_brief_markers(
        result.get("brief", ""),
        target_level=target,
    )
    return result
