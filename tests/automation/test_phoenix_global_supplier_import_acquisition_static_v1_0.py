import unittest
from pathlib import Path
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  r=Path(__file__).resolve().parents[2];cls.gms=(r/'phoenix/autonomy/global_material_sourcing.py').read_text();cls.a=(r/'phoenix/autonomy/global_supplier_import_acquisition.py').read_text();cls.reg=(r/'configs/phoenix/global_supplier_discovery_provider_registry_v1_0.json').read_text()
 def test_hook(self):self.assertIn('PHOENIX_GLOBAL_SUPPLIER_IMPORT_ACQUISITION_HOOK_v1_0',self.gms)
 def test_provider_keys(self):self.assertIn('PHOENIX_BRAVE_SEARCH_API_KEY',self.reg);self.assertIn('PHOENIX_SERPER_API_KEY',self.reg)
 def test_safety(self):self.assertIn('"automatic_ordering":False',self.a.replace(' ',''));self.assertIn('"customs_rate_fabrication":False',self.a.replace(' ',''))
if __name__=='__main__':unittest.main()
