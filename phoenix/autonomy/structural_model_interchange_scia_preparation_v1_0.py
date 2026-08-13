"""PROJECT PHOENIX Structural Model Interchange + SCIA Project Preparation v1.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import argparse
import hashlib
import json
import shutil

VERSION = "1.0.0"
ENGINE_ID = "PHX-STRUCTURAL-MODEL-INTERCHANGE-SCIA-PREPARATION"

VALID = "CANONICAL_STRUCTURAL_MODEL_VALIDATED"
INVALID = "CANONICAL_STRUCTURAL_MODEL_INVALID"
SCIA_MODEL_BUILD_REQUIRED = "SCIA_MODEL_BUILD_REQUIRED"
SCIA_SEED_PRESENT_XML_MAPPING_REQUIRED = "SCIA_SEED_PRESENT_XML_MAPPING_REQUIRED"
SCIA_ANALYSIS_SCOPE_REQUIRED = "SCIA_ANALYSIS_SCOPE_REQUIRED"
SCIA_SEED_XML_PREPARATION_READY = "SCIA_SEED_XML_PREPARATION_READY"

SAFETY = {
    "automatic_binary_esa_synthesis": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_production_release": False,
    "automatic_for_construction_release": False,
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
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(model: dict[str, Any]) -> bytes:
    return json.dumps(model, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_model_sha256(model: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(model)).hexdigest()


def _unique_ids(items: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(items, list):
        errors.append(f"{label}:must_be_array")
        return set()
    ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}]:must_be_object")
            continue
        value = item.get("id")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}[{index}].id:required")
            continue
        ids.append(value)
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    for value in duplicates:
        errors.append(f"{label}:duplicate_id:{value}")
    return set(ids)


def _require_ref(value: Any, allowed: set[str], path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{path}:required")
    elif value not in allowed:
        errors.append(f"{path}:unknown_reference:{value}")


def validate_model(model: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if model.get("schema_version") != "phoenix.canonical-structural-model/1.0":
        errors.append("schema_version:unsupported")
    if not isinstance(model.get("model_id"), str) or not model.get("model_id", "").strip():
        errors.append("model_id:required")

    units = model.get("units")
    if not isinstance(units, dict):
        errors.append("units:required_object")
    else:
        for key in ("length", "force"):
            if not isinstance(units.get(key), str) or not units.get(key):
                errors.append(f"units.{key}:required")

    node_ids = _unique_ids(model.get("nodes"), "nodes", errors)
    material_ids = _unique_ids(model.get("materials"), "materials", errors)
    section_ids = _unique_ids(model.get("sections"), "sections", errors)
    member_ids = _unique_ids(model.get("members"), "members", errors)
    _unique_ids(model.get("supports"), "supports", errors)
    load_case_ids = _unique_ids(model.get("load_cases"), "load_cases", errors)
    _unique_ids(model.get("nodal_loads"), "nodal_loads", errors)
    _unique_ids(model.get("line_loads"), "line_loads", errors)
    _unique_ids(model.get("load_combinations"), "load_combinations", errors)

    for index, node in enumerate(model.get("nodes", []) if isinstance(model.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        for axis in ("x", "y", "z"):
            if not isinstance(node.get(axis), (int, float)) or isinstance(node.get(axis), bool):
                errors.append(f"nodes[{index}].{axis}:number_required")

    for index, member in enumerate(model.get("members", []) if isinstance(model.get("members"), list) else []):
        if not isinstance(member, dict):
            continue
        _require_ref(member.get("start_node"), node_ids, f"members[{index}].start_node", errors)
        _require_ref(member.get("end_node"), node_ids, f"members[{index}].end_node", errors)
        _require_ref(member.get("material"), material_ids, f"members[{index}].material", errors)
        _require_ref(member.get("section"), section_ids, f"members[{index}].section", errors)
        if member.get("start_node") == member.get("end_node") and member.get("start_node"):
            errors.append(f"members[{index}]:zero_topological_length")

    for index, support in enumerate(model.get("supports", []) if isinstance(model.get("supports"), list) else []):
        if isinstance(support, dict):
            _require_ref(support.get("node"), node_ids, f"supports[{index}].node", errors)

    for index, load in enumerate(model.get("nodal_loads", []) if isinstance(model.get("nodal_loads"), list) else []):
        if isinstance(load, dict):
            _require_ref(load.get("node"), node_ids, f"nodal_loads[{index}].node", errors)
            _require_ref(load.get("load_case"), load_case_ids, f"nodal_loads[{index}].load_case", errors)

    for index, load in enumerate(model.get("line_loads", []) if isinstance(model.get("line_loads"), list) else []):
        if isinstance(load, dict):
            _require_ref(load.get("member"), member_ids, f"line_loads[{index}].member", errors)
            _require_ref(load.get("load_case"), load_case_ids, f"line_loads[{index}].load_case", errors)

    for index, combo in enumerate(model.get("load_combinations", []) if isinstance(model.get("load_combinations"), list) else []):
        if not isinstance(combo, dict):
            continue
        terms = combo.get("terms")
        if not isinstance(terms, list) or not terms:
            errors.append(f"load_combinations[{index}].terms:nonempty_array_required")
            continue
        for term_index, term in enumerate(terms):
            if not isinstance(term, dict):
                errors.append(f"load_combinations[{index}].terms[{term_index}]:object_required")
                continue
            _require_ref(term.get("load_case"), load_case_ids, f"load_combinations[{index}].terms[{term_index}].load_case", errors)
            if not isinstance(term.get("factor"), (int, float)) or isinstance(term.get("factor"), bool):
                errors.append(f"load_combinations[{index}].terms[{term_index}].factor:number_required")

    if not isinstance(model.get("metadata"), dict):
        errors.append("metadata:object_required")

    return {
        "status": VALID if not errors else INVALID,
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "model_id": model.get("model_id"),
        "canonical_sha256": canonical_model_sha256(model),
        "errors": errors,
        "counts": {
            key: len(model.get(key, [])) if isinstance(model.get(key), list) else 0
            for key in (
                "nodes", "materials", "sections", "members", "supports",
                "load_cases", "nodal_loads", "line_loads", "load_combinations"
            )
        },
        "safety": dict(SAFETY),
    }


def solver_neutral_mapping(model: dict[str, Any]) -> dict[str, Any]:
    def entries(source: str, target_kind: str) -> list[dict[str, Any]]:
        return [
            {
                "canonical_id": item["id"],
                "canonical_collection": source,
                "scia_target_kind": target_kind,
                "scia_object_id": "UNRESOLVED_UNTIL_SCIA_MODEL_ADAPTER",
            }
            for item in model.get(source, [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]

    return {
        "schema_version": "phoenix.scia-object-mapping-plan/1.0",
        "model_id": model.get("model_id"),
        "mapping_status": "SCIA_OBJECT_IDS_UNRESOLVED",
        "mappings": (
            entries("nodes", "NODE")
            + entries("materials", "MATERIAL")
            + entries("sections", "SECTION")
            + entries("members", "MEMBER")
            + entries("supports", "SUPPORT")
            + entries("load_cases", "LOAD_CASE")
            + entries("nodal_loads", "NODAL_LOAD")
            + entries("line_loads", "LINE_LOAD")
            + entries("load_combinations", "LOAD_COMBINATION")
        ),
        "boundary": "No SCIA GUID/object identifier is fabricated.",
    }


def _copy_exact(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    before = sha256_file(source)
    shutil.copy2(source, destination)
    after = sha256_file(destination)
    if before != after:
        raise RuntimeError(f"Exact-copy SHA256 mismatch: {source}")
    return {
        "source": str(source),
        "stored_as": str(destination),
        "sha256": after,
        "size_bytes": destination.stat().st_size,
    }


def prepare_scia(
    model_path: Path,
    output_root: Path,
    seed_esa: Path | None = None,
    xml_update: Path | None = None,
    xml_definition: Path | None = None,
    analysis_scope: str | None = None,
    esa_xml_path: str = r"C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe",
) -> dict[str, Any]:
    model = read_json(model_path)
    validation = validate_model(model)
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "canonical_model_validation.json", validation)
    if validation["status"] != VALID:
        result = {
            "status": INVALID,
            "model_id": model.get("model_id"),
            "validation": validation,
            "safety": dict(SAFETY),
        }
        write_json(output_root / "scia_project_preparation_result.json", result)
        return result

    normalized = output_root / "canonical_structural_model.normalized.json"
    write_json(normalized, model)
    evidence: list[dict[str, Any]] = [{
        "role": "CANONICAL_MODEL",
        "path": str(normalized),
        "sha256": sha256_file(normalized),
        "canonical_sha256": validation["canonical_sha256"],
    }]

    copied: dict[str, Any] = {}
    if seed_esa is not None:
        if not seed_esa.is_file():
            raise FileNotFoundError(seed_esa)
        copied["seed_esa"] = _copy_exact(seed_esa, output_root / "inputs" / "seed_model.esa")
        evidence.append({"role": "SCIA_SEED_ESA", **copied["seed_esa"]})
    if xml_update is not None:
        if not xml_update.is_file():
            raise FileNotFoundError(xml_update)
        copied["xml_update"] = _copy_exact(xml_update, output_root / "inputs" / "project_update.xml")
        evidence.append({"role": "SCIA_XML_UPDATE", **copied["xml_update"]})
    if xml_definition is not None:
        if not xml_definition.is_file():
            raise FileNotFoundError(xml_definition)
        copied["xml_definition"] = _copy_exact(xml_definition, output_root / "inputs" / "project_update.xml.def")
        evidence.append({"role": "SCIA_XML_DEFINITION", **copied["xml_definition"]})

    mapping = solver_neutral_mapping(model)
    write_json(output_root / "scia_object_mapping_plan.json", mapping)

    scope = analysis_scope.strip().upper() if isinstance(analysis_scope, str) and analysis_scope.strip() else None
    if seed_esa is None:
        status = SCIA_MODEL_BUILD_REQUIRED
    elif xml_update is None or xml_definition is None:
        status = SCIA_SEED_PRESENT_XML_MAPPING_REQUIRED
    elif scope is None:
        status = SCIA_ANALYSIS_SCOPE_REQUIRED
    else:
        status = SCIA_SEED_XML_PREPARATION_READY

    command_plan = {
        "schema_version": "phoenix.scia-command-plan/1.0",
        "execution": "NOT_EXECUTED_PREPARATION_ONLY",
        "esa_xml": esa_xml_path,
        "analysis_scope": scope or "REQUIRED",
        "working_seed": str(output_root / "inputs" / "seed_model.esa") if seed_esa else None,
        "xml_update": str(output_root / "inputs" / "project_update.xml") if xml_update else None,
        "argv_template": (
            [esa_xml_path, scope, str(output_root / "inputs" / "seed_model.esa"), str(output_root / "inputs" / "project_update.xml")]
            if status == SCIA_SEED_XML_PREPARATION_READY else None
        ),
        "boundary": "Command plan is evidence only; preparation never launches SCIA.",
    }
    write_json(output_root / "scia_command_plan.json", command_plan)

    calculation_plan = {
        "schema_version": "phoenix.structural-calculation-plan/1.0",
        "model_id": model.get("model_id"),
        "analysis_scope": scope or "REQUIRED_PROJECT_SPECIFIC_INPUT",
        "scope_status": "EXPLICIT" if scope else "INPUT_REQUIRED",
        "automatic_seismic_scope": False,
        "automatic_nonlinear_scope": False,
        "automatic_robustness_scope": False,
        "professional_approval": "NOT_AUTOMATIC",
    }
    write_json(output_root / "scia_calculation_plan.json", calculation_plan)

    manifest = {
        "schema_version": "phoenix.scia-project-preparation-manifest/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "model_id": model.get("model_id"),
        "status": status,
        "canonical_sha256": validation["canonical_sha256"],
        "copied_inputs": copied,
        "mapping_plan": "scia_object_mapping_plan.json",
        "calculation_plan": "scia_calculation_plan.json",
        "command_plan": "scia_command_plan.json",
        "binary_esa_synthesis": "NOT_PERFORMED",
        "live_scia_execution": "NOT_STARTED",
        "safety": dict(SAFETY),
    }
    write_json(output_root / "scia_project_preparation_manifest.json", manifest)

    evidence_doc = {
        "schema_version": "phoenix.evidence-manifest/1.0",
        "model_id": model.get("model_id"),
        "evidence": evidence,
        "preparation_status": status,
        "release": {
            "production": "LOCKED",
            "for_construction": "LOCKED",
        }
    }
    write_json(output_root / "evidence_manifest.json", evidence_doc)

    result = {
        "status": status,
        "model_id": model.get("model_id"),
        "validation": validation,
        "manifest": manifest,
        "output_root": str(output_root),
        "safety": dict(SAFETY),
    }
    write_json(output_root / "scia_project_preparation_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--model", required=True)
    v.add_argument("--output", required=True)

    p = sub.add_parser("prepare-scia")
    p.add_argument("--model", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seed-esa")
    p.add_argument("--xml-update")
    p.add_argument("--xml-definition")
    p.add_argument("--analysis-scope")
    p.add_argument("--esa-xml", default=r"C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe")

    args = parser.parse_args()
    if args.action == "validate":
        model = read_json(Path(args.model))
        result = validate_model(model)
        write_json(Path(args.output), result)
    else:
        result = prepare_scia(
            Path(args.model),
            Path(args.output),
            Path(args.seed_esa) if args.seed_esa else None,
            Path(args.xml_update) if args.xml_update else None,
            Path(args.xml_definition) if args.xml_definition else None,
            args.analysis_scope,
            args.esa_xml,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result.get("status") in {INVALID}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
