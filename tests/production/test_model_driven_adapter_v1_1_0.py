from __future__ import annotations
import json,unittest
from pathlib import Path
from phoenix.production.model_driven_adapter import derive_production_config
ROOT=Path(__file__).resolve().parents[2]
class ModelDrivenAdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  base=json.loads((ROOT/'configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json').read_text(encoding='utf-8'));model=json.loads((ROOT/'artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/02_canonical_geometric_project_model.json').read_text(encoding='utf-8'));cls.model=model;cls.config=derive_production_config(base,model)
 def test_model_id(self):self.assertEqual(self.model['model_id'],self.config['model_provenance']['model_id'])
 def test_fingerprint(self):self.assertEqual(self.model['model_fingerprint_sha256'],self.config['model_provenance']['model_fingerprint_sha256'])
 def test_geometry_source(self):self.assertEqual('central_geometric_project_model_v1_0_0',self.config['model_provenance']['geometry_source'])
 def test_width(self):self.assertEqual(7.0,self.config['geometry']['extension_width_m'])
 def test_length(self):self.assertEqual(10.0,self.config['geometry']['extension_length_m'])
 def test_area(self):self.assertEqual(140.0,self.config['geometry']['gross_area_m2'])
 def test_storeys(self):self.assertEqual(2,self.config['geometry']['storeys'])
 def test_parking(self):self.assertEqual(225,self.config['parking']['confirmed_capacity_spaces'])
 def test_new_issue(self):self.assertEqual('HBM-CONCEPT-ISSUE-2026-002',self.config['issue_id'])
if __name__=='__main__':unittest.main()
