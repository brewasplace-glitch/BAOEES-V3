"""Deterministic MCDA ranking for Project Phoenix Wave 15.4."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json, math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
ENGINE_ID="phoenix.variant_ranking_decision_intelligence.wave15_4"
ENGINE_VERSION="1.0.0"
SCHEMA_VERSION="1.0"
class DecisionIntelligenceError(ValueError): pass
@dataclass(frozen=True)
class Criterion:
    criterion_id:str; weight:float; direction:str
    def validate(self):
        if not self.criterion_id.strip(): raise DecisionIntelligenceError("criterion_id must not be empty.")
        if not math.isfinite(self.weight) or self.weight<=0: raise DecisionIntelligenceError("criterion weight must be positive.")
        if self.direction not in {"min","max"}: raise DecisionIntelligenceError("criterion direction must be min or max.")
@dataclass(frozen=True)
class VariantDecisionInput:
    variant_id:str; metrics:Mapping[str,float]; attributes:Mapping[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.variant_id.strip(): raise DecisionIntelligenceError("variant_id must not be empty.")
        if not self.metrics: raise DecisionIntelligenceError("metrics must not be empty.")
        for k,v in self.metrics.items():
            if not str(k).strip(): raise DecisionIntelligenceError("metric name must not be empty.")
            if not math.isfinite(float(v)): raise DecisionIntelligenceError(f"metric {k} must be finite.")
@dataclass(frozen=True)
class DecisionContext:
    project_id:str; sensitivity_delta:float=0.10
    def validate(self):
        if not self.project_id.strip(): raise DecisionIntelligenceError("project_id must not be empty.")
        if not math.isfinite(self.sensitivity_delta) or not 0<self.sensitivity_delta<1: raise DecisionIntelligenceError("sensitivity_delta must be between 0 and 1.")
class DecisionIntelligenceEngine:
    @staticmethod
    def _canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
    @classmethod
    def _digest(cls,v): return sha256(cls._canonical_json(v).encode()).hexdigest()
    @staticmethod
    def _weights(criteria):
        total=sum(c.weight for c in criteria); return {c.criterion_id:c.weight/total for c in criteria}
    @staticmethod
    def _norm(v,lo,hi,direction):
        if hi==lo: return 1.0
        return (v-lo)/(hi-lo) if direction=="max" else (hi-v)/(hi-lo)
    @staticmethod
    def _pareto(rows, criteria):
        front=set()
        for c in rows:
            dominated=False
            for h in rows:
                if c['variant_id']==h['variant_id']: continue
                no_worse=True; better=False
                for crit in criteria:
                    a=c['raw_metrics'][crit.criterion_id]; b=h['raw_metrics'][crit.criterion_id]
                    if crit.direction=='max':
                        if b<a: no_worse=False; break
                        if b>a: better=True
                    else:
                        if b>a: no_worse=False; break
                        if b<a: better=True
                if no_worse and better: dominated=True; break
            if not dominated: front.add(c['variant_id'])
        return front
    def _rank_once(self,criteria,variants,weights):
        ranges={}
        for c in criteria:
            vals=[float(v.metrics[c.criterion_id]) for v in variants]; ranges[c.criterion_id]=(min(vals),max(vals))
        normalized={}
        for v in variants:
            normalized[v.variant_id]={c.criterion_id:self._norm(float(v.metrics[c.criterion_id]),*ranges[c.criterion_id],c.direction) for c in criteria}
        weighted={v.variant_id:{cid:normalized[v.variant_id][cid]*weights[cid] for cid in weights} for v in variants}
        best={cid:max(weighted[v.variant_id][cid] for v in variants) for cid in weights}
        worst={cid:min(weighted[v.variant_id][cid] for v in variants) for cid in weights}
        rows=[]; eps=1e-12
        for v in variants:
            vid=v.variant_id
            wsm=sum(weights[cid]*normalized[vid][cid] for cid in weights)
            wpm=math.prod(max(normalized[vid][cid],eps)**weights[cid] for cid in weights)
            db=math.sqrt(sum((weighted[vid][cid]-best[cid])**2 for cid in weights)); dw=math.sqrt(sum((weighted[vid][cid]-worst[cid])**2 for cid in weights))
            topsis=1.0 if db+dw==0 else dw/(db+dw); consensus=(wsm+wpm+topsis)/3
            rows.append({'variant_id':vid,'raw_metrics':{cid:float(v.metrics[cid]) for cid in weights},'normalized_metrics':{cid:round(normalized[vid][cid],9) for cid in weights},'scores':{'weighted_sum':round(wsm,9),'weighted_product':round(wpm,9),'topsis':round(topsis,9),'consensus':round(consensus,9)},'attributes':dict(v.attributes)})
        rows.sort(key=lambda x:(-x['scores']['consensus'],x['variant_id']))
        for i,row in enumerate(rows,1): row['rank']=i
        return rows
    def evaluate(self,*,context,criteria,variants):
        context.validate(); criteria=sorted(list(criteria),key=lambda x:x.criterion_id); variants=sorted(list(variants),key=lambda x:x.variant_id)
        if not criteria or not variants: raise DecisionIntelligenceError("At least one criterion and one variant are required.")
        cids=set()
        for c in criteria:
            c.validate()
            if c.criterion_id in cids: raise DecisionIntelligenceError(f"Duplicate criterion_id: {c.criterion_id}")
            cids.add(c.criterion_id)
        vids=set()
        for v in variants:
            v.validate()
            if v.variant_id in vids: raise DecisionIntelligenceError(f"Duplicate variant_id: {v.variant_id}")
            vids.add(v.variant_id); missing=cids-set(v.metrics)
            if missing: raise DecisionIntelligenceError(f"Variant {v.variant_id} missing metrics: {sorted(missing)}")
        weights=self._weights(criteria); ranking=self._rank_once(criteria,variants,weights); pareto=self._pareto(ranking,criteria)
        for row in ranking: row['pareto_optimal']=row['variant_id'] in pareto
        winners={}
        for c in criteria:
            modified=dict(weights); modified[c.criterion_id]*=1+context.sensitivity_delta; total=sum(modified.values()); modified={k:v/total for k,v in modified.items()}
            winners[c.criterion_id]=self._rank_once(criteria,variants,modified)[0]['variant_id']
        rec=ranking[0]['variant_id']; stability=sum(1 for x in winners.values() if x==rec)/len(winners)
        result={'schema_version':SCHEMA_VERSION,'engine':{'id':ENGINE_ID,'version':ENGINE_VERSION},'project_id':context.project_id,'criteria':[{**asdict(c),'normalized_weight':round(weights[c.criterion_id],9)} for c in criteria],'variant_count':len(ranking),'ranking':ranking,'recommended_variant_id':rec,'alternative_variant_ids':[r['variant_id'] for r in ranking[1:4]],'pareto_front_variant_ids':sorted(pareto),'sensitivity':{'delta':context.sensitivity_delta,'winner_by_increased_criterion_weight':winners,'recommendation_stability':round(stability,9),'confidence_score':round(stability,9)},'decision_contract':{'upstream_engines':['phoenix.optimization_core.wave15_1','phoenix.multi_material_design.wave15_2','phoenix.cost_carbon_optimization.wave15_3'],'downstream_engine':'phoenix.autonomous_decision_engine.wave15_5'},'limitations':['Results depend on supplied criteria, weights and metrics.','Decision-support only; qualified multidisciplinary review required.']}
        result['evidence']={'algorithm':'sha256','payload_sha256':self._digest(result)}
        return result
    def write_result(self,*,context,criteria,variants,destination):
        result=self.evaluate(context=context,criteria=criteria,variants=variants); path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n'); tmp.replace(path); return path
