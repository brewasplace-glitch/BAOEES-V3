from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from phoenix.adapters.open_source.controlled_install import (
    install_ifcopenshell, register_portable, write_environment_script
)

REGISTRY=ROOT/"configs/phoenix/third_party_engine_registry_v5_1_0.json"
MANAGED=ROOT/"tools/third_party_engines"

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("install-ifcopenshell")
    r=sub.add_parser("register")
    r.add_argument("--engine",required=True,choices=["ifcconvert","freecad","qgis","energyplus","opensees","calculix"])
    r.add_argument("--source",required=True)
    r.add_argument("--sha256",required=True)
    e=sub.add_parser("write-env")
    e.add_argument("--acceptance-json",required=True)
    e.add_argument("--output",default="CONFIGURE_PROJECT_PHOENIX_ENGINE_ENVIRONMENT.ps1")
    a=p.parse_args()
    if a.command=="install-ifcopenshell":
        result=install_ifcopenshell(REGISTRY)
    elif a.command=="register":
        result=register_portable(a.engine,Path(a.source),MANAGED,REGISTRY,a.sha256)
    else:
        data=json.loads(Path(a.acceptance_json).read_text(encoding="utf-8"))
        write_environment_script(data,Path(a.output));return 0
    print(json.dumps(result.__dict__,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
