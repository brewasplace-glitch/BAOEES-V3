from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from phoenix.autonomy.global_supplier_import_acquisition import build_request_register,acquire_global_supplier_import_evidence

class EuropeanSupplierDiscoveryQueryPriorityR1Tests(unittest.TestCase):
    def setUp(self):
        self.root=Path(tempfile.mkdtemp(prefix='phx_eu_query_r1_'));self.ws=self.root/'projects'/'runtime'/'P1';self.ws.mkdir(parents=True)
        cfg=self.root/'configs'/'phoenix';cfg.mkdir(parents=True)
        (cfg/'global_supplier_discovery_import_acquisition_policy_v1_0.json').write_text(json.dumps({'https_timeout_seconds':1,'https_max_bytes':100000}),encoding='utf-8')
        self.ctx={'facts':{'country_code':'SR','municipality':'Paramaribo','project_location':'Paramaribo, Suriname','currency':'SRD'}}
        self.local={'selections':[{'requirement_id':'REQ-REBAR','material_family':'reinforcement_steel','element_role':'reinforcement','engineering_qualification_status':'NOT_QUALIFIED','selected_product':None}]}
    def test_01_queries_are_nl_be_eu_global(self):
        row=build_request_register('P1',self.ctx,self.local)['requests'][0];self.assertEqual(['NL','BE','EU27','GLOBAL'],row['discovery_priority']);q=row['queries'];self.assertIn('Netherlands',q[0]);self.assertIn('Belgium',q[1]);self.assertIn('European Union',q[2])
    def test_02_candidate_catalog_persistence_works(self):
        cfg=self.root/'configs'/'phoenix';(cfg/'global_supplier_discovery_provider_registry_v1_0.json').write_text(json.dumps({'providers':[{'provider_id':'TEST_EU','category':'SUPPLIER_CATALOG','enabled':True,'method':'GET','url_template':'https://example.test/catalog?q={query}','response_mode':'PRODUCT_ROWS'}]}),encoding='utf-8')
        fake={'products':[{'product_id':'REB-EU-1','supplier_name':'EU Test Supplier','material_family':'reinforcement_steel','availability_status':'AVAILABLE_TO_ORDER','country_code':'NL','unit_price':100,'currency':'EUR'}]}
        with patch('phoenix.autonomy.global_supplier_import_acquisition._fetch',return_value=(fake,'application/json')):
            result=acquire_global_supplier_import_evidence(repository=self.root,workspace=self.ws,project_id='P1',project_context=self.ctx,local_selection_register=self.local,manifest={})
        self.assertTrue(result.written_catalogs);self.assertTrue(any((self.ws/'sources'/'global_material_supply'/'acquired').glob('GLOBAL_IMPORT_DISCOVERY_*.json')))
    def test_03_safety_contract_still_locked(self):
        cfg=self.root/'configs'/'phoenix';(cfg/'global_supplier_discovery_provider_registry_v1_0.json').write_text(json.dumps({'providers':[]}),encoding='utf-8')
        result=acquire_global_supplier_import_evidence(repository=self.root,workspace=self.ws,project_id='P1',project_context=self.ctx,local_selection_register=self.local,manifest={});self.assertFalse(result.register['automatic_ordering']);self.assertFalse(result.register['automatic_payment']);self.assertEqual('LOCKED',result.register['production_release'])
if __name__=='__main__':unittest.main()
