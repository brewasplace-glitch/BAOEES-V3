import unittest
from phoenix.architecture.r2d_r4_host_authority import resolve_exterior_window_host, WINDOW_HOST_AUTHORITY_KIND

ROOMS=[
    ['badkamer_hoof',6,0,2,4],
    ['overloop',3,4,8,2],
    ['slaapkamer_hoof',0,0,6,4],
]

class HostAuthorityTests(unittest.TestCase):
    def base(self):
        return {
            'opening_id':'A-W20','opening_type':'WINDOW','kind':'window','level':'upper','storey':1,
            'source_room':'badkamer_hoof','orientation':'H','center_xy':[7.0,0.0],'width_m':1.0,
            'exterior_boundary_proof':'GLOBAL_ROOM_UNION_XOR_5_POINT_PASS',
            'repair_reason':'R2D_R4_BATHROOM_MINIMUM_EXTERIOR_WINDOW',
        }
    def test_bathroom_window_on_exposed_boundary_gets_local_host(self):
        spec,proof=resolve_exterior_window_host('A',self.base(),ROOMS,3.3,6.4)
        self.assertIsNotNone(spec)
        self.assertEqual(spec['authority_kind'],WINDOW_HOST_AUTHORITY_KIND)
        self.assertEqual(spec['derived_for_opening_id'],'A-W20')
        self.assertLess(spec['hi']-spec['lo'],2.0)
        self.assertEqual(proof['reason'],'EXTERIOR_WINDOW_BOUNDARY_PROVEN')
    def test_internal_shared_boundary_is_rejected(self):
        w=self.base();w['orientation']='H';w['center_xy']=[7.0,4.0]
        spec,proof=resolve_exterior_window_host('A',w,ROOMS,3.3,6.4)
        self.assertIsNone(spec)
        self.assertIn('EXTERIOR',proof['reason'])
    def test_non_window_is_rejected(self):
        w=self.base();w['opening_type']='DOOR';w['kind']='door'
        spec,proof=resolve_exterior_window_host('A',w,ROOMS,3.3,6.4)
        self.assertIsNone(spec);self.assertEqual(proof['reason'],'NOT_WINDOW')
    def test_width_must_fit_exposed_segment(self):
        w=self.base();w['width_m']=2.5
        spec,proof=resolve_exterior_window_host('A',w,ROOMS,3.3,6.4)
        self.assertIsNone(spec)
    def test_ambiguous_room_provenance_is_rejected(self):
        w=self.base();w.pop('source_room');w['exterior_inside_rooms']=['badkamer_hoof','slaapkamer_hoof']
        spec,proof=resolve_exterior_window_host('A',w,ROOMS,3.3,6.4)
        self.assertIsNone(spec);self.assertEqual(proof['reason'],'WINDOW_EXTERIOR_ROOM_AMBIGUOUS')

if __name__=='__main__':
    unittest.main()
