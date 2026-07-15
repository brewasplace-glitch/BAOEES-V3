from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path
from typing import Any,Dict,List,Set

ENGINE_NAME="Phoenix Knowledge Graph & Reasoning Engine"
ENGINE_VERSION="v18.0"

def root()->Path:
    p=Path.cwd().resolve()
    for c in [p,*p.parents]:
        if (c/".git").exists():return c
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT=root()
POLICY=ROOT/"configs/phoenix/knowledge_reasoning_policy_v18_0.json"
RUNTIME_REGISTRY=ROOT/"configs/phoenix/ai_runtime_registry_v13_0.json"
OUT=ROOT/"outputs/runtime/v18_0"

class KnowledgeReasoning:
    def __init__(self):
        self.policy=self.read(POLICY)

    def self_test(self)->Dict[str,Any]:
        checks={
            "policy_exists":POLICY.exists(),
            "runtime_registry_exists":RUNTIME_REGISTRY.exists(),
            "apps_exists":(ROOT/"apps").exists(),
            "configs_exists":(ROOT/"configs").exists(),
            "python_supported":sys.version_info>=(3,10)
        }
        return self.save("self_test",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "checks":checks,"status":"PASS" if all(checks.values()) else "FAIL"})

    def build(self)->Dict[str,Any]:
        nodes=[];edges=[]
        for base,node_type,pattern in [
            (ROOT/"apps","module","*.py"),
            (ROOT/"configs","config","*.json"),
            (ROOT/"docs","documentation","*.md")
        ]:
            if not base.exists():continue
            for path in sorted(base.rglob(pattern)):
                rel=path.relative_to(ROOT).as_posix()
                nodes.append({"id":f"{node_type}:{rel}","type":node_type,"name":path.name,"path":rel})

        registry=self.read(RUNTIME_REGISTRY)
        engines={e["engine_id"]:e for e in registry.get("engines",[])}
        for engine_id,entry in engines.items():
            nodes.append({"id":f"engine:{engine_id}","type":"engine","name":engine_id,"path":entry.get("module","")})
            for dep in entry.get("dependencies",[]):
                edges.append({"source":f"engine:{engine_id}","target":f"engine:{dep}","relation":"depends_on"})

        graph={"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "generated_at":datetime.now().isoformat(timespec="seconds"),
            "nodes":nodes,"edges":edges,"node_count":len(nodes),"edge_count":len(edges),"status":"PASS"}
        return self.save("knowledge_graph",graph)

    def validate_dependencies(self)->Dict[str,Any]:
        registry=self.read(RUNTIME_REGISTRY)
        engines={e["engine_id"]:e for e in registry.get("engines",[])}
        errors=[];visiting:Set[str]=set();visited:Set[str]=set()

        for engine_id,entry in engines.items():
            module=ROOT/entry.get("module","")
            if not module.is_file():errors.append(f"Module ontbreekt voor {engine_id}: {entry.get('module','')}")
            for dep in entry.get("dependencies",[]):
                if dep not in engines:errors.append(f"Dependency ontbreekt: {dep} voor {engine_id}")

        def visit(i:str):
            if i in visited:return
            if i in visiting:raise RuntimeError(f"Circulaire dependency bij {i}")
            visiting.add(i)
            for dep in engines[i].get("dependencies",[]):
                if dep in engines:visit(dep)
            visiting.remove(i);visited.add(i)

        try:
            for engine_id in engines:visit(engine_id)
        except RuntimeError as exc:
            errors.append(str(exc))

        return self.save("dependency_graph",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "engine_count":len(engines),"errors":errors,"status":"PASS" if not errors else "FAIL"})

    def reason(self)->Dict[str,Any]:
        graph=self.build()
        deps=self.validate_dependencies()
        findings=[];recommendations=[]

        modules=sum(1 for n in graph["nodes"] if n["type"]=="module")
        configs=sum(1 for n in graph["nodes"] if n["type"]=="config")
        docs=sum(1 for n in graph["nodes"] if n["type"]=="documentation")

        if deps["errors"]:
            for error in deps["errors"]:
                findings.append({"category":"DEPENDENCY","severity":"HIGH","message":error})

        if configs<modules:
            findings.append({"category":"METADATA","severity":"MEDIUM",
                "message":"Niet alle modules lijken expliciet door configuratie te worden beschreven."})
            recommendations.append("Breid capability- en configuratiemetadata gecontroleerd uit.")

        if docs==0:
            findings.append({"category":"DOCUMENTATION","severity":"MEDIUM","message":"Geen documentatieknooppunten gevonden."})

        if not findings:
            recommendations.append("Knowledge Graph en dependencystructuur zijn consistent als v18-baseline.")

        result={"engine":ENGINE_NAME,"version":ENGINE_VERSION,"mode":"DRY_RUN",
            "metrics":{"modules":modules,"configs":configs,"documentation":docs,
                       "nodes":graph["node_count"],"edges":graph["edge_count"]},
            "findings":findings,"recommendations":recommendations,
            "automatic_source_changes":False,"automatic_commit_push":False,
            "status":"ATTENTION_REQUIRED" if any(x["severity"]=="HIGH" for x in findings) else "PASS"}
        return self.save("reasoning_report",result)

    def query(self,node_type:str)->Dict[str,Any]:
        graph_path=OUT/"knowledge_graph_v18_0.json"
        graph=self.read(graph_path) if graph_path.exists() else self.build()
        matches=[n for n in graph["nodes"] if n["type"]==node_type]
        return self.save("query",{"engine":ENGINE_NAME,"version":ENGINE_VERSION,
            "query":{"node_type":node_type},"matches":matches,"count":len(matches),"status":"PASS"})

    def read(self,p:Path)->Dict[str,Any]:
        return json.loads(p.read_text(encoding="utf-8-sig"))

    def save(self,name:str,data:Dict[str,Any])->Dict[str,Any]:
        OUT.mkdir(parents=True,exist_ok=True)
        data["generated_at"]=datetime.now().isoformat(timespec="seconds")
        path=OUT/f"{name}_v18_0.json"
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        data["output_path"]=str(path)
        return data

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("self-test");sub.add_parser("build");sub.add_parser("validate");sub.add_parser("reason")
    q=sub.add_parser("query");q.add_argument("--node-type",choices=["module","config","documentation","engine"],required=True)
    a=p.parse_args();engine=KnowledgeReasoning()
    if a.cmd=="self-test":r=engine.self_test()
    elif a.cmd=="build":r=engine.build()
    elif a.cmd=="validate":r=engine.validate_dependencies()
    elif a.cmd=="reason":r=engine.reason()
    else:r=engine.query(a.node_type)
    print(json.dumps(r,ensure_ascii=True,indent=2))
    if r.get("status")=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
