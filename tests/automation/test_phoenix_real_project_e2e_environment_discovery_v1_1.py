
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "phoenix/validation/real_project_e2e_environment_discovery.py"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_real_project_e2e_environment_discovery_v1_1.ps1"

class E2ERuntimeDiscoveryTests(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(DISCOVERY.exists())
        self.assertTrue(RUNNER.exists())

    def test_no_npx_fetch_side_effect(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn('["npx"', source)
        self.assertIn("network_fetch_attempted", source)

    def test_calculix_versioned_binary_supported(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("ccx_*.exe", source)

    def test_bounded_windows_search(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("ProgramFiles", source)
        self.assertIn("LOCALAPPDATA", source)
        self.assertNotIn("Path(r\"C:\\\").rglob", source)

    def test_real_project_roots_not_silently_selected(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("selection_required", source)
        self.assertIn("moskee_bunschoten.json", source)
        self.assertIn("plutostraat.json", source)
        self.assertIn("bruynzeel_waterfront.json", source)

    def test_release_stays_locked(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"production": "LOCKED"', source)
        self.assertIn('"for_construction": "LOCKED"', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
