import hashlib
import tempfile
import unittest
from pathlib import Path
from phoenix.afoundation.cad_semantic_gate import audit, validate_manifest, SOURCE_SHA
class Tests(unittest.TestCase):
    def test_no_source(self):
        r=audit();self.assertEqual(r['status'],'WAITING_FOR_AUTHENTICATED_CAD_SEMANTICS')
    def test_lock(self):
        r=audit();self.assertEqual(r['gates']['do_release'],'LOCKED')
    def test_missing_source(self):
        with self.assertRaises(FileNotFoundError):audit(dwg='/missing/random.dwg')
    def test_wrong_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fake.dwg';p.write_bytes(b'AC1015garbage')
            with self.assertRaises(ValueError):audit(dwg=p)
    def test_invalid_magic(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fake.dwg';p.write_bytes(b'AC1027')
            with self.assertRaises(ValueError):audit(dwg=p)
    def test_manifest_wrong_sha(self):
        with self.assertRaises(ValueError):validate_manifest({'original_dwg_sha256':'abc'})
    def test_manifest_wrong_method(self):
        with self.assertRaises(ValueError):validate_manifest({'original_dwg_sha256':SOURCE_SHA,'conversion_method':'guess'})
    def test_manifest_no_operator(self):
        with self.assertRaises(ValueError):validate_manifest({'original_dwg_sha256':SOURCE_SHA,'conversion_method':'AUTOCAD_EXPORT','conversion_operator':''})
    def test_manifest_source_modified(self):
        m=self.ok_manifest();m['source_modified']=True
        with self.assertRaises(ValueError):validate_manifest(m)
    def test_manifest_valid(self):self.assertTrue(validate_manifest(self.ok_manifest()))
    def test_dxf_without_provenance(self):
        with self.assertRaises(ValueError):audit(dxf='anything.dxf')
    def test_manifest_without_dxf(self):
        with self.assertRaises(ValueError):audit(manifest='anything.json')
    @staticmethod
    def ok_manifest():
        return {'original_dwg_sha256':SOURCE_SHA,'conversion_method':'ODA_FILE_CONVERTER',
                'conversion_operator':'read-only conversion','dxf_sha256':'a'*64,'source_modified':False}
if __name__=='__main__':unittest.main()
