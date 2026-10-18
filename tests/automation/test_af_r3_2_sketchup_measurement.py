import importlib.util
import pathlib
import unittest
here=pathlib.Path(__file__).resolve()
root=next(p for p in here.parents if (p/'phoenix'/'afoundation'/'sketchup_measurement.py').is_file())
spec=importlib.util.spec_from_file_location('af32',root/'phoenix'/'afoundation'/'sketchup_measurement.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    return {'schema':m.SCHEMA,'units':'mm','coordinate_system':'sketchup_world_xyz_no_alignment_asserted',
    'measurement_status':'MEASURED_GEOMETRY_NOT_ARCHITECTURALLY_VERIFIED','do_release':'LOCKED','walls_verified':False,
    'edges':[{'id':'1/2','classification':'MODEL_3D_GEOMETRY_UNVERIFIED','vertices_mm':[[0,0,0],[0,0,3430]],'length_3d_mm':3430}],
    'edge_count':1,'classification_counts':{'MODEL_3D_GEOMETRY_UNVERIFIED':1}}
class Tests(unittest.TestCase):
    def test_valid(self):self.assertEqual(m.validate(sample())['status'],'MEASUREMENT_QA_PASS_ARCHITECTURE_NOT_EVALUATED')
    def test_block_fake_approval(self):
        d=sample();d['walls_verified']=True
        with self.assertRaises(ValueError):m.validate(d)
    def test_no_coverage_claim(self):self.assertEqual(m.validate(sample())['source_2d_coverage'],'NOT_EVALUATED')
    def test_duplicate_instances(self):
        d=sample();d['edges'].append(d['edges'][0]);d['edge_count']=2;d['classification_counts']['MODEL_3D_GEOMETRY_UNVERIFIED']=2
        with self.assertRaises(ValueError):m.validate(d)
    def test_nonfinite(self):
        d=sample();d['edges'][0]['vertices_mm'][1][2]=float('nan')
        with self.assertRaises(ValueError):m.validate(d)
    def test_length_mismatch(self):
        d=sample();d['edges'][0]['length_3d_mm']=12
        with self.assertRaises(ValueError):m.validate(d)
    def test_bad_registration(self):
        d=sample();d['coordinate_system']='source_world_xy'
        with self.assertRaises(ValueError):m.validate(d)
    def test_invalid_classification(self):
        d=sample();d['edges'][0]['classification']='VERIFIED_WALL'
        with self.assertRaises(ValueError):m.validate(d)
if __name__=='__main__':unittest.main()
