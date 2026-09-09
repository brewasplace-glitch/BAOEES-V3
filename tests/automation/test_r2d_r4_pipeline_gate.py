import unittest
from phoenix.architecture.r2d_r4_pipeline_gate import exact_opening_id_gate, geometry_gate

class PipelineGateTests(unittest.TestCase):
    def test_exact_ids(self):
        v={'openings':[{'opening_id':'A-W01'},{'opening_id':'A-DG01'}]}
        a={'openings':[{'opening_id':'A-W01'},{'opening_id':'A-DG01'}]}
        self.assertEqual(exact_opening_id_gate(v,a,a)['status'],'PASS')

    def test_geometry(self):
        m=[{'opening_id':'A-W01','orientation':'H','center_xy':[1,2]}]
        f=[{'opening_id':'A-W01','orientation':'H','center_xy':[1,2],'actual_z0':1.1,'actual_height_m':1.6}]
        b=[{'opening_id':'A-W01','orientation':'H','center_xy':[1.01,2],'actual_z0':1.12,'actual_height_m':1.59}]
        self.assertEqual(geometry_gate(m,f,b)['status'],'PASS')

if __name__=='__main__': unittest.main()
