import json,tempfile,unittest
from pathlib import Path
from phoenix.adapters.cost_carbon_optimization_adapter import run_cost_carbon_optimization
from phoenix.cost_carbon import CostCarbonContext,CostCarbonEngine,CostCarbonError,LifecycleProfile,VariantInput
class Wave153Tests(unittest.TestCase):
    def test_lowest(self):
        r=CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(analysis_years=10),variants=(VariantInput('A',100,500),VariantInput('B',120,300)))
        self.assertEqual(r['lowest_lifecycle_cost_variant_id'],'A'); self.assertEqual(r['lowest_lifecycle_carbon_variant_id'],'B')
    def test_maintenance(self):
        r=CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(analysis_years=2,discount_rate=0,annual_maintenance_fraction=.1),variants=(VariantInput('A',100,10),)); self.assertEqual(r['variants'][0]['lifecycle_cost'],120)
    def test_replacement(self):
        r=CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(analysis_years=5,discount_rate=0,annual_maintenance_fraction=0,replacement_interval_years=2,replacement_cost_fraction=.5,replacement_carbon_fraction=.25),variants=(VariantInput('A',100,40),)); self.assertEqual(r['variants'][0]['replacement_cost_npv'],100); self.assertEqual(r['variants'][0]['replacement_carbon_kgco2e'],20)
    def test_salvage(self):
        r=CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(analysis_years=1,discount_rate=0,annual_maintenance_fraction=0),variants=(VariantInput('A',100,10,salvage_value_fraction=.2),)); self.assertEqual(r['variants'][0]['lifecycle_cost'],80)
    def test_duplicate(self):
        with self.assertRaises(CostCarbonError): CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(),variants=(VariantInput('A',1,1),VariantInput('A',2,2)))
    def test_hash(self):
        r=CostCarbonEngine().evaluate(context=CostCarbonContext('PHX'),profile=LifecycleProfile(),variants=(VariantInput('A',1,1),)); self.assertEqual(len(r['evidence']['payload_sha256']),64)
    def test_adapter(self):
        req={'context':{'project_id':'PHX'},'profile':{'analysis_years':5},'variants':[{'variant_id':'A','initial_cost':100,'embodied_carbon_kgco2e':50}]}
        with tempfile.TemporaryDirectory() as f:
            p=Path(f)/'r.json'; r=run_cost_carbon_optimization(req,p); s=json.loads(p.read_text())
        self.assertEqual(r['variant_count'],1); self.assertEqual(s['adapter']['version'],'1.0.0')
    def test_atomic(self):
        with tempfile.TemporaryDirectory() as f:
            p=Path(f)/'r.json'; CostCarbonEngine().write_result(context=CostCarbonContext('PHX'),profile=LifecycleProfile(),variants=(VariantInput('A',1,1),),destination=p); self.assertTrue(p.exists()); self.assertFalse(p.with_suffix('.json.tmp').exists())
if __name__=='__main__': unittest.main()
