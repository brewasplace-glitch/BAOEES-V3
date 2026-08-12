from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from .package_b_licensed_source_traceability_r9_5_2_3 import (
    apply_package_b_traceability_to_r9_5_required_input_document as _phoenix_apply_r9_5_2_3_package_b_to_r9_5_input,
    apply_package_b_traceability_to_r9_5_2_result as _phoenix_apply_r9_5_2_3_package_b_to_r9_5_2_result,
)

ENGINE_ID = "PHX-STABILITY-A-B-PROJECT-POLICY-INTEGRATION-R9.5.2.2"
VERSION = "R9.5.2.2"
POLICY_SOURCE_RECORD_ID = "PROJECT_STABILITY_POLICY_REQUIRED"

PACKAGE_A = "PKG-A-STABILITY-METHODOLOGY-DECISION"
PACKAGE_B = "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"

A_CHECKS = (
    "DIAPHRAGM_CONTINUITY",
    "GLOBAL_BUCKLING_FACTOR",
    "LOAD_PATH_CONTINUITY",
    "SECOND_ORDER_AMPLIFICATION",
    "STOREY_STABILITY_INDEX",
)
B_CHECKS = (
    "GLOBAL_BUCKLING_FACTOR",
    "SECOND_ORDER_AMPLIFICATION",
    "STOREY_STABILITY_INDEX",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _empty(value: Any) -> bool:
    return value in (None, "", [], {})


def _project_matches(project_id: str | None, jurisdiction: str | None, policy: Mapping[str, Any]) -> bool:
    expected_project = str(policy.get("project_id") or "").strip()
    expected_jurisdiction = str(policy.get("jurisdiction") or "").strip().lower()
    got_project = str(project_id or "").strip()
    got_jurisdiction = str(jurisdiction or "").strip().lower()
    return (
        (not expected_project or got_project == expected_project)
        and (not expected_jurisdiction or expected_jurisdiction == got_jurisdiction)
    )


def _project_policy_record(policy: Mapping[str, Any], existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = deepcopy(dict(existing or {}))
    decision = _mapping(policy.get("decision_origin"))
    package_a = _mapping(policy.get("package_a"))
    row.update({
        "reference_type": "PROJECT_ENGINEERING_POLICY",
        "reference": package_a.get("methodology_reference"),
        "project_policy_approved": True,
        "approval_reference": decision.get("decision_reference"),
        "approval_date": decision.get("decision_date"),
        "qualification_scope": decision.get("qualification_scope"),
        "scope": (
            "R9.5/v8.6 non-seismic stability methodology for PHOENIX-PAT-001. "
            "Package B numerical values remain project-policy candidates until licensed source traceability is completed."
        ),
        "legal_or_normative_status": "PROJECT_ENGINEERING_POLICY_ONLY",
        "professional_review_required": True,
    })
    return row


def apply_ab_policy_to_r9_5_required_input_document(
    document: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    out = deepcopy(dict(document))
    root = _mapping(out.get("r9_5_project_stability_design_basis_decision"))
    if not root:
        return out

    basis = _mapping(root.get("jurisdictional_basis"))
    if not _project_matches(
        str(out.get("project_id") or root.get("project_id") or policy.get("project_id") or ""),
        str(basis.get("project_jurisdiction") or ""),
        policy,
    ):
        return out

    source_records = _mapping(root.get("source_records"))
    source_records[POLICY_SOURCE_RECORD_ID] = _project_policy_record(
        policy, _mapping(source_records.get(POLICY_SOURCE_RECORD_ID))
    )
    root["source_records"] = source_records

    checks = _mapping(root.get("checks"))
    for check_id in A_CHECKS:
        row = _mapping(checks.get(check_id))
        if not row:
            continue
        if _empty(row.get("applicability")):
            row["applicability"] = "APPLICABLE"
        if _empty(row.get("methodology_acceptance_reference")):
            row["methodology_accepted"] = True
            row["methodology_acceptance_reference"] = POLICY_SOURCE_RECORD_ID
        if _empty(row.get("primary_source_record_id")):
            row["primary_source_record_id"] = POLICY_SOURCE_RECORD_ID
        row["r9_5_2_2_project_policy_methodology"] = {
            "policy_id": policy.get("policy_id"),
            "approval_reference": _mapping(policy.get("decision_origin")).get("decision_reference"),
            "status": "APPROVED_FOR_ENGINEERING_DESIGN_CANDIDATE_ONLY",
        }
        checks[check_id] = row

    candidate_criteria = deepcopy(_mapping(_mapping(policy.get("package_b")).get("candidate_criteria")))
    for check_id in B_CHECKS:
        row = _mapping(checks.get(check_id))
        if not row:
            continue
        row["r9_5_2_2_candidate_project_policy_criteria"] = deepcopy(
            _mapping(candidate_criteria.get(check_id))
        )
        row["r9_5_2_2_licensed_source_traceability_required"] = True
        checks[check_id] = row

    root["checks"] = checks
    root["r9_5_2_2_ab_policy"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "policy_id": policy.get("policy_id"),
        "package_a_status": "PROJECT_POLICY_APPROVED",
        "package_b_status": "PROJECT_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED",
        "actual_r9_5_numerical_acceptance_criteria_promoted": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    out["r9_5_project_stability_design_basis_decision"] = root
    return out


def apply_ab_project_policy_to_workspace(
    *,
    workspace: Path,
    policy_path: Path,
) -> dict[str, Any]:
    policy = _read_json(Path(policy_path))
    path = Path(workspace) / "inputs" / "structural" / "global_stability_engineering_input_REQUIRED.json"

    if not path.is_file():
        return {
            "engine": ENGINE_ID,
            "version": VERSION,
            "status": "SCAFFOLD_NOT_FOUND_NO_CHANGE",
            "path": str(path),
        }

    original = _read_json(path)
    updated = apply_ab_policy_to_r9_5_required_input_document(original, policy)
    repo_root = Path(policy_path).resolve().parents[3]
    traceability_registry_path = repo_root / "configs" / "phoenix" / "structural" / "package_b_licensed_source_traceability_r9_5_2_3.json"
    updated = _phoenix_apply_r9_5_2_3_package_b_to_r9_5_input(
        updated,
        repo_root=repo_root,
        registry_path=traceability_registry_path,
    )

    if updated == original:
        return {
            "engine": ENGINE_ID,
            "version": VERSION,
            "status": "NO_CHANGE",
            "path": str(path),
        }

    _write_json(path, updated)
    return {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "PROJECT_POLICY_APPLIED_TO_R9_5_INPUT",
        "path": str(path),
        "package_a_status": "PROJECT_POLICY_APPROVED",
        "package_b_status": "PROJECT_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED",
        "numerical_acceptance_criteria_promoted": False,
    }


def apply_ab_project_policy_to_r9_5_2_result(
    *,
    r952_result: Mapping[str, Any],
    policy_path: Path,
) -> dict[str, Any]:
    result = deepcopy(dict(r952_result))
    policy = _read_json(Path(policy_path))
    if str(result.get("status") or "") == "PASSED":
        return result

    intake = _mapping(result.get("evidence_intake"))
    basis = _mapping(intake.get("project_basis"))
    if not _project_matches(
        str(result.get("project_id") or intake.get("project_id") or ""),
        str(basis.get("project_jurisdiction") or ""),
        policy,
    ):
        result["r9_5_2_2"] = {
            "engine": ENGINE_ID,
            "version": VERSION,
            "status": "NOT_APPLIED_SCOPE_MISMATCH",
        }
        return result

    source_records = _mapping(intake.get("source_records"))
    source_records[POLICY_SOURCE_RECORD_ID] = _project_policy_record(
        policy, _mapping(source_records.get(POLICY_SOURCE_RECORD_ID))
    )
    intake["source_records"] = source_records

    package_inputs = _mapping(intake.get("package_inputs"))
    package_a = _mapping(package_inputs.get(PACKAGE_A))
    package_a_inputs = _mapping(package_a.get("inputs"))
    a = _mapping(policy.get("package_a"))
    for key in (
        "decision_status",
        "methodology_reference_type",
        "methodology_reference",
        "approval_or_clause_reference",
        "scope",
    ):
        if _empty(package_a_inputs.get(key)):
            package_a_inputs[key] = deepcopy(a.get(key))
    package_a["inputs"] = package_a_inputs
    package_a["status"] = "PROJECT_POLICY_APPROVED_R9_5_QUALIFICATION_GATE_PRESERVED"
    package_a["validation"] = {
        "qualified": False,
        "project_policy_approved": True,
        "qualification_message": (
            "Package A project engineering policy is explicitly approved. "
            "R9.5/R9.4/v8.6 remain the qualification gates."
        ),
    }
    package_inputs[PACKAGE_A] = package_a

    package_b = _mapping(package_inputs.get(PACKAGE_B))
    package_b_inputs = _mapping(package_b.get("inputs"))
    b = _mapping(policy.get("package_b"))
    candidates = _mapping(b.get("candidate_criteria"))
    criteria = _mapping(package_b_inputs.get("criteria"))
    for check_id, candidate in candidates.items():
        c = _mapping(candidate)
        row = _mapping(criteria.get(check_id))
        for key, value in c.items():
            if key in {
                "max_amplification_factor",
                "minimum_critical_load_factor",
                "max_stability_index",
            } and _empty(row.get(key)):
                row[key] = value
        criteria[check_id] = row
    package_b_inputs["criteria"] = criteria
    package_b_inputs["criteria_classification"] = {
        check_id: {
            "classification": _mapping(candidate).get("classification"),
            "policy_basis": _mapping(candidate).get("policy_basis"),
        }
        for check_id, candidate in candidates.items()
    }
    package_b_inputs["source_record_id"] = package_b_inputs.get("source_record_id")
    package_b_inputs["source_file"] = package_b_inputs.get("source_file")
    package_b_inputs["sha256"] = package_b_inputs.get("sha256")
    package_b_inputs["clause_reference"] = package_b_inputs.get("clause_reference")
    package_b_inputs["licensed_use_confirmed"] = bool(package_b_inputs.get("licensed_use_confirmed"))
    package_b_inputs["extraction_reviewed"] = bool(package_b_inputs.get("extraction_reviewed"))
    package_b["inputs"] = package_b_inputs
    package_b["status"] = "PROJECT_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED"
    package_b["validation"] = {
        "qualified": False,
        "project_policy_criteria_approved": True,
        "licensed_source_traceability_complete": False,
        "qualification_message": (
            "Package B numerical project-policy criteria are approved, but licensed source file, checksum, "
            "clause traceability, licensed-use confirmation and extraction review remain required for final R9.5."
        ),
    }
    package_inputs[PACKAGE_B] = package_b
    intake["package_inputs"] = package_inputs

    checks = _mapping(intake.get("checks_snapshot"))
    for check_id in A_CHECKS:
        row = _mapping(checks.get(check_id))
        if not row:
            continue
        if _empty(row.get("applicability")):
            row["applicability"] = "APPLICABLE"
        if _empty(row.get("methodology_acceptance_reference")):
            row["methodology_accepted"] = True
            row["methodology_acceptance_reference"] = POLICY_SOURCE_RECORD_ID
        if _empty(row.get("primary_source_record_id")):
            row["primary_source_record_id"] = POLICY_SOURCE_RECORD_ID
        checks[check_id] = row

    for check_id in B_CHECKS:
        row = _mapping(checks.get(check_id))
        if not row:
            continue
        row["r9_5_2_2_candidate_project_policy_criteria"] = deepcopy(
            _mapping(candidates.get(check_id))
        )
        row["r9_5_2_2_licensed_source_traceability_required"] = True
        checks[check_id] = row
    intake["checks_snapshot"] = checks

    metadata = _mapping(intake.get("intake_metadata"))
    metadata["r9_5_2_2_ab_project_policy"] = {
        "status": "RECORDED",
        "policy_id": policy.get("policy_id"),
        "package_a_project_policy_approved": True,
        "package_b_project_policy_criteria_approved": True,
        "package_b_licensed_source_traceability_complete": False,
        "automatic_code_compliance_claim": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    intake["intake_metadata"] = metadata
    result["evidence_intake"] = intake
    repo_root = Path(policy_path).resolve().parents[3]
    traceability_registry_path = repo_root / "configs" / "phoenix" / "structural" / "package_b_licensed_source_traceability_r9_5_2_3.json"
    result = _phoenix_apply_r9_5_2_3_package_b_to_r9_5_2_result(
        result,
        repo_root=repo_root,
        registry_path=traceability_registry_path,
    )

    result["r9_5_2_2"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "status": "A_B_PROJECT_POLICY_RECORDED_LICENSED_SOURCE_TRACEABILITY_REQUIRED",
        "policy_id": policy.get("policy_id"),
        "package_a_status": "PROJECT_POLICY_APPROVED",
        "package_b_status": "PROJECT_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED",
        "candidate_criteria": deepcopy(candidates),
        "actual_r9_5_numerical_acceptance_criteria_promoted": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }

    blockers = list(result.get("blockers") or [])
    if blockers and isinstance(blockers[0], Mapping):
        blocker = dict(blockers[0])
        blocker["message"] = (
            "Technical stability analysis is complete. Packages A and B project engineering policy decisions "
            "are recorded. Package B still requires licensed/full-source clause traceability before numerical "
            "criteria may be promoted into the R9.5 acceptance fields. No code-compliance or approval claim is made."
        )
        blocker["r9_5_2_2_ab_policy_status"] = (
            "A_APPROVED_B_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED"
        )
        blockers[0] = blocker
        result["blockers"] = blockers

    return result


def render_licensed_clause_extract_request(result: Mapping[str, Any]) -> str:
    state = _mapping(result.get("r9_5_2_2"))
    return "\n".join([
        "# PROJECT PHOENIX — Licensed EC2 Clause Extract Required",
        "",
        f"Project: `{result.get('project_id')}`",
        f"R9.5.2.2 status: `{state.get('status')}`",
        "",
        "Package A project engineering policy has been recorded.",
        "Package B candidate criteria have been explicitly approved as project-policy candidates:",
        "",
        "- `SECOND_ORDER_AMPLIFICATION`: max `1.10`",
        "- `GLOBAL_BUCKLING_FACTOR`: min `11.0` — derived project-policy proxy, not a literal EC2 alpha_cr limit",
        "- `STOREY_STABILITY_INDEX`: max `0.10` — Phoenix PΔ/(Vh) project-policy proxy, not a literal EC2 storey-index clause",
        "",
        "## Remaining source-traceability requirement",
        "",
        "Provide a lawfully accessible extract from the applicable NEN-EN 1992-1-1 source and current Dutch National Annex",
        "covering the stability / second-order clauses used by this project policy, preferably:",
        "",
        "- NEN-EN 1992-1-1 clause 5.8.2(6)",
        "- NEN-EN 1992-1-1 clause 5.8.3.3 and relevant subclauses",
        "- NEN-EN 1992-1-1 clause 5.8.7.3",
        "- any current Dutch National Annex provision that modifies or qualifies these clauses",
        "",
        "Phoenix will require source file, SHA-256, clause reference, explicit licensed-use confirmation and extraction review.",
        "Professional structural review remains required and production release remains `LOCKED`.",
        "",
    ])
