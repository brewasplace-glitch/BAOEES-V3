from __future__ import annotations
import copy
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.structural.reinforced_concrete_beam import (
    ReinforcedConcreteBeamDesignEngine,
    ReinforcedConcreteBeamDesignExporter,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "configs/structural/reinforced_concrete_beam_example_v1_0_0.json").read_text(encoding="utf-8"))


class ReinforcedConcreteBeamDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = ReinforcedConcreteBeamDesignEngine().evaluate(CONFIG)

    def test_status_passed(self): self.assertEqual("PRELIMINARY_DESIGN_CHECKS_PASSED", self.result["status"])
    def test_beam_id(self): self.assertEqual("RCB-001", self.result["beam_id"])
    def test_span(self): self.assertEqual(5.0, self.result["geometry"]["span_m"])
    def test_section_width(self): self.assertEqual(300.0, self.result["geometry"]["width_mm"])
    def test_section_height(self): self.assertEqual(500.0, self.result["geometry"]["height_mm"])
    def test_self_weight(self): self.assertAlmostEqual(3.75, self.result["loads"]["self_weight_kn_m"], places=3)
    def test_reactions_equal(self): self.assertAlmostEqual(self.result["analysis"]["uls_reaction_a_kn"], self.result["analysis"]["uls_reaction_b_kn"], places=3)
    def test_reaction_value(self): self.assertAlmostEqual(92.156, self.result["analysis"]["uls_reaction_a_kn"], places=3)
    def test_moment_value(self): self.assertAlmostEqual(133.945, self.result["analysis"]["uls_max_moment_knm"], places=3)
    def test_shear_value(self): self.assertAlmostEqual(92.156, self.result["analysis"]["uls_max_abs_shear_kn"], places=3)
    def test_bottom_bar_selection(self): self.assertEqual("4T16 bottom (As=804 mm2; clear=50 mm)", self.result["detailing"]["bottom_reinforcement"])
    def test_stirrup_selection(self): self.assertEqual("2-leg T8 stirrups @ 175 mm", self.result["detailing"]["stirrups"])
    def test_flexure_utilization(self): self.assertLess(self.result["flexure"]["utilization"], 1.0)
    def test_shear_utilization(self): self.assertLess(self.result["shear"]["utilization"], 1.0)
    def test_deflection(self): self.assertAlmostEqual(8.311, self.result["serviceability"]["estimated_deflection_mm"], places=3)
    def test_deflection_passes(self): self.assertLess(self.result["serviceability"]["deflection_utilization"], 1.0)
    def test_crack_width(self): self.assertAlmostEqual(0.134, self.result["serviceability"]["estimated_crack_width_mm"], places=3)
    def test_crack_width_passes(self): self.assertLess(self.result["serviceability"]["crack_width_utilization"], 1.0)
    def test_anchorage_passes(self): self.assertLess(self.result["detailing"]["anchorage_utilization"], 1.0)
    def test_thirteen_technical_checks(self): self.assertEqual(13, self.result["metrics"]["technical_check_count"])
    def test_all_technical_checks_pass(self): self.assertEqual(13, self.result["metrics"]["technical_checks_passed"])
    def test_professional_review_required(self): self.assertTrue(self.result["metrics"]["professional_review_required"])
    def test_final_release_blocked(self): self.assertFalse(self.result["metrics"]["final_structural_release_allowed"])
    def test_standard_profile(self): self.assertIn("NA_A2_2025", self.result["standard_profile"]["profile_id"])
    def test_station_count(self): self.assertGreaterEqual(self.result["analysis"]["station_count"], 101)
    def test_invalid_point_load_rejected(self):
        bad = copy.deepcopy(CONFIG); bad["loads"]["point_loads"][0]["position_m"] = 7.0
        with self.assertRaises(ValueError): ReinforcedConcreteBeamDesignEngine().evaluate(bad)
    def test_negative_span_rejected(self):
        bad = copy.deepcopy(CONFIG); bad["beam"]["span_m"] = -1.0
        with self.assertRaises(ValueError): ReinforcedConcreteBeamDesignEngine().evaluate(bad)
    def test_deeper_beam_has_lower_deflection(self):
        deep = copy.deepcopy(CONFIG); deep["beam"]["height_mm"] = 600
        result = ReinforcedConcreteBeamDesignEngine().evaluate(deep)
        self.assertLess(result["serviceability"]["estimated_deflection_mm"], self.result["serviceability"]["estimated_deflection_mm"])
    def test_larger_load_increases_moment(self):
        heavy = copy.deepcopy(CONFIG); heavy["loads"]["variable_udl_kn_m"] = 15
        result = ReinforcedConcreteBeamDesignEngine().evaluate(heavy)
        self.assertGreater(result["analysis"]["uls_max_moment_knm"], self.result["analysis"]["uls_max_moment_knm"])
    def test_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ReinforcedConcreteBeamDesignExporter(self.result).export_all(tmp)
            self.assertEqual(18, len(paths))
            self.assertEqual(18, sum(1 for p in Path(tmp).rglob("*") if p.is_file()))
    def test_export_is_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ReinforcedConcreteBeamDesignExporter(self.result).export_all(a)
            ReinforcedConcreteBeamDesignExporter(self.result).export_all(b)
            ar, br = Path(a), Path(b)
            names = sorted(p.relative_to(ar).as_posix() for p in ar.rglob("*") if p.is_file())
            self.assertEqual(names, sorted(p.relative_to(br).as_posix() for p in br.rglob("*") if p.is_file()))
            self.assertTrue(all((ar/n).read_bytes() == (br/n).read_bytes() for n in names))
    def test_issue_zip_is_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ReinforcedConcreteBeamDesignExporter(self.result).export_all(tmp)
            with zipfile.ZipFile(paths["issue_package"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(info.date_time == (2020,1,1,0,0,0) for info in infos))
    def test_xlsx_contains_formulas(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ReinforcedConcreteBeamDesignExporter(self.result).export_all(tmp)
            with zipfile.ZipFile(paths["workbook"]) as archive:
                xml = archive.read("xl/worksheets/sheet4.xml").decode("utf-8")
            self.assertIn("<f>", xml)
    def test_docx_is_valid_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ReinforcedConcreteBeamDesignExporter(self.result).export_all(tmp)
            with zipfile.ZipFile(paths["report_docx"]) as archive:
                self.assertIn("word/document.xml", archive.namelist())
    def test_pdf_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ReinforcedConcreteBeamDesignExporter(self.result).export_all(tmp)
            self.assertTrue(paths["report_pdf"].read_bytes().startswith(b"%PDF-1.4"))


if __name__ == "__main__": unittest.main()
