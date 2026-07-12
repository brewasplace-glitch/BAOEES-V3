from __future__ import annotations
import argparse, importlib.util, json, subprocess, sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ENGINE_NAME="Phoenix AI Runtime"
ENGINE_VERSION="v13.0"

def root()->Path:
    p=Path.cwd().resolve()
    for c in [p,*p.parents]:
        if (c/".git").exists(): return c
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT=root()
POLICY=ROOT/"configs/phoenix/ai_runtime_policy_v13_0.json"
REGISTRY=ROOT/"configs/phoenix/ai_runtime_registry_v13_0.json"
CAPS=ROOT/"configs/phoenix/capability_registry_v12_0.json"
OUT=ROOT/"outputs/runtime/v13_0"
STATE=OUT/"state"

class Runtime:
    def __init__(self):
        self.policy=self.read(POLICY); self.registry=self.read(REGISTRY); self.caps=self.read(CAPS)

    def self_test(self)->Dict[str,Any]:
        checks={
            "policy":POLICY.exists(),"registry":REGISTRY.exists(),"capabilities":CAPS.exists(),
            "graph":self.graph_valid(),"python":sys.version_info>=(3,10)
        }
        return self.save("self_test",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "checks":checks,"status":"PASS" if all(checks.values()) else "FAIL"})

    def health(self)->Dict[str,Any]:
        rows=[]
        required=set(self.policy["required_engines"])
        ok=True
        for e in self.registry["engines"]:
            p=ROOT/e["module"]; loadable=False
            if p.is_file():
                spec=importlib.util.spec_from_file_location(p.stem,p)
                loadable=spec is not None and spec.loader is not None
            status="HEALTHY" if loadable else "UNAVAILABLE"
            if e["engine_id"] in required and status!="HEALTHY": ok=False
            rows.append({"engine_id":e["engine_id"],"module":e["module"],"status":status})
        return self.save("health",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "engines":rows,"status":"PASS" if ok else "FAIL"})

    def plan(self,capabilities:List[str],runtime_id:str)->Dict[str,Any]:
        chosen={}; unresolved=[]
        for cap in capabilities:
            matches=[e for e in self.caps["engines"] if cap in e.get("capabilities",[])]
            matches.sort(key=lambda e:(e.get("priority",100),e["engine_id"]))
            if not matches: unresolved.append(cap); continue
            e=matches[0]; chosen.setdefault(e["engine_id"],{"engine_id":e["engine_id"],"capabilities":[]})
            chosen[e["engine_id"]]["capabilities"].append(cap)
        selected=sorted(chosen.values(),key=lambda x:x["engine_id"])
        graph=self.graph([x["engine_id"] for x in selected])
        state={"runtime_id":runtime_id,"status":"PLANNED","selected_engines":selected,
               "execution_graph":graph,"completed_engines":[],"updated_at":datetime.now().isoformat()}
        self.write_state(state)
        return self.save("plan",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,"mode":"PLAN",
            "runtime_id":runtime_id,"selected_engines":selected,"execution_graph":graph,
            "unresolved_capabilities":unresolved,"ready":not unresolved,
            "status":"PASS" if not unresolved else "PARTIAL","automatic_commit_push":False})

    def execute(self,runtime_id:str,token:str,resume:bool=False)->Dict[str,Any]:
        if token!=self.policy["required_approval_token"]:
            return {"engine":ENGINE_NAME,"version":ENGINE_VERSION,"status":"BLOCKED_NO_GO"}
        if subprocess.run(["git","status","--porcelain"],cwd=ROOT,text=True,capture_output=True).stdout.strip():
            return {"engine":ENGINE_NAME,"version":ENGINE_VERSION,"status":"BLOCKED_REPOSITORY_PREFLIGHT"}
        path=self.state_path(runtime_id)
        if not path.exists(): return {"engine":ENGINE_NAME,"version":ENGINE_VERSION,"status":"BLOCKED_NO_PLAN"}
        state=self.read(path); done=set(state.get("completed_engines",[])); results=[]
        for engine_id in state["execution_graph"]:
            if resume and engine_id in done: continue
            e=self.engine(engine_id); cmd=self.expand(e.get("command",[]))
            if not cmd: continue
            cp=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
            results.append({"engine_id":engine_id,"returncode":cp.returncode,
                            "stdout":cp.stdout,"stderr":cp.stderr,
                            "status":"PASS" if cp.returncode==0 else "FAIL"})
            if cp.returncode!=0 and e.get("required",True):
                state["status"]="FAILED"; state["failed_engine"]=engine_id; self.write_state(state)
                return self.save("execute",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
                    "runtime_id":runtime_id,"results":results,"status":"FAILED_REQUIRED_ENGINE"})
            done.add(engine_id); state["completed_engines"]=sorted(done); self.write_state(state)
        state["status"]="PASS"; self.write_state(state)
        return self.save("execute",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "runtime_id":runtime_id,"results":results,"status":"PASS","automatic_commit_push":False})

    def graph(self,requested:List[str])->List[str]:
        out=[]; visiting:Set[str]=set(); visited:Set[str]=set()
        def visit(i:str):
            if i in visited:return
            if i in visiting:raise RuntimeError(f"Circulaire afhankelijkheid: {i}")
            visiting.add(i)
            for d in self.engine(i).get("dependencies",[]):visit(d)
            visiting.remove(i);visited.add(i);out.append(i)
        for i in requested:visit(i)
        return out

    def graph_valid(self)->bool:
        try:
            for e in self.registry["engines"]:self.graph([e["engine_id"]])
            return True
        except Exception:return False

    def engine(self,i:str)->Dict[str,Any]:
        for e in self.registry["engines"]:
            if e["engine_id"]==i:return e
        raise RuntimeError(f"Engine niet geregistreerd: {i}")

    def expand(self,cmd:List[str])->List[str]:
        return [x.replace("{python}",sys.executable).replace("{project_root}",str(ROOT)) for x in cmd]

    def state_path(self,i:str)->Path:
        safe="".join(c for c in i if c.isalnum() or c in "-_")
        if not safe:raise RuntimeError("Ongeldige runtime_id")
        return STATE/f"{safe}.json"

    def write_state(self,d:Dict[str,Any]):
        p=self.state_path(d["runtime_id"]);p.parent.mkdir(parents=True,exist_ok=True)
        d["updated_at"]=datetime.now().isoformat();p.write_text(json.dumps(d,indent=2),encoding="utf-8-sig")

    def save(self,name:str,d:Dict[str,Any])->Dict[str,Any]:
        OUT.mkdir(parents=True,exist_ok=True)
        d["generated_at"]=datetime.now().isoformat()
        (OUT/f"ai_runtime_{name}_v13_0.json").write_text(json.dumps(d,indent=2),encoding="utf-8-sig")
        return d

    def read(self,p:Path):return json.loads(p.read_text(encoding="utf-8-sig"))

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("self-test");s.add_parser("health")
    q=s.add_parser("plan");q.add_argument("--runtime-id",default="phoenix-core-v13");q.add_argument("--capability",action="append",required=True)
    for n in ("execute","resume"):
        q=s.add_parser(n);q.add_argument("--runtime-id",default="phoenix-core-v13");q.add_argument("--approval-token",default="")
    a=p.parse_args();r=Runtime()
    if a.cmd=="self-test":x=r.self_test()
    elif a.cmd=="health":x=r.health()
    elif a.cmd=="plan":x=r.plan(a.capability,a.runtime_id)
    else:x=r.execute(a.runtime_id,a.approval_token,a.cmd=="resume")
    print(json.dumps(x,indent=2))
    if x.get("status") in {"FAIL","BLOCKED_NO_GO","BLOCKED_REPOSITORY_PREFLIGHT","BLOCKED_NO_PLAN","FAILED_REQUIRED_ENGINE"}:raise SystemExit(1)
if __name__=="__main__":main()
