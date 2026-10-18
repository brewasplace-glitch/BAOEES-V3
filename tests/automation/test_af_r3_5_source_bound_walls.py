import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from phoenix.afoundation.source_bound_walls import analyze

def fixture():
 s={'components':{'floorplan':{'edges':[[[0,0,0],[1000,0,0]],[[0,100,0],[1000,100,0]]]}}}
 def edge(eid,a,b,cls,tags):return {'id':eid,'vertices_mm':[a,b],'length_3d_mm':__import__('math').dist(a,b),'classification':cls,'source_tags':tags}
 m={'schema':'phoenix.af_r3_2.sketchup_measurement.v1','units':'mm','coordinate_system':'sketchup_world_xyz_no_alignment_asserted','walls_verified':False,'openings_verified':False,'do_release':'LOCKED','model_modified':False,'edges':[
 edge('a',[0,0,3430],[1000,0,3430],'MODEL_3D_GEOMETRY_UNVERIFIED',['WALL_CANDIDATE_001 GEOMETRY_ONLY']),
 edge('b',[0,0,0],[0,0,3430],'MODEL_3D_GEOMETRY_UNVERIFIED',['WALL_CANDIDATE_001 GEOMETRY_ONLY'])]}
 m['edge_count']=len(m['edges']);return s,m
class WallTests(unittest.TestCase):
 def test_one_match(self):
  s,m=fixture();r=analyze(s,m);self.assertEqual(r['source_attribution']['top_edges_one_match'],1);self.assertEqual(r['source_attribution']['r4_segments_not_referenced'],1)
 def test_never_missing_walls(self):
  s,m=fixture();r=analyze(s,m);self.assertEqual(r['gates']['missing_wall_length'],'NOT_EVALUATED');self.assertIsNone(r['candidates'][0]['missing_wall_length_mm'])
 def test_ambiguous(self):
  s,m=fixture();s['components']['floorplan']['edges'].append([[0,1,0],[1000,1,0]]);r=analyze(s,m);self.assertEqual(r['source_attribution']['top_edges_ambiguous'],1)
 def test_false_positive_angular(self):
  s,m=fixture();m['edges'][0]['vertices_mm']=[[0,0,3430],[1000,20,3430]];m['edges'][0]['length_3d_mm']=__import__('math').dist(*m['edges'][0]['vertices_mm']);r=analyze(s,m);self.assertEqual(r['source_attribution']['top_edges_no_match'],1)
 def test_bad_coordinate(self):
  s,m=fixture();m['coordinate_system']='aligned';self.assertRaises(ValueError,analyze,s,m)
 def test_fake_approval(self):
  s,m=fixture();m['walls_verified']=True;self.assertRaises(ValueError,analyze,s,m)
 def test_duplicate_id(self):
  s,m=fixture();m['edges'][1]['id']='a';self.assertRaises(ValueError,analyze,s,m)
 def test_nonfinite(self):
  s,m=fixture();m['edges'][0]['vertices_mm'][0][0]=float('nan');self.assertRaises(ValueError,analyze,s,m)
 def test_invalid_tolerance(self):
  s,m=fixture();self.assertRaises(ValueError,analyze,s,m,30)
 def test_source_must_be_flat(self):
  s,m=fixture();s['components']['floorplan']['edges'][0][0][2]=100;self.assertRaises(ValueError,analyze,s,m)
if __name__=='__main__':unittest.main()
