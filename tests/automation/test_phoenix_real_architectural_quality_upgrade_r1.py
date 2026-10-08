from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phoenix.design.tropical_residential.architectural_quality import (
    evaluate_layout_quality,
    evaluate_variant_set_quality,
    write_quality_report,
)

def layout():
    rooms=[]
    zones=["LIVING","KITCHEN","BEDROOM","BEDROOM","BATH","CIRCULATION"]
    for idx,zone in enumerate(zones):
        col=idx%3; row=idx//3
        rooms.append({
            "room_id":f"R{idx+1}",
            "storey_index":0,
            "zone":zone,
            "x":col*4.2,
            "y":row*4.2,
            "width":4.0,
            "depth":4.0,
        })
    return {
        "rooms":rooms,
        "walls":[{"wall_id":f"W{i}"} for i in range(12)],
        "openings":[
            {"opening_id":f"O{i}","storey_index":0,"kind":"WINDOW","host_wall_key":f"W{i}","x":float(i),"y":0.0,"width_m":1.2}
            for i in range(6)
        ],
        "geometry_validation":{"valid":True},
    }

class ArchitecturalQualityR1Tests(unittest.TestCase):
    def test_good_layout_passes(self):
        result=evaluate_layout_quality(layout(),{"variant_id":"A","strategy":"BALANCED"})
        self.assertTrue(result["hard_pass"])
        self.assertGreaterEqual(result["score"],45.0)

    def test_overlap_is_rejected(self):
        bad=layout()
        bad["rooms"][1]["x"]=bad["rooms"][0]["x"]
        bad["rooms"][1]["y"]=bad["rooms"][0]["y"]
        result=evaluate_layout_quality(bad,{"variant_id":"A","strategy":"BALANCED"})
        self.assertFalse(result["hard_pass"])
        self.assertIn("EXCESSIVE_ROOM_OVERLAP",result["hard_failures"])

    def test_adjacency_threshold_is_translation_deterministic(self):
        a=layout()
        b=layout()
        for room in b["rooms"]:
            room["x"] += 100.0
            room["y"] += 250.0
        qa=evaluate_layout_quality(a,{"variant_id":"A","strategy":"BALANCED"})
        qb=evaluate_layout_quality(b,{"variant_id":"B","strategy":"BALANCED"})
        self.assertEqual(qa["semantic_signature"],qb["semantic_signature"])

    def test_global_translation_does_not_create_new_variant(self):
        a=layout()
        b=layout()
        for room in b["rooms"]:
            room["x"] += 100.0
            room["y"] += 250.0
        for opening in b["openings"]:
            opening["x"] += 100.0
            opening["y"] += 250.0
        qa=evaluate_layout_quality(a,{"variant_id":"A","strategy":"BALANCED"})
        qb=evaluate_layout_quality(b,{"variant_id":"B","strategy":"BALANCED"})
        self.assertEqual(qa["semantic_signature"],qb["semantic_signature"])

    def test_opening_set_translation_alone_is_ignored(self):
        a=layout()
        b=layout()
        for opening in b["openings"]:
            opening["x"] += 30.0
            opening["y"] += 45.0
        qa=evaluate_layout_quality(a,{"variant_id":"A","strategy":"BALANCED"})
        qb=evaluate_layout_quality(b,{"variant_id":"B","strategy":"BALANCED"})
        self.assertEqual(qa["semantic_signature"],qb["semantic_signature"])

    def test_opening_distribution_can_distinguish_architecture(self):
        a=layout()
        b=layout()
        b["openings"][0]["x"] += 3.0
        qa=evaluate_layout_quality(a,{"variant_id":"A","strategy":"BALANCED"})
        qb=evaluate_layout_quality(b,{"variant_id":"B","strategy":"BALANCED"})
        self.assertNotEqual(qa["semantic_signature"],qb["semantic_signature"])

    def test_duplicate_semantic_variants_are_rejected(self):
        row=evaluate_layout_quality(layout(),{"variant_id":"A","strategy":"BALANCED"})
        rows=[]
        for vid in "ABCDE":
            item=dict(row); item["variant_id"]=vid; rows.append(item)
        result=evaluate_variant_set_quality(rows)
        self.assertFalse(result["hard_pass"])
        self.assertEqual(result["unique_semantic_signature_count"],1)

    def test_five_semantically_distinct_variants_pass(self):
        permutations = [
            [0,1,2,3,4,5],
            [1,0,2,3,5,4],
            [2,1,0,4,3,5],
            [3,4,5,0,1,2],
            [5,3,4,2,0,1],
        ]
        rows=[]
        for vid,perm in zip("ABCDE",permutations):
            item=layout()
            slots=[(r["x"],r["y"]) for r in item["rooms"]]
            for room,slot_index in zip(item["rooms"],perm):
                room["x"],room["y"]=slots[slot_index]
            rows.append(evaluate_layout_quality(item,{"variant_id":vid,"strategy":"BALANCED"}))
        result=evaluate_variant_set_quality(rows)
        self.assertTrue(result["hard_pass"], result)
        self.assertEqual(result["unique_semantic_signature_count"],5)

    def test_report_written(self):
        permutations = [
            [0,1,2,3,4,5],
            [1,0,2,3,5,4],
            [2,1,0,4,3,5],
            [3,4,5,0,1,2],
            [5,3,4,2,0,1],
        ]
        rows=[]
        for vid,perm in zip("ABCDE",permutations):
            item=layout()
            slots=[(r["x"],r["y"]) for r in item["rooms"]]
            for room,slot_index in zip(item["rooms"],perm):
                room["x"],room["y"]=slots[slot_index]
            rows.append(evaluate_layout_quality(item,{"variant_id":vid,"strategy":"BALANCED"}))
        report=evaluate_variant_set_quality(rows)
        with tempfile.TemporaryDirectory() as td:
            paths=write_quality_report(Path(td),report)
            self.assertTrue(Path(paths["json"]).is_file())
            self.assertTrue(Path(paths["markdown"]).is_file())

if __name__=="__main__":
    unittest.main()
