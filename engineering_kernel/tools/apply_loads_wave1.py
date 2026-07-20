from __future__ import annotations
import json
from pathlib import Path

NAMES = [
    "normalize_direction", "create_load", "dead_load", "imposed_load", "wind_load",
    "snow_load", "seismic_load", "thermal_load", "hydrostatic_pressure",
    "earth_pressure_unit_weight", "uniform_line_load", "uniform_area_load",
    "point_load_from_pressure", "resultant_of_uniform_line_load",
    "resultant_of_uniform_area_load", "triangular_line_load_resultant",
    "triangular_line_load_position", "trapezoidal_line_load_resultant",
    "moment_from_force", "load_component", "load_vector", "scale_load",
    "sum_load_vectors", "resultant_load", "combination_value",
    "combination_vector", "characteristic_combination", "design_combination",
    "accidental_combination", "dynamic_amplification",
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
        is_load = (
            function_id.startswith("PEK-LOAD-")
            or function_id.startswith("PEK-LOADS-")
            or domain in {"LOAD", "LOADS"}
        )
        if not is_load:
            continue

        number = int(function_id.rsplit("-", 1)[1])
        if 1 <= number <= len(NAMES):
            item["name"] = NAMES[number - 1]
            item["status"] = "UNIT_TESTED"
            item["maturity"] = "M2"
            item["inputs"] = [{"contract": "Finite load data in one consistent unit system."}]
            item["outputs"] = [{"contract": "Deterministic load, resultant or combination value."}]
            item["errors"] = ["LoadError for invalid, degenerate or non-finite data."]
            item["dependencies"] = ["PEK-UNITS", "PEK-MATH", "PEK-GEOM"]
            item["standards"] = ["General load mechanics; code coefficients supplied externally."]
            item["accuracy_requirement"] = "IEEE-754 double precision with explicit engineering validation."
            item["implementation"] = "engineering_kernel/src/phoenix_engineering_kernel/loads.py"
            item["tests"] = "engineering_kernel/tests/test_loads_wave1.py"
            updated += 1
            matched_ids.append(function_id)

    if updated != 30:
        raise RuntimeError(f"Expected 30 Loads registry updates, got {updated}.")

    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8", newline="\n")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    links = trace.setdefault("links", [])
    existing = {(x.get("function_id"), x.get("link_type")) for x in links}

    for function_id in matched_ids:
        for link_type, target in (
            ("SPEC_TO_CODE", "engineering_kernel/src/phoenix_engineering_kernel/loads.py"),
            ("CODE_TO_TEST", "engineering_kernel/tests/test_loads_wave1.py"),
        ):
            if (function_id, link_type) not in existing:
                links.append({"function_id": function_id, "link_type": link_type, "target": target})
                existing.add((function_id, link_type))

    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8", newline="\n")
    print("Updated 30 Loads records and traceability links.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
