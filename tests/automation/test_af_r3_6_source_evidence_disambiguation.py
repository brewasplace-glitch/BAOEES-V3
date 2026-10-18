import copy
import unittest
from phoenix.afoundation.source_evidence_disambiguation import analyze

def fixtures():
    src={'components':{'floorplan':{'edges':[
        [[0.,0.,0.],[100.,0.,0.]], [[100.,0.,0.],[0.,0.,0.]],
        [[0.,1.,0.],[100.,1.,0.]], [[20.,5.,0.],[30.,5.,0.]]
    ]}}}
    prior={'schema':'phoenix.af_r3_5.source_bound_walls.v1','status':'SOURCE_LINE_ATTRIBUTION_DESCRIPTIVE_ONLY',
    'gates':{'coordinate_registration':'UNVERIFIED','do_release':'LOCKED','architectural_approval':'LOCKED',
             'outside_wall_coverage':'NOT_EVALUATED','inside_wall_coverage':'NOT_EVALUATED',
             'missing_wall_length':'NOT_EVALUATED','source_line_to_wall_classification':'NOT_EVALUATED'},
    'input_counts':{'r4_floorplan_edges':4,'candidate_groups':1,'top_edges':3},
    'source_attribution':{'top_edges_one_match':1,'top_edges_ambiguous':2,'top_edges_no_match':0},
    'candidates':[{'candidate_id':'WALL_CANDIDATE_001','top_edges':3,'unique_source_match_edges':1,
        'ambiguous_source_match_edges':2,'unmatched_top_edges':0,'wall_identity':'NOT_EVALUATED','wall_type':'UNKNOWN',
        'missing_wall_length_mm':None,'openings':'NOT_EVALUATED','source_evidence':[
        {'edge_id':'a','source_segment_indices':[0,1],'match_status':'AMBIGUOUS'},
        {'edge_id':'b','source_segment_indices':[0,2],'match_status':'AMBIGUOUS'},
        {'edge_id':'c','source_segment_indices':[3],'match_status':'ONE'}]}]}
    return src,prior
class Tests(unittest.TestCase):
    def test_decompose(self):
        r=analyze(*fixtures()); c=r['counts'];self.assertEqual((c['ambiguous_duplicate_geometry_only'],c['ambiguous_distinct_geometry']), (1,1));self.assertEqual(c['ambiguities_architecturally_resolved'],0)
    def test_no_approval(self):
        r=analyze(*fixtures());self.assertEqual(r['gates']['do_release'],'LOCKED');self.assertTrue(all(x['selection']=='UNRESOLVED' for x in r['candidate_evidence'][0]['evidence']))
    def test_reverse_duplicate(self):
        r=analyze(*fixtures());self.assertEqual(r['candidate_evidence'][0]['evidence'][0]['distinct_geometries'],1)
    def test_distinct_lines(self):
        r=analyze(*fixtures());self.assertEqual(r['candidate_evidence'][0]['evidence'][1]['distinct_geometries'],2)
    def test_bad_gate(self):
        s,p=fixtures();p['gates']['do_release']='PASS';self.assertRaises(ValueError,analyze,s,p)
    def test_bad_count(self):
        s,p=fixtures();p['input_counts']['top_edges']=30;self.assertRaises(ValueError,analyze,s,p)
    def test_bad_indices(self):
        s,p=fixtures();p['candidates'][0]['source_evidence'][0]['source_segment_indices']=[0,10];self.assertRaises(ValueError,analyze,s,p)
    def test_duplicate_edge(self):
        s,p=fixtures();p['candidates'][0]['source_evidence'][1]['edge_id']='a';self.assertRaises(ValueError,analyze,s,p)
    def test_fake_wall_identity(self):
        s,p=fixtures();p['candidates'][0]['wall_type']='EXTERIOR';self.assertRaises(ValueError,analyze,s,p)
    def test_bad_source(self):
        s,p=fixtures();s['components']['floorplan']['edges'][0][0][2]=1.;self.assertRaises(ValueError,analyze,s,p)
if __name__=='__main__':unittest.main()
