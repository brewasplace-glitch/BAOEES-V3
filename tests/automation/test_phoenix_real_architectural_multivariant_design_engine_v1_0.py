import json,tempfile,unittest
from pathlib import Path
from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design

class T(unittest.TestCase):
 def ws(self,root):
  w=root/'projects/runtime/PHOENIX-PAT-TEST';a=w/'results/session_adapters/architecture';a.mkdir(parents=True)
  (a/'architectural_model.json').write_text(json.dumps({'project_id':'PHOENIX-PAT-TEST','description':'Vrijstaande woning van twee bouwlagen'}))
  (a/'architectural_session_intake.json').write_text(json.dumps({'project_id':'PHOENIX-PAT-TEST','prompt':'Ontwerp een vrijstaande woning van twee bouwlagen'}))
  (a/'project_context.json').write_text(json.dumps({'project_id':'PHOENIX-PAT-TEST','parcel_width':28.0,'parcel_depth':42.0}))
  (a/'site_context.json').write_text('{}')
  for p in (w/'results/session_adapters/digital_twin/central_project_digital_twin.json',w/'digital_twin/central_project_digital_twin.json'):
   p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'project_id':'PHOENIX-PAT-TEST'}))
  return w

 def test_three_variants(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);x=run_multivariant_design(r,w)
   self.assertEqual(x['status'],'PASSED')
   self.assertEqual(x['variant_count'],3)
   self.assertEqual(x['selected_variant'],'B')
   ids={v['id'] for v in x['variants']}
   self.assertEqual(ids,{'A','B','C'})

 def test_real_drawings(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);run_multivariant_design(r,w);a=w/'results/session_adapters/architecture/drawings'
   for n in ('floor_plan_ground.svg','floor_plan_upper.svg','section_AA.svg','site_plan.svg'):
    p=a/n
    self.assertTrue(p.exists(),n)
    t=p.read_text(encoding='utf-8')
    self.assertIn('<svg',t,n)
    self.assertIn('</svg>',t,n)
    self.assertGreater(len(t),350,n)
   g=(a/'floor_plan_ground.svg').read_text(encoding='utf-8')
   u=(a/'floor_plan_upper.svg').read_text(encoding='utf-8')
   s=(a/'site_plan.svg').read_text(encoding='utf-8')
   sec=(a/'section_AA.svg').read_text(encoding='utf-8')
   self.assertIn('Woonkamer',g)
   self.assertIn('Keuken',g)
   self.assertIn('Slaapkamer 1',u)
   self.assertIn('Badkamer',u)
   self.assertIn('WONING VARIANT B',s)
   self.assertIn('DOORSNEDE A-A',sec)
   self.assertGreaterEqual(g.count('<rect'),7)
   self.assertGreaterEqual(u.count('<rect'),7)

 def test_real_viewer(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);run_multivariant_design(r,w)
   p=w/'results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html'
   t=p.read_text(encoding='utf-8')
   self.assertIn('VARIANT B',t)
   self.assertIn('W=11.5',t)
   self.assertIn('2 bouwlagen',t)
   self.assertIn('<canvas',t)
   self.assertIn('requestAnimationFrame',t)
   self.assertIn('const W=11.5,D=9.5,H=6.4',t)
   self.assertIn('V=[[-W/2,0,-D/2]',t)
   self.assertIn('E=[[0,1],[1,2],[2,3],[3,0]',t)
   self.assertIn('onpointermove',t)
   self.assertIn('onwheel',t)

 def test_twin_selected_variant(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);run_multivariant_design(r,w)
   m=json.loads((w/'results/session_adapters/architecture/architectural_model.json').read_text())
   self.assertEqual(m['architectural_model_source'],'REAL_MULTI_VARIANT_PARAMETRIC_DESIGN')
   self.assertEqual(m['selected_variant'],'B')
   self.assertEqual(m['variant_count'],3)
   self.assertIn('rooms',m)
   t=json.loads((w/'digital_twin/central_project_digital_twin.json').read_text())
   self.assertEqual(t['architectural_design']['selected_variant'],'B')
   self.assertEqual(len(t['architectural_design']['available_variants']),3)

 def test_release_locked(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);w=self.ws(r);run_multivariant_design(r,w)
   s=json.loads((w/'results/session_adapters/architecture/selected_design_variant.json').read_text())
   self.assertTrue(s['candidate_only'])
   self.assertTrue(s['professional_review_required'])
   self.assertEqual(s['production_release'],'LOCKED')

if __name__=='__main__': unittest.main()
