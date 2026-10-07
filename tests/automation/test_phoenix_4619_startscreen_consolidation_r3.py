from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
START=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"
J=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js").read_text(encoding="utf-8")
C=(START/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css").read_text(encoding="utf-8")

class Phoenix4619StartscreenConsolidationR3(unittest.TestCase):
    def test_01_runtime_version_visual_fix(self):
        self.assertIn('replace("START v4.41","START v4.6.19")',J)

    def test_02_tv_header_compact(self):
        self.assertIn("r3CompactTvTitle",J)
        self.assertIn("white-space:nowrap!important",C)

    def test_03_engineering_controls_move_to_management(self):
        self.assertIn("r3MoveEngineeringControlsToManagement",J)
        self.assertIn('data-phoenix-management-only',J)

    def test_04_output_level_collapsed(self):
        self.assertIn("r3CollapseOutputLevel",J)
        self.assertIn("phoenix-r3-advanced-hidden",C)

    def test_05_autonomous_flow_duplicate_hidden(self):
        self.assertIn("r3HideAutonomousFlowDuplicate",J)
        self.assertIn("AUTONOME PHOENIX-FLOW",J)

    def test_06_duplicate_results_hidden(self):
        self.assertIn("r3RemoveDuplicateResultsButton",J)
        self.assertIn("phoenix-r3-duplicate-results",C)

    def test_07_output_list_collapsed(self):
        self.assertIn("r3CollapseDesiredOutputs",J)
        self.assertIn("UITVOERLIJST TONEN",J)
        self.assertIn("phoenix-r3-output-collapsed",C)

    def test_08_stale_session_suppressed(self):
        self.assertIn("r3SuppressStaleSession",J)
        self.assertIn("PHOENIX-PAT-003",J)

    def test_09_r1_compatibility_strings_preserved(self):
        self.assertIn("button.hidden = true",J)
        self.assertIn("drawer.hidden = !managementOpen",J)

    def test_10_r3_version_marker(self):
        self.assertIn('version:"4.6.19-r3"',J)

if __name__=="__main__":
    unittest.main()