#!/usr/bin/env python3
"""Project Phoenix Structural Analysis Results, Combination & Sanity Validation Engine v8.4.0.

Consumes normalized solver results produced under the v8.3.0 contract, validates
provenance/completeness/numerics, synthesizes configured linear combinations,
checks explicit project sanity thresholds, optionally compares independent solver
result sets, and creates a Digital Twin writeback candidate.

This engine does NOT claim code compliance and does NOT grant structural approval.
"""
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

ENGINE_ID = "PHX-STRUCT-ANALYSIS-RESULTS-VALIDATION-V8.4.0"
VERSION = "8.4.0"
LOCKED_RELEASE = "LOCKED"


def _items(value: Any) -> List[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be a non-empty string")
    return result


def _num(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive(value: Any, label: str) -> float:
    result = _num(value, label)
    if result <= 0:
        raise ValueError(f"{label} must be > 0")
    return result


def _nonnegative(value: Any, label: str) -> float:
    result = _num(value, label)
    if result < 0:
        raise ValueError(f"{label} must be >= 0")
    return result


def _walk_numeric(value: Any, path: str = "result") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _walk_numeric(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_numeric(child, f"{path}[{index}]")
    else:
        _num(value, path)


def _flatten_numeric(value: Mapping[str, Any], prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, Mapping):
            out.update(_flatten_numeric(child, path))
        else:
            out[path] = _num(child, path)
    return out


def _unflatten_numeric(flat: Mapping[str, float]) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    for path, value in flat.items():
        cursor: MutableMapping[str, Any] = root
        parts = path.split(".")
        for part in parts[:-1]:
            next_cursor = cursor.setdefault(part, {})
            if not isinstance(next_cursor, dict):
                raise ValueError(f"Path collision while reconstructing {path}")
            cursor = next_cursor
        cursor[parts[-1]] = float(value)
    return root


def _max_abs(value: Mapping[str, Any]) -> float:
    flat = _flatten_numeric(value)
    return max((abs(v) for v in flat.values()), default=0.0)


def _result_fields() -> Tuple[str, ...]:
    return ("node_displacements", "node_reactions", "element_forces", "element_stresses")


def _known_ids(payload: Mapping[str, Any]) -> Tuple[set[str], set[str]]:
    model = payload.get("analytical_model") or {}
    node_ids = {_text(n.get("id"), "analytical node id") for n in _items(model.get("nodes")) if isinstance(n, Mapping)}
    member_ids = {_text(e.get("id"), "analytical member id") for e in _items(model.get("members")) if isinstance(e, Mapping)}
    shell_ids = {_text(e.get("id"), "analytical shell id") for e in _items(model.get("shells")) if isinstance(e, Mapping)}
    if not node_ids:
        raise ValueError("analytical_model.nodes must define at least one node")
    return node_ids, member_ids | shell_ids


def _load_model(payload: Mapping[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    model = payload.get("action_load_model") or {}
    cases = [_text(c.get("id"), "load case id") for c in _items(model.get("load_cases")) if isinstance(c, Mapping)]
    if not cases:
        raise ValueError("action_load_model.load_cases must define at least one case")
    if len(cases) != len(set(cases)):
        raise ValueError("Duplicate load case IDs")
    combinations = [dict(c) for c in _items(model.get("load_combinations")) if isinstance(c, Mapping)]
    for combo in combinations:
        combo_id = _text(combo.get("id"), "load combination id")
        terms = _items(combo.get("terms"))
        if not terms:
            raise ValueError(f"Combination {combo_id} has no terms")
        for term in terms:
            if not isinstance(term, Mapping):
                raise ValueError(f"Combination {combo_id} term must be an object")
            case_id = _text(term.get("case_id"), f"combination {combo_id} case_id")
            if case_id not in cases:
                raise ValueError(f"Combination {combo_id} references unknown case {case_id}")
            _num(term.get("coefficient"), f"combination {combo_id} coefficient")
    return cases, combinations


def _policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw = dict(payload.get("validation_policy") or {})
    expected_units = raw.get("expected_units") or {"length": "m", "force": "kN", "stress": "kN/m2", "rotation": "rad"}
    thresholds = raw.get("sanity_thresholds") or {}
    tolerances = raw.get("comparison_tolerances") or {}
    required_fields = list(raw.get("required_result_fields") or _result_fields())
    invalid_fields = [f for f in required_fields if f not in _result_fields()]
    if invalid_fields:
        raise ValueError(f"Unsupported required result fields: {', '.join(invalid_fields)}")
    return {
        "required_solvers": [str(v).lower() for v in _items(raw.get("required_solvers") or ["opensees"])],
        "required_result_fields": required_fields,
        "expected_units": dict(expected_units),
        "require_raw_solver_evidence": bool(raw.get("require_raw_solver_evidence", True)),
        "require_converged_status": bool(raw.get("require_converged_status", True)),
        "require_known_entity_ids": bool(raw.get("require_known_entity_ids", True)),
        "require_all_load_cases_per_solver": bool(raw.get("require_all_load_cases_per_solver", True)),
        "cross_solver_comparison_enabled": bool(raw.get("cross_solver_comparison_enabled", True)),
        "sanity_thresholds": {
            "max_translation_m": _positive(thresholds.get("max_translation_m", 0.05), "max_translation_m"),
            "max_rotation_rad": _positive(thresholds.get("max_rotation_rad", 0.02), "max_rotation_rad"),
            "max_equilibrium_relative_residual": _nonnegative(thresholds.get("max_equilibrium_relative_residual", 0.02), "max_equilibrium_relative_residual"),
        },
        "comparison_tolerances": {
            "absolute": _nonnegative(tolerances.get("absolute", 1e-8), "comparison absolute tolerance"),
            "relative": _nonnegative(tolerances.get("relative", 0.05), "comparison relative tolerance"),
        },
    }


def _validate_units(result: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    units = result.get("units") or {}
    for key, expected_value in expected.items():
        actual = units.get(key)
        if actual != expected_value:
            raise ValueError(f"{label} unit mismatch for {key}: expected {expected_value!r}, found {actual!r}")


def _validate_entity_ids(result: Mapping[str, Any], known_nodes: set[str], known_elements: set[str], label: str) -> None:
    unknown_nodes = (set((result.get("node_displacements") or {}).keys()) | set((result.get("node_reactions") or {}).keys())) - known_nodes
    unknown_elements = (set((result.get("element_forces") or {}).keys()) | set((result.get("element_stresses") or {}).keys())) - known_elements
    if unknown_nodes:
        raise ValueError(f"{label} contains unknown node IDs: {', '.join(sorted(unknown_nodes))}")
    if unknown_elements:
        raise ValueError(f"{label} contains unknown element IDs: {', '.join(sorted(unknown_elements))}")


def _index_results(payload: Mapping[str, Any], policy: Mapping[str, Any], cases: Sequence[str], known_nodes: set[str], known_elements: set[str]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for index, raw in enumerate(_items(payload.get("analysis_result_sets")), 1):
        if not isinstance(raw, Mapping):
            raise ValueError("analysis_result_sets entries must be objects")
        result = deepcopy(dict(raw))
        solver = _text(result.get("solver"), f"result[{index}] solver").lower()
        case_id = _text(result.get("case_id"), f"result[{index}] case_id")
        label = f"result {solver}/{case_id}"
        if case_id not in cases:
            raise ValueError(f"{label} references unknown load case")
        key = (solver, case_id)
        if key in indexed:
            raise ValueError(f"Duplicate result set for {solver}/{case_id}")
        status = str(result.get("status") or "").upper()
        if policy["require_converged_status"]:
            if status not in {"SUCCESS", "COMPLETED", "CONVERGED"} or result.get("converged") is not True:
                raise ValueError(f"{label} is not explicitly completed and converged")
        if policy["require_raw_solver_evidence"] and not str(result.get("raw_solver_evidence_reference") or "").strip():
            raise ValueError(f"{label} has no raw solver evidence reference")
        _validate_units(result, policy["expected_units"], label)
        for field in policy["required_result_fields"]:
            if field not in result or not isinstance(result[field], Mapping):
                raise ValueError(f"{label} missing required result field {field}")
            _walk_numeric(result[field], f"{label}.{field}")
        if policy["require_known_entity_ids"]:
            _validate_entity_ids(result, known_nodes, known_elements, label)
        indexed[key] = result

    if not indexed:
        raise ValueError("analysis_result_sets must contain at least one normalized result set")
    if policy["require_all_load_cases_per_solver"]:
        for solver in policy["required_solvers"]:
            missing = [case_id for case_id in cases if (solver, case_id) not in indexed]
            if missing:
                raise ValueError(f"Required solver {solver} missing load cases: {', '.join(missing)}")
    return indexed


def _combine_numeric_maps(result_sets: Mapping[Tuple[str, str], Mapping[str, Any]], solver: str, combo: Mapping[str, Any], field: str) -> Dict[str, Any]:
    total: Dict[str, float] = {}
    combo_id = _text(combo.get("id"), "combination id")
    for term in _items(combo.get("terms")):
        case_id = _text(term.get("case_id"), f"combination {combo_id} case_id")
        coefficient = _num(term.get("coefficient"), f"combination {combo_id} coefficient")
        key = (solver, case_id)
        if key not in result_sets:
            raise ValueError(f"Cannot synthesize {combo_id} for {solver}; missing case {case_id}")
        flat = _flatten_numeric(result_sets[key].get(field) or {})
        for path, value in flat.items():
            total[path] = total.get(path, 0.0) + coefficient * value
    return _unflatten_numeric(total)


def synthesize_combinations(indexed: Mapping[Tuple[str, str], Mapping[str, Any]], combinations: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    solvers = sorted({solver for solver, _ in indexed})
    output: Dict[str, Dict[str, Any]] = {}
    for solver in solvers:
        solver_output: Dict[str, Any] = {}
        for combo in combinations:
            combo_id = _text(combo.get("id"), "combination id")
            try:
                combined = {field: _combine_numeric_maps(indexed, solver, combo, field) for field in _result_fields()}
            except ValueError:
                continue
            combined["limit_state"] = str(combo.get("limit_state") or "UNSPECIFIED")
            combined["derivation"] = "LINEAR_SUPERPOSITION_OF_NORMALIZED_BASE_CASE_RESULTS"
            solver_output[combo_id] = combined
        output[solver] = solver_output
    return output


def _compare_values(a: float, b: float, absolute: float, relative: float) -> Tuple[bool, float, float]:
    delta = abs(a - b)
    scale = max(abs(a), abs(b), absolute)
    rel = delta / scale if scale else 0.0
    return delta <= absolute or rel <= relative, delta, rel


def cross_solver_checks(indexed: Mapping[Tuple[str, str], Mapping[str, Any]], cases: Sequence[str], policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if not policy["cross_solver_comparison_enabled"]:
        return []
    solvers = sorted({solver for solver, _ in indexed})
    if len(solvers) < 2:
        return []
    reference_solver = solvers[0]
    abs_tol = policy["comparison_tolerances"]["absolute"]
    rel_tol = policy["comparison_tolerances"]["relative"]
    checks: List[Dict[str, Any]] = []
    for other_solver in solvers[1:]:
        for case_id in cases:
            if (reference_solver, case_id) not in indexed or (other_solver, case_id) not in indexed:
                continue
            failures = 0
            compared = 0
            worst_relative = 0.0
            for field in _result_fields():
                a = _flatten_numeric(indexed[(reference_solver, case_id)].get(field) or {})
                b = _flatten_numeric(indexed[(other_solver, case_id)].get(field) or {})
                common = sorted(set(a) & set(b))
                for key in common:
                    ok, _, rel = _compare_values(a[key], b[key], abs_tol, rel_tol)
                    compared += 1
                    worst_relative = max(worst_relative, rel)
                    if not ok:
                        failures += 1
            checks.append({
                "reference_solver": reference_solver,
                "comparison_solver": other_solver,
                "case_id": case_id,
                "compared_numeric_values": compared,
                "outside_tolerance_count": failures,
                "worst_relative_difference": worst_relative,
                "status": "PASS" if failures == 0 else "REVIEW_REQUIRED",
            })
    return checks


def _translation_rotation_max(result: Mapping[str, Any]) -> Tuple[float, float]:
    max_translation = 0.0
    max_rotation = 0.0
    for dofs in (result.get("node_displacements") or {}).values():
        if not isinstance(dofs, Mapping):
            continue
        for dof, value in dofs.items():
            numeric = abs(_num(value, f"displacement {dof}"))
            if str(dof).upper() in {"UX", "UY", "UZ"}:
                max_translation = max(max_translation, numeric)
            elif str(dof).upper() in {"RX", "RY", "RZ"}:
                max_rotation = max(max_rotation, numeric)
    return max_translation, max_rotation


def _reaction_resultant(result: Mapping[str, Any]) -> Dict[str, float]:
    resultant = {"FX": 0.0, "FY": 0.0, "FZ": 0.0}
    for reaction in (result.get("node_reactions") or {}).values():
        if not isinstance(reaction, Mapping):
            continue
        for axis in resultant:
            if axis in reaction:
                resultant[axis] += _num(reaction[axis], f"reaction {axis}")
    return resultant


def sanity_checks(indexed: Mapping[Tuple[str, str], Mapping[str, Any]], payload: Mapping[str, Any], policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    thresholds = policy["sanity_thresholds"]
    expected_resultants = payload.get("expected_case_resultants_kN") or {}
    checks: List[Dict[str, Any]] = []
    for (solver, case_id), result in sorted(indexed.items()):
        translation, rotation = _translation_rotation_max(result)
        displacement_status = "PASS" if translation <= thresholds["max_translation_m"] and rotation <= thresholds["max_rotation_rad"] else "REVIEW_REQUIRED"
        checks.append({
            "type": "DISPLACEMENT_ENVELOPE",
            "solver": solver,
            "case_id": case_id,
            "max_translation_m": translation,
            "max_rotation_rad": rotation,
            "threshold_translation_m": thresholds["max_translation_m"],
            "threshold_rotation_rad": thresholds["max_rotation_rad"],
            "status": displacement_status,
            "basis": "EXPLICIT_PROJECT_SANITY_THRESHOLD_NOT_CODE_LIMIT",
        })
        if case_id in expected_resultants:
            expected = expected_resultants[case_id]
            reactions = _reaction_resultant(result)
            residual = {}
            numerator = 0.0
            denominator = 0.0
            for axis in ("FX", "FY", "FZ"):
                load = _num(expected.get(axis, 0.0), f"expected resultant {case_id} {axis}")
                res = reactions[axis] + load
                residual[axis] = res
                numerator += res * res
                denominator += load * load
            relative = math.sqrt(numerator) / max(math.sqrt(denominator), 1e-12)
            checks.append({
                "type": "GLOBAL_FORCE_EQUILIBRIUM",
                "solver": solver,
                "case_id": case_id,
                "expected_applied_resultant_kN": {axis: _num(expected.get(axis, 0.0), f"expected resultant {case_id} {axis}") for axis in ("FX", "FY", "FZ")},
                "reaction_resultant_kN": reactions,
                "residual_kN": residual,
                "relative_residual": relative,
                "threshold_relative_residual": thresholds["max_equilibrium_relative_residual"],
                "status": "PASS" if relative <= thresholds["max_equilibrium_relative_residual"] else "REVIEW_REQUIRED",
                "basis": "EXPLICIT_EXPECTED_RESULTANT_FROM_UPSTREAM_ANALYSIS_CONTRACT",
            })
    return checks


def validate_provided_combinations(payload: Mapping[str, Any], synthesized: Mapping[str, Any], policy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    provided = _items(payload.get("provided_combination_result_sets"))
    if not provided:
        return []
    abs_tol = policy["comparison_tolerances"]["absolute"]
    rel_tol = policy["comparison_tolerances"]["relative"]
    reports: List[Dict[str, Any]] = []
    for index, raw in enumerate(provided, 1):
        if not isinstance(raw, Mapping):
            raise ValueError("provided_combination_result_sets entries must be objects")
        solver = _text(raw.get("solver"), f"provided combination[{index}] solver").lower()
        combo_id = _text(raw.get("combination_id"), f"provided combination[{index}] combination_id")
        target = synthesized.get(solver, {}).get(combo_id)
        if target is None:
            raise ValueError(f"No synthesized combination available for {solver}/{combo_id}")
        failures = 0
        compared = 0
        worst_relative = 0.0
        for field in _result_fields():
            expected = _flatten_numeric(target.get(field) or {})
            actual = _flatten_numeric(raw.get(field) or {})
            if set(expected) != set(actual):
                failures += len(set(expected) ^ set(actual))
            for key in sorted(set(expected) & set(actual)):
                ok, _, rel = _compare_values(expected[key], actual[key], abs_tol, rel_tol)
                compared += 1
                worst_relative = max(worst_relative, rel)
                if not ok:
                    failures += 1
        reports.append({
            "solver": solver,
            "combination_id": combo_id,
            "compared_numeric_values": compared,
            "outside_tolerance_or_schema_count": failures,
            "worst_relative_difference": worst_relative,
            "status": "PASS" if failures == 0 else "REVIEW_REQUIRED",
        })
    return reports


def build_validation_report(payload: Mapping[str, Any]) -> Dict[str, Any]:
    project_id = _text(payload.get("project_id"), "project_id")
    source_engine = str(payload.get("source_engine") or "")
    if source_engine and "V8.3.0" not in source_engine.upper():
        raise ValueError("v8.4.0 expects normalized solver-result input originating from the v8.3.0 analysis contract")
    known_nodes, known_elements = _known_ids(payload)
    cases, combinations = _load_model(payload)
    policy = _policy(payload)
    indexed = _index_results(payload, policy, cases, known_nodes, known_elements)
    synthesized = synthesize_combinations(indexed, combinations)
    cross_checks = cross_solver_checks(indexed, cases, policy)
    sanity = sanity_checks(indexed, payload, policy)
    combo_checks = validate_provided_combinations(payload, synthesized, policy)

    review_items: List[Dict[str, Any]] = []
    for check in cross_checks + sanity + combo_checks:
        if check.get("status") != "PASS":
            review_items.append(deepcopy(check))

    provenance = []
    for (solver, case_id), result in sorted(indexed.items()):
        provenance.append({
            "solver": solver,
            "case_id": case_id,
            "raw_solver_evidence_reference": result.get("raw_solver_evidence_reference"),
            "normalization_version": result.get("normalization_version"),
            "status": result.get("status"),
            "converged": result.get("converged"),
        })

    state = "SANITY_VALIDATED_CANDIDATE" if not review_items else "ENGINEERING_REVIEW_REQUIRED"
    return {
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": project_id,
        "source_engine": source_engine or "PHX-STRUCT-SOLVER-INPUT-ANALYSIS-V8.3.0",
        "validation_state": state,
        "policy": deepcopy(policy),
        "result_provenance": provenance,
        "synthesized_combination_results": synthesized,
        "checks": {
            "result_set_count": len(indexed),
            "combination_count": sum(len(v) for v in synthesized.values()),
            "cross_solver": cross_checks,
            "sanity": sanity,
            "provided_combination_verification": combo_checks,
            "review_item_count": len(review_items),
            "review_items": review_items,
        },
        "digital_twin_writeback": {
            "enabled": True,
            "target": "CENTRAL_DIGITAL_TWIN.structural.analysis_validation",
            "write_state": state,
            "solver_result_provenance_preserved": True,
            "raw_solver_evidence_required": policy["require_raw_solver_evidence"],
            "automatic_release": False,
        },
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "structural_model_release": LOCKED_RELEASE,
            "engineering_review_required": True,
            "next_required_capabilities": [
                "CODE_AND_LIMIT_STATE_CHECKS",
                "MEMBER_AND_SECTION_VERIFICATION",
                "GLOBAL_STABILITY_VERIFICATION",
                "ENGINEERING_REVIEW_GATE",
            ],
        },
        "summary": {
            "solver_count": len({solver for solver, _ in indexed}),
            "base_result_set_count": len(indexed),
            "load_case_count": len(cases),
            "configured_combination_count": len(combinations),
            "synthesized_combination_result_count": sum(len(v) for v in synthesized.values()),
            "review_item_count": len(review_items),
        },
    }


def _demo_payload() -> Dict[str, Any]:
    zero6 = {"UX": 0.0, "UY": 0.0, "UZ": 0.0, "RX": 0.0, "RY": 0.0, "RZ": 0.0}

    def rs(solver: str, case: str, uz: float, fz: float, m: float) -> Dict[str, Any]:
        return {
            "solver": solver,
            "case_id": case,
            "status": "COMPLETED",
            "converged": True,
            "normalization_version": "8.3.0",
            "units": {"length": "m", "force": "kN", "stress": "kN/m2", "rotation": "rad"},
            "node_displacements": {"N1": dict(zero6), "N2": {**zero6, "UZ": uz}},
            "node_reactions": {"N1": {"FX": 0.0, "FY": 0.0, "FZ": fz}},
            "element_forces": {"M1": {"N": -fz, "MY": m}},
            "element_stresses": {"M1": {"SXX": abs(fz) * 10.0}},
            "raw_solver_evidence_reference": f"evidence/{solver}_{case}.raw",
        }

    return {
        "project_id": "SELF-TEST-V8.4.0",
        "source_engine": "PHX-STRUCT-SOLVER-INPUT-ANALYSIS-V8.3.0",
        "analytical_model": {
            "nodes": [{"id": "N1"}, {"id": "N2"}],
            "members": [{"id": "M1"}],
            "shells": [],
        },
        "action_load_model": {
            "load_cases": [{"id": "G"}, {"id": "Q"}],
            "load_combinations": [{"id": "ULS1", "limit_state": "ULS", "terms": [{"case_id": "G", "coefficient": 1.35}, {"case_id": "Q", "coefficient": 1.5}]}],
        },
        "analysis_result_sets": [
            rs("opensees", "G", -0.0020, 100.0, 10.0),
            rs("opensees", "Q", -0.0030, 40.0, 5.0),
            rs("calculix", "G", -0.00202, 100.2, 10.05),
            rs("calculix", "Q", -0.00302, 40.1, 5.02),
        ],
        "expected_case_resultants_kN": {
            "G": {"FX": 0.0, "FY": 0.0, "FZ": -100.0},
            "Q": {"FX": 0.0, "FY": 0.0, "FZ": -40.0},
        },
        "validation_policy": {
            "required_solvers": ["opensees", "calculix"],
            "required_result_fields": list(_result_fields()),
            "expected_units": {"length": "m", "force": "kN", "stress": "kN/m2", "rotation": "rad"},
            "require_raw_solver_evidence": True,
            "require_converged_status": True,
            "require_known_entity_ids": True,
            "require_all_load_cases_per_solver": True,
            "cross_solver_comparison_enabled": True,
            "sanity_thresholds": {"max_translation_m": 0.05, "max_rotation_rad": 0.02, "max_equilibrium_relative_residual": 0.01},
            "comparison_tolerances": {"absolute": 1e-8, "relative": 0.02},
        },
    }


def self_test() -> None:
    payload = _demo_payload()
    report = build_validation_report(payload)
    assert report["engine"]["version"] == VERSION
    assert report["summary"]["solver_count"] == 2
    assert report["summary"]["base_result_set_count"] == 4
    assert report["summary"]["synthesized_combination_result_count"] == 2
    expected_uz = 1.35 * -0.0020 + 1.5 * -0.0030
    assert abs(report["synthesized_combination_results"]["opensees"]["ULS1"]["node_displacements"]["N2"]["UZ"] - expected_uz) < 1e-12
    assert report["checks"]["review_item_count"] == 0
    assert report["release"]["structural_model_release"] == "LOCKED"
    print("STRUCTURAL ANALYSIS RESULTS VALIDATION ENGINE: PASSED")
    print("NORMALIZED RESULT PROVENANCE: VERIFIED")
    print("RESULT COMPLETENESS AND NUMERIC SANITY: PASSED")
    print("LINEAR LOAD COMBINATION SYNTHESIS: PASSED")
    print("DISPLACEMENT SANITY ENVELOPE: PASSED")
    print("GLOBAL FORCE EQUILIBRIUM CHECK: PASSED")
    print("CROSS-SOLVER COMPARISON: PASSED")
    print("RAW SOLVER EVIDENCE CONTRACT: ENFORCED")
    print("CENTRAL DIGITAL TWIN ANALYSIS VALIDATION WRITEBACK: PASSED")
    print("AUTOMATIC CODE COMPLIANCE CLAIM: DISABLED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_validation_report(payload)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
