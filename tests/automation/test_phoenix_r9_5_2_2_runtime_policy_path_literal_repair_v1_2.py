from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAIN = ROOT / "phoenix" / "autonomy" / "structural_session_chain.py"

BAD = 'repository/"configs"/"phoenix"/"structural"/stability_ab_project_policy_r9_5_2_2.json'
GOOD = 'repository/"configs"/"phoenix"/"structural"/"stability_ab_project_policy_r9_5_2_2.json"'
PRE_MARKER = "PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_PRE_R9_5_V1_1"
POST_MARKER = "PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_POST_R9_5_2_V1_1"


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CHAIN.read_text(encoding="utf-8")

    def test_01_chain_exists(self):
        self.assertTrue(CHAIN.is_file())

    def test_02_bad_unquoted_path_absent(self):
        self.assertNotIn(BAD, self.text)

    def test_03_good_quoted_path_count_two(self):
        self.assertEqual(2, self.text.count(GOOD))

    def test_04_pre_hook_preserved(self):
        self.assertEqual(1, self.text.count(PRE_MARKER))

    def test_05_post_hook_preserved(self):
        self.assertEqual(1, self.text.count(POST_MARKER))

    def test_06_chain_compiles(self):
        compile(self.text, str(CHAIN), "exec")

    def test_07_engine_import_preserved(self):
        self.assertIn("from .stability_ab_project_policy_integration_r9_5_2_2 import", self.text)

    def test_08_pre_hook_preserved(self):
        self.assertIn("_phoenix_apply_r9_5_2_2_ab_policy_to_workspace(", self.text)

    def test_09_post_hook_preserved(self):
        self.assertIn("_phoenix_apply_r9_5_2_2_ab_policy_to_r9_5_2_result(", self.text)

    def test_10_policy_filename_preserved(self):
        self.assertIn("stability_ab_project_policy_r9_5_2_2.json", self.text)


if __name__ == "__main__":
    unittest.main()
