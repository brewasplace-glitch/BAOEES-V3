from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_start_capability_registry_v1_0.js"

class TestPhoenixOfficialStartVisualStability(unittest.TestCase):
    def setUp(self):
        self.source = JS.read_text(encoding="utf-8")

    def test_no_fast_full_rerender_interval(self):
        self.assertNotIn("setInterval(refresh,3000)", self.source)
        self.assertNotIn("setInterval(refresh, 3000)", self.source)
        self.assertIn("STATUS_POLL_MS = 6000", self.source)

    def test_status_diffing_prevents_unchanged_dom_rebuilds(self):
        self.assertIn("lastCapabilityKey", self.source)
        self.assertIn("lastProjectKey", self.source)
        self.assertIn("lastJobKey", self.source)
        self.assertIn("if (nextKey === lastProjectKey) return;", self.source)
        self.assertIn("if (nextKey === lastCapabilityKey) return;", self.source)
        self.assertIn("if (key === lastJobKey) return;", self.source)

    def test_polling_pauses_when_tab_is_hidden(self):
        self.assertIn("document.hidden", self.source)
        self.assertIn('document.addEventListener("visibilitychange"', self.source)
        self.assertIn("window.clearTimeout(refreshTimer)", self.source)

    def test_no_mutation_observer_or_external_frontend_dependency(self):
        self.assertNotIn("MutationObserver", self.source)
        self.assertNotIn("https://", self.source)

    def test_control_no_longer_overlaps_top_status_strip(self):
        compact = self.source.replace(" ", "")
        self.assertIn("bottom:18px", compact)
        self.assertIn("top:auto", compact)
        self.assertIn("flex-direction:column-reverse", compact)

    def test_legacy_architectural_project_source_contract_remains(self):
        self.assertIn("status.architectural_orchestration?.projects", self.source)

    def test_existing_security_and_api_contract_remain(self):
        self.assertIn('"X-Phoenix-Token":TOKEN', self.source)
        self.assertIn('api("/api/status")', self.source)
        self.assertIn("status.architectural_orchestration", self.source)
        self.assertIn("status.start_capabilities", self.source)
        self.assertIn("START A–E PROJECTFLOW", self.source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
