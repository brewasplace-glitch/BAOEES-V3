from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "index.html"


class TestPhoenixOfficialStartUICleanupV12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8-sig")

    def test_de_tv_is_preserved(self):
        self.assertIn("<span>DE TV</span>", self.html)
        self.assertIn('id="phoenixTvPanel"', self.html)

    def test_modules_are_collapsible_and_closed_by_default(self):
        marker = '<details class="panel phoenix-modules-collapsible" id="phoenixModulesPanel">'
        self.assertIn(marker, self.html)
        self.assertNotIn(marker[:-1] + ' open>', self.html)
        self.assertIn("<summary>PHOENIX MODULES</summary>", self.html)

    def test_workflows_are_collapsible_and_closed_by_default(self):
        marker = '<details class="panel phoenix-modules-collapsible" id="phoenixWorkflowsPanel">'
        self.assertIn(marker, self.html)
        self.assertNotIn(marker[:-1] + ' open>', self.html)
        self.assertIn("<summary>BESCHIKBARE WORKFLOWS</summary>", self.html)
        self.assertIn('id="workflowList"', self.html)

    def test_workflows_are_after_modules_and_projects(self):
        pos_projects = self.html.index("<h2>Projecten</h2>")
        pos_modules = self.html.index('id="phoenixModulesPanel"')
        pos_workflows = self.html.index('id="phoenixWorkflowsPanel"')
        pos_aside_end = self.html.index("</aside>", pos_workflows)
        self.assertLess(pos_projects, pos_modules)
        self.assertLess(pos_modules, pos_workflows)
        self.assertLess(pos_workflows, pos_aside_end)

    def test_single_runtime_targets_preserved(self):
        self.assertEqual(self.html.count('id="workflowList"'), 1)
        self.assertEqual(self.html.count('id="moduleGrid"'), 1)
        self.assertEqual(self.html.count('id="phoenixTvPanel"'), 1)


if __name__ == "__main__":
    unittest.main()
