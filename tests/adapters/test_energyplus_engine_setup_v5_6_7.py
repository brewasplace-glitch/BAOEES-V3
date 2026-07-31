from pathlib import Path
import json,unittest
R=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_config(self):
  c=json.loads((R/"configs/phoenix/energyplus_engine_setup_v5_6_0.json").read_text());self.assertEqual(c["version"],"26.1.0");self.assertFalse(c["simulated_results_allowed"])
 def test_acceptance(self):
  t=(R/"phoenix/adapters/open_source/energyplus_acceptance_v5_6_0.py").read_text();self.assertIn("1ZoneUncontrolled",t);self.assertIn("eplusout.sql",t)
if __name__=="__main__":unittest.main()


class X8664AssetSelectionTests(unittest.TestCase):
 def test_asset_selection_contract(self):
  c=json.loads((R/"configs/phoenix/energyplus_engine_setup_v5_6_0.json").read_text())
  s=c["asset_selection"]
  self.assertEqual(s["required_name_pattern"],"Windows-x86_64")
  self.assertEqual(s["forbidden_name_pattern"],"arm64")
  self.assertEqual(s["required_pe_machine"],"0x8664")

# v5.6.2 validates unattended Qt IFW license acceptance.

# v5.6.3 removes --accept-messages because it conflicts with --default-answer.

# v5.6.4 validates controlled UAC elevation and loop protection.

# v5.6.5 reuses existing EnergyPlus and forbids install/UAC.


class MultiplePyLauncherResultsTests(unittest.TestCase):
 def test_python_resolution_contract(self):
  c=json.loads((R/"configs/phoenix/energyplus_engine_setup_v5_6_0.json").read_text())
  p=c["python_resolution"]
  self.assertTrue(p["get_command_all"])
  self.assertTrue(p["enumerate_results_individually"])
  self.assertTrue(p["exclude_windowsapps"])

# v5.6.7 injects Output:SQLite, SimpleAndTabular before simulation.
