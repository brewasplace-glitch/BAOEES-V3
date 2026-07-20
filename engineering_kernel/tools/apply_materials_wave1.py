from __future__ import annotations
import json
from pathlib import Path

NAMES = [
    "create_material", "concrete_material", "structural_steel_material",
    "reinforcement_steel_material", "timber_material", "masonry_material",
    "aluminium_material", "glass_material", "plastic_material", "soil_material",
    "shear_modulus", "bulk_modulus", "specific_weight", "stress", "strain",
    "elastic_stress", "elastic_strain", "characteristic_to_design_value",
    "design_to_characteristic_value", "safety_factor", "utilization_ratio",
    "apply_temperature_factor", "apply_moisture_factor", "thermal_strain",
    "thermal_expansion_length", "creep_adjusted_modulus",
    "shrinkage_deformation", "classify_material", "validate_material",
    "adjusted_material",
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
        is_material = (
            function_id.startswith("PEK-MATL-")
            or function_id.startswith("PEK-MATERIALS-")
            or domain in {"MATL", "MATERIAL", "MATERIALS"}
        )
        if not is_material:
            continue

        number = int(function_id.rsplit("-", 1)[1])
        if 1 <= number <= len(NAMES):
            item["name"] = NAMES[number - 1]
            item["status"] = "UNIT_TESTED"
            item["maturity"] = "M2"
            item["inputs"] = [{"contract": "Finite material properties in one consistent unit system."}]
            item["outputs"] = [{"contract": "Deterministic material property or engineering value."}]
            item["errors"] = ["MaterialError for invalid, non-physical or non-finite data."]
            item["dependencies"] = ["PEK-UNITS", "PEK-MATH"]
            item["standards"] = ["General material mechanics; code-specific values supplied by higher layers."]
            item["accuracy_requirement"] = "IEEE-754 double precision with explicit engineering validation."
            item["implementation"] = "engineering_kernel/src/phoenix_engineering_kernel/materials.py"
            item["tests"] = "engineering_kernel/tests/test_materials_wave1.py"
            updated += 1
            matched_ids.append(function_id)

    if updated != 30:
        raise RuntimeError(f"Expected 30 Materials registry updates, got {updated}.")

    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8", newline="\n")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    links = trace.setdefault("links", [])
    existing = {(x.get("function_id"), x.get("link_type")) for x in links}

    for function_id in matched_ids:
        for link_type, target in (
            ("SPEC_TO_CODE", "engineering_kernel/src/phoenix_engineering_kernel/materials.py"),
            ("CODE_TO_TEST", "engineering_kernel/tests/test_materials_wave1.py"),
        ):
            if (function_id, link_type) not in existing:
                links.append({"function_id": function_id, "link_type": link_type, "target": target})
                existing.add((function_id, link_type))

    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8", newline="\n")
    print("Updated 30 Materials records and traceability links.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
