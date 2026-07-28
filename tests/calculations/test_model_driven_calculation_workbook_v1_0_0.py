from __future__ import annotations
import json, tempfile, unittest, zipfile
from pathlib import Path
from phoenix.calculations.model_driven_workbook import ModelDrivenCalculationEngine, CalculationArtifactExporter
ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((ROOT/'configs/projects/moskee_bunschoten_model_driven_calculation_workbook_v1_0_0.json').read_text(encoding='utf-8'))

class ModelDrivenCalculationWorkbookTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.result=ModelDrivenCalculationEngine().evaluate(repository=ROOT,config=CONFIG)
 def test_status(self): self.assertEqual('MODEL_DRIVEN_CONCEPT_CALCULATIONS_GENERATED',self.result['status'])
 def test_model_id(self): self.assertEqual('HBM-GEO-2026-001',self.result['model_id'])
 def test_fingerprint(self): self.assertEqual(CONFIG['expected_model_fingerprint_sha256'],self.result['model_fingerprint_sha256'])
 def test_input_count(self): self.assertEqual(38,self.result['metrics']['input_count'])
 def test_calculation_count(self): self.assertEqual(32,self.result['metrics']['calculation_count'])
 def test_category_count(self): self.assertEqual(8,self.result['metrics']['calculation_category_count'])
 def test_quality_count(self): self.assertEqual(18,self.result['metrics']['quality_check_count'])
 def test_all_quality_pass(self): self.assertEqual(18,self.result['metrics']['quality_checks_passed'])
 def test_parking_capacity(self): self.assertEqual(225,self.result['metrics']['parking_capacity_spaces'])
 def test_six_blockers(self): self.assertEqual(6,self.result['metrics']['professional_blocker_count'])
 def test_extension_area(self): self.assertEqual(140.0,self._calc('CAL-A02')['result'])
 def test_extension_volume(self): self.assertEqual(448.0,self._calc('CAL-A03')['result'])
 def test_total_service_load(self): self.assertEqual(1335.0,self._calc('CAL-S03')['result'])
 def test_average_column_reaction(self): self.assertEqual(148.33,self._calc('CAL-S04')['result'])
 def test_line_load(self): self.assertEqual(24.5,self._calc('CAL-S05')['result'])
 def test_moment(self): self.assertEqual(76.56,self._calc('CAL-S06')['result'])
 def test_bearing_area(self): self.assertEqual(72.0,self._calc('CAL-F01')['result'])
 def test_contact_pressure(self): self.assertEqual(18.54,self._calc('CAL-F02')['result'])
 def test_persons_per_exit(self): self.assertEqual(100.0,self._calc('CAL-E02')['result'])
 def test_persons_per_m(self): self.assertEqual(83.33,self._calc('CAL-E03')['result'])
 def test_peak_ventilation(self): self.assertEqual(5040.0,self._calc('CAL-V03')['result'])
 def test_equipment_hours(self): self.assertEqual(496.0,self._calc('CAL-C02')['result'])
 def test_vehicle_km(self): self.assertEqual(6600.0,self._calc('CAL-C03')['result'])
 def test_final_generation_blocked(self): self.assertFalse(self.result['gates']['final_permit_ready_generation_allowed'])
 def test_bb36_locked(self): self.assertFalse(self.result['gates']['bb36_production_release_allowed'])
 def test_traceability(self): self.assertGreater(self.result['metrics']['traceability_link_count'],31)
 def test_export_count(self):
  with tempfile.TemporaryDirectory() as tmp:
   CalculationArtifactExporter().export_all(self.result,tmp)
   self.assertEqual(22,sum(1 for p in Path(tmp).rglob('*') if p.is_file()))
 def test_workbook_valid_zip(self):
  with tempfile.TemporaryDirectory() as tmp:
   paths=CalculationArtifactExporter().export_all(self.result,tmp)
   with zipfile.ZipFile(paths['workbook']) as z:
    self.assertIsNone(z.testzip()); self.assertIn('xl/workbook.xml',z.namelist()); self.assertEqual(13,len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet')]))
 def test_internal_package_valid(self):
  with tempfile.TemporaryDirectory() as tmp:
   paths=CalculationArtifactExporter().export_all(self.result,tmp)
   with zipfile.ZipFile(paths['package']) as z: self.assertIsNone(z.testzip())
 def test_two_exports_byte_identical(self):
  with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
   CalculationArtifactExporter().export_all(self.result,a); CalculationArtifactExporter().export_all(self.result,b)
   ar=Path(a); br=Path(b); names=sorted(p.relative_to(ar).as_posix() for p in ar.rglob('*') if p.is_file()); self.assertEqual(names,sorted(p.relative_to(br).as_posix() for p in br.rglob('*') if p.is_file())); self.assertTrue(all((ar/n).read_bytes()==(br/n).read_bytes() for n in names))
 def _calc(self,calc_id): return next(x for x in self.result['calculations'] if x['calculation_id']==calc_id)
if __name__=='__main__': unittest.main()
