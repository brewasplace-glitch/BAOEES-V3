from __future__ import annotations

import json
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
POLICY = ROOT / "configs" / "phoenix" / "official_start_layout_cleanup_policy_v1_1.json"


class OfficialStartLayoutCleanupV11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML.read_text(encoding="utf-8")
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8-sig"))

    def test_01_toolbar_has_in_flow_target(self) -> None:
        self.assertIn('id="phoenixProjectTypeActions"', self.html)
        self.assertIn("target.appendChild(bar)", self.html)

    def test_02_toolbar_is_not_fixed(self) -> None:
        self.assertNotIn("position:fixed;top:82px;left:238px", self.html)
        self.assertIn("projecttype-inline-toolbar", self.html)
        self.assertIn("position:static!important", self.html)

    def test_03_toolbar_sits_before_civiel_and_infra(self) -> None:
        action = self.html.index('id="phoenixProjectTypeActions"')
        civiel = self.html.index('class="typecard type-civiel"')
        infra = self.html.index('class="typecard type-infra"')
        self.assertLess(action, civiel)
        self.assertLess(action, infra)

    def test_04_toolbar_spans_second_and_third_project_columns(self) -> None:
        self.assertIn(".projecttype-actions-slot{grid-column:2/4;", self.html)

    def test_05_no_overlap_grid_uses_minmax_zero(self) -> None:
        self.assertIn(".types{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));", self.html)
        self.assertIn(".twocol{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));", self.html)
        self.assertIn(".outputgroups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));", self.html)

    def test_06_long_section_labels_wrap(self) -> None:
        self.assertIn(".sectionlabel>div:last-child", self.html)
        self.assertIn("overflow-wrap:anywhere", self.html)
        self.assertIn("width:auto;min-width:24px", self.html)

    def test_07_text_controls_do_not_overflow_parent(self) -> None:
        self.assertIn("textarea,select,input{max-width:100%}", self.html)
        self.assertIn(".twocol>*,.types>*,.modus>*,.outputgroups>*,.mainwrap>*,.sidepanel>*", self.html)

    def test_08_tv_controls_are_less_crowded(self) -> None:
        self.assertIn(".tvcontrols{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));", self.html)
        self.assertIn("white-space:normal;overflow-wrap:anywhere", self.html)

    def test_09_phoenix_modules_is_details_panel(self) -> None:
        self.assertIn('<details class="panel phoenix-modules-collapsible" id="phoenixModulesPanel">', self.html)
        self.assertIn("<summary>PHOENIX MODULES</summary>", self.html)

    def test_10_phoenix_modules_is_collapsed_by_default(self) -> None:
        start = self.html.index('<details class="panel phoenix-modules-collapsible"')
        tag_end = self.html.index(">", start)
        opening_tag = self.html[start:tag_end + 1]
        self.assertNotIn(" open", opening_tag)

    def test_11_phoenix_modules_is_below_projects(self) -> None:
        self.assertGreater(
            self.html.index('<details class="panel phoenix-modules-collapsible"'),
            self.html.index('id="projectList"'),
        )

    def test_12_module_grid_id_is_preserved(self) -> None:
        self.assertEqual(1, self.html.count('id="moduleGrid"'))

    def test_13_de_tv_controls_are_preserved(self) -> None:
        for marker in (
            'id="phoenixTvPanel"',
            'id="phoenixTvSelected"',
            'id="phoenixTvPrev"',
            'id="phoenixTvNext"',
            'id="phoenixTvPlay"',
            'id="phoenixTvFullscreen"',
            'id="phoenixTvCommand"',
            'id="phoenixTvMic"',
        ):
            self.assertIn(marker, self.html)

    def test_14_pdf_output_ui_remains_dynamic(self) -> None:
        self.assertIn("window.PHOENIX_DESIRED_OUTPUTS", self.html)
        self.assertIn('id="desiredOutputGroups"', self.html)

    def test_15_material_certification_logic_is_preserved(self) -> None:
        self.assertIn("PHOENIX_MATERIAL_CERTIFICATION_MODE", self.html)
        self.assertIn("phoenix-certified-materials", self.html)
        self.assertIn("phoenix-return-powershell", self.html)

    def test_16_policy_layout_version(self) -> None:
        self.assertEqual("1.1.1", self.policy["policy_version"])

    def test_17_legacy_versions_unchanged(self) -> None:
        compat = self.policy["compatibility"]
        self.assertEqual("1.8.7", compat["phoenix_local_app"])
        self.assertEqual("3.0.2", compat["official_start"])
        self.assertEqual("1.0.2", compat["de_tv"])
        self.assertFalse(compat["legacy_version_gates_modified"])

    def test_18_release_safety_unchanged(self) -> None:
        safety = self.policy["safety"]
        self.assertFalse(safety["professional_approval_changed"])
        self.assertFalse(safety["code_compliance_claim_changed"])
        self.assertEqual("LOCKED", safety["production_release"])
        self.assertEqual("LOCKED", safety["for_construction_release"])

    def test_19_no_live_solver_execution_during_install(self) -> None:
        self.assertFalse(self.policy["safety"]["live_solver_execution_during_install"])

    def test_20_collapsible_css_exists(self) -> None:
        self.assertIn(".phoenix-modules-collapsible>summary", self.html)
        self.assertIn(".phoenix-modules-collapsible[open]>summary::after", self.html)


if __name__ == "__main__":
    unittest.main()
