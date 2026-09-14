import unittest
from phoenix.startscreen_regression_fix import repair_r9

class TestUtf8RuntimeLabelFixR9(unittest.TestCase):
    def test_exact_r8_nested_building_residual(self):
        bad="\u00f0\u00c5\u00b8\u008f\u00a2"
        fixed,repls=repair_r9.repair_known_nested_utf8_residuals(bad)
        self.assertEqual(fixed,"&#x1F3E2;")
        self.assertEqual(len(repls),1)
        self.assertEqual(repls[0]["utf8_bytes"],"F0 9F 8F A2")

    def test_tag_bounded_navicon_policy_preserved(self):
        source='<span class="navicon">Ôù┼Æ</span>Simulaties'
        generic=repair_r9.fix_mojibake(source)
        fixed,repls=repair_r9.repair_navicons(generic)
        self.assertIn("</span>Simulaties",fixed)
        self.assertEqual(repair_r9.suspicious_count(repair_r9.visible_text(fixed)),0)

    def test_prev_policy_preserved(self):
        source='<button id="phoenixTvPrev">ÔùÔé¼ VORIGE</button>'
        fixed,repls=repair_r9.repair_prev_button(source)
        self.assertIn("&#x2190; VORIGE",fixed)

    def test_runtime_guard_stays_separate(self):
        self.assertNotEqual(repair_r9.GUARD_REL,repair_r9.BRIDGE_REL)

if __name__=="__main__":
    unittest.main()
