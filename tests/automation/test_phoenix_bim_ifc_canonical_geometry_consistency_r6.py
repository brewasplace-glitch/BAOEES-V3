from __future__ import annotations
import unittest
from phoenix.design.tropical_residential.canonical_geometry_consistency import (
    XYBox, canonical_rooms, greedy_match, room_box
)

class CanonicalGeometryConsistencyR6Tests(unittest.TestCase):
    def test_room_box(self):
        b=room_box({"x":1,"y":2,"width":3,"depth":4})
        self.assertEqual((b.minx,b.miny,b.maxx,b.maxy),(1,2,4,6))

    def test_translation_invariant_matching(self):
        canonical=[
            {"room_id":"living","name":"Living","storey_index":0,"box":XYBox(0,0,4,5)},
            {"room_id":"kitchen","name":"Kitchen","storey_index":0,"box":XYBox(4,0,7,5)},
        ]
        spaces=[
            {"name":"Living","global_id":"A","box":XYBox(100,50,104,55)},
            {"name":"Kitchen","global_id":"B","box":XYBox(104,50,107,55)},
        ]
        rows=greedy_match(canonical,spaces)
        self.assertTrue(all(r["matched"] for r in rows))
        self.assertLess(max(r["center_distance"] for r in rows),0.001)
        self.assertLess(max(r["width_difference"] for r in rows),0.001)

    def test_room_count(self):
        layout={"rooms":[
            {"room_id":"a","x":0,"y":0,"width":2,"depth":3},
            {"room_id":"b","x":2,"y":0,"width":4,"depth":3},
        ]}
        self.assertEqual(len(canonical_rooms(layout)),2)

if __name__=="__main__":
    unittest.main()
