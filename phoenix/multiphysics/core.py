from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Any, Callable
from uuid import uuid4
import hashlib, json

@dataclass
class AnalysisTask:
    engine: str
    operation: str
    input_data: dict[str, Any]=field(default_factory=dict)
    depends_on: list[str]=field(default_factory=list)
    task_id: str=field(default_factory=lambda:str(uuid4()))
    required: bool=True
    def validate(self):
        if not self.engine.strip() or not self.operation.strip():
            raise ValueError("engine and operation are required")
        if self.task_id in self.depends_on:
            raise ValueError("task cannot depend on itself")

@dataclass
class MultiPhysicsWorkflow:
    name: str
    workflow_id: str
    tasks: list[AnalysisTask]
    metadata: dict[str, Any]=field(default_factory=dict)
    def validate(self):
        if not self.name.strip() or not self.workflow_id.strip():
            raise ValueError("workflow identity is required")
        ids=[t.task_id for t in self.tasks]
        if len(ids)!=len(set(ids)): raise ValueError("duplicate task identifiers")
        known=set(ids)
        for t in self.tasks:
            t.validate()
            unknown=set(t.depends_on)-known
            if unknown: raise KeyError(f"unknown dependencies: {sorted(unknown)}")

@dataclass
class EngineDescriptor:
    name: str
    version: str
    capabilities: tuple[str,...]
    handler: Callable[[str,dict[str,Any],dict[str,Any]],dict[str,Any]]

class EngineRegistry:
    def __init__(self): self._items={}
    def register(self,name,handler,version="unknown",capabilities=(),replace=False):
        key=name.strip().lower()
        if not key: raise ValueError("engine name required")
        if key in self._items and not replace: raise KeyError(f"engine already registered: {name}")
        self._items[key]=EngineDescriptor(name,version,tuple(capabilities),handler)
    def get(self,name):
        key=name.strip().lower()
        if key not in self._items: raise KeyError(f"engine not registered: {name}")
        return self._items[key]
    def contains(self,name): return name.strip().lower() in self._items
    def snapshot(self):
        return {k:{"name":v.name,"version":v.version,"capabilities":list(v.capabilities)}
                for k,v in sorted(self._items.items())}

class ResultComparator:
    def __init__(self,relative_tolerance=0.05,absolute_tolerance=1e-9):
        if relative_tolerance<0 or absolute_tolerance<0: raise ValueError("invalid tolerance")
        self.relative_tolerance=relative_tolerance
        self.absolute_tolerance=absolute_tolerance
    def compare(self,label,left,right):
        absolute=abs(float(left)-float(right))
        relative=absolute/max(abs(float(left)),abs(float(right)),self.absolute_tolerance)
        return {"label":label,"left":float(left),"right":float(right),
                "absolute_difference":absolute,"relative_difference":relative,
                "passed":absolute<=self.absolute_tolerance or relative<=self.relative_tolerance}

class MultiPhysicsOrchestrator:
    def __init__(self,registry,comparator=None):
        self.registry=registry
        self.comparator=comparator or ResultComparator()
    def order(self,workflow):
        workflow.validate()
        tasks={t.task_id:t for t in workflow.tasks}
        remaining=set(tasks); done=set(); order=[]
        while remaining:
            ready=sorted(i for i in remaining if set(tasks[i].depends_on)<=done)
            if not ready: raise ValueError("workflow dependency cycle")
            for i in ready:
                order.append(i); done.add(i); remaining.remove(i)
        return order
    def execute(self,workflow):
        order=self.order(workflow)
        tasks={t.task_id:t for t in workflow.tasks}
        executions=[]; context={"results":{}}
        for task_id in order:
            task=tasks[task_id]
            try:
                desc=self.registry.get(task.engine)
                output=desc.handler(task.operation,dict(task.input_data),context)
                if not isinstance(output,dict): raise TypeError("engine output must be a dictionary")
                item={"task_id":task_id,"engine":desc.name,"operation":task.operation,
                      "success":True,"output":output,"version":desc.version}
            except Exception as exc:
                item={"task_id":task_id,"engine":task.engine,"operation":task.operation,
                      "success":False,"error":type(exc).__name__,"message":str(exc)}
                executions.append(item)
                if task.required:
                    return self._finish(workflow,order,executions,False)
            else:
                executions.append(item); context["results"][task_id]=item
        return self._finish(workflow,order,executions,True)
    def _finish(self,workflow,order,executions,base_success):
        successful=[e for e in executions if e["success"]]
        sources={}; comparisons=[]
        for e in successful:
            metrics=e.get("output",{}).get("metrics",{})
            if isinstance(metrics,dict):
                for key,value in metrics.items():
                    if isinstance(value,(int,float)):
                        sources.setdefault(key,[]).append((e["engine"],float(value)))
        fused={k:fmean(v for _,v in values) for k,values in sorted(sources.items())}
        for key,values in sorted(sources.items()):
            for i in range(len(values)):
                for j in range(i+1,len(values)):
                    result=self.comparator.compare(key,values[i][1],values[j][1])
                    result.update({"left_engine":values[i][0],"right_engine":values[j][0]})
                    comparisons.append(result)
        success=base_success and all(e["success"] for e in executions) and all(c["passed"] for c in comparisons)
        return {"workflow_id":workflow.workflow_id,"success":success,
                "execution_order":order,"executions":executions,
                "fusion":{"metrics":fused,"engine_count":len(successful),
                          "source_engines":[e["engine"] for e in successful]},
                "comparisons":comparisons,"registry":self.registry.snapshot()}
    @staticmethod
    def save_evidence(path,execution):
        data=json.dumps(execution,sort_keys=True,indent=2).encode()
        checksum=hashlib.sha256(data).hexdigest()
        payload=dict(execution); payload["checksum_sha256"]=checksum
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(payload,sort_keys=True,indent=2),encoding="utf-8",newline="\n")
        return checksum

def _adapter(domain,allowed,source):
    def run(operation,input_data,context):
        if operation not in allowed: raise ValueError(f"unsupported {domain} operation: {operation}")
        return {"domain":domain,"operation":operation,"metrics":input_data.get("metrics",{}),"source":source}
    return run

def register_default_adapters(registry):
    registry.register("QGIS",_adapter("gis",{"prepare_geometry","spatial_context"},"BB12"),
                      "BB12",("prepare_geometry","spatial_context"))
    registry.register("OpenSees",_adapter("structural",{"structural_analysis","verification"},"BB13"),
                      "BB13",("structural_analysis","verification"))
    registry.register("CalculiX",_adapter("fea",{"finite_element_analysis","verification"},"BB14"),
                      "BB14",("finite_element_analysis","verification"))
