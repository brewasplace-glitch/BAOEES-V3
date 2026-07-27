from __future__ import annotations
import json,tempfile,unittest,zipfile
from pathlib import Path
from phoenix.model.central_geometric_project_model import CentralGeometricProjectModelEngine,CentralGeometricProjectModelExporter,polygon_area
ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((ROOT/'configs/projects/moskee_bunschoten_central_geometric_model_v1_0_0.json').read_text(encoding='utf-8'))
class CentralModelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.result=CentralGeometricProjectModelEngine(CONFIG).build();cls.model=cls.result['model'];cls.objects=cls.model['objects'];cls.by_id={o['id']:o for o in cls.objects}
 def test_model_id(self):self.assertEqual('HBM-GEO-2026-001',self.model['model_id'])
 def test_object_count(self):self.assertEqual(299,len(self.objects))
 def test_relationship_count_positive(self):self.assertGreater(len(self.model['relationships']),270)
 def test_three_levels(self):self.assertEqual(3,len(self.model['levels']))
 def test_extension_area(self):self.assertEqual(70.0,polygon_area(self.by_id['BLD-EXTENSION']['geometry']['points']))
 def test_extension_gross_area(self):self.assertEqual(140.0,CONFIG['extension']['gross_area_m2'])
 def test_existing_area(self):self.assertEqual(168.0,polygon_area(self.by_id['BLD-EXISTING']['geometry']['points']))
 def test_two_storeys(self):self.assertEqual(2,self.by_id['BLD-EXTENSION']['storeys'])
 def test_wall_count(self):self.assertEqual(26,sum(o['type']=='wall' for o in self.objects))
 def test_space_count(self):self.assertEqual(12,sum(o['type']=='space' for o in self.objects))
 def test_opening_count(self):self.assertEqual(16,sum(o['type']=='opening' for o in self.objects))
 def test_connection_count(self):self.assertEqual(4,sum(o['type']=='connection' for o in self.objects))
 def test_parking_zones(self):self.assertEqual(5,sum(o['type']=='parking_zone' for o in self.objects))
 def test_parking_bays(self):self.assertEqual(225,sum(o['type']=='parking_bay' for o in self.objects))
 def test_parking_total(self):self.assertEqual(225,sum(o['space_count'] for o in self.objects if o['type']=='parking_zone'))
 def test_stair(self):self.assertEqual(['L00','L01'],self.by_id['STAIR-001']['connects_levels'])
 def test_opening_hosts(self):
  ids=set(self.by_id);self.assertTrue(all(o['host_id'] in ids for o in self.objects if o['type']=='opening'))
 def test_req107(self):self.assertEqual('CLOSED_PROJECT_LEADER_APPROVED',self.model['req107_status'])
 def test_six_blockers(self):self.assertEqual(6,len(self.model['professional_blockers']))
 def test_fingerprint(self):self.assertEqual(64,len(self.model['model_fingerprint_sha256']))
 def test_checks_count(self):self.assertEqual(22,len(self.result['checks']))
 def test_checks_all_pass(self):self.assertTrue(all(c['passed'] for c in self.result['checks']))
 def test_export_count(self):
  with tempfile.TemporaryDirectory() as tmp:
   CentralGeometricProjectModelExporter().export_all(self.result,tmp);self.assertEqual(22,sum(p.is_file() for p in Path(tmp).rglob('*')))
 def test_export_zip(self):
  with tempfile.TemporaryDirectory() as tmp:
   paths=CentralGeometricProjectModelExporter().export_all(self.result,tmp)
   with zipfile.ZipFile(paths['package']) as z:self.assertIsNone(z.testzip())
 def test_two_exports_identical(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   CentralGeometricProjectModelExporter().export_all(self.result,a);CentralGeometricProjectModelExporter().export_all(self.result,b);ra=Path(a);rb=Path(b);names=sorted(p.relative_to(ra).as_posix() for p in ra.rglob('*') if p.is_file());self.assertEqual(names,sorted(p.relative_to(rb).as_posix() for p in rb.rglob('*') if p.is_file()));self.assertTrue(all((ra/n).read_bytes()==(rb/n).read_bytes() for n in names))
if __name__=='__main__':unittest.main()
