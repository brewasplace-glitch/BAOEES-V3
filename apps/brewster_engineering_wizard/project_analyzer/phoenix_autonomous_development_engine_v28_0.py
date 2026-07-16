from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path

NAME="Phoenix Autonomous Development Engine"; VER="v28.0"

def root():
    p=Path.cwd().resolve()
    for x in [p,*p.parents]:
        if (x/".git").exists(): return x
    raise RuntimeError("root not found")

ROOT=root(); CFG=ROOT/"configs/phoenix"; OUT=ROOT/"outputs/runtime/v28_0"; DEV=ROOT/"outputs/development/v28_0"

class Engine:
    def __init__(self):
        self.policy=self.read(CFG/"autonomous_development_policy_v28_0.json")
        self.registry=self.read(CFG/"development_capability_registry_v28_0.json")

    def self_test(self):
        c={"policy":bool(self.policy),"registry":bool(self.registry),"python":sys.version_info>=(3,10)}
        return self.save(OUT/"development_self_test_v28_0.json",{"engine":NAME,"version":VER,"checks":c,"status":"PASS" if all(c.values()) else "FAIL"})

    def analyze(self):
        rows=[]
        for t in self.registry["targets"]:
            e=(ROOT/t["path"]).exists()
            rows.append({"target_id":t["target_id"],"path":t["path"],"exists":e,"required":t["required"],"status":"AVAILABLE" if e else "MISSING"})
        return self.save(OUT/"development_analysis_v28_0.json",{"engine":NAME,"version":VER,"findings":rows,"missing_required_count":sum(1 for r in rows if r["required"] and not r["exists"]),"status":"PASS"})

    def propose(self):
        a=self.analyze(); p=[]
        for r in a["findings"]:
            if not r["exists"]:
                p.append({"proposal_id":f"DEV-{len(p)+1:03d}","target_id":r["target_id"],"action":"CREATE_MISSING_COMPONENT","requires_go":True,"automatic_execution":False})
        if not p:
            p=[{"proposal_id":"DEV-001","target_id":"platform","action":"RUN_CAPABILITY_GAP_REVIEW","requires_go":True,"automatic_execution":False}]
        return self.save(DEV/"development_proposals_v28_0.json",{"engine":NAME,"version":VER,"proposals":p,"mode":"PROPOSAL_ONLY","status":"PASS"})

    def patch_plan(self):
        p=self.propose()
        patches=[{"patch_id":x["proposal_id"],"target_id":x["target_id"],"steps":["validate_target","generate_patch_in_temp","run_syntax_tests","run_unit_tests","require_explicit_go_before_apply"],"apply_automatically":False} for x in p["proposals"]]
        return self.save(DEV/"development_patch_plan_v28_0.json",{"engine":NAME,"version":VER,"patches":patches,"status":"PASS"})

    def regression(self):
        tests=[{"capability_id":x["capability_id"],"test_type":x["test_type"],"required":True,"status":"PLANNED"} for x in self.registry["capabilities"]]
        return self.save(DEV/"development_regression_plan_v28_0.json",{"engine":NAME,"version":VER,"tests":tests,"automatic_source_changes":False,"status":"PASS"})

    def summary(self):
        a=self.analyze(); p=self.propose(); r=self.regression()
        return self.save(OUT/"development_summary_v28_0.json",{"engine":NAME,"version":VER,"missing_required_count":a["missing_required_count"],"proposal_count":len(p["proposals"]),"regression_test_count":len(r["tests"]),"safe_to_apply_without_go":False,"status":"PASS"})

    def read(self,p): return json.loads(p.read_text(encoding="utf-8-sig"))
    def save(self,p,d):
        p.parent.mkdir(parents=True,exist_ok=True)
        d["generated_at"]=datetime.now().isoformat(timespec="seconds")
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        d["output_path"]=str(p); return d

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("cmd",choices=["self-test","analyze","propose","patch-plan","regression-plan","summary"]); a=ap.parse_args()
    e=Engine()
    r={"self-test":e.self_test,"analyze":e.analyze,"propose":e.propose,"patch-plan":e.patch_plan,"regression-plan":e.regression,"summary":e.summary}[a.cmd]()
    print(json.dumps(r,ensure_ascii=True,indent=2))
    if r.get("status")!="PASS": raise SystemExit(1)
if __name__=="__main__": main()
