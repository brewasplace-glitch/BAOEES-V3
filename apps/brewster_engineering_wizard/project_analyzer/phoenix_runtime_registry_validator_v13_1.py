from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME="Phoenix Runtime Registry Validator"
ENGINE_VERSION="v13.1"

def root()->Path:
    p=Path.cwd().resolve()
    for c in [p,*p.parents]:
        if (c/".git").exists(): return c
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT=root()
RUNTIME=ROOT/"configs/phoenix/ai_runtime_registry_v13_0.json"
CAPS=ROOT/"configs/phoenix/capability_registry_v12_0.json"
OUT=ROOT/"outputs/runtime/v13_0"

class Validator:
    def __init__(self):
        self.runtime=self.read(RUNTIME)
        self.caps=self.read(CAPS)

    def repair(self)->Dict[str,Any]:
        engines=self.runtime.setdefault("engines",[])
        ids={e["engine_id"] for e in engines}
        added=[]
        base=ROOT/"apps/brewster_engineering_wizard/project_analyzer"

        for cap in self.caps.get("engines",[]):
            eid=cap.get("engine_id","")
            if not eid or eid in ids: continue
            module=None
            for pattern in cap.get("module_patterns",[]):
                candidate=base/pattern
                if candidate.is_file():
                    module=candidate.relative_to(ROOT).as_posix()
                    break
            if module is None: continue
            engines.append({
                "engine_id":eid,
                "module":module,
                "dependencies":[],
                "required":False,
                "command":["{python}","{project_root}/"+module,"self-test"],
                "source":"capability_registry_v12_0"
            })
            ids.add(eid); added.append(eid)

        aliases={
            "phoenix.engine_discovery":"phoenix.engine_intelligence",
            "phoenix.engine_intelligence":"phoenix.engine_discovery"
        }
        changes=[]
        ids={e["engine_id"] for e in engines}
        for e in engines:
            repaired=[]
            for dep in e.get("dependencies",[]):
                if dep in ids:
                    repaired.append(dep)
                elif aliases.get(dep) in ids:
                    repaired.append(aliases[dep]);changes.append({"engine_id":e["engine_id"],"from":dep,"to":aliases[dep]})
                else:
                    repaired.append(dep)
            e["dependencies"]=repaired

        engines.sort(key=lambda x:x["engine_id"])
        self.runtime["registry_version"]="v13.1"
        RUNTIME.write_text(json.dumps(self.runtime,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        return {"engine":ENGINE_NAME,"version":ENGINE_VERSION,"added":added,"changes":changes,"status":"PASS"}

    def validate(self)->Dict[str,Any]:
        engines=self.runtime.get("engines",[])
        ids=[e.get("engine_id","") for e in engines]
        idset=set(ids);errors=[]
        if len(ids)!=len(idset):errors.append("Dubbele engine_id gevonden.")
        byid={e["engine_id"]:e for e in engines}
        for e in engines:
            if not (ROOT/e.get("module","")).is_file():errors.append(f"Module ontbreekt: {e.get('engine_id')}")
            for dep in e.get("dependencies",[]):
                if dep not in idset:errors.append(f"Niet-geregistreerde dependency {dep} bij {e['engine_id']}")

        visiting:Set[str]=set();visited:Set[str]=set()
        def visit(i:str):
            if i in visited:return
            if i in visiting:raise RuntimeError(f"Circulaire dependency bij {i}")
            visiting.add(i)
            for d in byid[i].get("dependencies",[]):visit(d)
            visiting.remove(i);visited.add(i)
        try:
            for i in byid:visit(i)
        except RuntimeError as exc:
            errors.append(str(exc))

        result={"engine":ENGINE_NAME,"version":ENGINE_VERSION,"errors":errors,"status":"PASS" if not errors else "FAIL"}
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/"runtime_registry_validation_v13_1.json").write_text(json.dumps(result,indent=2),encoding="utf-8-sig")
        return result

    def read(self,p:Path):return json.loads(p.read_text(encoding="utf-8-sig"))

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["repair","validate","repair-and-validate"])
    a=p.parse_args();v=Validator()
    if a.command=="repair":r=v.repair()
    elif a.command=="validate":r=v.validate()
    else:
        repair=v.repair();v=Validator();validation=v.validate()
        r={"engine":ENGINE_NAME,"version":ENGINE_VERSION,"repair":repair,"validation":validation,"status":validation["status"]}
    print(json.dumps(r,indent=2))
    if r["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
