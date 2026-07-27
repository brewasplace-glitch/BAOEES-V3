from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.production.real_drawings_reports import RealConceptProductionEngine

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json").read_text(encoding="utf-8"))


class RealDrawingsReportsProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.result = RealConceptProductionEngine(CONFIG).produce(cls.root)
        cls.summary = cls.result["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_status(self):
        self.assertEqual("REAL_CONCEPT_DRAWINGS_AND_REPORTS_GENERATED", self.summary["status"])

    def test_ten_drawing_sheets(self):
        self.assertEqual(10, self.summary["drawing_sheet_count"])

    def test_eleven_drawing_pdfs(self):
        self.assertEqual(11, self.summary["drawing_pdf_count"])

    def test_ten_svg_drawings(self):
        self.assertEqual(10, self.summary["drawing_svg_count"])

    def test_five_dxf_drawings(self):
        self.assertEqual(5, self.summary["drawing_dxf_count"])

    def test_six_reports(self):
        self.assertEqual(6, self.summary["report_count"])

    def test_six_report_pdfs(self):
        self.assertEqual(6, self.summary["report_pdf_count"])

    def test_six_report_docx(self):
        self.assertEqual(6, self.summary["report_docx_count"])

    def test_fourteen_checks_passed(self):
        self.assertEqual(14, self.summary["cross_check_count"])
        self.assertEqual(14, self.summary["cross_checks_passed"])
        self.assertTrue(self.summary["all_cross_checks_passed"])

    def test_concept_issue_ready(self):
        self.assertTrue(self.summary["concept_issue_package_ready"])

    def test_gross_area(self):
        self.assertEqual(140.0, self.summary["gross_area_m2"])

    def test_parking_basis(self):
        self.assertEqual(225, self.summary["parking_basis_spaces"])

    def test_req107_closed(self):
        self.assertEqual("CLOSED_PROJECT_LEADER_APPROVED", self.summary["req107_status"])

    def test_six_professional_blockers(self):
        self.assertEqual(6, self.summary["professional_evidence_blocker_count"])

    def test_final_permit_gate_blocked(self):
        self.assertFalse(self.summary["final_permit_ready_generation_allowed"])

    def test_bb36_production_locked(self):
        self.assertFalse(self.summary["bb36_production_release_allowed"])

    def test_pdf_signatures(self):
        pdfs = list(self.root.rglob("*.pdf"))
        self.assertEqual(17, len(pdfs))
        self.assertTrue(all(path.read_bytes().startswith(b"%PDF-1.4") for path in pdfs))

    def test_svg_signatures(self):
        svgs = list(self.root.rglob("*.svg"))
        self.assertEqual(10, len(svgs))
        self.assertTrue(all("<svg" in path.read_text(encoding="utf-8") for path in svgs))

    def test_dxf_signatures(self):
        dxfs = list(self.root.rglob("*.dxf"))
        self.assertEqual(5, len(dxfs))
        self.assertTrue(all("SECTION" in path.read_text(encoding="utf-8") and "EOF" in path.read_text(encoding="utf-8") for path in dxfs))

    def test_docx_packages(self):
        docx = list(self.root.rglob("*.docx"))
        self.assertEqual(6, len(docx))
        self.assertTrue(all(zipfile.is_zipfile(path) for path in docx))
        with zipfile.ZipFile(docx[0]) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            self.assertIn("word/styles.xml", archive.namelist())

    def test_combined_drawing_set_has_ten_pages(self):
        path = self.root / "drawings/pdf/BB35_PILOT_1_REAL_CONCEPT_DRAWING_SET_v1_0_0.pdf"
        self.assertEqual(10, path.read_bytes().count(b"/Type /Page "))

    def test_issue_index_links_files(self):
        text = (self.root / "06_issue_index.html").read_text(encoding="utf-8")
        self.assertIn("BB35_PILOT_1_REAL_CONCEPT_DRAWING_SET_v1_0_0.pdf", text)
        self.assertIn("R-001", text)
        self.assertIn("A-101", text)

    def test_issue_zip_is_valid(self):
        path = self.root / "BB35_PILOT_1_REAL_CONCEPT_ISSUE_PACKAGE_v1_0_0.zip"
        with zipfile.ZipFile(path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertGreater(len(archive.namelist()), 40)

    def test_output_count(self):
        self.assertEqual(46, self.summary["output_file_count"])

    def test_two_runs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as second:
            other = Path(second)
            RealConceptProductionEngine(CONFIG).produce(other)
            first_names = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
            second_names = sorted(p.relative_to(other).as_posix() for p in other.rglob("*") if p.is_file())
            self.assertEqual(first_names, second_names)
            self.assertTrue(all((self.root / name).read_bytes() == (other / name).read_bytes() for name in first_names))

    def test_status_marking_in_drawing_pdf(self):
        sample = next((self.root / "drawings/pdf").glob("A-101_*.pdf"))
        self.assertIn(b"CONCEPT - NOT FOR SUBMISSION OR EXECUTION", sample.read_bytes())

    def test_status_marking_in_docx(self):
        sample = next((self.root / "reports/docx").glob("R-001_*.docx"))
        with zipfile.ZipFile(sample) as archive:
            text = archive.read("word/document.xml")
        self.assertIn(b"CONCEPT - NOT FOR SUBMISSION OR EXECUTION", text)


if __name__ == "__main__":
    unittest.main()
