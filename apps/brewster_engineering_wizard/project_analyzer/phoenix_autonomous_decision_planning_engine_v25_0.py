from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path
from typing import Any,Dict,List

ENGINE_NAME="Phoenix Autonomous Decision & Planning Engine"
ENGINE_VERSION="v25.0"

def root()->Path:
    p=Path.cwd().resolve()
    for c in [p,*p.parents]:
        if (c/".git").exists(): return c
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT=root()
POLICY=ROOT/"configs/phoenix/autonomous_decision_policy_v25_0.json"
REGISTRY=ROOT/"configs/phoenix/decision_strategy_registry_v25_0.json"
MEMORY=ROOT/"outputs/memory/v24_0/project-phoenix_memory_snapshot_v24_0.json"
LESSONS=ROOT/"outputs/memory/v24_0/project-phoenix_lessons_learned_v24_0.json"
OUT=ROOT/"outputs/runtime/v25_0"
DECISIONS=ROOT/"outputs/decisions/v25_0"

class DecisionPlanning:
    def __init__(self):
        self.policy=self.read(POLICY)
        self.registry=self.read(REGISTRY)

    def self_test(self)->Dict[str,Any]:
        checks={
            "policy_exists":POLICY.exists(),
            "registry_exists":REGISTRY.exists(),
            "memory_exists":MEMORY.exists(),
            "lessons_exists":LESSONS.exists(),
            "python_supported":sys.version_info>=(3,10)
        }
        return self.save_runtime("decision_planning_self_test_v25_0.json",{
            "engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "checks":checks,"status":"PASS" if all(checks.values()) else "FAIL"
        })

    def analyze(self,objective:str)->Dict[str,Any]:
        memory=self.read(MEMORY)
        statuses=memory.get("status_counts",{})
        passed=statuses.get("PASS",0)
        blocked=sum(v for k,v in statuses.items() if str(k).startswith("BLOCKED"))
        failed=sum(v for k,v in statuses.items() if k in {"FAIL","FAILED","FAILED_REQUIRED_TASK","FAILED_REQUIRED_AGENT"})
        risk=min(100,blocked*self.policy["blocked_weight"]+failed*self.policy["failure_weight"])
        confidence=min(100,passed*self.policy["pass_confidence_weight"])
        return self.save_runtime("decision_analysis_v25_0.json",{
            "engine":ENGINE_NAME,"version":ENGINE_VERSION,"objective":objective,
            "metrics":{"pass_count":passed,"blocked_count":blocked,"failure_count":failed,
                       "risk_score":risk,"confidence_score":confidence},
            "project_fingerprint":memory.get("fingerprint"),"status":"PASS"
        })

    def decide(self,objective:str)->Dict[str,Any]:
        analysis=self.analyze(objective)
        m=analysis["metrics"]
        candidates=[]
        for strategy in self.registry["strategies"]:
            score=strategy["base_score"]
            if m["risk_score"]>=self.policy["high_risk_threshold"]:
                score += 30 if strategy["strategy_id"]=="stabilize_first" else 0
                score -= 20 if strategy["strategy_id"]=="accelerate_build" else 0
            if m["confidence_score"]>=self.policy["high_confidence_threshold"]:
                score += 20 if strategy["strategy_id"]=="accelerate_build" else 0
            candidates.append({
                "strategy_id":strategy["strategy_id"],
                "title":strategy["title"],
                "description":strategy["description"],
                "score":score,
                "requires_go":True
            })
        candidates.sort(key=lambda x:x["score"],reverse=True)
        return self.save_decision("decision_record_v25_0.json",{
            "engine":ENGINE_NAME,"version":ENGINE_VERSION,"objective":objective,
            "analysis":analysis,"candidates":candidates,
            "selected_strategy":candidates[0],
            "mode":"PROPOSAL_ONLY","automatic_execution":False,
            "automatic_source_changes":False,"status":"PASS"
        })

    def plan(self,objective:str)->Dict[str,Any]:
        decision=self.decide(objective)
        selected=decision["selected_strategy"]["strategy_id"]
        strategy=next(s for s in self.registry["strategies"] if s["strategy_id"]==selected)
        steps=[]
        for i,step in enumerate(strategy["steps"],1):
            steps.append({
                "sequence":i,
                "step_id":step["step_id"],
                "description":step["description"],
                "requires_go":step.get("requires_go",True),
                "status":"PLANNED"
            })
        return self.save_decision("decision_plan_v25_0.json",{
            "engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "objective":objective,"strategy_id":selected,
            "steps":steps,"mode":"DRY_RUN",
            "automatic_execution":False,"status":"PASS"
        })

    def next_step(self,objective:str)->Dict[str,Any]:
        plan=self.plan(objective)
        return self.save_runtime("decision_next_step_v25_0.json",{
            "engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "objective":objective,
            "recommended_next_step":plan["steps"][0] if plan["steps"] else None,
            "safe_to_execute_without_go":False,"status":"PASS"
        })

    def read(self,path:Path)->Dict[str,Any]:
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def save_runtime(self,name:str,data:Dict[str,Any])->Dict[str,Any]:
        OUT.mkdir(parents=True,exist_ok=True)
        data["generated_at"]=datetime.now().isoformat(timespec="seconds")
        path=OUT/name
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        data["output_path"]=str(path)
        return data

    def save_decision(self,name:str,data:Dict[str,Any])->Dict[str,Any]:
        DECISIONS.mkdir(parents=True,exist_ok=True)
        data["generated_at"]=datetime.now().isoformat(timespec="seconds")
        path=DECISIONS/name
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        data["output_path"]=str(path)
        return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["self-test","analyze","decide","plan","next-step"])
    parser.add_argument("--objective",default="Continue building Project Phoenix safely and autonomously.")
    args=parser.parse_args()
    engine=DecisionPlanning()
    if args.command=="self-test": result=engine.self_test()
    elif args.command=="analyze": result=engine.analyze(args.objective)
    elif args.command=="decide": result=engine.decide(args.objective)
    elif args.command=="plan": result=engine.plan(args.objective)
    else: result=engine.next_step(args.objective)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    if result.get("status")!="PASS": raise SystemExit(1)

if __name__=="__main__": main()
