"""PROJECT PHOENIX PAT-001 structural evidence harvester + contract bootstrap v1.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import copy
import hashlib
import json
import re

from phoenix.autonomy.structural_model_interchange_scia_preparation_v1_0 import (
    VALID as CANONICAL_VALID,
    validate_model,
)
from phoenix.autonomy.pat001_structural_preparation_v1_0 import assess as assess_pat001

VERSION = "1.1.0"
ENGINE_ID = "PHX-PAT001-STRUCTURAL-EVIDENCE-HARVEST-BOOTSTRAP"
PROJECT_ID = "PHOENIX-PAT-001"

HARVEST_COMPLETE = "PAT001_STRUCTURAL_EVIDENCE_HARVEST_COMPLETE"
BOOTSTRAP_WRITTEN = "PAT001_STRUCTURAL_CONTRACT_BOOTSTRAPPED"
BOOTSTRAP_NO_AUTOFILL = "PAT001_STRUCTURAL_CONTRACT_BOOTSTRAP_NO_AUTOFILL"

SAFETY = {
    "source_contract_overwritten": False,
    "field_invented_without_source": False,
    "historical_esa_auto_labeled_pat001": False,
    "reference_model_is_pat001_project_evidence": False,
    "automatic_live_scia": False,
    "automatic_live_calculix": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}

IDENTITY_KEYS = {
    "name": ("project_name", "projectname", "name"),
    "location": ("project_location", "projectlocation", "location"),
    "structural_scope": ("structural_scope", "structuralscope"),
}
PROV_KEYWORDS = {
    "geometry": {"nodes", "members", "geometry", "structural_geometry", "coordinates"},
    "materials": {"materials", "material"},
    "sections": {"sections", "section", "cross_sections", "crosssections"},
    "supports_and_boundaries": {"supports", "boundaries", "boundary_conditions", "boundaryconditions"},
    "load_basis": {"load_basis", "loadbasis", "loads"},
    "load_cases": {"load_cases", "loadcases"},
    "load_combinations": {"load_combinations", "loadcombinations", "combinations"},
}
CALC_TYPES = {"NONE","NOC","LIN","NEL","CON","EIG","STB","INF","MOB","TDA","SLN","PHA","NPH","CSS","NST","TID"}


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


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", value.strip().lower())


def contains_project_id(value: Any) -> bool:
    if isinstance(value, dict):
        for k, v in value.items():
            if norm_key(str(k)) in {"project_id","projectid"} and str(v).strip() == PROJECT_ID:
                return True
            if contains_project_id(v):
                return True
    elif isinstance(value, list):
        return any(contains_project_id(x) for x in value)
    return False


def flatten_key_values(value: Any, out: list[tuple[str, Any]], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.append((path, child))
            flatten_key_values(child, out, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            flatten_key_values(child, out, f"{prefix}[{index}]")


def json_candidates(repository: Path) -> list[dict[str, Any]]:
    roots = [
        repository / "projects" / "runtime" / PROJECT_ID,
        repository / "configs" / "projects",
        repository / "configs" / "phoenix" / "structural",
    ]
    candidates = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            if not path.is_file():
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                data = read_json(path)
            except Exception:
                continue
            explicit = contains_project_id(data)
            path_scoped = (
                repository / "projects" / "runtime" / PROJECT_ID
            ) in path.parents
            candidates.append({
                "path": path,
                "data": data,
                "explicit_project_id": explicit,
                "path_scoped_pat001": path_scoped,
                "sha256": sha256_file(path),
            })
    return candidates


def source_record(item: dict[str, Any], field_path: str | None = None) -> dict[str, Any]:
    rec = {
        "reference": str(item["path"]),
        "sha256": item["sha256"],
        "project_id_explicit": item["explicit_project_id"],
        "path_scoped_pat001": item["path_scoped_pat001"],
    }
    if field_path:
        rec["field_path"] = field_path
    return rec


def unique_values(values: list[tuple[Any, dict[str, Any], str]]) -> tuple[Any | None, list[dict[str, Any]], list[Any]]:
    normalized = {}
    for value, src, path in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        normalized.setdefault(key, {"value": value, "sources": []})
        normalized[key]["sources"].append(source_record(src, path))
    if len(normalized) == 1:
        only = next(iter(normalized.values()))
        return only["value"], only["sources"], []
    conflicts = [x["value"] for x in normalized.values()]
    return None, [], conflicts


def harvest_identity(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for target, aliases in IDENTITY_KEYS.items():
        found = []
        for item in candidates:
            if not item["explicit_project_id"]:
                continue
            flat = []
            flatten_key_values(item["data"], flat)
            for path, value in flat:
                key = norm_key(path.split(".")[-1])
                if key in aliases and isinstance(value, (str, int, float)):
                    text = str(value).strip()
                    if text and text.upper() != "REQUIRED":
                        found.append((text, item, path))
        value, sources, conflicts = unique_values(found)
        result[target] = {"value": value, "sources": sources, "conflicts": conflicts}
    return result


def harvest_canonical(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    valid = []
    invalid = []
    for item in candidates:
        data = item["data"]
        if data.get("schema_version") != "phoenix.canonical-structural-model/1.0":
            continue
        if not item["explicit_project_id"] and not item["path_scoped_pat001"]:
            continue
        result = validate_model(data)
        rec = {
            "path": str(item["path"]),
            "sha256": item["sha256"],
            "validation": result,
            "project_id_explicit": item["explicit_project_id"],
            "path_scoped_pat001": item["path_scoped_pat001"],
        }
        if result["status"] == CANONICAL_VALID:
            valid.append(rec)
        else:
            invalid.append(rec)
    selected = valid[0] if len(valid) == 1 else None
    return {
        "selected": selected,
        "valid_candidates": valid,
        "invalid_candidates": invalid,
        "conflict": len(valid) > 1,
    }


def harvest_provenance(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for category, keywords in PROV_KEYWORDS.items():
        sources = []
        for item in candidates:
            if not item["explicit_project_id"] and not item["path_scoped_pat001"]:
                continue
            flat = []
            flatten_key_values(item["data"], flat)
            matched = []
            for path, value in flat:
                key = norm_key(path.split(".")[-1])
                if key in keywords and value not in (None, [], {}, ""):
                    matched.append(path)
            if matched:
                rec = source_record(item)
                rec["matched_fields"] = sorted(set(matched))
                sources.append(rec)
        result[category] = {
            "status": "TRACEABLE" if sources else "REQUIRED",
            "sources": sources,
        }
    return result


def harvest_analysis_scope(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    found = []
    for item in candidates:
        if not item["explicit_project_id"] and not item["path_scoped_pat001"]:
            continue
        flat = []
        flatten_key_values(item["data"], flat)
        for path, value in flat:
            key = norm_key(path.split(".")[-1])
            if key in {"calculation_type","calculationtype","analysis_type","analysistype"}:
                text = str(value).strip().upper()
                if text in CALC_TYPES:
                    found.append((text, item, path))
    value, sources, conflicts = unique_values(found)
    return {
        "calculation_type": value,
        "status": "CONFIRMED" if value else "REQUIRED",
        "sources": sources,
        "conflicts": conflicts,
    }


def resolve_candidate_path(repository: Path, source_json: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    local = source_json.parent / p
    if local.exists():
        return local
    return repository / p


def harvest_scia_seed(repository: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    qualified = []
    rejected = []
    for item in candidates:
        if not item["explicit_project_id"]:
            continue
        flat = []
        flatten_key_values(item["data"], flat)
        seed_values = []
        sha_values = []
        xml_values = []
        def_values = []
        for path, value in flat:
            key = norm_key(path.split(".")[-1])
            if key in {"seed_esa","selected_seed","esa_seed"} and isinstance(value, str) and value.lower().endswith(".esa"):
                seed_values.append((value, path))
            elif key in {"sha256","seed_sha256","esa_sha256"} and isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()):
                sha_values.append((value.strip().lower(), path))
            elif key in {"xml_update","xmlupdate"} and isinstance(value, str):
                xml_values.append((value, path))
            elif key in {"xml_definition","xmldefinition","xml_def"} and isinstance(value, str):
                def_values.append((value, path))
        for seed_value, seed_field in seed_values:
            seed_path = resolve_candidate_path(repository, item["path"], seed_value)
            if not seed_path.is_file():
                rejected.append({"source": str(item["path"]), "seed": str(seed_path), "reason": "FILE_NOT_FOUND"})
                continue
            actual = sha256_file(seed_path)
            matching = [x for x in sha_values if x[0] == actual]
            if not matching:
                rejected.append({"source": str(item["path"]), "seed": str(seed_path), "reason": "NO_MATCHING_SHA256", "actual_sha256": actual})
                continue
            qualified.append({
                "seed_esa": str(seed_path),
                "sha256": actual,
                "project_id": PROJECT_ID,
                "source": source_record(item, seed_field),
                "xml_update_candidates": [x[0] for x in xml_values],
                "xml_definition_candidates": [x[0] for x in def_values],
            })
    return {
        "selected": qualified[0] if len(qualified) == 1 else None,
        "qualified_candidates": qualified,
        "rejected_candidates": rejected,
        "conflict": len(qualified) > 1,
    }


def harvest_calculix_adapter(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    found = []
    for item in candidates:
        if not item["explicit_project_id"]:
            continue
        flat = []
        flatten_key_values(item["data"], flat)
        for path, value in flat:
            key = norm_key(path.split(".")[-1])
            if key in {"project_adapter","calculix_project_adapter","adapter_id"} and isinstance(value, str):
                text = value.strip()
                if text and not text.upper().startswith("REQUIRED"):
                    found.append((text, item, path))
    value, sources, conflicts = unique_values(found)
    return {
        "project_adapter": value,
        "sources": sources,
        "conflicts": conflicts,
    }


def bootstrap(repository: Path, source_contract: Path, output_contract: Path, audit_path: Path) -> dict[str, Any]:
    if not source_contract.is_file():
        raise FileNotFoundError(source_contract)
    original = read_json(source_contract)
    boot = copy.deepcopy(original)
    candidates = json_candidates(repository)

    identity = harvest_identity(candidates)
    canonical = harvest_canonical(candidates)
    provenance = harvest_provenance(candidates)
    scope = harvest_analysis_scope(candidates)
    scia = harvest_scia_seed(repository, candidates)
    calculix = harvest_calculix_adapter(candidates)

    applied = []
    unresolved = []
    conflicts = []

    ident = boot.setdefault("project_identity", {})
    for key, result in identity.items():
        if result["value"] is not None:
            ident[key] = result["value"]
            applied.append({"field": f"project_identity.{key}", "value": result["value"], "sources": result["sources"]})
        else:
            unresolved.append(f"project_identity.{key}")
            if result["conflicts"]:
                conflicts.append({"field": f"project_identity.{key}", "values": result["conflicts"]})

    if canonical["selected"]:
        rel = canonical["selected"]["path"]
        try:
            rel = str(Path(rel).resolve().relative_to(repository.resolve()))
        except Exception:
            pass
        boot.setdefault("canonical_structural_model", {})["path"] = rel
        applied.append({"field": "canonical_structural_model.path", "value": rel, "sources": [canonical["selected"]]})
    else:
        unresolved.append("canonical_structural_model.path")
        if canonical["conflict"]:
            conflicts.append({"field": "canonical_structural_model.path", "values": [x["path"] for x in canonical["valid_candidates"]]})

    boot_prov = boot.setdefault("provenance", {})
    for category, result in provenance.items():
        if result["sources"]:
            boot_prov[category] = {"status": "TRACEABLE", "sources": result["sources"]}
            applied.append({"field": f"provenance.{category}", "value": "TRACEABLE", "sources": result["sources"]})
        else:
            unresolved.append(f"provenance.{category}")

    boot_scope = boot.setdefault("analysis_scope", {})
    if scope["calculation_type"]:
        boot_scope["status"] = "CONFIRMED"
        boot_scope["calculation_type"] = scope["calculation_type"]
        boot_scope["evidence"] = scope["sources"]
        applied.append({"field": "analysis_scope.calculation_type", "value": scope["calculation_type"], "sources": scope["sources"]})
    else:
        unresolved.append("analysis_scope.calculation_type")
        if scope["conflicts"]:
            conflicts.append({"field": "analysis_scope.calculation_type", "values": scope["conflicts"]})

    boot_scia = boot.setdefault("scia", {})
    if scia["selected"]:
        s = scia["selected"]
        boot_scia["seed_esa"] = s["seed_esa"]
        boot_scia["seed_provenance"] = {"project_id": PROJECT_ID, "sha256": s["sha256"], "source": s["source"]}
        if len(s["xml_update_candidates"]) == 1:
            boot_scia["xml_update"] = s["xml_update_candidates"][0]
        if len(s["xml_definition_candidates"]) == 1:
            boot_scia["xml_definition"] = s["xml_definition_candidates"][0]
        applied.append({"field": "scia.seed_esa", "value": s["seed_esa"], "sources": [s["source"]]})
    else:
        unresolved.append("scia.seed_esa")
        if scia["conflict"]:
            conflicts.append({"field": "scia.seed_esa", "values": [x["seed_esa"] for x in scia["qualified_candidates"]]})

    boot_calc = boot.setdefault("calculix", {})
    if calculix["project_adapter"]:
        boot_calc["project_adapter"] = calculix["project_adapter"]
        boot_calc["evidence"] = calculix["sources"]
        applied.append({"field": "calculix.project_adapter", "value": calculix["project_adapter"], "sources": calculix["sources"]})
    else:
        unresolved.append("calculix.project_adapter")
        if calculix["conflicts"]:
            conflicts.append({"field": "calculix.project_adapter", "values": calculix["conflicts"]})

    write_json(output_contract, boot)
    audit = {
        "schema_version": "phoenix.pat001-structural-bootstrap-audit/1.1",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": BOOTSTRAP_WRITTEN if applied else BOOTSTRAP_NO_AUTOFILL,
        "source_contract": str(source_contract),
        "source_contract_sha256": sha256_file(source_contract),
        "output_contract": str(output_contract),
        "output_contract_sha256": sha256_file(output_contract),
        "candidate_json_count": len(candidates),
        "applied_fields": applied,
        "unresolved_fields": sorted(set(unresolved)),
        "conflicts": conflicts,
        "harvest": {
            "identity": identity,
            "canonical": canonical,
            "provenance": provenance,
            "analysis_scope": scope,
            "scia_seed": scia,
            "calculix_adapter": calculix,
        },
        "safety": dict(SAFETY),
    }
    write_json(audit_path, audit)
    return audit


def bootstrap_and_assess(repository: Path, source_contract: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    output_contract = output_root / "pat001_structural_input_contract_v1_1.json"
    audit_path = output_root / "pat001_structural_bootstrap_audit_v1_1.json"
    audit = bootstrap(repository, source_contract, output_contract, audit_path)
    assessment_root = output_root / "assessment_v1_1"
    assessment = assess_pat001(output_contract, repository, assessment_root)
    result = {
        "schema_version": "phoenix.pat001-structural-bootstrap-and-assess/1.1",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": PROJECT_ID,
        "status": HARVEST_COMPLETE,
        "bootstrap_status": audit["status"],
        "bootstrapped_contract": str(output_contract),
        "bootstrap_audit": str(audit_path),
        "assessment_status": assessment.get("status"),
        "assessment_gaps": assessment.get("gaps", []),
        "assessment_result": str(assessment_root / "pat001_structural_preparation_result_v1_0.json"),
        "applied_field_count": len(audit["applied_fields"]),
        "unresolved_field_count": len(audit["unresolved_fields"]),
        "conflict_count": len(audit["conflicts"]),
        "live_scia_started": False,
        "live_calculix_started": False,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "pat001_structural_bootstrap_and_assess_result_v1_1.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = bootstrap_and_assess(
        Path(args.repository),
        Path(args.source_contract),
        Path(args.output),
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
