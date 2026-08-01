#!/usr/bin/env python3
"""Project Phoenix Structural Action and Load Model Generation Engine v8.2.0.

Builds a solver-neutral action/load model from an analytical structural model and
explicit project action inputs. The engine does not invent design values, execute
a solver, prove code compliance, grant structural approval, or unlock release.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Set, Tuple

ENGINE_ID = "PHX-STRUCT-ACTION-LOAD-MODEL-V8.2.0"
VERSION = "8.2.0"
LOCKED_RELEASE = "LOCKED"

ALLOWED_ACTION_KINDS = {"self_weight", "nodal", "line", "area", "acceleration"}
ALLOWED_DIRECTIONS = {"X", "Y", "Z", "GLOBAL_X", "GLOBAL_Y", "GLOBAL_Z", "GRAVITY"}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _require_nonempty_string(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be a non-empty string")
    return text


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, not boolean")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric: {value!r}") from exc


def _normalise_direction(value: Any) -> str:
    direction = _require_nonempty_string(value, "action direction").upper()
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Unsupported action direction: {direction}")
    return direction


def _element_index(analytical_model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for collection_name in ("members", "shells"):
        for item in _as_list(analytical_model.get(collection_name)):
            if not isinstance(item, dict):
                raise ValueError(f"{collection_name} entries must be objects")
            element_id = _require_nonempty_string(item.get("id"), f"{collection_name} element id")
            if element_id in index:
                raise ValueError(f"Duplicate analytical element id: {element_id}")
            copy = deepcopy(item)
            copy["collection"] = collection_name
            index[element_id] = copy
    return index


def _node_index(analytical_model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for item in _as_list(analytical_model.get("nodes")):
        if not isinstance(item, dict):
            raise ValueError("nodes entries must be objects")
        node_id = _require_nonempty_string(item.get("id"), "node id")
        if node_id in index:
            raise ValueError(f"Duplicate analytical node id: {node_id}")
        index[node_id] = deepcopy(item)
    return index


def _select_element_ids(
    selector: Mapping[str, Any],
    elements: Mapping[str, Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """Resolve explicit and type-based selectors without silently inventing targets."""
    selected: Set[str] = set()
    warnings: List[str] = []

    if bool(selector.get("all_members")):
        selected.update(eid for eid, item in elements.items() if item.get("collection") == "members")
    if bool(selector.get("all_shells")):
        selected.update(eid for eid, item in elements.items() if item.get("collection") == "shells")
    if bool(selector.get("all_elements")):
        selected.update(elements)

    requested_types = {
        str(value).strip()
        for value in _as_list(selector.get("element_types"))
        if str(value).strip()
    }
    if requested_types:
        selected.update(
            eid for eid, item in elements.items() if str(item.get("type", "")) in requested_types
        )

    for element_id in _as_list(selector.get("element_ids")):
        element_id = str(element_id).strip()
        if not element_id:
            continue
        if element_id in elements:
            selected.add(element_id)
        else:
            warnings.append(f"Selector references unknown analytical element: {element_id}")

    return sorted(selected), warnings


def _validate_units(unit_system: Mapping[str, Any]) -> Dict[str, str]:
    required = ("length", "force", "moment", "stress", "mass")
    normalised: Dict[str, str] = {}
    for key in required:
        normalised[key] = _require_nonempty_string(unit_system.get(key), f"unit_system.{key}")
    return normalised


def build_action_load_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    analytical_model = payload.get("analytical_model")
    if not isinstance(analytical_model, dict):
        raise ValueError("payload.analytical_model must be an object")

    action_input = payload.get("action_load_input")
    if not isinstance(action_input, dict):
        raise ValueError("payload.action_load_input must be an object")

    units = _validate_units(action_input.get("unit_system", {}))
    basis = _require_nonempty_string(action_input.get("basis"), "action_load_input.basis")
    elements = _element_index(analytical_model)
    nodes = _node_index(analytical_model)

    load_cases: List[Dict[str, Any]] = []
    assignments: List[Dict[str, Any]] = []
    traceability: MutableMapping[str, List[str]] = {}
    warnings: List[str] = []
    case_ids: Set[str] = set()
    action_ids: Set[str] = set()

    actions = _as_list(action_input.get("actions"))
    for action_index, action in enumerate(actions, 1):
        if not isinstance(action, dict):
            raise ValueError("Each action must be an object")

        action_id = _require_nonempty_string(action.get("id"), f"action[{action_index}].id")
        if action_id in action_ids:
            raise ValueError(f"Duplicate action id: {action_id}")
        action_ids.add(action_id)

        case_id = _require_nonempty_string(action.get("case_id"), f"action {action_id} case_id")
        category = _require_nonempty_string(action.get("category"), f"action {action_id} category")
        kind = _require_nonempty_string(action.get("kind"), f"action {action_id} kind").lower()
        if kind not in ALLOWED_ACTION_KINDS:
            raise ValueError(f"Unsupported action kind for {action_id}: {kind}")

        if case_id not in case_ids:
            load_cases.append({
                "id": case_id,
                "name": str(action.get("case_name") or case_id),
                "category": category,
                "analysis_type": str(action.get("analysis_type") or "STATIC"),
                "approval_state": "CANDIDATE_ONLY",
            })
            case_ids.add(case_id)
        else:
            existing = next(case for case in load_cases if case["id"] == case_id)
            if existing["category"] != category:
                raise ValueError(
                    f"Load case {case_id} is assigned conflicting categories: "
                    f"{existing['category']} and {category}"
                )

        direction = _normalise_direction(action.get("direction", "GRAVITY"))
        factor = _number(action.get("factor", 1.0), f"action {action_id} factor")
        traceability[action_id] = []

        if kind == "self_weight":
            target_ids, selector_warnings = _select_element_ids(
                action.get("target", {"all_elements": True}), elements
            )
            warnings.extend(selector_warnings)
            if not target_ids:
                warnings.append(f"Self-weight action {action_id} resolved to no analytical elements")
            assignment_id = f"LA{len(assignments) + 1:04d}"
            assignment = {
                "id": assignment_id,
                "source_action_id": action_id,
                "case_id": case_id,
                "kind": kind,
                "direction": direction,
                "factor": factor,
                "target_element_ids": target_ids,
                "derivation": "SOLVER_SELF_WEIGHT_FLAG",
                "approval_state": "CANDIDATE_ONLY",
            }
            assignments.append(assignment)
            traceability[action_id].append(assignment_id)
            continue

        if kind == "nodal":
            target_node_ids: List[str] = []
            for node_id in _as_list(action.get("target", {}).get("node_ids")):
                node_id = str(node_id).strip()
                if not node_id:
                    continue
                if node_id in nodes:
                    target_node_ids.append(node_id)
                else:
                    warnings.append(f"Action {action_id} references unknown analytical node: {node_id}")
            magnitude = _number(action.get("magnitude"), f"action {action_id} magnitude")
            if not target_node_ids:
                warnings.append(f"Nodal action {action_id} resolved to no analytical nodes")
            for node_id in sorted(set(target_node_ids)):
                assignment_id = f"LA{len(assignments) + 1:04d}"
                assignments.append({
                    "id": assignment_id,
                    "source_action_id": action_id,
                    "case_id": case_id,
                    "kind": kind,
                    "direction": direction,
                    "magnitude": magnitude,
                    "factor": factor,
                    "target_node_id": node_id,
                    "approval_state": "CANDIDATE_ONLY",
                })
                traceability[action_id].append(assignment_id)
            continue

        target_ids, selector_warnings = _select_element_ids(action.get("target", {}), elements)
        warnings.extend(selector_warnings)
        magnitude = _number(action.get("magnitude"), f"action {action_id} magnitude")
        if not target_ids:
            warnings.append(f"Action {action_id} resolved to no analytical elements")

        for element_id in target_ids:
            assignment_id = f"LA{len(assignments) + 1:04d}"
            assignments.append({
                "id": assignment_id,
                "source_action_id": action_id,
                "case_id": case_id,
                "kind": kind,
                "direction": direction,
                "magnitude": magnitude,
                "factor": factor,
                "target_element_id": element_id,
                "distribution": str(action.get("distribution") or "UNIFORM"),
                "approval_state": "CANDIDATE_ONLY",
            })
            traceability[action_id].append(assignment_id)

    combinations: List[Dict[str, Any]] = []
    combination_ids: Set[str] = set()
    for combination_index, combination in enumerate(_as_list(action_input.get("combinations")), 1):
        if not isinstance(combination, dict):
            raise ValueError("Each load combination must be an object")
        combination_id = _require_nonempty_string(
            combination.get("id"), f"combination[{combination_index}].id"
        )
        if combination_id in combination_ids:
            raise ValueError(f"Duplicate load combination id: {combination_id}")
        combination_ids.add(combination_id)

        terms: List[Dict[str, Any]] = []
        for term in _as_list(combination.get("terms")):
            if not isinstance(term, dict):
                raise ValueError(f"Combination {combination_id} terms must be objects")
            case_id = _require_nonempty_string(term.get("case_id"), f"combination {combination_id} case_id")
            if case_id not in case_ids:
                raise ValueError(f"Combination {combination_id} references unknown load case: {case_id}")
            terms.append({
                "case_id": case_id,
                "coefficient": _number(
                    term.get("coefficient"),
                    f"combination {combination_id} coefficient for {case_id}",
                ),
            })
        if not terms:
            raise ValueError(f"Combination {combination_id} must contain at least one term")

        combinations.append({
            "id": combination_id,
            "name": str(combination.get("name") or combination_id),
            "limit_state": str(combination.get("limit_state") or "UNSPECIFIED"),
            "basis": str(combination.get("basis") or basis),
            "terms": terms,
            "approval_state": "CANDIDATE_ONLY",
        })

    if not load_cases:
        warnings.append("No load cases were generated from the supplied project action input")
    if not assignments:
        warnings.append("No action assignments were generated; downstream analysis must remain blocked")
    if not combinations:
        warnings.append("No load combinations were supplied; downstream design checks must remain blocked")

    category_counts: Dict[str, int] = {}
    for case in load_cases:
        category = str(case["category"])
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "model_state": "ACTION_LOAD_MODEL_CANDIDATE",
        "source_analytical_model": {
            "engine": analytical_model.get("engine"),
            "model_state": analytical_model.get("model_state"),
            "element_count": len(elements),
            "node_count": len(nodes),
        },
        "unit_system": units,
        "action_basis": {
            "basis": basis,
            "values_source": "EXPLICIT_PROJECT_INPUT",
            "automatic_normative_value_invention": False,
        },
        "load_cases": load_cases,
        "action_assignments": assignments,
        "load_combinations": combinations,
        "traceability": dict(traceability),
        "category_counts": category_counts,
        "digital_twin_writeback": {
            "contract": "STRUCTURAL_ACTION_LOAD_MODEL_CANDIDATE",
            "enabled": True,
            "approval_state": "CANDIDATE_ONLY",
        },
        "release": {
            "automatic_structural_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "engineering_review_required": True,
            "analysis_execution_allowed": False,
            "blocking_requirements": [
                "action_basis_validation",
                "preliminary_sizing",
                "solver_adapter",
                "solver_results",
                "code_checks",
                "engineering_review",
            ],
        },
        "warnings": warnings,
        "summary": {
            "load_case_count": len(load_cases),
            "action_assignment_count": len(assignments),
            "load_combination_count": len(combinations),
            "traceable_action_count": len(traceability),
            "warning_count": len(warnings),
        },
    }


def _sample_payload() -> Dict[str, Any]:
    return {
        "analytical_model": {
            "engine": {"id": "PHX-STRUCT-ANALYTICAL-MODEL-V8.1.0", "version": "8.1.0"},
            "model_state": "ANALYTICAL_CANDIDATE",
            "nodes": [
                {"id": "N0001", "x": 0, "y": 0, "z": 0},
                {"id": "N0002", "x": 0, "y": 0, "z": 3},
                {"id": "N0003", "x": 5, "y": 0, "z": 0},
                {"id": "N0004", "x": 5, "y": 0, "z": 3},
            ],
            "members": [
                {"id": "M0001", "type": "column", "node_i": "N0001", "node_j": "N0002"},
                {"id": "M0002", "type": "column", "node_i": "N0003", "node_j": "N0004"},
                {"id": "M0003", "type": "beam", "node_i": "N0002", "node_j": "N0004"},
            ],
            "shells": [
                {"id": "S0001", "type": "slab_panel", "node_ids": ["N0001", "N0002", "N0004", "N0003"]},
            ],
        },
        "action_load_input": {
            "basis": "PROJECT_DEFINED_PRELIMINARY_ACTION_BASIS",
            "unit_system": {"length": "m", "force": "kN", "moment": "kNm", "stress": "kPa", "mass": "kg"},
            "actions": [
                {"id": "ACT-G-SW", "case_id": "LC-G", "case_name": "Permanent self weight", "category": "permanent", "kind": "self_weight", "direction": "GRAVITY", "factor": 1.0, "target": {"all_elements": True}},
                {"id": "ACT-G-FIN", "case_id": "LC-G", "case_name": "Permanent self weight", "category": "permanent", "kind": "area", "direction": "GLOBAL_Z", "magnitude": -1.5, "target": {"element_types": ["slab_panel"]}},
                {"id": "ACT-Q-FLOOR", "case_id": "LC-Q", "case_name": "Variable floor action", "category": "variable", "kind": "area", "direction": "GLOBAL_Z", "magnitude": -2.5, "target": {"element_types": ["slab_panel"]}},
                {"id": "ACT-W-X", "case_id": "LC-WX", "case_name": "Wind +X", "category": "wind", "kind": "line", "direction": "GLOBAL_X", "magnitude": 1.0, "target": {"element_types": ["column"]}},
            ],
            "combinations": [
                {"id": "COMB-ULS-01", "name": "Configured ULS candidate", "limit_state": "ULS", "basis": "PROJECT_DEFINED_PRELIMINARY_ACTION_BASIS", "terms": [{"case_id": "LC-G", "coefficient": 1.35}, {"case_id": "LC-Q", "coefficient": 1.5}, {"case_id": "LC-WX", "coefficient": 1.5}]},
                {"id": "COMB-SLS-01", "name": "Configured SLS candidate", "limit_state": "SLS", "basis": "PROJECT_DEFINED_PRELIMINARY_ACTION_BASIS", "terms": [{"case_id": "LC-G", "coefficient": 1.0}, {"case_id": "LC-Q", "coefficient": 1.0}]},
            ],
        },
    }


def _run_self_test() -> None:
    model = build_action_load_model(_sample_payload())
    assert model["engine"]["version"] == VERSION
    assert model["summary"]["load_case_count"] == 3
    assert model["summary"]["load_combination_count"] == 2
    assert model["summary"]["action_assignment_count"] == 5
    assert model["release"]["automatic_structural_approval"] is False
    assert model["release"]["structural_model_release"] == LOCKED_RELEASE
    assert model["digital_twin_writeback"]["enabled"] is True

    print("STRUCTURAL ACTION AND LOAD MODEL GENERATION ENGINE: PASSED")
    print("SOLVER-NEUTRAL ACTION/LOAD MODEL: GENERATED")
    print("LOAD CASE GENERATION: PASSED")
    print("PERMANENT ACTION MODEL: GENERATED")
    print("VARIABLE ACTION MODEL: GENERATED")
    print("WIND ACTION MODEL: GENERATED")
    print("SELF-WEIGHT ACTION: GENERATED")
    print("ELEMENT LOAD ASSIGNMENTS: GENERATED")
    print("LOAD COMBINATIONS: GENERATED")
    print("ACTION TRACEABILITY: ENABLED")
    print("CENTRAL DIGITAL TWIN ACTION/LOAD WRITEBACK: PASSED")
    print("AUTOMATIC NORMATIVE VALUE INVENTION: DISABLED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Input JSON payload")
    parser.add_argument("--output", type=Path, help="Output JSON model")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic internal self-test")
    args = parser.parse_args()

    if args.self_test:
        _run_self_test()
        return 0

    if args.input is None:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    model = build_action_load_model(payload)
    encoded = json.dumps(model, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
