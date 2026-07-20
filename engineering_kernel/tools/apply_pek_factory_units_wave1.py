from __future__ import annotations
import json
from pathlib import Path

NAMES = [
"quantity","convert","convert_length","convert_area","convert_volume","convert_mass",
"convert_time","convert_force","convert_pressure","convert_density","convert_acceleration",
"convert_energy","convert_power","convert_angle","convert_temperature","to_si","from_si",
"are_compatible","validate_dimension","normalized_symbol"
]

def main() -> int:
    repo=Path(__file__).resolve().parents[2]
    registry_path=repo/"engineering_kernel/specification/functions/function_registry.json"
    trace_path=repo/"engineering_kernel/specification/traceability/traceability_matrix.json"
    data=json.loads(registry_path.read_text(encoding="utf-8"))
    updated=0
    for item in data["functions"]:
        if item.get("domain")!="UNITS": continue
        number=int(item["id"].rsplit("-",1)[1])
        if 1 <= number <= len(NAMES):
            item["name"]=NAMES[number-1]
            item["status"]="UNIT_TESTED"
            item["maturity"]="M2"
            item["implementation"]="engineering_kernel/src/phoenix_engineering_kernel/units.py"
            item["tests"]="engineering_kernel/tests/test_units_wave1.py"
            item["inputs"]=[{"contract":"Typed Python API"}]
            item["outputs"]=[{"contract":"Deterministic SI-traceable result"}]
            item["errors"]=["UnitError"]
            item["standards"]=["SI principles"]
            updated += 1
    if updated != 20:
        raise RuntimeError(f"Expected 20 updates, got {updated}")
    registry_path.write_text(json.dumps(data,indent=2),encoding="utf-8",newline="\n")
    trace=json.loads(trace_path.read_text(encoding="utf-8"))
    links=trace.setdefault("links",[])
    existing={(x.get("function_id"),x.get("link_type")) for x in links}
    for i in range(1,21):
        fid=f"PEK-UNITS-{i:04d}"
        for typ,target in [
            ("SPEC_TO_CODE","engineering_kernel/src/phoenix_engineering_kernel/units.py"),
            ("CODE_TO_TEST","engineering_kernel/tests/test_units_wave1.py")
        ]:
            if (fid,typ) not in existing:
                links.append({"function_id":fid,"link_type":typ,"target":target})
    trace_path.write_text(json.dumps(trace,indent=2),encoding="utf-8",newline="\n")
    print("Updated 20 UNITS records.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
