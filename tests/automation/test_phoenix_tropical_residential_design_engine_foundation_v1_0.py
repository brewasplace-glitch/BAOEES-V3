from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from phoenix.design.tropical_residential.engine import generate_variants,select_balanced
from phoenix.design.tropical_residential.adapters import detect_open_source_stack
from phoenix.design.tropical_residential.digital_twin import build_digital_twin_patch
from phoenix.design.tropical_residential.ifc_handoff import build_authoritative_ifc_contract
from phoenix.design.tropical_residential.output import write_package
ROOT=Path(__file__).resolve().parents[2]; FIX=ROOT/'tests/fixtures/phoenix_tropical_residential_demo_v1_0.json'
class TestTRDEFoundation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.project=json.loads(FIX.read_text(encoding='utf-8')); cls.vars=generate_variants(cls.project); cls.sel=select_balanced(cls.vars)
 def test_five_variants(self): self.assertEqual([v.variant_id for v in self.vars],list('ABCDE'))
 def test_strategies(self): self.assertEqual({v.strategy for v in self.vars},{'PASSIVE_COOLING','LOW_COST','RESILIENCE','INDOOR_OUTDOOR','BALANCED'})
 def test_tropical_features(self):
  for v in self.vars: self.assertIn('cross_ventilation_layout',v.features); self.assertIn('external_shading',v.features)
 def test_flood_response(self):
  for v in self.vars: self.assertGreaterEqual(v.raised_floor_m,0.5); self.assertIn('raised_floor_strategy',v.features)
 def test_no_release_claim(self):
  for v in self.vars: self.assertEqual(v.release_status,'CONCEPT_ONLY_NOT_FOR_CONSTRUCTION')
 def test_oss_contract(self):
  s=detect_open_source_stack()
  for k in ('ifcopenshell','freecad','shapely','networkx','pymoo','energyplus','blender'): self.assertIn(k,s)
 def test_dt_governance(self):
  vs=[v.to_dict() for v in self.vars]; d=build_digital_twin_patch(self.project,vs,self.sel.variant_id); self.assertEqual(d['governance']['production'],'LOCKED'); self.assertEqual(d['governance']['for_construction'],'LOCKED')
 def test_ifc_contract(self):
  c=build_authoritative_ifc_contract(self.project,self.sel.to_dict()); self.assertEqual(c['contract'],'PHOENIX_AUTHORITATIVE_IFC_HANDOFF_v1'); self.assertEqual(c['release_status'],'CONCEPT_ONLY_NOT_FOR_CONSTRUCTION')
 def test_outputs(self):
  vs=[v.to_dict() for v in self.vars]; s=detect_open_source_stack(); d=build_digital_twin_patch(self.project,vs,self.sel.variant_id); c=build_authoritative_ifc_contract(self.project,self.sel.to_dict())
  with tempfile.TemporaryDirectory() as td:
   summary=write_package(td,self.project,vs,self.sel.to_dict(),s,d,c); self.assertEqual(summary['variant_count'],5); self.assertEqual(len(list((Path(td)/'variants').glob('*.svg'))),5)
if __name__=='__main__': unittest.main(verbosity=2)
