"""PAT-001 canonicalization, legacy CalculiX adapter registration and harvest hardening v1.2."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import copy
import hashlib
import json
import re

from phoenix.autonomy.structural_model_interchange_v1_1 import (
    VALID as CANONICAL_VALID,
    canonical_sha256,
    sha256_file,
    validate_model,
)

VERSION = "1.2.0"
ENGINE_ID = "PHX-PAT001-CANONICALIZATION-ADAPTER-HARVEST-HARDENING"
PROJECT_ID = "PHOENIX-PAT-001"
ADAPTER_ID = "PAT001-LEGACY-V8_3-CALCULIX-PROJECT-ADAPTER-v1"

STATUS_COMPLETE = "PAT001_CANONICALIZATION_ADAPTER_HARDENING_COMPLETE"
STATUS_PARTIAL = "PAT001_CANONICALIZATION_ADAPTER_HARDENING_PARTIAL"
IDENTITY_REQUIRED = "PAT001_STRUCTURAL_IDENTITY_REQUIRED"
SCIA_REQUIRED = "PAT001_SCIA_PROJECT_MODEL_REQUIRED"
CANONICAL_REQUIRED = "PAT001_CANONICAL_MODEL_REQUIRED"
ANALYSIS_REQUIRED = "PAT001_ANALYSIS_SCOPE_REQUIRED"
CALCULIX_REQUIRED = "PAT001_CALCULIX_PROJECT_ADAPTER_REQUIRED"
PROVENANCE_REQUIRED = "PAT001_STRUCTURAL_PROVENANCE_REQUIRED"
PREPARATION_READY = "PAT001_STRUCTURAL_PREPARATION_READY"

SAFETY = {
    "generic_name_used_as_project_name": False,
    "required_template_used_as_analysis_authority": False,
    "shells_dropped_during_canonicalization": False,
    "design_values_invented": False,
    "legacy_calculix_adapter_reexecuted_for_registration": False,
    "automatic_live_scia": False,
    "automatic_live_calculix": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}

ANALYSIS_TYPE_MAP = {
    "LINEAR_STATIC": "LIN",
    "LIN": "LIN",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().upper()
        return not text or text == "REQUIRED" or text.startswith("REQUIRED_")
    return False


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except Exception:
        return str(path)


def _source(path: Path, repository: Path, field: str | None = None) -> dict[str, Any]:
    record = {
        "reference": _repo_ref(path, repository),
        "sha256": sha256_file(path),
    }
    if field:
        record["field"] = field
    return record


def _dict_to_id_list(values: Any, *, role: str) -> list[dict[str, Any]]:
    if not isinstance(values, dict):
        raise ValueError(f"{role} dictionary required.")
    result = []
    for ident in sorted(values):
        raw = values[ident]
        if not isinstance(raw, dict):
            raise ValueError(f"{role} {ident} must be an object.")
        result.append({
            "id": str(ident),
            "properties": copy.deepcopy(raw),
        })
    return result


def _member_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "member_type": item.get("type"),
        "start_node": item.get("node_i"),
        "end_node": item.get("node_j"),
        "material": item.get("material_id"),
        "section": item.get("section_id"),
        "source_candidate_id": item.get("source_candidate_id"),
        "approval_state": item.get("approval_state"),
        "review_required": bool(item.get("review_required", False)),
        "source_record": copy.deepcopy(item),
    }


def _shell_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "shell_type": item.get("type"),
        "node_ids": list(item.get("node_ids") or []),
        "material": item.get("material_id"),
        "section": item.get("section_id"),
        "source_candidate_id": item.get("source_candidate_id"),
        "approval_state": item.get("approval_state"),
        "review_required": bool(item.get("review_required", False)),
        "source_record": copy.deepcopy(item),
    }


def _support_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "node": item.get("node_id"),
        "dofs": list(item.get("dofs") or []),
        "source_candidate_id": item.get("source_candidate_id"),
        "source_support_type": item.get("source_support_type"),
        "approval_state": item.get("approval_state"),
        "review_required": bool(item.get("review_required", False)),
        "source_record": copy.deepcopy(item),
    }


def _load_case_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "category": item.get("category"),
        "analysis_type": item.get("analysis_type"),
        "name": item.get("name"),
        "approval_state": item.get("approval_state"),
        "source_record": copy.deepcopy(item),
    }


def _load_action_record(item: dict[str, Any]) -> dict[str, Any]:
    target_element = item.get("target_element_id")
    target_elements = item.get("target_element_ids")
    if target_elements is None and target_element is not None:
        target_elements = None
    return {
        "id": str(item.get("id") or ""),
        "load_case": item.get("case_id"),
        "kind": item.get("kind"),
        "direction": item.get("direction"),
        "distribution": item.get("distribution"),
        "magnitude": item.get("magnitude"),
        "factor": item.get("factor"),
        "target_node": item.get("target_node_id"),
        "target_element": target_element,
        "target_elements": list(target_elements) if isinstance(target_elements, list) else None,
        "source_action_id": item.get("source_action_id"),
        "approval_state": item.get("approval_state"),
        "source_record": copy.deepcopy(item),
    }


def _combination_record(item: dict[str, Any]) -> dict[str, Any]:
    terms = []
    for term in item.get("terms") or []:
        if isinstance(term, dict):
            terms.append({
                "load_case": term.get("case_id"),
                "factor": term.get("coefficient"),
                "source_record": copy.deepcopy(term),
            })
    return {
        "id": str(item.get("id") or ""),
        "name": item.get("name"),
        "limit_state": item.get("limit_state"),
        "basis": item.get("basis"),
        "approval_state": item.get("approval_state"),
        "terms": terms,
        "source_record": copy.deepcopy(item),
    }


def build_canonical_v1_1(v83_path: Path, repository: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    v83 = read_json(v83_path)
    if v83.get("project_id") != PROJECT_ID:
        raise ValueError("v8.3 input does not explicitly identify PHOENIX-PAT-001.")

    analytical = v83.get("analytical_model")
    basis = v83.get("solver_basis")
    action = v83.get("action_load_model")
    if not isinstance(analytical, dict):
        raise ValueError("v8.3 analytical_model missing.")
    if not isinstance(basis, dict):
        raise ValueError("v8.3 solver_basis missing.")
    if not isinstance(action, dict):
        raise ValueError("v8.3 action_load_model missing.")

    raw_nodes = analytical.get("nodes")
    raw_members = analytical.get("members")
    raw_shells = analytical.get("shells")
    raw_supports = analytical.get("supports")
    if not isinstance(raw_nodes, list):
        raise ValueError("analytical_model.nodes missing.")
    if not isinstance(raw_members, list):
        raise ValueError("analytical_model.members missing.")
    if not isinstance(raw_shells, list):
        raise ValueError("analytical_model.shells missing; refusing lossy conversion.")
    if not isinstance(raw_supports, list):
        raise ValueError("analytical_model.supports missing.")

    nodes = []
    for item in raw_nodes:
        if not isinstance(item, dict):
            raise ValueError("Node record must be an object.")
        nodes.append({
            "id": str(item.get("id") or ""),
            "x": item.get("x", item.get("x_m")),
            "y": item.get("y", item.get("y_m")),
            "z": item.get("z", item.get("z_m")),
            "source_ids": copy.deepcopy(item.get("source_ids") or []),
            "source_record": copy.deepcopy(item),
        })

    materials = _dict_to_id_list(basis.get("materials"), role="material")
    sections = _dict_to_id_list(basis.get("sections"), role="section")
    members = [_member_record(x) for x in raw_members if isinstance(x, dict)]
    shells = [_shell_record(x) for x in raw_shells if isinstance(x, dict)]
    supports = [_support_record(x) for x in raw_supports if isinstance(x, dict)]
    load_cases = [_load_case_record(x) for x in (action.get("load_cases") or []) if isinstance(x, dict)]
    assignments = action.get("action_assignments")
    if assignments is None:
        assignments = action.get("load_actions")
    if not isinstance(assignments, list):
        raise ValueError("action_load_model action assignments missing.")
    load_actions = [_load_action_record(x) for x in assignments if isinstance(x, dict)]
    load_combinations = [_combination_record(x) for x in (action.get("load_combinations") or []) if isinstance(x, dict)]

    unit_system = action.get("unit_system")
    if not isinstance(unit_system, dict):
        raise ValueError("action_load_model.unit_system missing; refusing to invent units.")

    source_hash = sha256_file(v83_path)
    model = {
        "schema_version": "phoenix.canonical-structural-model/1.1",
        "project_id": PROJECT_ID,
        "model_id": "PHOENIX-PAT-001-CANONICAL-STRUCTURAL-v1_1",
        "units": {
            "length": unit_system.get("length"),
            "force": unit_system.get("force"),
            "mass": unit_system.get("mass"),
            "moment": unit_system.get("moment"),
            "stress": unit_system.get("stress"),
        },
        "nodes": nodes,
        "materials": materials,
        "sections": sections,
        "members": members,
        "shells": shells,
        "supports": supports,
        "load_cases": load_cases,
        "load_actions": load_actions,
        "load_combinations": load_combinations,
        "metadata": {
            "source": _repo_ref(v83_path, repository),
            "source_sha256": source_hash,
            "source_model_state": analytical.get("model_state"),
            "source_action_model_state": action.get("model_state"),
            "candidate_only_records_preserved": True,
            "shells_preserved": True,
            "design_values_invented": False,
            "automatic_professional_approval": False,
            "automatic_code_compliance_claim": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }
    validation = validate_model(model)
    if validation["status"] != CANONICAL_VALID:
        raise ValueError("Canonical v1.1 validation failed: " + "; ".join(validation["errors"]))
    audit = {
        "status": "PAT001_CANONICAL_STRUCTURAL_MODEL_V1_1_BUILT",
        "source_v8_3": _source(v83_path, repository),
        "source_counts": {
            "nodes": len(raw_nodes),
            "members": len(raw_members),
            "shells": len(raw_shells),
            "supports": len(raw_supports),
            "load_cases": len(action.get("load_cases") or []),
            "load_actions": len(assignments),
            "load_combinations": len(action.get("load_combinations") or []),
        },
        "output_counts": validation["counts"],
        "shells_dropped": False,
        "design_values_invented": False,
        "canonical_sha256": validation["canonical_sha256"],
        "warnings": validation["warnings"],
    }
    return model, audit


def resolve_project_identity(repository: Path, contract: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(contract.get("project_identity") or {})
    evidence: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    manifest_path = repository / "projects" / "runtime" / PROJECT_ID / "project_manifest.json"
    candidates: dict[str, list[tuple[str, dict[str, Any]]]] = {
        "name": [],
        "structural_scope": [],
    }
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        if manifest.get("project_id") == PROJECT_ID:
            for field in ("project_name", "project_title"):
                value = manifest.get(field)
                if isinstance(value, str) and value.strip() and not _placeholder(value):
                    candidates["name"].append((value.strip(), _source(manifest_path, repository, field)))
            value = manifest.get("structural_scope")
            if isinstance(value, str) and value.strip() and not _placeholder(value):
                candidates["structural_scope"].append((value.strip(), _source(manifest_path, repository, "structural_scope")))

    for field in ("name", "structural_scope"):
        unique = {}
        for value, src in candidates[field]:
            unique.setdefault(value, []).append(src)
        if len(unique) == 1:
            value = next(iter(unique))
            result[field] = value
            evidence.append({"field": f"project_identity.{field}", "value": value, "sources": unique[value]})
        elif len(unique) > 1:
            result[field] = "REQUIRED"
            conflicts.append({"field": f"project_identity.{field}", "values": sorted(unique)})
        elif _placeholder(result.get(field)):
            result[field] = "REQUIRED"

    return {
        "project_identity": result,
        "evidence": evidence,
        "conflicts": conflicts,
        "generic_name_field_used": False,
    }


def resolve_analysis_scope(v83_path: Path, repository: Path, contract: dict[str, Any]) -> dict[str, Any]:
    v83 = read_json(v83_path)
    basis = v83.get("solver_basis")
    raw = basis.get("analysis_type") if isinstance(basis, dict) else None
    normalized = str(raw).strip().upper() if raw is not None else ""
    mapped = ANALYSIS_TYPE_MAP.get(normalized)
    scope = copy.deepcopy(contract.get("analysis_scope") or {})
    if mapped:
        scope["status"] = "CONFIRMED"
        scope["calculation_type"] = mapped
        scope["evidence"] = [{
            **_source(v83_path, repository, "solver_basis.analysis_type"),
            "source_value": raw,
            "mapped_value": mapped,
            "mapping_rule": f"{normalized}->{mapped}",
        }]
        status = "PAT001_ANALYSIS_SCOPE_RESOLVED"
    else:
        scope["status"] = "REQUIRED"
        scope["calculation_type"] = None
        status = "PAT001_ANALYSIS_SCOPE_REQUIRED"
    return {
        "status": status,
        "analysis_scope": scope,
        "source_value": raw,
        "mapped_value": mapped,
        "required_template_used_as_authority": False,
        "load_case_analysis_type_used_as_global_scope": False,
    }


def qualify_existing_calculix_adapter(repository: Path, v83_path: Path) -> dict[str, Any]:
    root = repository / "projects" / "runtime" / PROJECT_ID / "results" / "session_adapters" / "structural_engineering" / "validated_v8_1_to_v8_12"
    runner = repository / "runners" / "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"
    manifest = root / "v8_3" / "solver_package" / "PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
    project_deck = root / "v8_4" / "solver_evidence" / "calculix" / "LC-G" / "phoenix_v8_4_case.inp"

    v83 = read_json(v83_path)
    adapters = [str(x).strip().lower() for x in (v83.get("solver_adapters") or [])]
    checks = {
        "project_id_matches": v83.get("project_id") == PROJECT_ID,
        "calculix_declared": "calculix" in adapters,
        "legacy_runner_present": runner.is_file(),
        "solver_package_manifest_present": manifest.is_file(),
        "existing_project_calculix_deck_present": project_deck.is_file(),
    }
    ready = all(checks.values())
    evidence = []
    for role, path in (
        ("v8_3_input", v83_path),
        ("legacy_runner", runner),
        ("solver_package_manifest", manifest),
        ("existing_project_calculix_deck", project_deck),
    ):
        if path.is_file():
            evidence.append({
                "role": role,
                **_source(path, repository),
            })
    return {
        "status": "PAT001_EXISTING_CALCULIX_ADAPTER_QUALIFIED" if ready else "PAT001_EXISTING_CALCULIX_ADAPTER_NOT_QUALIFIED",
        "qualified": ready,
        "adapter_id": ADAPTER_ID if ready else None,
        "checks": checks,
        "evidence": evidence,
        "live_solver_started": False,
        "golden_reference_used_as_project_evidence": False,
    }


def _provenance_complete(contract: dict[str, Any]) -> bool:
    provenance = contract.get("provenance")
    if not isinstance(provenance, dict):
        return False
    required = (
        "geometry", "materials", "sections", "supports_and_boundaries",
        "load_basis", "load_cases", "load_combinations",
    )
    for key in required:
        item = provenance.get(key)
        if not isinstance(item, dict):
            return False
        if str(item.get("status", "")).upper() not in {"TRACEABLE", "CONFIRMED", "VALIDATED"}:
            return False
        if not isinstance(item.get("sources"), list) or not item["sources"]:
            return False
    return True


def assess_v1_2(
    contract: dict[str, Any],
    canonical_validation: dict[str, Any],
    calculix_registration: dict[str, Any],
) -> dict[str, Any]:
    gaps = []
    identity = contract.get("project_identity") or {}
    if any(_placeholder(identity.get(key)) for key in ("name", "location", "structural_scope")):
        gaps.append("PAT001-GAP-IDENTITY")
    if canonical_validation.get("status") != CANONICAL_VALID:
        gaps.append("PAT001-GAP-CANONICAL")
    if not _provenance_complete(contract):
        gaps.append("PAT001-GAP-PROVENANCE")
    scope = contract.get("analysis_scope") or {}
    if str(scope.get("status", "")).upper() not in {"CONFIRMED", "VALIDATED"} or _placeholder(scope.get("calculation_type")):
        gaps.append("PAT001-GAP-ANALYSIS-SCOPE")
    scia = contract.get("scia") or {}
    if _placeholder(scia.get("seed_esa")):
        gaps.append("PAT001-GAP-SCIA-MODEL")
    if not calculix_registration.get("qualified"):
        gaps.append("PAT001-GAP-CALCULIX-ADAPTER")

    if not gaps:
        status = PREPARATION_READY
    elif "PAT001-GAP-IDENTITY" in gaps:
        status = IDENTITY_REQUIRED
    elif "PAT001-GAP-CANONICAL" in gaps:
        status = CANONICAL_REQUIRED
    elif "PAT001-GAP-PROVENANCE" in gaps:
        status = PROVENANCE_REQUIRED
    elif "PAT001-GAP-ANALYSIS-SCOPE" in gaps:
        status = ANALYSIS_REQUIRED
    elif "PAT001-GAP-SCIA-MODEL" in gaps:
        status = SCIA_REQUIRED
    else:
        status = CALCULIX_REQUIRED
    return {
        "schema_version": "phoenix.pat001-structural-preparation-assessment/1.2",
        "project_id": PROJECT_ID,
        "status": status,
        "gaps": gaps,
        "canonical_validation": canonical_validation,
        "calculix_adapter_qualified": bool(calculix_registration.get("qualified")),
        "live_scia_started": False,
        "live_calculix_started": False,
        "professional_review_started": False,
        "safety": dict(SAFETY),
    }


def run(repository: Path, output_root: Path) -> dict[str, Any]:
    project_root = repository / "projects" / "runtime" / PROJECT_ID
    structural_root = project_root / "results" / "session_adapters" / "structural_engineering" / "validated_v8_1_to_v8_12"
    v83_path = structural_root / "v8_3" / "input.json"
    source_contract = project_root / "structural_bootstrap_v1_1" / "pat001_structural_input_contract_v1_1.json"

    if not v83_path.is_file():
        raise FileNotFoundError(f"PAT-001 v8.3 input missing: {v83_path}")
    if not source_contract.is_file():
        raise FileNotFoundError(f"PAT-001 v1.1 bootstrap contract missing: {source_contract}")

    output_root.mkdir(parents=True, exist_ok=True)
    contract = read_json(source_contract)

    canonical, canonical_audit = build_canonical_v1_1(v83_path, repository)
    canonical_path = output_root / "pat001_canonical_structural_model_v1_1.json"
    write_json(canonical_path, canonical)
    canonical_validation = validate_model(canonical)
    canonical_audit["output"] = _repo_ref(canonical_path, repository)
    canonical_audit["output_file_sha256"] = sha256_file(canonical_path)
    write_json(output_root / "pat001_canonicalization_audit_v1_2.json", canonical_audit)

    identity_resolution = resolve_project_identity(repository, contract)
    contract["project_identity"] = identity_resolution["project_identity"]

    analysis_resolution = resolve_analysis_scope(v83_path, repository, contract)
    contract["analysis_scope"] = analysis_resolution["analysis_scope"]

    registration = qualify_existing_calculix_adapter(repository, v83_path)
    write_json(output_root / "pat001_calculix_adapter_registration_v1_2.json", registration)
    calc = contract.setdefault("calculix", {})
    if registration["qualified"]:
        calc["project_adapter"] = registration["adapter_id"]
        calc["adapter_evidence"] = registration["evidence"]
        calc["registration"] = _repo_ref(output_root / "pat001_calculix_adapter_registration_v1_2.json", repository)

    canonical_ref = _repo_ref(canonical_path, repository)
    contract.setdefault("canonical_structural_model", {})["path"] = canonical_ref
    contract["canonical_structural_model"]["schema_version"] = "phoenix.canonical-structural-model/1.1"
    contract["canonical_structural_model"]["canonical_sha256"] = canonical_validation.get("canonical_sha256")
    contract["canonical_structural_model"]["source"] = _source(v83_path, repository)

    contract["schema_version"] = "phoenix.pat001-structural-input-contract/1.2"
    contract["bootstrap_v1_2"] = {
        "source_contract": _source(source_contract, repository),
        "identity_resolution": identity_resolution,
        "analysis_scope_resolution": analysis_resolution,
        "canonicalization_audit": _repo_ref(output_root / "pat001_canonicalization_audit_v1_2.json", repository),
        "calculix_adapter_registration": _repo_ref(output_root / "pat001_calculix_adapter_registration_v1_2.json", repository),
        "source_contract_overwritten": False,
        "design_values_invented": False,
    }

    contract_path = output_root / "pat001_structural_input_contract_v1_2.json"
    write_json(contract_path, contract)

    assessment = assess_v1_2(contract, canonical_validation, registration)
    write_json(output_root / "pat001_structural_preparation_assessment_v1_2.json", assessment)

    summary_status = STATUS_COMPLETE if (
        canonical_validation.get("status") == CANONICAL_VALID
        and registration.get("qualified")
        and analysis_resolution.get("mapped_value") is not None
    ) else STATUS_PARTIAL

    result = {
        "schema_version": "phoenix.pat001-canonicalization-adapter-harvest-hardening-result/1.2",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": summary_status,
        "canonical_model": _repo_ref(canonical_path, repository),
        "canonical_model_sha256": canonical_validation.get("canonical_sha256"),
        "canonical_counts": canonical_validation.get("counts"),
        "shells_preserved": canonical_audit["source_counts"]["shells"] == canonical_audit["output_counts"]["shells"],
        "identity_resolution": identity_resolution,
        "analysis_scope_resolution": analysis_resolution,
        "calculix_adapter_registration": registration,
        "updated_contract": _repo_ref(contract_path, repository),
        "assessment_status": assessment["status"],
        "assessment_gaps": assessment["gaps"],
        "live_scia_started": False,
        "live_calculix_started": False,
        "source_contract_overwritten": False,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "pat001_canonicalization_adapter_hardening_result_v1_2.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(Path(args.repository), Path(args.output))
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
