from __future__ import annotations
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json, math
from pathlib import Path
from typing import Any, Iterable, Mapping
ENGINE_ID='phoenix.autonomous_decision_engine.wave15_5'; ENGINE_VERSION='1.0.0'; SCHEMA_VERSION='1.0'
class AutonomousDecisionError(ValueError): pass
@dataclass(frozen=True)
class ConstraintRule:
    rule_id:str; metric:str; operator:str; threshold:float; severity:str='hard'; description:str=''
    def validate(self):
        if not self.rule_id.strip() or not self.metric.strip(): raise AutonomousDecisionError('rule_id and metric must not be empty.')
        if self.operator not in {'<=','>=','<','>','=='}: raise AutonomousDecisionError(f'Unsupported operator: {self.operator}')
        if self.severity not in {'hard','review'}: raise AutonomousDecisionError('severity must be hard or review.')
        if not math.isfinite(self.threshold): raise AutonomousDecisionError('threshold must be finite.')
@dataclass(frozen=True)
class DecisionVariant:
    variant_id:str; rank:int; confidence_score:float; metrics:Mapping[str,float]; risk_scores:Mapping[str,float]=field(default_factory=dict); assumptions:tuple[str,...]=(); attributes:Mapping[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.variant_id.strip(): raise AutonomousDecisionError('variant_id must not be empty.')
        if self.rank<=0: raise AutonomousDecisionError('rank must be positive.')
        if not math.isfinite(self.confidence_score) or not 0<=self.confidence_score<=1: raise AutonomousDecisionError('confidence_score must be between 0 and 1.')
        for n,v in self.metrics.items():
            if not n.strip() or not math.isfinite(float(v)): raise AutonomousDecisionError(f'Invalid metric: {n}')
        for n,v in self.risk_scores.items():
            if not n.strip() or not math.isfinite(float(v)) or not 0<=float(v)<=1: raise AutonomousDecisionError(f'Invalid risk score: {n}')
@dataclass(frozen=True)
class AutonomousDecisionContext:
    project_id:str; auto_approve_min_confidence:float=.85; review_min_confidence:float=.60; max_auto_approve_risk:float=.30; human_approval_required:bool=True
    def validate(self):
        if not self.project_id.strip(): raise AutonomousDecisionError('project_id must not be empty.')
        for n,v in {'auto_approve_min_confidence':self.auto_approve_min_confidence,'review_min_confidence':self.review_min_confidence,'max_auto_approve_risk':self.max_auto_approve_risk}.items():
            if not math.isfinite(v) or not 0<=v<=1: raise AutonomousDecisionError(f'{n} must be between 0 and 1.')
        if self.review_min_confidence>self.auto_approve_min_confidence: raise AutonomousDecisionError('review_min_confidence must not exceed auto_approve_min_confidence.')
class AutonomousDecisionEngine:
    @staticmethod
    def _canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    @classmethod
    def _digest(cls,v): return sha256(cls._canonical_json(v).encode()).hexdigest()
    @staticmethod
    def _rule_passes(v,o,t): return {'<=':v<=t,'>=':v>=t,'<':v<t,'>':v>t,'==':v==t}[o]
    def decide(self,*,context,variants,constraints):
        context.validate(); vs=sorted(list(variants),key=lambda x:(x.rank,x.variant_id)); rs=sorted(list(constraints),key=lambda x:x.rule_id)
        if not vs: raise AutonomousDecisionError('At least one variant is required.')
        seen=set()
        for v in vs:
            v.validate()
            if v.variant_id in seen: raise AutonomousDecisionError(f'Duplicate variant_id: {v.variant_id}')
            seen.add(v.variant_id)
        seen=set()
        for r in rs:
            r.validate()
            if r.rule_id in seen: raise AutonomousDecisionError(f'Duplicate rule_id: {r.rule_id}')
            seen.add(r.rule_id)
        evaluated=[]
        for v in vs:
            hard=[]; review=[]; passed=[]
            for r in rs:
                if r.metric not in v.metrics:
                    f={'rule_id':r.rule_id,'metric':r.metric,'reason':'missing_metric','severity':r.severity}; (hard if r.severity=='hard' else review).append(f); continue
                value=float(v.metrics[r.metric])
                if self._rule_passes(value,r.operator,r.threshold): passed.append(r.rule_id)
                else:
                    f={'rule_id':r.rule_id,'metric':r.metric,'value':value,'operator':r.operator,'threshold':r.threshold,'severity':r.severity,'reason':'constraint_failed'}; (hard if r.severity=='hard' else review).append(f)
            maxrisk=max((float(x) for x in v.risk_scores.values()),default=0.0); meanrisk=sum(map(float,v.risk_scores.values()))/len(v.risk_scores) if v.risk_scores else 0.0
            if hard: status='blocked'
            elif v.confidence_score>=context.auto_approve_min_confidence and maxrisk<=context.max_auto_approve_risk and not review and not v.assumptions: status='auto_approved'
            elif v.confidence_score>=context.review_min_confidence: status='review_required'
            else: status='blocked'
            evaluated.append({'variant_id':v.variant_id,'rank':v.rank,'status':status,'confidence_score':round(v.confidence_score,9),'max_risk_score':round(maxrisk,9),'mean_risk_score':round(meanrisk,9),'hard_failures':hard,'review_failures':review,'passed_rules':passed,'assumptions':list(v.assumptions),'metrics':{k:float(x) for k,x in sorted(v.metrics.items())},'risk_scores':{k:float(x) for k,x in sorted(v.risk_scores.items())},'attributes':dict(v.attributes)})
        eligible=[x for x in evaluated if x['status']!='blocked']; selected=min(eligible,key=lambda x:(x['rank'],x['variant_id'])) if eligible else None
        status=selected['status'] if selected else 'blocked'; sid=selected['variant_id'] if selected else None
        payload={'schema_version':SCHEMA_VERSION,'engine':{'id':ENGINE_ID,'version':ENGINE_VERSION},'project_id':context.project_id,'context':asdict(context),'selected_variant_id':sid,'decision_status':status,'approval_gate':{'human_approval_required':context.human_approval_required,'machine_status':status,'final_release_status':'awaiting_human_approval' if context.human_approval_required and status!='blocked' else status},'explanation':f'Selected {sid} as highest-ranked non-blocked variant.' if sid else 'No variant passed the policy.','evaluated_variants':evaluated,'audit_trail':{'variant_order':[x['variant_id'] for x in evaluated],'constraint_order':[x.rule_id for x in rs],'selection_policy':'highest-ranked non-blocked variant'},'integration_contract':{'upstream_engines':['phoenix.optimization_core.wave15_1','phoenix.multi_material_design.wave15_2','phoenix.cost_carbon_optimization.wave15_3','phoenix.variant_ranking_decision_intelligence.wave15_4'],'downstream_engine':'phoenix.autonomous_design_orchestrator.wave15_6'},'limitations':['Only explicit supplied constraints are enforced.','No certification is claimed.','Human approval remains enabled by default.']}
        payload['evidence']={'algorithm':'sha256','payload_sha256':self._digest(payload)}; return payload
    def write_result(self,*,context,variants,constraints,destination):
        p=Path(destination); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(self.decide(context=context,variants=variants,constraints=constraints),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n'); t.replace(p); return p
