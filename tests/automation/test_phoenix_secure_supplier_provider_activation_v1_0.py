from __future__ import annotations
import json, unittest
from pathlib import Path
class SecureSupplierProviderActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]
        cls.registry=json.loads((cls.repo/'configs'/'phoenix'/'global_supplier_discovery_provider_registry_v1_0.json').read_text(encoding='utf-8'))
    def provider(self,pid):
        return next(p for p in self.registry['providers'] if p.get('provider_id')==pid)
    def test_01_brave_enabled_primary(self):
        p=self.provider('BRAVE_WEB_SEARCH_API'); self.assertTrue(p['enabled']); self.assertEqual('PHOENIX_BRAVE_SEARCH_API_KEY',p['api_key_env']); self.assertEqual('BRAVE_WEB_SEARCH_API',self.registry['primary_supplier_discovery_provider'])
    def test_02_serper_disabled(self): self.assertFalse(self.provider('SERPER_GOOGLE_SEARCH_API')['enabled'])
    def test_03_secret_not_stored(self):
        p=self.provider('BRAVE_WEB_SEARCH_API'); self.assertFalse(p['credential_repository_storage']); self.assertFalse(p['credential_logging']); self.assertNotIn('api_key',p)
    def test_04_fail_safe_and_procurement(self):
        self.assertEqual('BLOCK_WHEN_PROVIDER_OR_CREDENTIAL_UNAVAILABLE',self.registry['supplier_discovery_fail_safe']); self.assertFalse(self.registry['automatic_ordering']); self.assertFalse(self.registry['automatic_payment'])
if __name__=='__main__': unittest.main()
