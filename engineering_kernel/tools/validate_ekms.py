from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ID_PATTERN = re.compile(r"^PEK-(UNITS|MATH|GEOM|MATL|LOAD|STAT|OPTI|CODE|VALD|REPT)-[0-9]{4}$")
VALID_STATES = {"PLANNED","SPECIFIED","IMPLEMENTED","UNIT_TESTED","VALIDATED","RELEASED"}

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    spec = root / "specification"
    ekms = json.loads((spec / "ekms.json").read_text(encoding="utf-8"))
    registry = json.loads((spec / "functions" / "function_registry.json").read_text(encoding="utf-8"))["functions"]

    errors: list[str] = []
    ids = [item.get("id", "") for item in registry]
    duplicates = [k for k, v in Counter(ids).items() if v > 1]

    if len(registry) != 750:
        errors.append(f"Expected 750 functions, found {len(registry)}.")
    if duplicates:
        errors.append(f"Duplicate IDs: {duplicates[:10]}")
    for item in registry:
        if not ID_PATTERN.match(item.get("id", "")):
            errors.append(f"Invalid ID: {item.get('id')}")
        if item.get("status") not in VALID_STATES:
            errors.append(f"Invalid state for {item.get('id')}: {item.get('status')}")
        if item.get("internal_units") != "SI":
            errors.append(f"Non-SI internal units for {item.get('id')}")
        if len(item.get("test_requirements", [])) < 5:
            errors.append(f"Insufficient test requirements for {item.get('id')}")

    expected = {d["code"]: d["target_function_count"] for d in ekms["domains"]}
    actual = Counter(item["domain"] for item in registry)
    if dict(actual) != expected:
        errors.append(f"Domain counts mismatch. Expected {expected}, actual {dict(actual)}")

    if errors:
        print("EKMS validation FAILED")
        for error in errors[:50]:
            print(f" - {error}")
        return 1

    print("EKMS validation PASSED")
    print(f"Functions: {len(registry)}")
    print(f"Domains: {len(actual)}")
    print("Internal units: SI")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
