"""PROJECT PHOENIX PAT-001 Structural Preparation v1.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import hashlib
import json

from phoenix.autonomy.structural_model_interchange_scia_preparation_v1_0 import (
    VALID as CANONICAL_VALID,
    validate_model,
)

VERSION = "1.0.0"
ENGINE_ID = "PHX-PAT001-STRUCTURAL-PREPARATION"
PROJECT_ID = "PHOENIX-PAT-001"

INPUT_CONTRACT_REQUIRED = "PAT001_STRUCTURAL_INPUT_CONTRACT_REQUIRED"
CANONICAL_REQUIRED = "PAT001_CANONICAL_MODEL_REQUIRED"
CANONICAL_INVALID = "PAT001_CANONICAL_MODEL_INVALID"
PROVENANCE_REQUIRED = "PAT001_STRUCTURAL_PROVENANCE_REQUIRED"
ANALYSIS_SCOPE_REQUIRED = "PAT001_ANALYSIS_SCOPE_REQUIRED"
SCIA_MODEL_REQUIRED = "PAT001_SCIA_PROJECT_MODEL_REQUIRED"
CALCULIX_ADAPTER_REQUIRED = "PAT001_CALCULIX_PROJECT_ADAPTER_REQUIRED"
PREPARATION_READY = "PAT001_STRUCTURAL_PREPARATION_READY"

SAFETY = {
    "historical_esa_auto_labeled_pat001": False,
    "reference_model_is_pat001_project_evidence": False,
    "automatic_binary_esa_synthesis": False,
    "automatic_live_scia": False,
    "automatic_live_calculix": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}

PROVENANCE_KEYS = (
    "geometry",
    "materials",
    "sections",
    "supports_and_boundaries",
    "load_basis",
    "load_cases",
    "load_combinations",
)


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
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        s = value.strip().upper()
        return (not s) or s == "REQUIRED" or s.startswith("REQUIRED_")
    return False


def _source_evidence(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if str(entry.get("status", "")).strip().upper() not in {"CONFIRMED", "TRACEABLE", "VALIDATED"}:
        return False
    sources = entry.get("sources")
    return isinstance(sources, list) and len(sources) > 0 and all(
        isinstance(x, dict)
        and isinstance(x.get("reference"), str)
        and x["reference"].strip()
        for x in sources
    )


def _qualified_scia_seed(contract: dict[str, Any], repository: Path) -> dict[str, Any]:
    scia = contract.get("scia", {})
    seed = scia.get("seed_esa") if isinstance(scia, dict) else None
    prov = scia.get("seed_provenance") if isinstance(scia, dict) else None
    if not seed:
        return {"qualified": False, "reason": "SCIA_SEED_MISSING"}
    seed_path = Path(seed)
    if not seed_path.is_absolute():
        seed_path = repository / seed_path
    if not seed_path.is_file():
        return {"qualified": False, "reason": "SCIA_SEED_FILE_NOT_FOUND", "path": str(seed_path)}
    if not isinstance(prov, dict):
        return {"qualified": False, "reason": "SCIA_SEED_PROVENANCE_MISSING", "path": str(seed_path)}
    if prov.get("project_id") != PROJECT_ID:
        return {"qualified": False, "reason": "SCIA_SEED_PROJECT_ID_NOT_CONFIRMED", "path": str(seed_path)}
    declared = str(prov.get("sha256", "")).lower()
    actual = sha256_file(seed_path)
    if not declared or declared != actual:
        return {
            "qualified": False,
            "reason": "SCIA_SEED_SHA256_NOT_CONFIRMED",
            "path": str(seed_path),
            "actual_sha256": actual,
        }
    return {
        "qualified": True,
        "path": str(seed_path),
        "sha256": actual,
        "project_id": PROJECT_ID,
    }


def inventory_candidates(repository: Path) -> list[dict[str, Any]]:
    roots = [
        repository / "projects" / "runtime" / PROJECT_ID,
        repository / "reference_models" / "structural",
    ]
    candidates = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.esa", "*.xml", "*.def", "*.inp"):
            for p in root.rglob(pattern):
                try:
                    resolved = p.resolve()
                except OSError:
                    resolved = p
                key = str(resolved).lower()
                if key in seen or not p.is_file():
                    continue
                seen.add(key)
                role = "UNQUALIFIED_CANDIDATE"
                if "reference_models" in p.parts:
                    role = "REFERENCE_MODEL_NOT_PAT001_EVIDENCE"
                candidates.append({
                    "path": str(p),
                    "suffix": p.suffix.lower(),
                    "sha256": sha256_file(p),
                    "size_bytes": p.stat().st_size,
                    "role": role,
                })
    return sorted(candidates, key=lambda x: x["path"].lower())


def assess(contract_path: Path, repository: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    if not contract_path.is_file():
        result = {
            "status": INPUT_CONTRACT_REQUIRED,
            "project_id": PROJECT_ID,
            "contract": str(contract_path),
            "gaps": ["PAT001-GAP-INPUT-CONTRACT"],
            "safety": dict(SAFETY),
        }
        write_json(output_root / "pat001_structural_preparation_result_v1_0.json", result)
        return result

    contract = read_json(contract_path)
    gaps = []
    errors = []

    if contract.get("project_id") != PROJECT_ID:
        errors.append("PROJECT_ID_MUST_EQUAL_PHOENIX-PAT-001")

    identity = contract.get("project_identity")
    if not isinstance(identity, dict) or any(_placeholder(identity.get(k)) for k in ("name", "location", "structural_scope")):
        gaps.append("PAT001-GAP-IDENTITY")

    canonical_ref = contract.get("canonical_structural_model")
    canonical_path = canonical_ref.get("path") if isinstance(canonical_ref, dict) else None
    canonical_result = None
    resolved_canonical = None
    if _placeholder(canonical_path):
        gaps.append("PAT001-GAP-CANONICAL")
    else:
        resolved_canonical = Path(str(canonical_path))
        if not resolved_canonical.is_absolute():
            resolved_canonical = repository / resolved_canonical
        if not resolved_canonical.is_file():
            gaps.append("PAT001-GAP-CANONICAL")
        else:
            canonical_model = read_json(resolved_canonical)
            canonical_result = validate_model(canonical_model)
            if canonical_result["status"] != CANONICAL_VALID:
                gaps.append("PAT001-GAP-CANONICAL")

    provenance = contract.get("provenance")
    missing_prov = []
    if not isinstance(provenance, dict):
        missing_prov = list(PROVENANCE_KEYS)
    else:
        for key in PROVENANCE_KEYS:
            if not _source_evidence(provenance.get(key)):
                missing_prov.append(key)
    if missing_prov:
        gaps.append("PAT001-GAP-PROVENANCE")

    scope = contract.get("analysis_scope")
    calc_type = scope.get("calculation_type") if isinstance(scope, dict) else None
    if not isinstance(scope, dict) or str(scope.get("status", "")).upper() not in {"CONFIRMED", "VALIDATED"} or _placeholder(calc_type):
        gaps.append("PAT001-GAP-ANALYSIS-SCOPE")

    scia_seed = _qualified_scia_seed(contract, repository)
    scia = contract.get("scia", {})
    xml_update = scia.get("xml_update") if isinstance(scia, dict) else None
    xml_definition = scia.get("xml_definition") if isinstance(scia, dict) else None
    scia_ready = bool(
        scia_seed.get("qualified")
        and not _placeholder(xml_update)
        and not _placeholder(xml_definition)
        and not _placeholder(calc_type)
    )
    if not scia_ready:
        gaps.append("PAT001-GAP-SCIA-MODEL")

    calculix = contract.get("calculix")
    adapter = calculix.get("project_adapter") if isinstance(calculix, dict) else None
    calculix_ready = isinstance(adapter, str) and adapter.strip() and not _placeholder(adapter)
    if not calculix_ready:
        gaps.append("PAT001-GAP-CALCULIX-ADAPTER")

    if errors:
        status = INPUT_CONTRACT_REQUIRED
    elif "PAT001-GAP-IDENTITY" in gaps:
        status = INPUT_CONTRACT_REQUIRED
    elif "PAT001-GAP-CANONICAL" in gaps:
        status = CANONICAL_INVALID if canonical_result is not None else CANONICAL_REQUIRED
    elif "PAT001-GAP-PROVENANCE" in gaps:
        status = PROVENANCE_REQUIRED
    elif "PAT001-GAP-ANALYSIS-SCOPE" in gaps:
        status = ANALYSIS_SCOPE_REQUIRED
    elif "PAT001-GAP-SCIA-MODEL" in gaps:
        status = SCIA_MODEL_REQUIRED
    elif "PAT001-GAP-CALCULIX-ADAPTER" in gaps:
        status = CALCULIX_ADAPTER_REQUIRED
    else:
        status = PREPARATION_READY

    candidates = inventory_candidates(repository)
    inventory_path = output_root / "pat001_structural_candidate_inventory_v1_0.json"
    write_json(inventory_path, {
        "project_id": PROJECT_ID,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "boundary": "Candidates are not PAT-001 project evidence unless explicitly qualified by provenance.",
    })

    plan = {
        "schema_version": "phoenix.pat001-structural-execution-plan/1.0",
        "project_id": PROJECT_ID,
        "preparation_status": status,
        "analysis_scope": calc_type,
        "canonical_model": str(resolved_canonical) if resolved_canonical else None,
        "canonical_validation": canonical_result,
        "scia": {
            "qualified_seed": scia_seed,
            "xml_update": xml_update,
            "xml_definition": xml_definition,
            "preparation_ready": scia_ready,
            "live_execution": "NOT_STARTED",
            "license_environment": "SEPARATE_READINESS_GATE_REQUIRED",
        },
        "calculix": {
            "project_adapter": adapter,
            "preparation_ready": bool(calculix_ready and canonical_result and canonical_result["status"] == CANONICAL_VALID),
            "live_execution": "NOT_STARTED",
        },
        "analytical_spot_checks": {
            "status": "PROJECT_SPECIFIC_SELECTION_REQUIRED",
            "golden_reference_suite_is_project_evidence": False,
        },
        "professional_review": "NOT_STARTED",
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }
    write_json(output_root / "pat001_structural_execution_plan_v1_0.json", plan)

    result = {
        "schema_version": "phoenix.pat001-structural-preparation-result/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": status,
        "errors": errors,
        "gaps": sorted(set(gaps)),
        "missing_provenance_categories": missing_prov,
        "canonical_validation": canonical_result,
        "scia_seed_qualification": scia_seed,
        "scia_preparation_ready": scia_ready,
        "calculix_project_adapter_ready": bool(calculix_ready),
        "candidate_inventory": str(inventory_path),
        "execution_plan": str(output_root / "pat001_structural_execution_plan_v1_0.json"),
        "live_scia_started": False,
        "live_calculix_started": False,
        "professional_review_started": False,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "pat001_structural_preparation_result_v1_0.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = assess(Path(args.contract), Path(args.repository), Path(args.output))
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
