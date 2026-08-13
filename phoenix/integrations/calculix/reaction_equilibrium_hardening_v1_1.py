"""PROJECT PHOENIX CalculiX reaction/equilibrium hardening v1.1."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import argparse, hashlib, json, re

VERSION = "1.1.0"
ENGINE_ID = "PHX-CALCULIX-REACTION-EQUILIBRIUM-HARDENING"
PARSED = "CALCULIX_SUPPORT_FORCE_PARSED"
INPUT_PARSE_REQUIRED = "CALCULIX_INPUT_LOAD_PARSE_REQUIRED"
DAT_PARSE_REQUIRED = "CALCULIX_REFERENCE_REACTION_PARSE_REQUIRED"
VALIDATED = "CALCULIX_GOLDEN_REFERENCE_VALIDATED"
FAILED = "CALCULIX_GOLDEN_REFERENCE_EQUILIBRIUM_FAILED"

SAFETY = {
    "raw_solver_evidence_overwritten": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "software_test_tolerance_is_general_engineering_tolerance": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _numbers(line: str) -> list[float]:
    return [float(x) for x in re.findall(r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?",line)]

def parse_support_forces_dat(dat_path: Path, support_set: str="SUPPORTS") -> dict[str,Any]:
    if not dat_path.is_file():
        return {"status":DAT_PARSE_REQUIRED,"reason":"DAT_MISSING","path":str(dat_path)}
    lines=dat_path.read_text(encoding="utf-8",errors="replace").splitlines()
    rows={}
    total=None
    in_rows=False
    want_total=False
    for line in lines:
        low=line.lower()
        if "forces (fx,fy,fz) for set" in low and support_set.lower() in low and "total force" not in low:
            in_rows=True; want_total=False; continue
        if "total force (fx,fy,fz) for set" in low and support_set.lower() in low:
            in_rows=False; want_total=True; continue
        if in_rows:
            nums=_numbers(line)
            if len(nums)==4:
                rows[int(nums[0])]=[nums[1],nums[2],nums[3]]
            elif line.strip() and rows:
                in_rows=False
        if want_total:
            nums=_numbers(line)
            if len(nums)==3:
                total=[nums[0],nums[1],nums[2]]
                want_total=False
    if total is None:
        return {"status":DAT_PARSE_REQUIRED,"reason":"TOTAL_FORCE_BLOCK_NOT_FOUND","support_rows":rows,"path":str(dat_path)}
    return {
        "status":PARSED,
        "support_set":support_set,
        "support_rows":rows,
        "reported_total_force_N":total,
        "reported_total_force_z_N":total[2],
        "dat_sha256":sha256_file(dat_path),
        "path":str(dat_path),
    }

def parse_support_nodes_and_cloads(inp_path: Path, support_set: str="SUPPORTS") -> dict[str,Any]:
    if not inp_path.is_file():
        return {"status":INPUT_PARSE_REQUIRED,"reason":"INP_MISSING","path":str(inp_path)}
    lines=inp_path.read_text(encoding="utf-8",errors="replace").splitlines()
    target=support_set.upper()
    supports=[]
    cloads=[]
    in_support=False
    in_cload=False
    for raw in lines:
        s=raw.strip()
        u=s.upper()
        if not s or s.startswith("**"):
            continue
        if s.startswith("*"):
            in_support=False; in_cload=False
            if u.startswith("*NSET") and f"NSET={target}" in u.replace(" ",""):
                in_support=True
            elif u.startswith("*CLOAD"):
                in_cload=True
            continue
        if in_support:
            for tok in s.split(","):
                tok=tok.strip()
                if tok:
                    supports.append(int(tok))
            continue
        if in_cload:
            parts=[p.strip() for p in s.split(",")]
            if len(parts)>=3:
                cloads.append({"node":int(parts[0]),"dof":int(parts[1]),"value":float(parts[2])})
    supports=sorted(set(supports))
    if not supports:
        return {"status":INPUT_PARSE_REQUIRED,"reason":"SUPPORT_SET_NOT_FOUND","path":str(inp_path)}
    vertical=[x for x in cloads if x["dof"]==3]
    direct=[x for x in vertical if x["node"] in supports]
    by_node={n:sum(x["value"] for x in direct if x["node"]==n) for n in supports}
    return {
        "status":PARSED,
        "support_nodes":supports,
        "vertical_cload_total_N":sum(x["value"] for x in vertical),
        "vertical_support_cload_total_N":sum(x["value"] for x in direct),
        "vertical_support_cload_by_node_N":by_node,
        "inp_sha256":sha256_file(inp_path),
        "path":str(inp_path),
    }

def reconstruct_equilibrium(dat_result: dict[str,Any], inp_result: dict[str,Any],
                            expected_applied_load_N: float=-5000.0,
                            expected_each_support_reaction_N: float=2500.0,
                            tolerance_N: float=5.0) -> dict[str,Any]:
    if dat_result.get("status")!=PARSED:
        return {"status":DAT_PARSE_REQUIRED,"dat":dat_result,"safety":dict(SAFETY)}
    if inp_result.get("status")!=PARSED:
        return {"status":INPUT_PARSE_REQUIRED,"input":inp_result,"safety":dict(SAFETY)}
    reported=float(dat_result["reported_total_force_z_N"])
    direct=float(inp_result["vertical_support_cload_total_N"])
    applied=float(inp_result["vertical_cload_total_N"])
    reconstructed=reported-direct
    balance=abs(reconstructed+applied)
    corrected={}
    for node in inp_result["support_nodes"]:
        row=dat_result.get("support_rows",{}).get(node)
        if row is not None:
            corrected[node]=float(row[2])-float(inp_result["vertical_support_cload_by_node_N"].get(node,0.0))
    errors=[]
    if abs(applied-expected_applied_load_N)>tolerance_N:
        errors.append("APPLIED_LOAD_MISMATCH")
    if balance>tolerance_N:
        errors.append("GLOBAL_VERTICAL_EQUILIBRIUM")
    if len(corrected)!=2:
        errors.append("EXPECTED_TWO_SUPPORT_REACTIONS")
    elif any(abs(v-expected_each_support_reaction_N)>tolerance_N for v in corrected.values()):
        errors.append("SUPPORT_REACTION_MISMATCH")
    return {
        "status":VALIDATED if not errors else FAILED,
        "reference_model_id":"PHX-GOLDEN-SCIA-BEAM-001",
        "reported_support_force_z_N":reported,
        "direct_support_cload_z_N":direct,
        "reconstructed_total_support_reaction_z_N":reconstructed,
        "applied_total_cload_z_N":applied,
        "global_vertical_balance_error_N":balance,
        "reported_support_rows_N":{str(k):v for k,v in dat_result.get("support_rows",{}).items()},
        "direct_support_cload_by_node_N":{str(k):v for k,v in inp_result["vertical_support_cload_by_node_N"].items()},
        "reconstructed_support_reaction_by_node_N":{str(k):v for k,v in corrected.items()},
        "expected_each_support_reaction_N":expected_each_support_reaction_N,
        "software_test_tolerance_N":tolerance_N,
        "tolerance_scope":"SOFTWARE_GOLDEN_REFERENCE_ONLY_NOT_GENERAL_ENGINEERING",
        "accounting_basis":"DAT_REPORTED_SUPPORT_FORCE_MINUS_DIRECT_SUPPORT_CLOAD",
        "errors":errors,
        "raw_evidence":{"dat_sha256":dat_result.get("dat_sha256"),"inp_sha256":inp_result.get("inp_sha256")},
        "safety":dict(SAFETY),
    }

def reevaluate_existing(dat_path: Path, inp_path: Path, output_path: Path) -> dict[str,Any]:
    result=reconstruct_equilibrium(parse_support_forces_dat(dat_path),parse_support_nodes_and_cloads(inp_path))
    result["reevaluation"]={
        "live_solver_started":False,
        "raw_solver_evidence_modified":False,
        "source_dat":str(dat_path),
        "source_inp":str(inp_path),
    }
    write_json(output_path,result)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dat",required=True)
    p.add_argument("--inp",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=reevaluate_existing(Path(a.dat),Path(a.inp),Path(a.output))
    print(json.dumps(r,indent=2,ensure_ascii=True))
    if r.get("status")==FAILED:
        raise SystemExit(1)

if __name__=="__main__":
    main()
