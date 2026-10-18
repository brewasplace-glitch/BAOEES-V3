import copy
import json
import unittest
from pathlib import Path
from phoenix.afoundation.candidate_topology import analyze

class CandidateTopologyTests(unittest.TestCase):
    def setUp(self):
        self.src={"components":{"floorplan":{"edges":[[[0,0,0],[100,0,0]]]}}}
        self.measure={"schema":"phoenix.af_r3_2.sketchup_measurement.v1","units":"mm","coordinate_system":"sketchup_world_xyz_no_alignment_asserted","walls_verified":False,"openings_verified":False,"do_release":"LOCKED","edge_count":2,"edges":[
         {"id":"top","vertices_mm":[[0.,0.,3430.],[100.,0.,3430.]],"length_3d_mm":100.,"classification":"MODEL_3D_GEOMETRY_UNVERIFIED","source_tags":["WALL_CANDIDATE_001 GEOMETRY_ONLY"]},
         {"id":"vert","vertices_mm":[[0.,0.,0.],[0.,0.,3430.]],"length_3d_mm":3430.,"classification":"MODEL_3D_GEOMETRY_UNVERIFIED","source_tags":["WALL_CANDIDATE_001 GEOMETRY_ONLY"]}]}
    def test_candidate(self):
        r=analyze(self.src,self.measure);self.assertEqual(r['candidate_totals']['top_edges_near_source'],1);self.assertEqual(r['candidate_totals']['vertical_edges'],1)
    def test_no_approval(self):
        r=analyze(self.src,self.measure);self.assertEqual(r['gates']['do_release'],'LOCKED');self.assertEqual(r['candidates'][0]['wall_thickness_mm'],None)
    def test_bad_claim(self):
        self.measure['walls_verified']=True
        with self.assertRaises(ValueError):analyze(self.src,self.measure)
    def test_bad_geometry(self):
        self.measure['edges'][0]['vertices_mm'][0][0]=float('nan')
        with self.assertRaises(ValueError):analyze(self.src,self.measure)
    def test_duplicate_id(self):
        self.measure['edges'][1]['id']='top'
        with self.assertRaises(ValueError):analyze(self.src,self.measure)
    def test_wrong_coordinate_frame(self):
        self.measure['coordinate_system']='registered'
        with self.assertRaises(ValueError):analyze(self.src,self.measure)
    def test_no_wall_category_inference(self):
        self.assertEqual(analyze(self.src,self.measure)['candidates'][0]['wall_type'],'UNKNOWN')
    def test_tolerance_guard(self):
        with self.assertRaises(ValueError):analyze(self.src,self.measure,200)
