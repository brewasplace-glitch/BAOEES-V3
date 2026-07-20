from __future__ import annotations
import json
from pathlib import Path

NAMES = [
    "validate_type", "validate_required", "validate_not_nan", "validate_finite",
    "validate_range", "validate_positive", "validate_non_negative",
    "validate_choice", "validate_length", "validate_dimensions", "validate_units",
    "validate_consistency", "validate_monotonic", "validate_tolerance",
    "validate_relative_tolerance", "validate_rounding", "validate_convergence",
    "validate_factor_of_safety", "validate_utilization",
    "validate_material_property", "validate_geometry_non_degenerate",
    "validate_load_magnitude", "validate_dependency_set", "validate_traceability",
    "validate_registry_unique_ids", "classify_issue", "create_issue",
    "create_validation_report", "merge_validation_reports", "validation_summary",
]

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    registry_path = root / "engineering_kernel/specification/functions/function_registry.json"
    trace_path = root / "engineering_kernel/specification/traceability/traceability_matrix.json"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    updated = 0
    matched_ids = []

    for item in registry["functions"]:
        function_id = str(item.get("id", ""))
        domain = str(item.get("domain", "")).upper()
        is_validation = (
            function_id.startswith("PEK-VAL-")
            or function_id.startswith("PEK-VALID-")
            or function_id.startswith("PEK-VALIDATION-")
            or domain in {"VAL", "VALID", "VALIDATION"}
        )
        if not is_validation:
            continue

        number = int(function_id.rsplit("-", 1)[1])
        if 1 <= number <= len(NAMES):
            item["name"] = NAMES[number - 1]
            item["status"] = "UNIT_TESTED"
            item["maturity"] = "M2"
            item["inputs"] = [{"contract": "Validation subject and explicit engineering constraints."}]
            item["outputs"] = [{"contract": "Deterministic boolean, issue or validation report."}]
            item["errors"] = ["ValidationError for invalid validator configuration or arguments."]
            item["dependencies"] = ["PEK-UNITS", "PEK-MATH", "PEK-GEOM", "PEK-MATL", "PEK-LOAD"]
            item["standards"] = ["Generic QA/QC validation; code-specific rules supplied externally."]
            item["accuracy_requirement"] = "Explicit finite checks and caller-defined tolerances."
            item["implementation"] = "engineering_kernel/src/phoenix_engineering_kernel/validation.py"
            item["tests"] = "engineering_kernel/tests/test_validation_wave1.py"
            updated += 1
            matched_ids.append(function_id)

    if updated != 30:
        raise RuntimeError(f"Expected 30 Validation registry updates, got {updated}.")

    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8", newline="\n")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    links = trace.setdefault("links", [])
    existing = {(x.get("function_id"), x.get("link_type")) for x in links}

    for function_id in matched_ids:
        for link_type, target in (
            ("SPEC_TO_CODE", "engineering_kernel/src/phoenix_engineering_kernel/validation.py"),
            ("CODE_TO_TEST", "engineering_kernel/tests/test_validation_wave1.py"),
        ):
            if (function_id, link_type) not in existing:
                links.append({"function_id": function_id, "link_type": link_type, "target": target})
                existing.add((function_id, link_type))

    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8", newline="\n")
    print("Updated 30 Validation records and traceability links.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
