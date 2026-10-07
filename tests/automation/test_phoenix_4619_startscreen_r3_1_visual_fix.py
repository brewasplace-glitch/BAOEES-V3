from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
START=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"
J=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js").read_text(encoding="utf-8")
C=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css").read_text(encoding="utf-8")

class Phoenix4619R31VisualFix(unittest.TestCase):
    def test_01_output_level_forced_closed(self):
        self.assertIn('panel.hidden=true',J)
        self.assertIn('panel.setAttribute("aria-hidden","true")',J)
        self.assertIn('#phoenixR3OutputLevelToggle',C)

    def test_02_new_project_text_is_recognized(self):
        self.assertIn("nieuw / geen bestaand project gekozen",J.lower())
        self.assertIn("geen bestaand project",J.lower())

    def test_03_stale_pat_session_hidden(self):
        self.assertIn("PHOENIX-PAT-003",J)
        self.assertIn('n.hidden=true',J)
        self.assertIn("phoenix-r3-session-hidden",C)

    def test_04_start_restores_progress(self):
        self.assertIn('n.hidden=false',J)
        self.assertIn('phxR31SessionBound',J)

    def test_05_r31_version_marker(self):
        self.assertIn('version:"4.6.19-r3"',J); self.assertIn('revision:"4.6.19-r3.1"',J)

    def test_06_r1_compatibility_preserved(self):
        self.assertIn("button.hidden = true",J)
        self.assertIn("drawer.hidden = !managementOpen",J)

if __name__=="__main__":
    unittest.main()