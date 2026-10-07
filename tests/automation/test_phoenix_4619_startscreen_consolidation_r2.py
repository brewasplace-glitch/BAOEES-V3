from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
START=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"
H=(START/"index.html").read_text(encoding="utf-8-sig")
J=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js").read_text(encoding="utf-8")
C=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css").read_text(encoding="utf-8")
class T(unittest.TestCase):
 def test_version(self):
  self.assertIn("PROJECT PHOENIX 4.6.19",H);self.assertIn("Official Start v4.6.19",H)
 def test_one_tv(self): self.assertEqual(H.count('id="phoenixTvPanel"'),1)
 def test_nav(self):
  for x in ("digital_twin","ai_agents","simulations","documents","reports","asset_management","dashboard"): self.assertIn(f'data-module="{x}"',C)
 def test_user_nav(self):
  for x in ('data-module="new_project"','data-module="projects"','id="resultsNav"','id="phoenixManageNav"'): self.assertIn(x,H)
 def test_project_registry_hidden(self): self.assertIn("phoenix-r2-project-registry-hidden",J)
 def test_mode_hidden(self): self.assertIn("phoenix-r2-project-mode-hidden",J)
 def test_reorder(self): self.assertIn("center.insertBefore(row,uprow)",J)
 def test_flow(self):
  for x in ("Nieuw project","locatie","uploads","projectomschrijving","gewenste uitvoer","Start project"): self.assertIn(x,J)
 def test_manage(self):
  for x in ("phoenixModulesPanel","phoenixWorkflowsPanel","phoenix-start-capability-drawer","phoenix-management-open"): self.assertIn(x,J)
 def test_css(self): self.assertIn("PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css?v=1.0.0",H)
if __name__=="__main__": unittest.main()