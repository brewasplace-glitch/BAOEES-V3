from __future__ import annotations
import unittest
from pathlib import Path
class EuropeanSupplierDiscoveryStaticR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo=Path(__file__).resolve().parents[2];cls.acq=(repo/'phoenix'/'autonomy'/'global_supplier_import_acquisition.py').read_text(encoding='utf-8')
    def test_01_query_hook_present(self):self.assertIn('european_discovery_queries',self.acq);self.assertIn('discovery_priority',self.acq)
    def test_02_repo_ref_defined(self):self.assertIn('def _repo_ref(',self.acq)
    def test_03_no_auto_ordering(self):self.assertIn('"automatic_ordering":False',self.acq);self.assertIn('"automatic_payment":False',self.acq)
if __name__=='__main__':unittest.main()
