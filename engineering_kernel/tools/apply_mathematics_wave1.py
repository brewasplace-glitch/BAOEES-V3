from __future__ import annotations

import json
from pathlib import Path

NAMES = [
    "add", "subtract", "multiply", "divide", "power",
    "square_root", "absolute", "minimum", "maximum", "clamp",
    "arithmetic_mean", "weighted_mean", "percentage", "percentage_change",
    "apply_factor", "margin", "utilization", "is_close",
    "round_to_decimals", "round_to_increment", "normalize",
    "linear_interpolate", "dot_product", "vector_magnitude", "vector_normalize",
]


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    registry_path = repository_root / "engineering_kernel/specification/functions/function_registry.json"
    traceability_path = repository_root / "engineering_kernel/specification/traceability/traceability_matrix.json"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    updated = 0

    for function in registry["functions"]:
        if function.get("domain") != "MATH":
            continue
        number = int(function["id"].rsplit("-", 1)[1])
        if 1 <= number <= len(NAMES):
            function["name"] = NAMES[number - 1]
            function["status"] = "UNIT_TESTED"
            function["maturity"] = "M2"
            function["inputs"] = [{"contract": "Finite numeric Python values or sequences."}]
            function["outputs"] = [{"contract": "Deterministic finite numeric result."}]
            function["errors"] = ["MathematicsError for invalid domains, dimensions, ranges or non-finite input."]
            function["dependencies"] = []
            function["standards"] = ["General numerical engineering practice"]
            function["accuracy_requirement"] = "IEEE-754 double precision with explicit test tolerances."
            function["implementation"] = "engineering_kernel/src/phoenix_engineering_kernel/mathematics.py"
            function["tests"] = "engineering_kernel/tests/test_mathematics_wave1.py"
            updated += 1

    if updated != 25:
        raise RuntimeError(f"Expected to update 25 Mathematics records, updated {updated}.")

    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8", newline="\n")

    traceability = json.loads(traceability_path.read_text(encoding="utf-8"))
    links = traceability.setdefault("links", [])
    existing = {(item.get("function_id"), item.get("link_type")) for item in links}

    for number in range(1, 26):
        function_id = f"PEK-MATH-{number:04d}"
        for link_type, target in (
            ("SPEC_TO_CODE", "engineering_kernel/src/phoenix_engineering_kernel/mathematics.py"),
            ("CODE_TO_TEST", "engineering_kernel/tests/test_mathematics_wave1.py"),
        ):
            if (function_id, link_type) not in existing:
                links.append({
                    "function_id": function_id,
                    "link_type": link_type,
                    "target": target,
                })

    traceability_path.write_text(
        json.dumps(traceability, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    print("Updated 25 Mathematics records and traceability links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
