"""PAT-001 Identity Closure + Structural Preparation State v1.3."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import copy
import hashlib
import json

from phoenix.autonomy.structural_model_interchange_v1_1 import (
    VALID as CANONICAL_VALID,
    validate_model,
)

VERSION = "1.3.0"
ENGINE_ID = "PHX-PAT001-IDENTITY-CLOSURE-STRUCTURAL-PREPARATION-STATE"
PROJECT_ID = "PHOENIX-PAT-001"

IDENTITY_CLOSED = "PAT001_PROJECT_IDENTITY_CLOSED"
PREPARED_SCIA_PENDING = "PAT001_STRUCTURAL_PREPARATION_COMPLETE_SCIA_PENDING"
PREPARATION_READY = "PAT001_STRUCTURAL_PREPARATION_READY"
PREPARATION_BLOCKED = "PAT001_STRUCTURAL_PREPARATION_BLOCKED"

SAFETY = {
    "identity_auto_inferred": False,
    "source_contract_overwritten": False,
    "automatic_live_scia": False,
    "automatic_live_calculix": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().upper()
        return (not text) or text == "REQUIRED" or text.startswith("REQUIRED_")
    return False


def complete_provenance(contract: dict[str, Any]) -> bool:
    provenance = contract.get("provenance")
    if not isinstance(provenance, dict):
        return False
    required = (
        "geometry",
        "materials",
        "sections",
        "supports_and_boundaries",
        "load_basis",
        "load_cases",
        "load_combinations",
    )
    for key in required:
        item = provenance.get(key)
        if not isinstance(item, dict):
            return False
        if str(item.get("status", "")).upper() not in {"TRACEABLE", "CONFIRMED", "VALIDATED"}:
            return False
        sources = item.get("sources")
        if not isinstance(sources, list) or not sources:
            return False
    return True


def close_identity(
    repository: Path,
    contract_path: Path,
    declaration_path: Path,
    canonical_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    if not contract_path.is_file():
        raise FileNotFoundError(contract_path)
    if not declaration_path.is_file():
        raise FileNotFoundError(declaration_path)
    if not canonical_path.is_file():
        raise FileNotFoundError(canonical_path)

    contract = read_json(contract_path)
    declaration = read_json(declaration_path)
    canonical = read_json(canonical_path)

    if contract.get("project_id") != PROJECT_ID:
        raise ValueError("Source contract project_id mismatch.")
    if declaration.get("project_id") != PROJECT_ID:
        raise ValueError("Identity declaration project_id mismatch.")
    if declaration.get("authority") != "PROJECT_OWNER":
        raise ValueError("Identity declaration must have PROJECT_OWNER authority.")
    if declaration.get("decision_source") != "USER_STRATEGIC_DECISION":
        raise ValueError("Identity declaration must be a user strategic decision.")

    project_name = declaration.get("project_name")
    structural_scope = declaration.get("structural_scope")
    if placeholder(project_name):
        raise ValueError("Declared project_name is missing.")
    if placeholder(structural_scope):
        raise ValueError("Declared structural_scope is missing.")

    identity = copy.deepcopy(contract.get("project_identity") or {})
    location = identity.get("location")
    if placeholder(location):
        raise ValueError("Existing traceable project location missing; refusing to invent location.")

    canonical_validation = validate_model(canonical)
    if canonical_validation.get("status") != CANONICAL_VALID:
        raise ValueError("Canonical Structural Model v1.1 is no longer valid.")

    scope = contract.get("analysis_scope") or {}
    analysis_ok = (
        str(scope.get("status", "")).upper() in {"CONFIRMED", "VALIDATED"}
        and not placeholder(scope.get("calculation_type"))
    )
    if not analysis_ok:
        raise ValueError("PAT-001 analysis scope is no longer confirmed.")

    calculix = contract.get("calculix") or {}
    adapter = calculix.get("project_adapter")
    if placeholder(adapter):
        raise ValueError("Qualified PAT-001 CalculiX adapter missing from source contract.")

    if not complete_provenance(contract):
        raise ValueError("PAT-001 structural provenance is no longer complete.")

    updated = copy.deepcopy(contract)
    updated["schema_version"] = "phoenix.pat001-structural-input-contract/1.3"
    updated["project_identity"] = {
        "name": str(project_name),
        "location": str(location),
        "structural_scope": str(structural_scope),
    }
    updated["project_identity_evidence"] = {
        "status": IDENTITY_CLOSED,
        "declaration": {
            "reference": declaration_path.resolve().relative_to(repository.resolve()).as_posix(),
            "sha256": sha256_file(declaration_path),
            "authority": declaration.get("authority"),
            "decision_source": declaration.get("decision_source"),
            "decision_date": declaration.get("decision_date"),
        },
        "source_contract": {
            "reference": contract_path.resolve().relative_to(repository.resolve()).as_posix(),
            "sha256": sha256_file(contract_path),
        },
        "identity_auto_inferred": False,
    }

    scia = updated.get("scia") or {}
    scia_ready = not placeholder(scia.get("seed_esa"))

    gaps = []
    if not scia_ready:
        gaps.append("PAT001-GAP-SCIA-MODEL")

    if gaps == ["PAT001-GAP-SCIA-MODEL"]:
        state = PREPARED_SCIA_PENDING
    elif not gaps:
        state = PREPARATION_READY
    else:
        state = PREPARATION_BLOCKED

    output_root.mkdir(parents=True, exist_ok=True)
    output_contract = output_root / "pat001_structural_input_contract_v1_3.json"
    write_json(output_contract, updated)

    state_record = {
        "schema_version": "phoenix.pat001-structural-preparation-state/1.3",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": state,
        "identity_status": IDENTITY_CLOSED,
        "project_identity": copy.deepcopy(updated["project_identity"]),
        "canonical_status": canonical_validation.get("status"),
        "canonical_sha256": canonical_validation.get("canonical_sha256"),
        "analysis_scope": copy.deepcopy(scope),
        "calculix_adapter": adapter,
        "provenance_complete": True,
        "scia_project_model_ready": scia_ready,
        "remaining_gaps": gaps,
        "live_scia_started": False,
        "live_calculix_started": False,
        "professional_review_started": False,
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
        "safety": dict(SAFETY),
    }
    state_path = output_root / "pat001_structural_preparation_state_v1_3.json"
    write_json(state_path, state_record)

    result = {
        "schema_version": "phoenix.pat001-identity-closure-result/1.3",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": state,
        "identity_status": IDENTITY_CLOSED,
        "project_name": project_name,
        "location": location,
        "structural_scope": structural_scope,
        "updated_contract": output_contract.resolve().relative_to(repository.resolve()).as_posix(),
        "preparation_state": state_path.resolve().relative_to(repository.resolve()).as_posix(),
        "remaining_gaps": gaps,
        "canonical_valid": True,
        "analysis_scope_confirmed": True,
        "calculix_adapter_qualified": True,
        "provenance_complete": True,
        "scia_project_model_ready": scia_ready,
        "live_scia_started": False,
        "live_calculix_started": False,
        "source_contract_overwritten": False,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "pat001_identity_closure_result_v1_3.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repository = Path(args.repository)
    result = close_identity(
        repository=repository,
        contract_path=repository / "projects/runtime/PHOENIX-PAT-001/structural_canonicalization_v1_2/pat001_structural_input_contract_v1_2.json",
        declaration_path=repository / "configs/projects/pat001_project_identity_declaration_v1_3.json",
        canonical_path=repository / "projects/runtime/PHOENIX-PAT-001/structural_canonicalization_v1_2/pat001_canonical_structural_model_v1_1.json",
        output_root=Path(args.output),
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
