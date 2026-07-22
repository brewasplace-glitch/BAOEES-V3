import json,tempfile,unittest
from pathlib import Path
from phoenix.adapters.autonomous_decision_adapter import run_autonomous_decision
from phoenix.autonomous_decision import *
class T(unittest.TestCase):
 def test_auto(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P',human_approval_required=False),variants=(DecisionVariant('A',1,.95,{'cost':100},{'technical':.1}),),constraints=(ConstraintRule('C','cost','<=',120),)); self.assertEqual(r['decision_status'],'auto_approved')
 def test_assumption_review(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.95,{},assumptions=('estimate',)),),constraints=()); self.assertEqual(r['decision_status'],'review_required')
 def test_hard_block(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.95,{'cost':150}),),constraints=(ConstraintRule('C','cost','<=',120),)); self.assertEqual(r['decision_status'],'blocked')
 def test_next_variant(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P',human_approval_required=False),variants=(DecisionVariant('A',1,.95,{'cost':150}),DecisionVariant('B',2,.95,{'cost':100})),constraints=(ConstraintRule('C','cost','<=',120),)); self.assertEqual(r['selected_variant_id'],'B')
 def test_missing_metric(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.95,{}),),constraints=(ConstraintRule('C','cost','<=',120),)); self.assertEqual(r['decision_status'],'blocked')
 def test_duplicate(self):
  with self.assertRaises(AutonomousDecisionError): AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.9,{}),DecisionVariant('A',2,.9,{})),constraints=())
 def test_hash(self):
  r=AutonomousDecisionEngine().decide(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.9,{}),),constraints=()); self.assertEqual(len(r['evidence']['payload_sha256']),64)
 def test_adapter(self):
  q={'context':{'project_id':'P'},'variants':[{'variant_id':'A','rank':1,'confidence_score':.9,'metrics':{'cost':100}}],'constraints':[{'rule_id':'C','metric':'cost','operator':'<=','threshold':120}]}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json'; r=run_autonomous_decision(q,p); self.assertEqual(r['selected_variant_id'],'A'); self.assertEqual(json.loads(p.read_text())['adapter']['version'],'1.0.0')
 def test_atomic(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json'; AutonomousDecisionEngine().write_result(context=AutonomousDecisionContext('P'),variants=(DecisionVariant('A',1,.9,{}),),constraints=(),destination=p); self.assertTrue(p.exists())
if __name__=='__main__': unittest.main()
