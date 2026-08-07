"""Autonomous v8.5 member-verification prerequisite derivation.

This module does NOT calculate reinforced-concrete resistance and does NOT
invent normative parameters. It converts a missing generic v8.5 input into a
specific, machine-readable engineering evidence requirement.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


ENGINE_ID = "PHX-AUTONOMOUS-MEMBER-VERIFICATION-PREREQUISITE-V8.5-R7"
VERSION = "1.0.0"

RC_TOKENS = (
    "REINFORCED-CONCRETE",
    "REINFORCED_CONCRETE",
    "RC-",
    "MAT-RC",
)


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_rc_member(member: Mapping[str, Any]) -> bool:
    haystack = " ".join(
        (
            _text(member.get("material_id")).upper(),
            _text(member.get("section_id")).upper(),
            _text(member.get("material_family")).upper(),
            _text(member.get("section_family")).upper(),
        )
    )
    return any(token in haystack for token in RC_TOKENS)


def _summary(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    material_counts = Counter(_text(m.get("material_id")) or "<UNSPECIFIED>" for m in members)
    section_counts = Counter(_text(m.get("section_id")) or "<UNSPECIFIED>" for m in members)
    rc_members = [m for m in members if _is_rc_member(m)]

    return {
        "member_count": len(members),
        "rc_member_count": len(rc_members),
        "material_counts": dict(sorted(material_counts.items())),
        "section_counts": dict(sorted(section_counts.items())),
        "rc_member_ids": [_text(m.get("id")) for m in rc_members if _text(m.get("id"))],
    }


def derive_member_verification_prerequisite(
    *,
    project_id: str,
    analytical_model: Mapping[str, Any],
    architecture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed prerequisite artifact for missing v8.5 input."""

    members = [
        item
        for item in _items((analytical_model or {}).get("members"))
        if isinstance(item, Mapping)
    ]
    model_summary = _summary(members)

    base = {
        "schema_version": "phoenix.autonomous-member-verification-prerequisite/1.0",
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": str(project_id),
        "status": "BLOCKED_INPUT",
        "model_summary": model_summary,
        "automatic_normative_value_invention": False,
        "automatic_member_capacity_invention": False,
        "automatic_code_compliance_claim": False,
        "automatic_structural_approval": False,
        "production_release": "LOCKED",
    }

    if model_summary["rc_member_count"] > 0:
        base.update(
            {
                "reason": "RC_MEMBER_DESIGN_RESISTANCE_EVIDENCE_REQUIRED",
                "message": (
                    "Gewapend-betonnen members zijn aanwezig, maar expliciete "
                    "projectspecifieke RC-ontwerpbasis, wapening en traceerbare "
                    "member-design-resistance evidence ontbreken voor v8.5."
                ),
                "required_evidence": [
                    {
                        "id": "RC_DESIGN_CODE_BASIS",
                        "description": (
                            "Expliciete projectspecifieke RC-ontwerpbasis met jurisdiction, "
                            "standard_set, edition, source_reference en reviewstatus."
                        ),
                        "mandatory": True,
                    },
                    {
                        "id": "RC_MATERIAL_DESIGN_PROPERTIES",
                        "description": (
                            "Traceerbare ontwerpsterkten en partiele factoren voor beton en "
                            "wapeningsstaal; analyse-only E-modulus/dichtheid is onvoldoende."
                        ),
                        "mandatory": True,
                    },
                    {
                        "id": "RC_REINFORCEMENT_LAYOUT_PER_MEMBER_OR_GROUP",
                        "description": (
                            "Wapening per member of aantoonbaar gekoppelde membergroep, "
                            "inclusief staalsoort, diameter/aantal/oppervlak en dekking waar relevant."
                        ),
                        "mandatory": True,
                    },
                    {
                        "id": "RC_MEMBER_RESISTANCE_DERIVATION",
                        "description": (
                            "Traceerbare N/M/V- en interactie-/knikweerstanden of voldoende "
                            "projectdata om deze volgens de goedgekeurde ontwerpbasis af te leiden."
                        ),
                        "mandatory": True,
                    },
                    {
                        "id": "RC_SLS_VERIFICATION_LIMITS",
                        "description": (
                            "Expliciete projectspecifieke SLS-limieten en normative_reference "
                            "voor de vereiste member-verificaties."
                        ),
                        "mandatory": True,
                    },
                ],
                "next_autonomous_capability": "RC_DESIGN_CANDIDATE_ENGINE_REQUIRED",
                "engineering_review_required": True,
            }
        )
        return base

    base.update(
        {
            "reason": "STRUCTURAL_CODE_BASIS_AND_MEMBER_VERIFICATION_RULES_REQUIRED",
            "message": "Expliciete codebasis en member-verification regels zijn vereist voor v8.5.",
            "required_evidence": [
                {
                    "id": "MEMBER_VERIFICATION_INPUT",
                    "description": "code_basis, verification_rules en verification_policy",
                    "mandatory": True,
                }
            ],
            "engineering_review_required": True,
        }
    )
    return base