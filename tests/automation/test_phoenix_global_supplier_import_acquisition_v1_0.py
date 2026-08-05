import json,tempfile,unittest
from pathlib import Path
from phoenix.autonomy.global_supplier_import_acquisition import build_request_register,acquire_global_supplier_import_evidence
class T(unittest.TestCase):
 def setUp(self):
  self.r=Path(tempfile.mkdtemp());self.w=self.r/'projects/runtime/P1';(self.w/'sources').mkdir(parents=True);c=self.r/'configs/phoenix';c.mkdir(parents=True);(c/'global_supplier_discovery_provider_registry_v1_0.json').write_text('{"providers":[]}');self.ctx={'facts':{'country_code':'SR','municipality':'Paramaribo','currency':'SRD'}};self.local={'selections':[{'requirement_id':'R1','element_role':'reinforcement','material_family':'reinforcement_steel','engineering_qualification_status':'NOT_QUALIFIED','selected_product':None}]}
 def test_request(self):
  x=build_request_register('P1',self.ctx,self.local);self.assertEqual(1,x['request_count']);self.assertIn('Paramaribo',x['requests'][0]['queries'][0])
 def test_block_no_provider(self):
  x=acquire_global_supplier_import_evidence(repository=self.r,workspace=self.w,project_id='P1',project_context=self.ctx,local_selection_register=self.local,manifest={});self.assertEqual('BLOCKED',x.status);self.assertFalse(x.register['freight_fabrication']);self.assertFalse(x.register['customs_rate_fabrication'])
 def test_no_ordering(self):
  x=acquire_global_supplier_import_evidence(repository=self.r,workspace=self.w,project_id='P1',project_context=self.ctx,local_selection_register={'selections':[]},manifest={});self.assertFalse(x.register['automatic_ordering']);self.assertFalse(x.register['automatic_payment'])
if __name__=='__main__':unittest.main()
