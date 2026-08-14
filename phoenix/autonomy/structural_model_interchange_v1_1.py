"""Project Phoenix Canonical Structural Model v1.1 validation utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import math

SCHEMA_VERSION = "phoenix.canonical-structural-model/1.1"
VALID = "CANONICAL_STRUCTURAL_MODEL_V1_1_VALIDATED"
INVALID = "CANONICAL_STRUCTURAL_MODEL_V1_1_INVALID"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _unique_ids(items: Any, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{label}:LIST_REQUIRED")
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}]:OBJECT_REQUIRED")
            continue
        raw = item.get("id")
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"{label}[{index}]:ID_REQUIRED")
            continue
        ident = raw.strip()
        if ident in mapping:
            errors.append(f"{label}:{ident}:DUPLICATE_ID")
            continue
        mapping[ident] = item
    return mapping


def _finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_model(model: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(model, dict):
        return {"status": INVALID, "errors": ["ROOT_OBJECT_REQUIRED"], "warnings": []}
    if model.get("schema_version") != SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_INVALID")
    if not isinstance(model.get("project_id"), str) or not model["project_id"].strip():
        errors.append("PROJECT_ID_REQUIRED")
    if not isinstance(model.get("model_id"), str) or not model["model_id"].strip():
        errors.append("MODEL_ID_REQUIRED")

    units = model.get("units")
    if not isinstance(units, dict):
        errors.append("UNITS_OBJECT_REQUIRED")
    else:
        for key in ("length", "force"):
            if not isinstance(units.get(key), str) or not units[key].strip():
                errors.append(f"UNITS_{key.upper()}_REQUIRED")

    nodes = _unique_ids(model.get("nodes"), "nodes", errors)
    materials = _unique_ids(model.get("materials"), "materials", errors)
    sections = _unique_ids(model.get("sections"), "sections", errors)
    members = _unique_ids(model.get("members"), "members", errors)
    shells = _unique_ids(model.get("shells"), "shells", errors)
    supports = _unique_ids(model.get("supports"), "supports", errors)
    load_cases = _unique_ids(model.get("load_cases"), "load_cases", errors)
    actions = _unique_ids(model.get("load_actions"), "load_actions", errors)
    combinations = _unique_ids(model.get("load_combinations"), "load_combinations", errors)

    if not nodes:
        errors.append("NODES_REQUIRED")
    if not members and not shells:
        errors.append("STRUCTURAL_ELEMENTS_REQUIRED")

    for ident, node in nodes.items():
        for key in ("x", "y", "z"):
            if not _finite_number(node.get(key)):
                errors.append(f"nodes:{ident}:{key.upper()}_FINITE_REQUIRED")

    for ident, member in members.items():
        start = member.get("start_node")
        end = member.get("end_node")
        material = member.get("material")
        section = member.get("section")
        if start not in nodes:
            errors.append(f"members:{ident}:UNKNOWN_START_NODE:{start}")
        if end not in nodes:
            errors.append(f"members:{ident}:UNKNOWN_END_NODE:{end}")
        if start == end and start is not None:
            errors.append(f"members:{ident}:ZERO_TOPOLOGICAL_LENGTH")
        if material not in materials:
            errors.append(f"members:{ident}:UNKNOWN_MATERIAL:{material}")
        if section not in sections:
            errors.append(f"members:{ident}:UNKNOWN_SECTION:{section}")

    for ident, shell in shells.items():
        refs = shell.get("node_ids")
        if not isinstance(refs, list) or len(refs) < 3:
            errors.append(f"shells:{ident}:AT_LEAST_3_NODE_IDS_REQUIRED")
        else:
            for ref in refs:
                if ref not in nodes:
                    errors.append(f"shells:{ident}:UNKNOWN_NODE:{ref}")
        if shell.get("material") not in materials:
            errors.append(f"shells:{ident}:UNKNOWN_MATERIAL:{shell.get('material')}")
        if shell.get("section") not in sections:
            errors.append(f"shells:{ident}:UNKNOWN_SECTION:{shell.get('section')}")

    for ident, support in supports.items():
        if support.get("node") not in nodes:
            errors.append(f"supports:{ident}:UNKNOWN_NODE:{support.get('node')}")
        dofs = support.get("dofs")
        if not isinstance(dofs, list) or not dofs:
            errors.append(f"supports:{ident}:DOFS_REQUIRED")

    element_ids = set(members) | set(shells)
    for ident, action in actions.items():
        case = action.get("load_case")
        if case not in load_cases:
            errors.append(f"load_actions:{ident}:UNKNOWN_LOAD_CASE:{case}")
        target_node = action.get("target_node")
        if target_node is not None and target_node not in nodes:
            errors.append(f"load_actions:{ident}:UNKNOWN_TARGET_NODE:{target_node}")
        target_element = action.get("target_element")
        if target_element is not None and target_element not in element_ids:
            errors.append(f"load_actions:{ident}:UNKNOWN_TARGET_ELEMENT:{target_element}")
        target_elements = action.get("target_elements")
        if target_elements is not None:
            if not isinstance(target_elements, list):
                errors.append(f"load_actions:{ident}:TARGET_ELEMENTS_LIST_REQUIRED")
            else:
                for target in target_elements:
                    if target not in element_ids:
                        errors.append(f"load_actions:{ident}:UNKNOWN_TARGET_ELEMENT:{target}")

    for ident, combination in combinations.items():
        terms = combination.get("terms")
        if not isinstance(terms, list) or not terms:
            errors.append(f"load_combinations:{ident}:TERMS_REQUIRED")
            continue
        for index, term in enumerate(terms):
            if not isinstance(term, dict):
                errors.append(f"load_combinations:{ident}:term[{index}]:OBJECT_REQUIRED")
                continue
            case = term.get("load_case")
            if case not in load_cases:
                errors.append(f"load_combinations:{ident}:UNKNOWN_LOAD_CASE:{case}")
            if not _finite_number(term.get("factor")):
                errors.append(f"load_combinations:{ident}:term[{index}]:FACTOR_FINITE_REQUIRED")

    metadata = model.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("METADATA_OBJECT_REQUIRED")
    elif metadata.get("design_values_invented") is True:
        errors.append("METADATA_DESIGN_VALUES_INVENTED_MUST_NOT_BE_TRUE")

    if any(
        str(item.get("approval_state", "")).upper() == "CANDIDATE_ONLY"
        for group in (members.values(), shells.values(), supports.values(), actions.values())
        for item in group
    ):
        warnings.append("MODEL_CONTAINS_CANDIDATE_ONLY_ENGINEERING_RECORDS")

    result = {
        "status": VALID if not errors else INVALID,
        "schema_version": SCHEMA_VERSION,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "counts": {
            "nodes": len(nodes),
            "materials": len(materials),
            "sections": len(sections),
            "members": len(members),
            "shells": len(shells),
            "supports": len(supports),
            "load_cases": len(load_cases),
            "load_actions": len(actions),
            "load_combinations": len(combinations),
        },
    }
    if not errors:
        result["canonical_sha256"] = canonical_sha256(model)
    return result
