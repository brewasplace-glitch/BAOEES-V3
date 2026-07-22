"""Adapter for Phoenix Wave 15.4."""
from pathlib import Path
from phoenix.decision_intelligence import Criterion, DecisionContext, DecisionIntelligenceEngine, VariantDecisionInput
ADAPTER_ID="phoenix.adapter.decision_intelligence.wave15_4"
ADAPTER_VERSION="1.0.0"
def run_decision_intelligence(request, output_path=None):
    c=request['context']; context=DecisionContext(str(c['project_id']),float(c.get('sensitivity_delta',0.10)))
    criteria=tuple(Criterion(str(x['criterion_id']),float(x['weight']),str(x['direction'])) for x in request['criteria'])
    variants=tuple(VariantDecisionInput(str(x['variant_id']),{str(k):float(v) for k,v in x['metrics'].items()},dict(x.get('attributes',{}))) for x in request['variants'])
    result=DecisionIntelligenceEngine().evaluate(context=context,criteria=criteria,variants=variants); result['adapter']={'id':ADAPTER_ID,'version':ADAPTER_VERSION}
    if output_path is not None:
        import json
        p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    return result
