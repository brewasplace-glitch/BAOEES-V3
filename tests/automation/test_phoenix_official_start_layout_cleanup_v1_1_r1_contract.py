from __future__ import annotations

import unittest
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = project_root()
HTML = ROOT / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "index.html"
LEGACY = ROOT / "tests" / "automation" / "test_phoenix_official_start_de_tv_v1_0.py"


class LayoutCleanupR1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML.read_text(encoding="utf-8")
        cls.legacy = LEGACY.read_text(encoding="utf-8")

    def test_01_obsolete_fixed_left_expectation_is_gone(self) -> None:
        self.assertNotIn('self.assertIn("left:238px;right:auto", self.html)', self.legacy)

    def test_02_legacy_test_now_requires_in_flow_target(self) -> None:
        self.assertIn('id="phoenixProjectTypeActions"', self.legacy)
        self.assertIn("projecttype-inline-toolbar", self.legacy)
        self.assertIn("target.appendChild(bar)", self.legacy)

    def test_03_html_has_no_fixed_old_toolbar(self) -> None:
        self.assertNotIn("position:fixed;top:82px;left:238px", self.html)

    def test_04_html_places_actions_before_civiel_infra(self) -> None:
        action = self.html.index('id="phoenixProjectTypeActions"')
        self.assertLess(action, self.html.index('class="typecard type-civiel"'))
        self.assertLess(action, self.html.index('class="typecard type-infra"'))

    def test_05_modules_remain_collapsed_at_bottom(self) -> None:
        self.assertIn('<details class="panel phoenix-modules-collapsible"', self.html)
        self.assertIn("<summary>PHOENIX MODULES</summary>", self.html)
        self.assertGreater(
            self.html.index('<details class="panel phoenix-modules-collapsible"'),
            self.html.index('id="projectList"'),
        )


if __name__ == "__main__":
    unittest.main()
