from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
START=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"
J=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js").read_text(encoding="utf-8")
C=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css").read_text(encoding="utf-8")

class Phoenix4619R32LiveUIEnforcement(unittest.TestCase):
    def test_01_live_enforcement_marker(self):
        self.assertIn("PHOENIX_4_6_19_R3_2_LIVE_UI_ENFORCEMENT",J)
        self.assertIn('liveEnforcement:"4.6.19-r3.2"',J)
    def test_02_output_level_reclosed(self):
        self.assertIn("r32EnsureOutputLevelClosed",J)
        self.assertIn("r32UserOpenedOutputLevel",J)
        self.assertIn("panel.hidden=true",J)
    def test_03_stale_session_rehidden(self):
        self.assertIn("r32HideStaleSessionIfNeeded",J)
        self.assertIn("PHOENIX-PAT-003",J)
        self.assertIn("Generic Sessieadapters",J)
        self.assertIn("92%",J)
    def test_04_new_project_detection(self):
        self.assertIn("nieuw / geen bestaand project gekozen",J.lower())
        self.assertIn("geen bestaand project",J.lower())
    def test_05_real_start_reenables_progress(self):
        self.assertIn("r32ProjectRunStarted=true",J)
        self.assertIn("n.hidden=false",J)
    def test_06_mutation_observer_enforces(self):
        self.assertIn("new MutationObserver(r32ScheduleEnforce)",J)
        self.assertIn("window.setInterval(r32Enforce,1500)",J)
    def test_07_r3_contracts_preserved(self):
        self.assertIn('version:"4.6.19-r3"',J)
        self.assertIn('revision:"4.6.19-r3.1"',J)
    def test_08_r1_contracts_preserved(self):
        self.assertIn("button.hidden = true",J)
        self.assertIn("drawer.hidden = !managementOpen",J)
    def test_09_css_enforcement_present(self):
        self.assertIn("PHOENIX 4.6.19 R3.2 LIVE UI ENFORCEMENT",C)

if __name__=="__main__":
    unittest.main()