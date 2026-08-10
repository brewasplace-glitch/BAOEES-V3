"""Project Phoenix R9.4 normative applicability and stability design-basis qualification.

R9.4 runs after R9.3 has produced technical evidence for all nine v8.6 stability
checks. It separates technical evidence, project applicability, methodology
acceptance, and traceable acceptance criteria.

Public standards metadata are used only for scope/applicability guidance. They
are never treated as a source of copyrighted National Annex parameter values.
Dutch/Eurocode legal applicability in Suriname is not asserted. A NOT_APPLICABLE
classification does not silently waive the existing mandatory v8.6 check set;
that requires professional review or a future explicit scope-control change.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

ENGINE_ID = "PHX-NORMATIVE-APPLICABILITY-STABILITY-DESIGN-BASIS-QUALIFICATION-R9.4"
VERSION = "R9.4.0"
SCHEMA = "phoenix.normative-applicability-stability-design-basis-qualification/1.0"
LOCKED_RELEASE = "LOCKED"

CHECK_TYPES = (
    "ALTERNATE_LOAD_PATH_EVIDENCE",
    "DIAPHRAGM_CONTINUITY",
    "GLOBAL_BUCKLING_FACTOR",
    "LOAD_PATH_CONTINUITY",
    "SECOND_ORDER_AMPLIFICATION",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "STOREY_STABILITY_INDEX",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
)


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


def _evidence(r93: Mapping[str, Any], check_type: str) -> Mapping[str, Any] | None:
    register = r93.get("qualification_register")
    row = register.get(check_type) if isinstance(register, Mapping) else None
    value = row.get("evidence") if isinstance(row, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _extract_input(
    candidates: Sequence[Any],
    forbidden_paths: Sequence[str],
) -> tuple[dict[str, Any], str | None, list[dict[str, Any]]]:
    rows: list[tuple[int, str, dict[str, Any]]] = []
    warnings: list[dict[str, Any]] = []
    for item in candidates:
        path, data = (
            (item[0], item[1])
            if isinstance(item, (list, tuple)) and len(item) >= 2
            else (None, item)
        )
        if not isinstance(data, Mapping):
            continue
        ptext = str(path or "").replace("\\", "/")
        if any(ptext.endswith(str(x)) for x in forbidden_paths):
            warnings.append({"reason": "R9_4_GENERIC_EXAMPLE_REJECTED", "source": ptext})
            continue
        section = data.get("r9_4_normative_applicability_input")
        if not isinstance(section, Mapping):
            continue
        value = dict(section)
        checks = value.get("checks") if isinstance(value.get("checks"), Mapping) else {}
        jurisdiction = (
            value.get("jurisdictional_basis")
            if isinstance(value.get("jurisdictional_basis"), Mapping)
            else {}
        )
        score = 1000 * len(checks) + 10 * sum(
            1 for v in jurisdiction.values() if v not in (None, "")
        )
        rows.append((score, ptext, value))
    if not rows:
        return {}, None, warnings
    rows.sort(key=lambda x: (-x[0], x[1]))
    return rows[0][2], rows[0][1], warnings


def _source_snapshot(
    registry: Mapping[str, Any],
    source_ids: Sequence[str],
) -> list[dict[str, Any]]:
    sources = registry.get("sources") if isinstance(registry.get("sources"), Mapping) else {}
    out = []
    for sid in source_ids:
        row = sources.get(sid)
        if isinstance(row, Mapping):
            out.append({"source_id": sid, **dict(row)})
    return out


def _acceptance_value(row: Mapping[str, Any], key: str) -> Any:
    criteria = (
        row.get("acceptance_criteria")
        if isinstance(row.get("acceptance_criteria"), Mapping)
        else {}
    )
    return criteria.get(key)


def _explicit_reference_ok(
    row: Mapping[str, Any],
    allowed_reference_types: Sequence[str],
) -> bool:
    return (
        _text(row.get("reference")) != ""
        and _text(row.get("reference_type")) in set(allowed_reference_types)
        and row.get("methodology_accepted") is True
    )


def _project_basis_from_r93(r93: Mapping[str, Any]) -> dict[str, Any]:
    template = r93.get("required_input_template")
    section = (
        template.get("r9_3_stability_design_basis_input")
        if isinstance(template, Mapping)
        else None
    )
    basis = section.get("stability_basis") if isinstance(section, Mapping) else None
    return dict(basis) if isinstance(basis, Mapping) else {}


def _build_v86_check(
    check_type: str,
    evidence: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any] | None:
    reference = _text(decision.get("reference"))
    base: dict[str, Any] = {
        "id": f"R9.4-{check_type}",
        "check_type": check_type,
        "mandatory": True,
        "normative_reference": reference,
        "applicability_status": _text(decision.get("applicability")),
        "reference_type": _text(decision.get("reference_type")),
        "methodology_acceptance_reference": (
            _text(decision.get("methodology_acceptance_reference")) or reference
        ),
        "evidence_reference": (
            _text(decision.get("evidence_reference")) or f"R9.3:{check_type}"
        ),
    }

    if check_type == "SECOND_ORDER_AMPLIFICATION":
        limit = _num(_acceptance_value(decision, "max_amplification_factor"))
        first = _num(evidence.get("first_order_max_horizontal_displacement_m"))
        second = _num(evidence.get("second_order_max_horizontal_displacement_m"))
        if None in (limit, first, second):
            return None
        base.update(
            first_order_displacement_m=first,
            second_order_displacement_m=second,
            max_amplification_factor=limit,
        )
    elif check_type == "GLOBAL_BUCKLING_FACTOR":
        limit = _num(_acceptance_value(decision, "minimum_critical_load_factor"))
        measured = _num(evidence.get("lowest_positive_buckling_factor"))
        if None in (limit, measured):
            return None
        base.update(
            critical_load_factor=measured,
            minimum_critical_load_factor=limit,
        )
    elif check_type == "STOREY_STABILITY_INDEX":
        limit = _num(_acceptance_value(decision, "max_stability_index"))
        values = {
            "gravity_load_kN": _num(evidence.get("gravity_load_above_storey_kN")),
            "storey_drift_m": _num(evidence.get("mean_interstorey_drift_m")),
            "storey_shear_kN": _num(evidence.get("storey_shear_kN")),
            "storey_height_m": _num(evidence.get("storey_height_m")),
        }
        if (
            limit is None
            or any(v is None for v in values.values())
            or not _text(evidence.get("storey_id"))
        ):
            return None
        base.update(
            storey_id=evidence.get("storey_id"),
            max_stability_index=limit,
            **values,
        )
    elif check_type == "TORSIONAL_DRIFT_RATIO":
        limit = _num(_acceptance_value(decision, "max_torsional_drift_ratio"))
        max_d = _num(evidence.get("max_nodal_interstorey_drift_m"))
        avg_d = _num(evidence.get("average_nodal_interstorey_drift_m"))
        if None in (limit, max_d, avg_d) or not _text(evidence.get("storey_id")):
            return None
        base.update(
            storey_id=evidence.get("storey_id"),
            max_edge_drift_m=max_d,
            average_edge_drift_m=avg_d,
            max_torsional_drift_ratio=limit,
        )
    elif check_type == "SOFT_STOREY_STIFFNESS_RATIO":
        limit = _num(_acceptance_value(decision, "minimum_ratio"))
        a = _num(evidence.get("storey_stiffness_kN_per_m"))
        b = _num(evidence.get("reference_stiffness_kN_per_m"))
        if None in (limit, a, b) or not _text(evidence.get("storey_id")):
            return None
        base.update(
            storey_id=evidence.get("storey_id"),
            storey_stiffness_kN_per_m=a,
            reference_stiffness_kN_per_m=b,
            minimum_ratio=limit,
        )
    elif check_type == "WEAK_STOREY_STRENGTH_RATIO":
        gov = (
            evidence.get("governing_candidate")
            if isinstance(evidence.get("governing_candidate"), Mapping)
            else None
        )
        limit = _num(_acceptance_value(decision, "minimum_ratio"))
        if not isinstance(gov, Mapping):
            return None
        a = _num(gov.get("storey_strength_proxy_kN"))
        b = _num(gov.get("reference_strength_proxy_kN"))
        if None in (limit, a, b) or not _text(gov.get("storey_id")):
            return None
        base.update(
            storey_id=gov.get("storey_id"),
            storey_strength_kN=a,
            reference_strength_kN=b,
            minimum_ratio=limit,
            candidate_methodology_status=(
                "R8_RC_SCREENING_PROXY_EXPLICITLY_ACCEPTED_FOR_PROJECT_CANDIDATE_GATE"
            ),
        )
    elif check_type == "DIAPHRAGM_CONTINUITY":
        if evidence.get("continuity_verified") is not True:
            return None
        base.update(continuity_verified=True)
    elif check_type == "LOAD_PATH_CONTINUITY":
        loaded = evidence.get("loaded_nodes")
        edges = evidence.get("load_path_edges")
        if (
            evidence.get("all_loaded_nodes_reach_support") is not True
            or not isinstance(loaded, list)
            or not isinstance(edges, list)
        ):
            return None
        base.update(loaded_nodes=loaded, load_path_edges=edges)
    elif check_type == "ALTERNATE_LOAD_PATH_EVIDENCE":
        verified = decision.get("alternate_path_verified")
        reviewed_ref = _text(
            decision.get("independent_engineering_evidence_reference")
        )
        if verified is not True or not reviewed_ref:
            return None
        base.update(
            alternate_path_verified=True,
            evidence_reference=reviewed_ref,
            screening_snapshot_reference=(
                "R9.3:TOPOLOGY_PLUS_TRACEABLE_CAPACITY_RESERVE_SCREENING"
            ),
        )
    else:
        return None
    return base


def build_normative_applicability_stability_design_basis(
    *,
    project_id: str,
    r93_qualification: Mapping[str, Any],
    candidates: Sequence[Any],
    policy_path: Path,
    source_registry_path: Path,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    registry = _read_json(Path(source_registry_path))
    required = list(policy["required_check_types"])
    input_value, input_source, warnings = _extract_input(
        candidates,
        policy.get("forbidden_project_evidence_paths", []),
    )
    technical = sorted(
        str(x) for x in (r93_qualification.get("technical_evidence_available_for") or [])
    )
    analysis_required = sorted(
        str(x) for x in (r93_qualification.get("analysis_required_for") or [])
    )
    technical_complete = set(required).issubset(set(technical)) and not analysis_required

    decisions = (
        input_value.get("checks")
        if isinstance(input_value.get("checks"), Mapping)
        else {}
    )
    jurisdictional = (
        input_value.get("jurisdictional_basis")
        if isinstance(input_value.get("jurisdictional_basis"), Mapping)
        else {}
    )
    seismic = (
        input_value.get("seismic_applicability")
        if isinstance(input_value.get("seismic_applicability"), Mapping)
        else {}
    )
    profiles = (
        policy.get("check_profiles")
        if isinstance(policy.get("check_profiles"), Mapping)
        else {}
    )
    allowed_states = policy.get("allowed_applicability_states", [])
    allowed_refs = policy.get("allowed_reference_types", [])
    seismic_checks = set(policy.get("seismic_style_check_types", []))

    register: dict[str, dict[str, Any]] = {}
    v86_checks: list[dict[str, Any]] = []
    qualified: list[str] = []
    unresolved: list[str] = []

    for ctype in required:
        profile = profiles.get(ctype) if isinstance(profiles.get(ctype), Mapping) else {}
        decision = decisions.get(ctype) if isinstance(decisions.get(ctype), Mapping) else {}
        evidence = _evidence(r93_qualification, ctype)
        sources = _source_snapshot(
            registry,
            profile.get("source_scope_candidates", []),
        )
        missing: list[str] = []
        applicability = _text(decision.get("applicability"))
        if applicability not in allowed_states:
            missing.append("explicit_applicability_decision")
        if ctype in seismic_checks:
            seismic_status = _text(seismic.get("status"))
            if seismic_status not in {
                "APPLICABLE",
                "NOT_APPLICABLE",
                "ENGINEERING_POLICY_APPLIED",
            }:
                missing.append("seismic_applicability_decision")
        if applicability == "NOT_APPLICABLE":
            missing.append("professional_v8_6_scope_waiver_or_policy_revision")
        elif applicability in {"APPLICABLE", "SUPPLEMENTAL_ENGINEERING_POLICY"}:
            if not _explicit_reference_ok(decision, allowed_refs):
                missing.extend(["methodology_acceptance", "traceable_reference"])
            for field in profile.get("acceptance_criteria_fields", []):
                if _acceptance_value(decision, field) is None:
                    missing.append(field)
            if ctype == "ALTERNATE_LOAD_PATH_EVIDENCE":
                if decision.get("alternate_path_verified") is not True:
                    missing.append("independently_reviewed_alternate_path_verification")
                if not _text(decision.get("independent_engineering_evidence_reference")):
                    missing.append("independent_engineering_evidence_reference")

        row = None
        if (
            technical_complete
            and evidence is not None
            and not missing
            and applicability in {"APPLICABLE", "SUPPLEMENTAL_ENGINEERING_POLICY"}
        ):
            row = _build_v86_check(ctype, evidence, decision)
            if row is None:
                missing.append("v8_6_check_payload_derivation_failed")
        if row is not None:
            v86_checks.append(row)
            qualified.append(ctype)
            state = "QUALIFIED_FOR_V8_6_CANDIDATE_GATE"
        else:
            unresolved.append(ctype)
            state = (
                "QUALIFICATION_INPUT_REQUIRED"
                if applicability != "NOT_APPLICABLE"
                else "NOT_APPLICABLE_REVIEW_REQUIRED"
            )
        register[ctype] = {
            "qualification_state": state,
            "technical_evidence_available": ctype in technical,
            "applicability_candidate": profile.get("applicability_candidate"),
            "project_applicability_decision": applicability or None,
            "public_source_scope_candidates": sources,
            "missing_requirements": sorted(set(missing)),
            "evidence_snapshot": evidence,
            "v8_6_check": row,
        }

    basis = _project_basis_from_r93(r93_qualification)
    basis.update(dict(jurisdictional))
    basis.setdefault("project_jurisdiction", "Suriname / Paramaribo")
    basis.setdefault("engineering_design_methodology", "Eurocode 2 based")
    basis.setdefault("legal_applicability_in_suriname", "NOT_VERIFIED")
    basis["qualification_scope"] = "ENGINEERING_DESIGN_CANDIDATE_ONLY"
    basis["automatic_code_compliance_claim"] = False
    basis["professional_structural_review_required"] = True

    global_input = None
    if technical_complete and len(qualified) == len(required):
        global_input = {
            "stability_basis": basis,
            "stability_checks": [
                next(x for x in v86_checks if x["check_type"] == c)
                for c in required
            ],
            "stability_policy": dict(policy["v8_6_policy"]),
            "release_policy": {
                "automatic_code_compliance_claim": False,
                "automatic_structural_approval": False,
                "automatic_robustness_approval": False,
                "structural_model_release": LOCKED_RELEASE,
            },
        }

    blockers = []
    if not technical_complete:
        blockers.append({
            "reason": "R9_4_R9_3_TECHNICAL_COMPLETION_REQUIRED",
            "message": (
                "R9.4 requires R9.3 technical evidence for all nine checks with "
                "no remaining analysis-required check types."
            ),
            "technical_evidence_available_for": technical,
            "analysis_required_for": analysis_required,
        })
    elif global_input is None:
        blockers.append({
            "reason": "R9_4_NORMATIVE_APPLICABILITY_OR_DESIGN_BASIS_INPUT_REQUIRED",
            "message": (
                "All nine technical checks are evidenced, but explicit applicability "
                "decisions, methodology acceptance, traceable references and/or "
                "acceptance criteria remain required before the existing v8.6 gate can run."
            ),
            "qualified_check_types": sorted(qualified),
            "unresolved_check_types": sorted(unresolved),
            "legal_applicability_in_suriname": basis.get(
                "legal_applicability_in_suriname"
            ),
        })

    template_checks: dict[str, dict[str, Any]] = {}
    for ctype in required:
        profile = profiles.get(ctype, {})
        template_checks[ctype] = {
            "applicability": None,
            "methodology_accepted": False,
            "methodology_acceptance_reference": None,
            "reference_type": None,
            "reference": None,
            "acceptance_criteria": {
                field: None
                for field in profile.get("acceptance_criteria_fields", [])
            },
            "evidence_reference": f"R9.3:{ctype}",
        }
        if ctype == "ALTERNATE_LOAD_PATH_EVIDENCE":
            template_checks[ctype]["alternate_path_verified"] = False
            template_checks[ctype]["independent_engineering_evidence_reference"] = None

    template = {
        "schema_version": "phoenix.r9-4-normative-applicability-input-template/1.0",
        "r9_4_normative_applicability_input": {
            "jurisdictional_basis": {
                "project_jurisdiction": basis.get(
                    "project_jurisdiction",
                    "Suriname / Paramaribo",
                ),
                "engineering_design_methodology": basis.get(
                    "engineering_design_methodology",
                    "Eurocode 2 based",
                ),
                "legal_applicability_in_suriname": "NOT_VERIFIED",
                "professional_review_status": "REQUIRED",
            },
            "seismic_applicability": {
                "status": None,
                "reference_type": None,
                "reference": None,
                "note": (
                    "Eurocode 8 scope applies to seismic regions; applicability to "
                    "this Paramaribo project must be explicitly established or rejected "
                    "by a traceable project basis."
                ),
            },
            "checks": template_checks,
            "notes": [
                "Public standards metadata in the R9.4 source registry do not supply copyrighted clause values or National Annex parameters.",
                "Use LICENSED_STANDARD_SOURCE, AUTHORITY_APPROVED_PROJECT_BASIS or explicit PROJECT_ENGINEERING_POLICY references for project qualification.",
                "NOT_APPLICABLE does not silently remove a mandatory v8.6 check; professional scope review is required.",
                "R8/R9.3 weak-storey capacity is a screening proxy only.",
                "R9.3 alternate-path evidence is a topology/capacity-reserve screening snapshot and is not redistributed nonlinear member-removal proof.",
                "Automatic code compliance, structural approval and production release remain disabled/locked.",
            ],
        },
        "public_source_registry_snapshot": registry,
        "r9_3_technical_completion_snapshot": {
            "technical_evidence_available_for": technical,
            "analysis_required_for": analysis_required,
        },
    }

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "PASSED" if global_input is not None else "BLOCKED",
        "source_states": {
            "r9_3_status": r93_qualification.get("status"),
            "explicit_input_source": input_source,
            "public_source_snapshot_date": registry.get("snapshot_date"),
        },
        "technical_completion": {
            "required_check_type_count": len(required),
            "technical_evidence_available_count": len(
                set(required).intersection(technical)
            ),
            "analysis_required_check_type_count": len(analysis_required),
            "complete": technical_complete,
        },
        "applicability_register": register,
        "qualified_check_types": sorted(qualified),
        "unresolved_check_types": sorted(unresolved),
        "project_stability_design_basis": basis,
        "global_stability_input": global_input,
        "required_input_template": template,
        "public_source_registry": registry,
        "summary": {
            "required_check_type_count": len(required),
            "technical_evidence_available_count": len(
                set(required).intersection(technical)
            ),
            "analysis_required_check_type_count": len(analysis_required),
            "qualified_for_v8_6_count": len(qualified),
            "unresolved_qualification_count": len(unresolved),
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            "normative_limits_invented": False,
            "copyrighted_national_annex_values_embedded": False,
            "legal_applicability_in_suriname_invented": False,
            "public_source_scope_promoted_to_exact_check_limit": False,
            "not_applicable_auto_waives_v8_6": False,
            "r8_screening_resistance_promoted_to_code_strength_without_acceptance": False,
            "alternate_path_screening_promoted_to_redistributed_analysis": False,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "automatic_robustness_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
