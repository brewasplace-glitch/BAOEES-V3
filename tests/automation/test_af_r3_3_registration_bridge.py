import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve(); root=next(x for x in p.parents if (x/'phoenix/afoundation/registration_bridge.py').exists());spec=importlib.util.spec_from_file_location('bridge',root/'phoenix/afoundation/registration_bridge.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
src={'components':{'floorplan':{'edges':[[[0,0,0],[100,0,0]]]}}}
def meas(z=3430):return {'schema':'phoenix.af_r3_2.sketchup_measurement.v1','units':'mm','coordinate_system':'sketchup_world_xyz_no_alignment_asserted','walls_verified':False,'do_release':'LOCKED','edge_count':2,'edges':[{'id':'a','vertices_mm':[[0,0,z],[100,0,z]],'classification':'MODEL_3D_GEOMETRY_UNVERIFIED','length_3d_mm':100,'source_tags':['WALL_CANDIDATE_001']},{'id':'b','vertices_mm':[[0,0,0],[0,0,z]],'classification':'MODEL_3D_GEOMETRY_UNVERIFIED','length_3d_mm':z}]}
class Tests(unittest.TestCase):
 def test_geometry(self):
  r=m.evaluate(src,meas());self.assertEqual(r['counts']['top_edges_with_source_xy_proximity'],1);self.assertEqual(r['counts']['vertical_edges_3d'],1)
 def test_not_approved(self):self.assertEqual(m.evaluate(src,meas())['gates']['architectural_wall_identity'],'NOT_EVALUATED')
 def test_fake_approval(self):
  x=meas();x['walls_verified']=True
  with self.assertRaises(ValueError):m.evaluate(src,x)
 def test_duplicate(self):
  x=meas();x['edges'][1]['id']='a'
  with self.assertRaises(ValueError):m.evaluate(src,x)
 def test_bad_height(self):
  x=meas();x['edges'][0]['length_3d_mm']=1000
  with self.assertRaises(ValueError):m.evaluate(src,x)
 def test_tolerance(self):
  with self.assertRaises(ValueError):m.evaluate(src,meas(),500)
if __name__=='__main__':unittest.main()
