import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specification"

def test_registry_has_750_functions():
    data = json.loads((SPEC / "functions" / "function_registry.json").read_text(encoding="utf-8"))
    assert len(data["functions"]) == 750

def test_unique_ids():
    data = json.loads((SPEC / "functions" / "function_registry.json").read_text(encoding="utf-8"))
    ids = [f["id"] for f in data["functions"]]
    assert len(ids) == len(set(ids))

def test_all_internal_units_are_si():
    data = json.loads((SPEC / "functions" / "function_registry.json").read_text(encoding="utf-8"))
    assert all(f["internal_units"] == "SI" for f in data["functions"])


def test_all_ids_match_registered_domain_codes():
    import re
    pattern = re.compile(r"^PEK-(UNITS|MATH|GEOM|MATL|LOAD|STAT|OPTI|CODE|VALD|REPT)-[0-9]{4}$")
    data = json.loads((SPEC / "functions" / "function_registry.json").read_text(encoding="utf-8"))
    assert all(pattern.fullmatch(f["id"]) for f in data["functions"])
