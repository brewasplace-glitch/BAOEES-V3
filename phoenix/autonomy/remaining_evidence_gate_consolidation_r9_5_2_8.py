"""PROJECT PHOENIX R9.5.2.8 - Remaining Evidence Gate Consolidation & Controlled R9.5 Requalification.

This module consolidates the remaining R9.5 evidence gates represented by Packages C, D and E.
It never fabricates missing evidence, professional decisions, reviewer identities, numerical criteria,
independent evidence, code-compliance claims, or release approval.

A controlled R9.5 requalification may be invoked only after all three package gates explicitly report
eligibility for later R9.5 promotion. Even then, the requalification engine's returned result is preserved
as authoritative; this module does not convert an attempted requalification into a successful one.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable, Iterable

VERSION = "R9.5.2.8"
ENGINE_ID = "PHX-R9.5.2.8-REMAINING-EVIDENCE-GATE-CONSOLIDATION"
PACKAGE_ID = "PKG-R9.5-REMAINING-EVIDENCE-GATE-CONSOLIDATION"

PACKAGE_C_ID = "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
PACKAGE_D_ID = "PKG-D-WEAK-STOREY-SCREENING-REVIEW"
PACKAGE_E_ID = "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"

ELIGIBLE_STATUS = "ELIGIBLE_FOR_LATER_R9_5_PROMOTION"
BLOCKED_STATUS = "BLOCKED_REMAINING_EVIDENCE"
READY_STATUS = "READY_FOR_CONTROLLED_R9_5_REQUALIFICATION"
EXECUTED_STATUS = "CONTROLLED_R9_5_REQUALIFICATION_EXECUTED"
RUNTIME_CONTEXT_INCOMPLETE = "READY_BUT_REQUALIFICATION_RUNTIME_CONTEXT_INCOMPLETE"

_REQUIRED_RUNTIME_KEYS = (
    "project_id",
    "workspace",
    "repository",
    "_phx_r93",
    "_phx_r94",
    "_phx_r95",
    "_phx_r951",
    "_phx_r952",
)


def consolidation_template() -> dict[str, Any]:
    return {
        "schema_version": "phoenix.remaining-evidence-gate-consolidation/1.0",
        "engine_version": VERSION,
        "package_id": PACKAGE_ID,
        "status": "INPUT_DISCOVERY_REQUIRED",
        "required_packages": [PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID],
        "human_input_policy": "NO_NEW_ENGINEERED_VALUES_CREATED_BY_R9_5_2_8",
        "requalification_policy": "ONLY_AFTER_ALL_REMAINING_EVIDENCE_GATES_EXPLICITLY_SATISFIED",
    }


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


def _discover_package_result(context: Any, package_id: str, aliases: tuple[str, ...]) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None

    direct_keys = (package_id,) + aliases
    for key in direct_keys:
        value = context.get(key)
        if isinstance(value, dict):
            return deepcopy(value)

    for document in _iter_dicts(context):
        if document.get("package_id") == package_id:
            return deepcopy(document)
        for key in aliases:
            value = document.get(key)
            if isinstance(value, dict):
                return deepcopy(value)
        package_inputs = document.get("package_inputs")
        if isinstance(package_inputs, dict):
            value = package_inputs.get(package_id)
            if isinstance(value, dict):
                return deepcopy(value)
    return None


def _explicit_eligibility(result: dict[str, Any] | None) -> bool:
    if not isinstance(result, dict):
        return False

    if result.get("eligible_for_r9_5_promotion") is True:
        return True
    if result.get("eligible_for_later_r9_5_promotion") is True:
        return True

    status = str(result.get("status") or "").upper()
    if status == ELIGIBLE_STATUS:
        return True

    package_id = result.get("package_id")
    if package_id == PACKAGE_E_ID:
        independent = result.get("independent_evidence_complete")
        reviewed = result.get("independent_review_complete")
        traceable = result.get("acceptance_criterion_traceability_complete")
        if independent is True and reviewed is True and traceable is True:
            return True

    return False


def _gate_summary(package_id: str, result: dict[str, Any] | None) -> dict[str, Any]:
    present = isinstance(result, dict)
    eligible = _explicit_eligibility(result)
    status = str((result or {}).get("status") or ("MISSING" if not present else "NOT_ELIGIBLE"))
    missing = list((result or {}).get("missing_requirements") or [])
    invalid = list((result or {}).get("invalid_requirements") or [])

    blockers: list[str] = []
    if not present:
        blockers.append("PACKAGE_RESULT_NOT_DISCOVERED")
    if present and not eligible:
        blockers.append("PACKAGE_NOT_EXPLICITLY_ELIGIBLE_FOR_LATER_R9_5_PROMOTION")
    blockers.extend(f"MISSING:{item}" for item in missing)
    blockers.extend(f"INVALID:{item}" for item in invalid)

    return {
        "package_id": package_id,
        "present": present,
        "status": status,
        "eligible_for_later_r9_5_promotion": eligible,
        "missing_requirements": missing,
        "invalid_requirements": invalid,
        "blockers": blockers,
    }


def _augment_r952_for_requalification(
    r952_initial: dict[str, Any],
    package_c: dict[str, Any],
    package_d: dict[str, Any],
    package_e: dict[str, Any],
    gate_result: dict[str, Any],
) -> dict[str, Any]:
    value = deepcopy(r952_initial)
    evidence_intake = value.setdefault("evidence_intake", {})
    if not isinstance(evidence_intake, dict):
        evidence_intake = {}
        value["evidence_intake"] = evidence_intake

    package_inputs = evidence_intake.setdefault("package_inputs", {})
    if not isinstance(package_inputs, dict):
        package_inputs = {}
        evidence_intake["package_inputs"] = package_inputs

    package_inputs[PACKAGE_C_ID] = deepcopy(package_c)
    package_inputs[PACKAGE_D_ID] = deepcopy(package_d)
    package_inputs[PACKAGE_E_ID] = deepcopy(package_e)
    evidence_intake["remaining_evidence_gate_r9_5_2_8"] = {
        "status": gate_result["status"],
        "all_remaining_evidence_gates_satisfied": gate_result["all_remaining_evidence_gates_satisfied"],
        "required_packages": [PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID],
    }
    return value


def _build_requalification_kwargs(
    context: dict[str, Any],
    package_c: dict[str, Any],
    package_d: dict[str, Any],
    package_e: dict[str, Any],
    gate_result: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    missing = [key for key in _REQUIRED_RUNTIME_KEYS if key not in context]
    if missing:
        return None, missing

    repository = context["repository"]
    if not isinstance(repository, Path):
        repository = Path(repository)

    r952_augmented = _augment_r952_for_requalification(
        context["_phx_r952"], package_c, package_d, package_e, gate_result
    )

    kwargs = {
        "project_id": context["project_id"],
        "workspace": context["workspace"],
        "repository_root": repository,
        "r93_qualification": context["_phx_r93"],
        "r94_initial": context["_phx_r94"],
        "r95_initial": context["_phx_r95"],
        "r951_initial": context["_phx_r951"],
        "r952_initial": r952_augmented,
        "r95_policy_path": repository.joinpath("configs", "phoenix", "structural", "project_stability_design_basis_decision_policy_r9_5.json"),
        "r951_policy_path": repository.joinpath("configs", "phoenix", "structural", "project_stability_design_basis_input_evidence_qualification_policy_r9_5_1.json"),
        "r952_policy_path": repository.joinpath("configs", "phoenix", "structural", "stability_design_basis_decision_dossier_evidence_intake_policy_r9_5_2.json"),
        "ab_policy_path": repository.joinpath("configs", "phoenix", "structural", "stability_ab_project_policy_r9_5_2_2.json"),
        "package_b_registry_path": repository.joinpath("configs", "phoenix", "structural", "package_b_licensed_source_traceability_r9_5_2_3.json"),
        "suriname_rule_registry_path": repository.joinpath("configs", "phoenix", "jurisdictions", "suriname", "suriname_structural_rule_registry_v1_0.json"),
        "suriname_source_registry_path": repository.joinpath("outputs", "bib", "index", "suriname_regulatory_source_registry_v1_0.json"),
        "r94_policy_path": repository.joinpath("configs", "phoenix", "structural", "normative_applicability_stability_design_basis_policy_r9_4.json"),
        "r94_public_source_registry_path": repository.joinpath("configs", "phoenix", "structural", "normative_applicability_public_source_registry_r9_4.json"),
    }
    return kwargs, []


def consolidate_remaining_evidence_gates(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context if isinstance(context, dict) else {}

    package_c = _discover_package_result(
        context,
        PACKAGE_C_ID,
        ("_phoenix_package_c_r9_5_2_6", "package_c", "package_c_result", "package_c_seismic_scope_criteria"),
    )
    package_d = _discover_package_result(
        context,
        PACKAGE_D_ID,
        ("_phoenix_package_d_r9_5_2_7", "package_d", "package_d_result", "weak_storey_screening_review"),
    )
    package_e = _discover_package_result(
        context,
        PACKAGE_E_ID,
        ("_phoenix_package_e_r9_5_2_5", "package_e", "package_e_result", "alternate_path_independent_evidence"),
    )

    gates = {
        "package_c": _gate_summary(PACKAGE_C_ID, package_c),
        "package_d": _gate_summary(PACKAGE_D_ID, package_d),
        "package_e": _gate_summary(PACKAGE_E_ID, package_e),
    }
    all_satisfied = all(item["eligible_for_later_r9_5_promotion"] for item in gates.values())

    remaining = []
    for key, gate in gates.items():
        if not gate["eligible_for_later_r9_5_promotion"]:
            remaining.append(
                {
                    "gate": key,
                    "package_id": gate["package_id"],
                    "status": gate["status"],
                    "blockers": gate["blockers"],
                }
            )

    status = READY_STATUS if all_satisfied else BLOCKED_STATUS
    return {
        "schema_version": "phoenix.remaining-evidence-gate-consolidation-result/1.0",
        "engine_version": VERSION,
        "engine_id": ENGINE_ID,
        "package_id": PACKAGE_ID,
        "status": status,
        "gates": gates,
        "all_remaining_evidence_gates_satisfied": all_satisfied,
        "remaining_evidence": remaining,
        "package_results": {
            PACKAGE_C_ID: package_c,
            PACKAGE_D_ID: package_d,
            PACKAGE_E_ID: package_e,
        },
        "requalification": {
            "authorized_by_evidence_gate": all_satisfied,
            "attempted": False,
            "status": "NOT_ATTEMPTED",
            "result": None,
        },
        "safety": {
            "automatic_seismic_applicability_decision": False,
            "automatic_numerical_criteria_generation": False,
            "automatic_screening_proxy_acceptance": False,
            "automatic_reviewer_identity_generation": False,
            "automatic_independent_evidence_generation": False,
            "automatic_professional_approval": False,
            "automatic_code_compliance_claim": False,
            "automatic_r9_5_success_claim": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }


def run_remaining_evidence_gate_consolidation_r9_5_2_8(
    context: dict[str, Any] | None,
    *,
    requalification_callable: Callable[..., dict[str, Any]] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    context = context if isinstance(context, dict) else {}
    result = consolidate_remaining_evidence_gates(context)

    if result["all_remaining_evidence_gates_satisfied"]:
        package_results = result["package_results"]
        kwargs, missing_runtime = _build_requalification_kwargs(
            context,
            package_results[PACKAGE_C_ID],
            package_results[PACKAGE_D_ID],
            package_results[PACKAGE_E_ID],
            result,
        )
        if missing_runtime:
            result["status"] = RUNTIME_CONTEXT_INCOMPLETE
            result["requalification"]["status"] = RUNTIME_CONTEXT_INCOMPLETE
            result["requalification"]["missing_runtime_context"] = missing_runtime
        elif not callable(requalification_callable):
            result["requalification"]["status"] = "READY_CALLBACK_NOT_SUPPLIED"
        else:
            requalified = requalification_callable(**kwargs)
            result["status"] = EXECUTED_STATUS
            result["requalification"] = {
                "authorized_by_evidence_gate": True,
                "attempted": True,
                "status": EXECUTED_STATUS,
                "result": deepcopy(requalified),
            }

    if output_dir is not None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        output_file = path / "r9_5_2_8_remaining_evidence_gate_consolidation_controlled_requalification.json"
        output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["output_file"] = str(output_file)

    return result


run_r9_5_2_8 = run_remaining_evidence_gate_consolidation_r9_5_2_8
