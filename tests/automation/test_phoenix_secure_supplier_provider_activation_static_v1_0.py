from __future__ import annotations
import unittest
from pathlib import Path
class SecureSupplierProviderActivationStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo=Path(__file__).resolve().parents[2]
        cls.acq=(repo/'phoenix'/'autonomy'/'global_supplier_import_acquisition.py').read_text(encoding='utf-8')
        cls.reg=(repo/'configs'/'phoenix'/'global_supplier_discovery_provider_registry_v1_0.json').read_text(encoding='utf-8')
    def test_01_env_contract(self): self.assertIn('api_key_env',self.acq); self.assertIn('os.environ.get',self.acq)
    def test_02_brave_enabled_no_repo_secret(self): self.assertIn('BRAVE_WEB_SEARCH_API',self.reg); self.assertIn('"credential_repository_storage": false',self.reg.lower())
    def test_03_serper_fallback_disabled(self): self.assertIn('OPTIONAL_FALLBACK_DISABLED',self.reg)
if __name__=='__main__': unittest.main()
