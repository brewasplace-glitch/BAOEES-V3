import json,tempfile,unittest
from pathlib import Path
from phoenix.adapters.decision_intelligence_adapter import run_decision_intelligence
from phoenix.decision_intelligence import Criterion,DecisionContext,DecisionIntelligenceEngine,DecisionIntelligenceError,VariantDecisionInput
def cs(): return (Criterion('cost',.5,'min'),Criterion('carbon',.3,'min'),Criterion('quality',.2,'max'))
def vs(): return (VariantDecisionInput('A',{'cost':100,'carbon':80,'quality':70}),VariantDecisionInput('B',{'cost':120,'carbon':50,'quality':90}),VariantDecisionInput('C',{'cost':160,'carbon':100,'quality':60}))
class Wave154Tests(unittest.TestCase):
 def test_ranking_generated(self):
  r=DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=cs(),variants=vs()); self.assertEqual(r['variant_count'],3); self.assertEqual(r['ranking'][0]['rank'],1)
 def test_dominated_variant_excluded(self):
  r=DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=cs(),variants=vs()); self.assertNotIn('C',r['pareto_front_variant_ids'])
 def test_scores_bounded(self):
  r=DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=cs(),variants=vs()); [self.assertTrue(0<=x['scores'][k]<=1) for x in r['ranking'] for k in ('weighted_sum','weighted_product','topsis','consensus')]
 def test_missing_metric_rejected(self):
  with self.assertRaisesRegex(DecisionIntelligenceError,'missing metrics'): DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=cs(),variants=(VariantDecisionInput('A',{'cost':1}),))
 def test_duplicate_variant_rejected(self):
  with self.assertRaisesRegex(DecisionIntelligenceError,'Duplicate variant_id'): DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=(Criterion('cost',1,'min'),),variants=(VariantDecisionInput('A',{'cost':1}),VariantDecisionInput('A',{'cost':2})))
 def test_evidence(self):
  r=DecisionIntelligenceEngine().evaluate(context=DecisionContext('PHX'),criteria=cs(),variants=vs()); self.assertEqual(len(r['evidence']['payload_sha256']),64)
 def test_adapter_writes(self):
  req={'context':{'project_id':'PHX'},'criteria':[{'criterion_id':'cost','weight':1,'direction':'min'}],'variants':[{'variant_id':'A','metrics':{'cost':10}},{'variant_id':'B','metrics':{'cost':20}}]}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json'; r=run_decision_intelligence(req,p); s=json.loads(p.read_text())
  self.assertEqual(r['recommended_variant_id'],'A'); self.assertEqual(s['adapter']['version'],'1.0.0')
 def test_atomic_write(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json'; DecisionIntelligenceEngine().write_result(context=DecisionContext('PHX'),criteria=(Criterion('cost',1,'min'),),variants=(VariantDecisionInput('A',{'cost':1}),),destination=p); self.assertTrue(p.exists()); self.assertFalse(p.with_suffix('.json.tmp').exists())
if __name__=='__main__': unittest.main()
