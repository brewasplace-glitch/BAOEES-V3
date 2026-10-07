from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
CSS=(ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_startscreen_consolidation_v4_6_19_r2.css").read_text(encoding="utf-8")

class Phoenix4619R33InfraIconContrast(unittest.TestCase):
    def test_marker(self):
        self.assertIn("PHOENIX 4.6.19 R3.3 INFRA ICON CONTRAST FIX",CSS)

    def test_infra_selector(self):
        self.assertIn(".typecard.type-infra .icon",CSS)

    def test_light_accent(self):
        self.assertIn("#FFD36A",CSS)

    def test_visibility(self):
        self.assertIn("opacity:1!important",CSS)
        self.assertIn("brightness(1.35)",CSS)

    def test_svg_support(self):
        self.assertIn(".typecard.type-infra .icon svg",CSS)

    def test_img_support(self):
        self.assertIn(".typecard.type-infra .icon img",CSS)

if __name__=="__main__":
    unittest.main()