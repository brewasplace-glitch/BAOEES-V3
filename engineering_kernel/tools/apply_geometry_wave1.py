from __future__ import annotations
import json
from pathlib import Path

NAMES = [
    "point_2d", "point_3d", "distance_2d", "distance_3d", "midpoint_2d",
    "midpoint_3d", "vector_2d", "vector_3d", "dot_2d", "dot_3d",
    "cross_2d", "cross_3d", "vector_length_2d", "vector_length_3d",
    "normalize_vector_2d", "normalize_vector_3d", "angle_between_vectors_2d",
    "polygon_area", "polygon_signed_area", "polygon_perimeter", "polygon_centroid",
    "bounding_box_2d", "translate_2d", "rotate_2d", "line_intersection_2d",
]

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    registry_path = root / "engineering_kernel/specification/functions/function_registry.json"
    trace_path = root / "engineering_kernel/specification/traceability/traceability_matrix.json"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    updated = 0
    for item in registry["functions"]:
        function_id = str(item.get("id", ""))
        domain = str(item.get("domain", "")).upper()
        if not function_id.startswith("PEK-GEOM-") and domain not in {"GEOM", "GEOMETRY"}:
            continue
        number = int(function_id.rsplit("-", 1)[1])
        if 1 <= number <= len(NAMES):
            item["name"] = NAMES[number-1]
            item["status"] = "UNIT_TESTED"
            item["maturity"] = "M2"
            item["inputs"] = [{"contract": "Finite coordinates using one consistent linear unit."}]
            item["outputs"] = [{"contract": "Deterministic geometric result."}]
            item["errors"] = ["GeometryError for invalid, degenerate or non-finite geometry."]
            item["dependencies"] = ["PEK-UNITS", "PEK-MATH"]
            item["standards"] = ["Cartesian analytic geometry"]
            item["accuracy_requirement"] = "IEEE-754 double precision; explicit tolerances where required."
            item["implementation"] = "engineering_kernel/src/phoenix_engineering_kernel/geometry.py"
            item["tests"] = "engineering_kernel/tests/test_geometry_wave1.py"
            updated += 1

    if updated != 25:
        raise RuntimeError(f"Expected 25 Geometry registry updates, got {updated}.")

    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8", newline="\n")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    links = trace.setdefault("links", [])
    existing = {(x.get("function_id"), x.get("link_type")) for x in links}
    for number in range(1, 26):
        function_id = f"PEK-GEOM-{number:04d}"
        for link_type, target in (
            ("SPEC_TO_CODE", "engineering_kernel/src/phoenix_engineering_kernel/geometry.py"),
            ("CODE_TO_TEST", "engineering_kernel/tests/test_geometry_wave1.py"),
        ):
            if (function_id, link_type) not in existing:
                links.append({"function_id": function_id, "link_type": link_type, "target": target})
                existing.add((function_id, link_type))

    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8", newline="\n")
    print("Updated 25 Geometry records and traceability links.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
