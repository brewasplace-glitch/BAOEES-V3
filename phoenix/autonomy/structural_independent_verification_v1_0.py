"""PROJECT PHOENIX Structural Independent Verification Engine v1.0.

This engine verifies structural calculation evidence using explicit project-supplied
criteria. It can compare SCIA with CalculiX, perform equilibrium checks, analytical
spot checks, load-path checks, solver-health checks, mesh-convergence checks,
sensitivity checks, and file-integrity checks.

Hard boundary:
- No default engineering acceptance tolerances are invented.
- No professional approval or code-compliance claim is generated.
- A second-solver cross-check is numerical cross-verification, not an independent
  professional review.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
ENGINE_ID = "PHX-STRUCTURAL-INDEPENDENT-VERIFICATION"

STATUS_INPUT_REQUIRED = "VERIFICATION_INPUT_REQUIRED"
STATUS_FAILED = "VERIFICATION_FAILED"
STATUS_VERIFIED = "TECHNICALLY_VERIFIED"
STATUS_CROSS_VERIFIED = "TECHNICALLY_CROSS_VERIFIED"

SCIA_CALCULATED_STATUS = "CALCULATED_UNVERIFIED"

CATEGORIES = (
    "source_evidence",
    "global_equilibrium",
    "analytical_spot_checks",
    "load_path",
    "solver_health",
    "scia_calculix_cross_check",
    "mesh_convergence",
    "sensitivity",
    "evidence_integrity",
)

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_for_construction_release": False,
    "automatic_production_release": False,
    "second_solver_is_not_independent_professional_review": True,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(repository: Path, value: str, *, must_exist: bool = False) -> Path:
    p = Path(value)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        if ".." in p.parts:
            raise ValueError(f"Unsafe repository-relative path: {value}")
        resolved = (repository / p).resolve()
    try:
        resolved.relative_to(repository.resolve())
    except ValueError:
        raise ValueError(f"Path outside repository: {value}")
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def _json_pointer(value: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    current = value
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def _numeric(spec: Any, repository: Path) -> float:
    if isinstance(spec, bool):
        raise ValueError("Boolean is not a numeric verification value.")
    if isinstance(spec, (int, float)):
        value = float(spec)
    elif isinstance(spec, dict):
        if "value" in spec:
            value = float(spec["value"])
        elif "source_file" in spec and "json_pointer" in spec:
            source = _safe_path(repository, str(spec["source_file"]), must_exist=True)
            data = _read_json(source)
            value = float(_json_pointer(data, str(spec["json_pointer"])))
        else:
            raise ValueError("Numeric spec requires value or source_file + json_pointer.")
    else:
        raise ValueError("Unsupported numeric specification.")
    if not math.isfinite(value):
        raise ValueError("Verification values must be finite.")
    return value


def _validate_tolerance(tolerance: Any) -> list[str]:
    errors = []
    if not isinstance(tolerance, dict):
        return ["tolerance_missing"]
    mode = str(tolerance.get("mode", "")).upper()
    if mode not in {"ALL", "ANY"}:
        errors.append("tolerance.mode must be ALL or ANY")
    has_abs = tolerance.get("absolute") is not None
    has_rel = tolerance.get("relative") is not None
    if not (has_abs or has_rel):
        errors.append("explicit absolute and/or relative tolerance required")
    if has_abs:
        try:
            if float(tolerance["absolute"]) < 0:
                errors.append("absolute tolerance must be >= 0")
        except Exception:
            errors.append("absolute tolerance invalid")
    if has_rel:
        try:
            if float(tolerance["relative"]) < 0:
                errors.append("relative tolerance must be >= 0")
        except Exception:
            errors.append("relative tolerance invalid")
    return errors


def _compare(a: float, b: float, tolerance: dict[str, Any]) -> dict[str, Any]:
    errors = _validate_tolerance(tolerance)
    if errors:
        return {"status": "INPUT_REQUIRED", "errors": errors}
    absolute_error = abs(a - b)
    denom = max(abs(a), abs(b))
    relative_error = 0.0 if denom == 0.0 else absolute_error / denom
    checks = []
    if tolerance.get("absolute") is not None:
        limit = float(tolerance["absolute"])
        checks.append(("absolute", absolute_error <= limit, limit))
    if tolerance.get("relative") is not None:
        limit = float(tolerance["relative"])
        checks.append(("relative", relative_error <= limit, limit))
    mode = str(tolerance["mode"]).upper()
    passed = all(x[1] for x in checks) if mode == "ALL" else any(x[1] for x in checks)
    return {
        "status": "PASS" if passed else "FAIL",
        "a": a,
        "b": b,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "tolerance": deepcopy(tolerance),
        "checks": [
            {"type": kind, "passed": ok, "limit": limit}
            for kind, ok, limit in checks
        ],
    }


def _category_applicability(config: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(config, dict):
        return "INPUT_REQUIRED", {"errors": ["category configuration missing"]}
    applicability = str(config.get("applicability", "")).upper()
    if applicability == "NOT_APPLICABLE":
        if not str(config.get("rationale", "")).strip():
            return "INPUT_REQUIRED", {"errors": ["NOT_APPLICABLE requires rationale"]}
        if not str(config.get("source_record_id", "")).strip():
            return "INPUT_REQUIRED", {"errors": ["NOT_APPLICABLE requires source_record_id"]}
        return "NOT_APPLICABLE_TRACEABLE", {
            "rationale": config["rationale"],
            "source_record_id": config["source_record_id"],
        }
    if applicability != "REQUIRED":
        return "INPUT_REQUIRED", {"errors": ["applicability must be REQUIRED or NOT_APPLICABLE"]}
    return "REQUIRED", {}


def _source_evidence(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    path = config.get("scia_run_result")
    if not path:
        return {"status": "INPUT_REQUIRED", "errors": ["scia_run_result required"]}
    try:
        data = _read_json(_safe_path(repository, str(path), must_exist=True))
    except Exception as exc:
        return {"status": "FAIL", "errors": [str(exc)]}
    errors = []
    if data.get("status") != SCIA_CALCULATED_STATUS:
        errors.append(f"SCIA status must be {SCIA_CALCULATED_STATUS}")
    safety = data.get("safety")
    if not isinstance(safety, dict):
        errors.append("SCIA safety object missing")
    else:
        if safety.get("automatic_professional_approval") is not False:
            errors.append("SCIA professional approval lock invalid")
        if safety.get("production_release") != "LOCKED":
            errors.append("SCIA production lock invalid")
        if safety.get("for_construction_release") != "LOCKED":
            errors.append("SCIA FOR-CONSTRUCTION lock invalid")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "scia_run_result": str(path),
        "scia_status": data.get("status"),
    }


def _global_equilibrium(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    cases = config.get("cases")
    if not isinstance(cases, list) or not cases:
        return {"status": "INPUT_REQUIRED", "errors": ["equilibrium cases required"]}
    results = []
    category_status = "PASS"
    components = ("Fx", "Fy", "Fz", "Mx", "My", "Mz")
    for case in cases:
        case_id = str(case.get("case_id", "UNNAMED"))
        applied = case.get("applied")
        reactions = case.get("reactions")
        tolerances = case.get("tolerances")
        if not isinstance(applied, dict) or not isinstance(reactions, dict) or not isinstance(tolerances, dict):
            results.append({"case_id": case_id, "status": "INPUT_REQUIRED"})
            category_status = "INPUT_REQUIRED"
            continue
        component_results = {}
        for comp in components:
            if comp not in applied or comp not in reactions or comp not in tolerances:
                component_results[comp] = {"status": "INPUT_REQUIRED"}
                category_status = "INPUT_REQUIRED"
                continue
            try:
                # Equilibrium convention: applied + reactions should be zero.
                a = _numeric(applied[comp], repository)
                r = _numeric(reactions[comp], repository)
                cmp = _compare(a + r, 0.0, tolerances[comp])
            except Exception as exc:
                cmp = {"status": "INPUT_REQUIRED", "errors": [str(exc)]}
            component_results[comp] = cmp
            if cmp["status"] == "FAIL":
                category_status = "FAIL"
            elif cmp["status"] == "INPUT_REQUIRED" and category_status != "FAIL":
                category_status = "INPUT_REQUIRED"
        results.append({"case_id": case_id, "status": category_status, "components": component_results})
    return {"status": category_status, "cases": results}


def _analytical_expected(check: dict[str, Any], repository: Path) -> float:
    formula = str(check.get("formula", "")).lower()
    p = check.get("parameters", {})
    if formula == "direct_expected":
        return _numeric(check["expected"], repository)
    if formula == "simply_supported_udl_max_moment":
        q = _numeric(p["q"], repository)
        L = _numeric(p["L"], repository)
        return q * L * L / 8.0
    if formula == "simply_supported_udl_reaction":
        q = _numeric(p["q"], repository)
        L = _numeric(p["L"], repository)
        return q * L / 2.0
    if formula == "simply_supported_midspan_point_load_max_moment":
        P = _numeric(p["P"], repository)
        L = _numeric(p["L"], repository)
        return P * L / 4.0
    if formula == "cantilever_tip_load_max_moment":
        P = _numeric(p["P"], repository)
        L = _numeric(p["L"], repository)
        return P * L
    if formula == "cantilever_udl_max_moment":
        q = _numeric(p["q"], repository)
        L = _numeric(p["L"], repository)
        return q * L * L / 2.0
    if formula == "cantilever_tip_load_deflection":
        P = _numeric(p["P"], repository)
        L = _numeric(p["L"], repository)
        E = _numeric(p["E"], repository)
        I = _numeric(p["I"], repository)
        return P * L**3 / (3.0 * E * I)
    raise ValueError(f"Unsupported analytical formula: {formula}")


def _analytical(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    checks = config.get("checks")
    if not isinstance(checks, list) or not checks:
        return {"status": "INPUT_REQUIRED", "errors": ["analytical checks required"]}
    results = []
    status = "PASS"
    for check in checks:
        check_id = str(check.get("check_id", "UNNAMED"))
        try:
            expected = _analytical_expected(check, repository)
            observed = _numeric(check["observed"], repository)
            cmp = _compare(observed, expected, check.get("tolerance"))
        except Exception as exc:
            cmp = {"status": "INPUT_REQUIRED", "errors": [str(exc)]}
        results.append({"check_id": check_id, **cmp})
        if cmp["status"] == "FAIL":
            status = "FAIL"
        elif cmp["status"] == "INPUT_REQUIRED" and status != "FAIL":
            status = "INPUT_REQUIRED"
    return {"status": status, "checks": results}


def _load_path(config: dict[str, Any]) -> dict[str, Any]:
    paths = config.get("paths")
    if not isinstance(paths, list) or not paths:
        return {"status": "INPUT_REQUIRED", "errors": ["load paths required"]}
    results = []
    status = "PASS"
    for item in paths:
        errors = []
        nodes = item.get("nodes")
        if not isinstance(nodes, list) or len(nodes) < 2:
            errors.append("at least two load-path nodes required")
        if item.get("complete_to_support") is not True:
            errors.append("load path does not explicitly reach a support/foundation")
        source_records = item.get("source_records")
        if not isinstance(source_records, list) or not source_records:
            errors.append("source_records required")
        item_status = "PASS" if not errors else "FAIL"
        if item_status == "FAIL":
            status = "FAIL"
        results.append({
            "path_id": item.get("path_id"),
            "status": item_status,
            "errors": errors,
            "nodes": nodes,
        })
    return {"status": status, "paths": results}


def _solver_health(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    files = config.get("log_files")
    patterns = config.get("blocking_patterns")
    if not isinstance(files, list) or not files:
        return {"status": "INPUT_REQUIRED", "errors": ["log_files required"]}
    if not isinstance(patterns, list):
        return {"status": "INPUT_REQUIRED", "errors": ["blocking_patterns must be explicitly supplied"]}
    hits = []
    read_files = []
    for value in files:
        try:
            path = _safe_path(repository, str(value), must_exist=True)
        except Exception as exc:
            return {"status": "FAIL", "errors": [str(exc)]}
        text = path.read_text(encoding="utf-8", errors="replace")
        read_files.append(str(value))
        for pattern in patterns:
            if re.search(str(pattern), text, flags=re.IGNORECASE | re.MULTILINE):
                hits.append({"file": str(value), "pattern": str(pattern)})
    return {
        "status": "PASS" if not hits else "FAIL",
        "blocking_hits": hits,
        "log_files": read_files,
    }


def _cross_solver(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    comparisons = config.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        return {"status": "INPUT_REQUIRED", "errors": ["SCIA/CalculiX comparisons required"]}
    results = []
    status = "PASS"
    for item in comparisons:
        try:
            scia = _numeric(item["scia"], repository)
            calculix = _numeric(item["calculix"], repository)
            cmp = _compare(scia, calculix, item.get("tolerance"))
        except Exception as exc:
            cmp = {"status": "INPUT_REQUIRED", "errors": [str(exc)]}
        results.append({
            "comparison_id": item.get("comparison_id"),
            "metric": item.get("metric"),
            **cmp,
        })
        if cmp["status"] == "FAIL":
            status = "FAIL"
        elif cmp["status"] == "INPUT_REQUIRED" and status != "FAIL":
            status = "INPUT_REQUIRED"
    return {"status": status, "comparisons": results}


def _mesh_convergence(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    studies = config.get("studies")
    if not isinstance(studies, list) or not studies:
        return {"status": "INPUT_REQUIRED", "errors": ["mesh convergence studies required"]}
    results = []
    status = "PASS"
    for study in studies:
        points = study.get("points")
        threshold = study.get("max_relative_change")
        if not isinstance(points, list) or len(points) < 2 or threshold is None:
            item = {"study_id": study.get("study_id"), "status": "INPUT_REQUIRED"}
            results.append(item)
            status = "INPUT_REQUIRED" if status != "FAIL" else status
            continue
        try:
            values = [_numeric(p["value"], repository) for p in points]
            prev, last = values[-2], values[-1]
            denom = max(abs(prev), abs(last))
            change = 0.0 if denom == 0.0 else abs(last - prev) / denom
            limit = float(threshold)
            passed = change <= limit
            item = {
                "study_id": study.get("study_id"),
                "status": "PASS" if passed else "FAIL",
                "last_step_relative_change": change,
                "max_relative_change": limit,
                "values": values,
            }
            if not passed:
                status = "FAIL"
        except Exception as exc:
            item = {"study_id": study.get("study_id"), "status": "INPUT_REQUIRED", "errors": [str(exc)]}
            if status != "FAIL":
                status = "INPUT_REQUIRED"
        results.append(item)
    return {"status": status, "studies": results}


def _sensitivity(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    studies = config.get("studies")
    if not isinstance(studies, list) or not studies:
        return {"status": "INPUT_REQUIRED", "errors": ["sensitivity studies required"]}
    results = []
    status = "PASS"
    for study in studies:
        try:
            baseline = _numeric(study["baseline"], repository)
            perturbed = _numeric(study["perturbed"], repository)
            direction = str(study.get("expected_direction", "")).upper()
            if direction not in {"INCREASE", "DECREASE", "NO_CHANGE"}:
                raise ValueError("expected_direction must be INCREASE, DECREASE or NO_CHANGE")
            tolerance = study.get("no_change_tolerance")
            if direction == "INCREASE":
                passed = perturbed > baseline
            elif direction == "DECREASE":
                passed = perturbed < baseline
            else:
                cmp = _compare(perturbed, baseline, tolerance)
                if cmp["status"] == "INPUT_REQUIRED":
                    raise ValueError("NO_CHANGE requires explicit no_change_tolerance")
                passed = cmp["status"] == "PASS"
            item = {
                "study_id": study.get("study_id"),
                "status": "PASS" if passed else "FAIL",
                "baseline": baseline,
                "perturbed": perturbed,
                "expected_direction": direction,
            }
            if not passed:
                status = "FAIL"
        except Exception as exc:
            item = {"study_id": study.get("study_id"), "status": "INPUT_REQUIRED", "errors": [str(exc)]}
            if status != "FAIL":
                status = "INPUT_REQUIRED"
        results.append(item)
    return {"status": status, "studies": results}


def _evidence_integrity(config: dict[str, Any], repository: Path) -> dict[str, Any]:
    files = config.get("files")
    if not isinstance(files, list) or not files:
        return {"status": "INPUT_REQUIRED", "errors": ["evidence files + SHA256 required"]}
    results = []
    status = "PASS"
    for item in files:
        value = item.get("path")
        expected = str(item.get("sha256", "")).strip().lower()
        if not value or not expected:
            results.append({"path": value, "status": "INPUT_REQUIRED"})
            if status != "FAIL":
                status = "INPUT_REQUIRED"
            continue
        try:
            path = _safe_path(repository, str(value), must_exist=True)
            actual = sha256_file(path)
            passed = actual == expected
            results.append({
                "path": str(value),
                "status": "PASS" if passed else "FAIL",
                "expected_sha256": expected,
                "actual_sha256": actual,
            })
            if not passed:
                status = "FAIL"
        except Exception as exc:
            results.append({"path": value, "status": "FAIL", "errors": [str(exc)]})
            status = "FAIL"
    return {"status": status, "files": results}


HANDLERS = {
    "source_evidence": _source_evidence,
    "global_equilibrium": _global_equilibrium,
    "analytical_spot_checks": _analytical,
    "load_path": lambda c, r: _load_path(c),
    "solver_health": _solver_health,
    "scia_calculix_cross_check": _cross_solver,
    "mesh_convergence": _mesh_convergence,
    "sensitivity": _sensitivity,
    "evidence_integrity": _evidence_integrity,
}


def verify(plan: dict[str, Any], repository: Path) -> dict[str, Any]:
    repository = repository.resolve()
    if plan.get("schema_version") != "phoenix.structural-independent-verification-plan/1.0":
        return {
            "status": STATUS_INPUT_REQUIRED,
            "errors": ["unsupported or missing schema_version"],
            "safety": dict(SAFETY),
        }
    if not str(plan.get("project_id", "")).strip():
        return {
            "status": STATUS_INPUT_REQUIRED,
            "errors": ["project_id required"],
            "safety": dict(SAFETY),
        }

    category_config = plan.get("categories")
    if not isinstance(category_config, dict):
        return {
            "status": STATUS_INPUT_REQUIRED,
            "errors": ["categories object required"],
            "safety": dict(SAFETY),
        }

    results: dict[str, Any] = {}
    input_required = False
    failed = False
    cross_solver_pass = False

    for category in CATEGORIES:
        config = category_config.get(category)
        applicability, app_detail = _category_applicability(config)
        if applicability == "INPUT_REQUIRED":
            results[category] = {"status": "INPUT_REQUIRED", **app_detail}
            input_required = True
            continue
        if applicability == "NOT_APPLICABLE_TRACEABLE":
            results[category] = {"status": applicability, **app_detail}
            continue
        handler = HANDLERS[category]
        result = handler(config, repository)
        results[category] = result
        if result["status"] == "INPUT_REQUIRED":
            input_required = True
        elif result["status"] == "FAIL":
            failed = True
        elif category == "scia_calculix_cross_check" and result["status"] == "PASS":
            cross_solver_pass = True

    if failed:
        status = STATUS_FAILED
    elif input_required:
        status = STATUS_INPUT_REQUIRED
    elif cross_solver_pass:
        status = STATUS_CROSS_VERIFIED
    else:
        status = STATUS_VERIFIED

    output = {
        "schema_version": "phoenix.structural-independent-verification-result/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": plan["project_id"],
        "status": status,
        "categories": results,
        "cross_solver_numerical_check_completed": cross_solver_pass,
        "professional_review_status": "NOT_PERFORMED_BY_THIS_ENGINE",
        "safety": dict(SAFETY),
    }
    return output


def _summary_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Structural Independent Verification — {result.get('project_id')}",
        "",
        f"**Status:** `{result.get('status')}`",
        "",
        "## Verification categories",
        "",
    ]
    for name in CATEGORIES:
        item = result.get("categories", {}).get(name, {})
        lines.append(f"- `{name}`: `{item.get('status', 'UNKNOWN')}`")
    lines += [
        "",
        "## Boundary",
        "",
        "- This is technical/numerical verification evidence.",
        "- It is not a professional approval.",
        "- It is not an automatic code-compliance claim.",
        "- A SCIA/CalculiX match is not an independent professional review.",
        "- Production remains `LOCKED`.",
        "- FOR-CONSTRUCTION remains `LOCKED`.",
    ]
    return "\n".join(lines)


def run_plan(plan_path: Path, repository: Path, output_root: Path | None = None) -> dict[str, Any]:
    plan = _read_json(plan_path)
    result = verify(plan, repository)
    if output_root is not None:
        out = _safe_path(repository.resolve(), str(output_root), must_exist=False) if not output_root.is_absolute() else output_root
        # Absolute output paths are only accepted when they remain inside the repository.
        try:
            out.resolve().relative_to(repository.resolve())
        except ValueError:
            raise ValueError("Verification output_root must remain inside repository.")
        out.mkdir(parents=True, exist_ok=True)
        _write_json(out / "structural_independent_verification_result.json", result)
        _write_text(out / "structural_independent_verification_summary.md", _summary_markdown(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output-root")
    args = parser.parse_args()

    repository = Path(args.repository)
    output = Path(args.output_root) if args.output_root else None
    result = run_plan(Path(args.plan), repository, output)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["status"] in {STATUS_INPUT_REQUIRED, STATUS_FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
