from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAIN = ROOT / "phoenix" / "autonomy" / "structural_session_chain.py"
GOOD = 'repository/"configs"/"phoenix"/"structural"/"stability_ab_project_policy_r9_5_2_2.json"'
JOINPATH = 'ab_policy_path=repository.joinpath("configs","phoenix","structural","stability_ab_project_policy_r9_5_2_2.json")'
PRE = "PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_PRE_R9_5_V1_1"
POST = "PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_POST_R9_5_2_V1_1"

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CHAIN.read_text(encoding="utf-8")

    def test_01_legacy_literal_count_two(self):
        self.assertEqual(2, self.text.count(GOOD))

    def test_02_pre_post_preserved(self):
        self.assertEqual(1, self.text.count(PRE))
        self.assertEqual(1, self.text.count(POST))

    def test_03_r9524_joinpath_present_once(self):
        self.assertEqual(1, self.text.count(JOINPATH))

    def test_04_chain_compiles(self):
        compile(self.text, str(CHAIN), "exec")

if __name__ == "__main__":
    unittest.main()
