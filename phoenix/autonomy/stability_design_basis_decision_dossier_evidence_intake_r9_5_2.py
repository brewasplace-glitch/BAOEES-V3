from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

ENGINE_ID = "PHX-STABILITY-DESIGN-BASIS-DECISION-DOSSIER-EVIDENCE-INTAKE-R9.5.2"
VERSION = "R9.5.2"
SCHEMA = "phoenix.stability-design-basis-decision-dossier-evidence-intake/1.0"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _deep_merge_preserve_explicit(base: Any, existing: Any) -> Any:
    if isinstance(base, Mapping) and isinstance(existing, Mapping):
        out = deepcopy(dict(base))
        for key, value in existing.items():
            if key in out:
                out[key] = _deep_merge_preserve_explicit(out[key], value)
            elif _nonempty(value):
                out[key] = deepcopy(value)
        return out
    if _nonempty(existing):
        return deepcopy(existing)
    return deepcopy(base)


def _default_package_input(package_id: str, definition: Mapping[str, Any]) -> dict[str, Any]:
    fields = list(definition.get("required_input_fields") or [])
    values: dict[str, Any] = {}
    for field in fields:
        if field in {"licensed_use_confirmed", "extraction_reviewed", "professional_scope_reviewed",
                     "screening_proxy_accepted_for_candidate_gate", "independently_verified_alternate_path"}:
            values[field] = False
        elif field == "criteria":
            values[field] = {
                "GLOBAL_BUCKLING_FACTOR": {"minimum_critical_load_factor": None},
                "SECOND_ORDER_AMPLIFICATION": {"max_amplification_factor": None},
                "STOREY_STABILITY_INDEX": {"max_stability_index": None},
            }
        elif field == "criteria_if_applicable":
            values[field] = {
                "SOFT_STOREY_STIFFNESS_RATIO": {"minimum_ratio": None},
                "TORSIONAL_DRIFT_RATIO": {"max_torsional_drift_ratio": None},
                "WEAK_STOREY_STRENGTH_RATIO": {"minimum_ratio": None},
            }
        elif field == "acceptance_criterion_and_traceability":
            values[field] = {
                "minimum_residual_capacity_proxy_ratio": None,
                "source_record_id": None,
                "clause_reference": None,
            }
        else:
            values[field] = None
    return {
        "package_id": package_id,
        "status": "INPUT_REQUIRED",
        "label": definition.get("label"),
        "checks": list(definition.get("checks") or []),
        "inputs": values,
        "validation": {
            "qualified": False,
            "qualification_message": "R9.5.2 collects evidence only; R9.5/R9.4/v8.6 remain the qualification gates.",
        },
    }


def _dossier_packages(
    package_definitions: Mapping[str, Any],
    r951_result: Mapping[str, Any],
) -> dict[str, Any]:
    matrix = _mapping(r951_result.get("evidence_requirement_matrix"))
    out: dict[str, Any] = {}
    for package_id, raw in package_definitions.items():
        definition = _mapping(raw)
        checks = list(definition.get("checks") or [])
        check_rows = {}
        for check in checks:
            row = _mapping(matrix.get(check))
            check_rows[check] = {
                "technical_evidence_reference": row.get("technical_evidence_reference"),
                "r9_5_state": row.get("r9_5_state"),
                "remaining_requirements": list(row.get("remaining_requirements") or []),
                "suriname_primary_support": list(row.get("suriname_primary_support") or []),
                "numerical_acceptance_criterion_still_required": bool(
                    row.get("numerical_acceptance_criterion_still_required")
                ),
                "professional_or_independent_review_required": bool(
                    row.get("professional_or_independent_review_required")
                ),
            }
        out[str(package_id)] = {
            "label": definition.get("label"),
            "purpose": definition.get("purpose"),
            "checks": checks,
            "known_check_state": check_rows,
            "required_input_fields": list(definition.get("required_input_fields") or []),
            "acceptable_source_types": list(definition.get("acceptable_source_types") or []),
            "status": "INPUT_REQUIRED",
        }
    return out


