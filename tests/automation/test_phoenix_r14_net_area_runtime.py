import unittest
from phoenix.design.tropical_residential.architectural_quality import evaluate_layout_quality

class TestRuntimeNetArea(unittest.TestCase):
    def setUp(self):
        self.layout={'rooms':[{'room_id':'living','storey_index':0,'x':0,'y':0,'width':4,'depth':3,'target_area_m2':12}], 'walls':[{'wall_key':'W1','storey_index':0,'x1':0,'y1':0,'x2':0,'y2':3,'thickness_m':0.2}], 'openings':[]}
    def test_diagnostic_keeps_old_gate(self):
        r=evaluate_layout_quality(self.layout, {'variant_id':'A'})
        self.assertFalse(r['hard_pass'])
        self.assertEqual(r['release_status'],'CONCEPT_QA_ONLY_NOT_FOR_CONSTRUCTION')
        d=r['r14_net_area_diagnostic']
        self.assertEqual(d['programme_acceptance'],'OPEN_NO_APPROVED_TOLERANCE')
        self.assertEqual(d['rooms'][0]['provisional_clear_m2'],11.7)
        self.assertFalse(d['formal_net_usable_area_approved'])
    def test_unsupported_geometry_blocks_estimate(self):
        self.layout['walls'][0]['x2']=2
        r=evaluate_layout_quality(self.layout)
        self.assertIsNone(r['r14_net_area_diagnostic']['rooms'][0]['provisional_clear_m2'])
        self.assertEqual(r['r14_net_area_diagnostic']['status'],'PARTIAL_UNSUPPORTED')
if __name__=='__main__':unittest.main()
