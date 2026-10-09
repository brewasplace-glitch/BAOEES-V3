from __future__ import annotations
import unittest
from phoenix.design.tropical_residential.aec_topology_quality import _category, analyze_aec_topology

class R5FixR2Tests(unittest.TestCase):
    def test_real_project_semantics(self):
        cases=[
            ({"room_id":"living","zone":"social","name":"Living"},"PUBLIC"),
            ({"room_id":"dining","zone":"social","name":"Dining"},"PUBLIC"),
            ({"room_id":"kitchen","zone":"service","name":"Kitchen"},"PUBLIC"),
            ({"room_id":"bathroom_s1","zone":"service","name":"Bathroom / WC S1"},"WET"),
            ({"room_id":"service","zone":"service","name":"Laundry / Service"},"WET"),
            ({"room_id":"bedroom_1","zone":"private","name":"Bedroom 1"},"PRIVATE"),
            ({"room_id":"circulation_s1","zone":"circulation","name":"Circulation / Stair S1"},"CIRCULATION"),
        ]
        for room,expected in cases:
            self.assertEqual(_category(room),expected,msg=room)

    def test_vertical_graph_produces_paths(self):
        rooms=[
            {"room_id":"living","zone":"social","name":"Living","storey_index":0,"x":0,"y":0,"width":4,"depth":4},
            {"room_id":"circulation_s1","zone":"circulation","name":"Circulation / Stair S1","storey_index":0,"x":4.1,"y":0,"width":2,"depth":4},
            {"room_id":"bathroom_s1","zone":"service","name":"Bathroom / WC S1","storey_index":0,"x":6.2,"y":0,"width":2,"depth":4},
            {"room_id":"service","zone":"service","name":"Laundry / Service","storey_index":0,"x":8.3,"y":0,"width":2,"depth":4},
            {"room_id":"bedroom_1","zone":"private","name":"Bedroom 1","storey_index":1,"x":0,"y":0,"width":4,"depth":4},
            {"room_id":"circulation_s2","zone":"circulation","name":"Circulation / Stair S2","storey_index":1,"x":4.1,"y":0,"width":2,"depth":4},
            {"room_id":"bathroom_s2","zone":"service","name":"Bathroom / WC S2","storey_index":1,"x":6.2,"y":0,"width":2,"depth":4},
        ]
        result=analyze_aec_topology({"rooms":rooms},{"variant_id":"E","strategy":"BALANCED"})
        m=result["metrics"]
        self.assertGreaterEqual(m["vertical_circulation_edge_count"],1)
        self.assertGreater(m["public_private_pair_count"],0)
        self.assertGreater(m["wet_pair_count"],0)
        self.assertIsNotNone(m["public_private_mean_path"])
        self.assertIsNotNone(m["wet_core_mean_path"])

if __name__=="__main__":
    unittest.main()
