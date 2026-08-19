from __future__ import annotations
import argparse,json
from pathlib import Path
from .engine import generate_variants,select_balanced
from .adapters import detect_open_source_stack
from .digital_twin import build_digital_twin_patch
from .ifc_handoff import build_authoritative_ifc_contract
from .output import write_package

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    project=json.loads(Path(a.input).read_text(encoding="utf-8"))
    variants_obj=generate_variants(project); selected_obj=select_balanced(variants_obj)
    variants=[v.to_dict() for v in variants_obj]; selected=selected_obj.to_dict(); stack=detect_open_source_stack()
    dt=build_digital_twin_patch(project,variants,selected["variant_id"]); ifc=build_authoritative_ifc_contract(project,selected)
    summary=write_package(a.output,project,variants,selected,stack,dt,ifc)
    print(json.dumps({"summary":summary,"open_source_stack":stack},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
