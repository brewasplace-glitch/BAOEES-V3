from __future__ import annotations
import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from phoenix.bb35_pilots.moskee_bunschoten.technical_design_a_to_d_masterpack import AcceleratedTechnicalDesignMasterpack, MasterpackExporter, STATUS
ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((ROOT/'configs/projects/moskee_bunschoten_technical_design_a_to_d_masterpack_v3_0_0.json').read_text(encoding='utf-8'))
class TechnicalDesignMasterpackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.engine=AcceleratedTechnicalDesignMasterpack(ROOT,CONFIG);cls.report=cls.engine.build()
    def test_status(self): self.assertEqual('TECHNICAL_DESIGN_A_TO_D_CONCEPT_MASTERPACK_READY',self.report['status'])
    def test_revision(self): self.assertEqual('C02',self.report['revision_code'])
    def test_four_phases(self): self.assertEqual(4,self.report['phase_count'])
    def test_four_gates_pass(self): self.assertEqual(4,self.report['phase_gates_passed']);self.assertTrue(self.report['all_phase_gates_passed'])
    def test_sixteen_master_checks(self): self.assertEqual(16,self.report['master_check_count'])
    def test_all_master_checks(self): self.assertEqual(16,self.report['master_checks_passed']);self.assertTrue(self.report['all_master_checks_passed'])
    def test_model_objects(self): self.assertEqual(299,self.report['model_object_count'])
    def test_area(self): self.assertEqual(140.0,self.report['extension_gross_area_m2'])
    def test_parking(self): self.assertEqual(225,self.report['parking_basis_spaces'])
    def test_req107_closed(self): self.assertEqual('CLOSED_PROJECT_LEADER_APPROVED',self.report['req107_status'])
    def test_six_blockers(self): self.assertEqual(6,self.report['professional_blocker_count'])
    def test_zero_evidence_accepted(self): self.assertEqual(0,self.report['professional_evidence_accepted_count'])
    def test_technical_concept_allowed(self): self.assertTrue(self.report['release_gates']['technical_concept_issue_allowed'])
    def test_permit_blocked(self): self.assertFalse(self.report['release_gates']['permit_ready_issue_allowed'])
    def test_tender_blocked(self): self.assertFalse(self.report['release_gates']['tender_ready_issue_allowed'])
    def test_execution_blocked(self): self.assertFalse(self.report['release_gates']['execution_ready_issue_allowed'])
    def test_bb36_locked(self): self.assertFalse(self.report['release_gates']['bb36_production_release_allowed'])
    def test_component_count(self): self.assertEqual(16,len(self.engine._component_rows()))
    def test_detail_count(self): self.assertEqual(12,len(self.engine._detail_definitions()))
    def test_door_count(self): self.assertEqual(12,len(self.engine._door_rows()))
    def test_window_count(self): self.assertEqual(8,len(self.engine._window_rows()))
    def test_room_finish_count(self): self.assertEqual(12,len(self.engine._room_finish_rows()))
    def test_mep_count(self): self.assertEqual(12,len(self.engine._mep_rows()))
    def test_sleeve_count(self): self.assertEqual(16,len(self.engine._sleeve_rows()))
    def test_clash_count(self): self.assertEqual(24,len(self.engine._clash_rows()))
    def test_coord_check_count(self): self.assertEqual(24,len(self.engine._coordination_checks()))
    def test_permit_index_count(self): self.assertEqual(24,len(self.engine._permit_index_rows()))
    def test_tender_index_count(self): self.assertEqual(28,len(self.engine._tender_index_rows()))
    def test_execution_index_count(self): self.assertEqual(32,len(self.engine._execution_index_rows()))
    def test_status_notice(self): self.assertIn('NOT FOR PERMIT',STATUS)
    def test_export_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=MasterpackExporter(self.engine).export_all(Path(tmp));self.assertGreaterEqual(len(paths),70);self.assertTrue(paths['combined_drawings'].is_file())
    def test_combined_pdf_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=MasterpackExporter(self.engine).export_all(Path(tmp));self.assertTrue(paths['combined_drawings'].read_bytes().startswith(b'%PDF-1.4'))
    def test_docx_is_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=MasterpackExporter(self.engine).export_all(Path(tmp));docx=paths['10_integrated_technical_design_report_docx'];self.assertTrue(zipfile.is_zipfile(docx))
    def test_issue_package_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=MasterpackExporter(self.engine).export_all(Path(tmp));
            with zipfile.ZipFile(paths['issue_package']) as archive: infos=archive.infolist()
            self.assertTrue(infos);self.assertTrue(all(info.date_time==(2020,1,1,0,0,0) for info in infos))
    def test_deterministic_export(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            MasterpackExporter(self.engine).export_all(Path(a));MasterpackExporter(self.engine).export_all(Path(b));ra=Path(a);rb=Path(b);names=sorted(p.relative_to(ra).as_posix() for p in ra.rglob('*') if p.is_file());self.assertEqual(names,sorted(p.relative_to(rb).as_posix() for p in rb.rglob('*') if p.is_file()));self.assertTrue(all((ra/n).read_bytes()==(rb/n).read_bytes() for n in names))
    def test_dashboard_has_four_phases(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=MasterpackExporter(self.engine).export_all(Path(tmp));text=paths['dashboard'].read_text(encoding='utf-8');self.assertIn('Phase A',text);self.assertIn('Phase D',text)
if __name__=='__main__': unittest.main()