def build_stability_design_basis_decision_dossier_evidence_intake(
    *,
    project_id: str,
    r951_result: Mapping[str, Any],
    policy_path: Path,
    existing_intake: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    safety = dict(policy.get("safety") or {})
    package_defs = _mapping(policy.get("package_definitions"))
    r951_status = str(r951_result.get("status") or "").strip()

    if r951_status == "PASSED":
        return {
            "schema_version": SCHEMA,
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "PASSED",
            "decision_dossier": {
                "status": "NOT_REQUIRED_R9_5_1_ALREADY_PASSED",
                "packages": {},
            },
            "evidence_intake": {},
            "blockers": [],
            "summary": {
                "technical_analysis_required_count": 0,
                "package_count": 0,
                "completed_package_count": 0,
                "unresolved_package_count": 0,
                "preserved_existing_input_value_count": 0,
            },
            "safety": safety,
        }

    scaffold_root = _mapping(r951_result.get("prefilled_project_input"))
    scaffold = _mapping(scaffold_root.get("r9_5_project_stability_design_basis_decision"))
    if not scaffold:
        return {
            "schema_version": SCHEMA,
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "BLOCKED",
            "decision_dossier": {
                "status": "BLOCKED_MISSING_R9_5_1_SCAFFOLD",
                "packages": {},
            },
            "evidence_intake": {},
            "blockers": [{
                "reason": "R9_5_2_R9_5_1_SCAFFOLD_REQUIRED",
                "message": "R9.5.2 requires the R9.5.1 project-specific input scaffold.",
            }],
            "summary": {
                "technical_analysis_required_count": 0,
                "package_count": len(package_defs),
                "completed_package_count": 0,
                "unresolved_package_count": len(package_defs),
                "preserved_existing_input_value_count": 0,
            },
            "safety": safety,
        }

    package_inputs = {
        package_id: _default_package_input(package_id, _mapping(definition))
        for package_id, definition in package_defs.items()
    }

    # Seed only traceable, already-known project facts and source records.
    source_records = deepcopy(_mapping(scaffold.get("source_records")))
    project_basis = deepcopy(_mapping(scaffold.get("jurisdictional_basis")))
    seismic_scope = deepcopy(_mapping(scaffold.get("seismic_applicability")))
    checks = deepcopy(_mapping(scaffold.get("checks")))

    base_intake = {
        "schema_version": "phoenix.r9-5-2-stability-design-basis-evidence-intake/1.0",
        "project_id": project_id,
        "project_basis": project_basis,
        "source_records": source_records,
        "seismic_scope": seismic_scope,
        "checks_snapshot": checks,
        "package_inputs": package_inputs,
        "intake_metadata": {
            "status": "DRAFT_INPUT_REQUIRING_EXPLICIT_SOURCE_REVIEW_DECISIONS",
            "generated_by": ENGINE_ID,
            "technical_analysis_required_count": 0,
            "automatic_normative_value_insertion": False,
            "automatic_seismic_applicability_decision": False,
            "automatic_project_policy_approval": False,
            "automatic_professional_review": False,
            "professional_review_required": True,
            "production_release": "LOCKED",
        },
    }

    existing = _mapping(existing_intake)
    merged = _deep_merge_preserve_explicit(base_intake, existing)

    preserved_count = 0
    existing_packages = _mapping(existing.get("package_inputs"))
    for package_id, row in existing_packages.items():
        inputs = _mapping(_mapping(row).get("inputs"))
        preserved_count += sum(1 for value in inputs.values() if _nonempty(value))

    dossier = {
        "status": "DECISION_DOSSIER_GENERATED_INPUT_REQUIRED",
        "project_basis": project_basis,
        "technical_status": {
            "r9_3_technical_evidence_count": _mapping(
                _mapping(r951_result.get("source_states")).get("r9_5_summary")
            ).get("r9_3_technical_evidence_count", 9),
            "technical_analysis_required_count": _mapping(
                r951_result.get("summary")
            ).get("technical_analysis_required_count", 0),
            "r9_5_1_remaining_decision_check_count": _mapping(
                r951_result.get("summary")
            ).get("remaining_decision_check_count", 9),
        },
        "packages": _dossier_packages(package_defs, r951_result),
        "instructions": {
            "preferred_workflow": [
                "Attach or register traceable licensed/authority/project-policy sources.",
                "Record exact clause/reference and checksum where a source file is used.",
                "Record professional scope/review decisions explicitly.",
                "Do not enter generic example limits or unverified background values.",
                "Rerun PHOENIX-PAT-001 only after the required package inputs are populated.",
            ],
            "qualification_gate": "R9.5 then R9.4 then existing v8.6 verifier",
        },
    }

    blocker = {
        "reason": "R9_5_2_STABILITY_DESIGN_BASIS_EVIDENCE_INTAKE_REQUIRED",
        "message": (
            "Technical stability analysis is complete. R9.5.2 generated the decision dossier "
            "and evidence-intake package. Explicit source, numerical-criteria, seismic-scope "
            "and professional/independent-review inputs remain required; none were invented."
        ),
        "unresolved_package_ids": list(package_defs),
        "technical_analysis_required_count": 0,
    }

    return {
        "schema_version": SCHEMA,
        "engine": ENGINE_ID,
        "version": VERSION,
        "project_id": project_id,
        "status": "BLOCKED",
        "source_states": {
            "r9_5_1_status": r951_result.get("status"),
            "r9_5_1_summary": r951_result.get("summary"),
            "r9_5_1_blockers": r951_result.get("blockers"),
        },
        "decision_dossier": dossier,
        "evidence_intake": merged,
        "blockers": [blocker],
        "summary": {
            "technical_analysis_required_count": 0,
            "package_count": len(package_defs),
            "completed_package_count": 0,
            "unresolved_package_count": len(package_defs),
            "preserved_existing_input_value_count": preserved_count,
            "suriname_primary_source_record_count": sum(
                1 for key in source_records if str(key).startswith("SURINAME_BOUWBESLUIT_")
            ),
        },
        "safety": safety,
    }


def render_decision_dossier_markdown(result: Mapping[str, Any]) -> str:
    dossier = _mapping(result.get("decision_dossier"))
    summary = _mapping(result.get("summary"))
    project_basis = _mapping(dossier.get("project_basis"))
    packages = _mapping(dossier.get("packages"))

    lines = [
        "# PROJECT PHOENIX — R9.5.2 Stability Design-Basis Decision Dossier",
        "",
        f"Project: `{result.get('project_id')}`",
        f"Status: `{result.get('status')}`",
        "",
        "## Projectbasis",
        "",
        f"- Jurisdiction: `{project_basis.get('project_jurisdiction')}`",
        f"- Engineering methodology: `{project_basis.get('engineering_design_methodology')}`",
        f"- Suriname legal status 2026: `{project_basis.get('current_2026_surinaame_legal_status')}`",
        f"- Eurocode 2 legal adoption: `{project_basis.get('eurocode_2_legal_adoption')}`",
        f"- Qualification scope: `{project_basis.get('qualification_scope')}`",
        f"- Professional review: `{project_basis.get('professional_review')}`",
        "",
        "## Engineeringstatus",
        "",
        f"- Technical analyses still required: `{summary.get('technical_analysis_required_count')}`",
        f"- Evidence/decision packages: `{summary.get('package_count')}`",
        f"- Unresolved packages: `{summary.get('unresolved_package_count')}`",
        "",
        "## Resterende evidence- en beslispakketten",
        "",
    ]
    for package_id, raw in packages.items():
        row = _mapping(raw)
        lines.extend([
            f"### {package_id} — {row.get('label')}",
            "",
            str(row.get("purpose") or ""),
            "",
            "Checks:",
        ])
        for check in row.get("checks") or []:
            lines.append(f"- `{check}`")
        lines.extend(["", "Benodigde input:"])
        for field in row.get("required_input_fields") or []:
            lines.append(f"- `{field}`")
        lines.append("")
    lines.extend([
        "## Veiligheidsstatus",
        "",
        "- Geen normatieve grenswaarden automatisch ingevuld.",
        "- Geen seismische applicability automatisch beslist.",
        "- Geen project-policy automatisch goedgekeurd.",
        "- Geen professionele of onafhankelijke review automatisch geclaimd.",
        "- R9.5, R9.4 en v8.6 blijven de qualification gates.",
        "- For-construction / production release blijft `LOCKED`.",
        "",
    ])
    return "\n".join(lines)
