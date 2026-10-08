from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phoenix.design.tropical_residential.spatial_quality import (
    evaluate_spatial_relationships,
    evaluate_variant_set_spatial_quality,
    write_spatial_quality_report,
)

def make_layout(variant_shift=0.0, disconnect=False):
    labels=["LIVING","KITCHEN","BEDROOM","BEDROOM","BATH","CIRCULATION"]
    rooms=[]
    slots=[(0,0),(4.2,0),(8.4,0),(0,4.2),(4.2,4.2),(8.4,4.2)]
    for i,(label,(x,y)) in enumerate(zip(labels,slots)):
        if disconnect and i==5:
            x+=40
        if i==0:
            x+=variant_shift
        rooms.append({
            "room_id":f"R{i+1}",
            "zone":label,
            "storey_index":0,
            "x":x,"y":y,"width":4.0,"depth":4.0,
        })
    openings=[
        {
            "opening_id":f"O{i}",
            "x":slots[i%6][0]+1.0,
            "y":slots[i%6][1]+0.2,
            "width_m":1.2,
            "kind":"WINDOW",
        }
        for i in range(12)
    ]
    return {
        "rooms":rooms,
        "walls":[{"wall_id":f"W{i}"} for i in range(12)],
        "openings":openings,
    }

class SpatialQualityR2Tests(unittest.TestCase):
    def test_valid_layout_produces_spatial_score(self):
        result=evaluate_spatial_relationships(make_layout(),{"variant_id":"A","strategy":"BALANCED"})
        self.assertTrue(result["hard_pass"])
        self.assertGreater(result["score"],0)
        self.assertIn("connectivity",result["subscores"])
        self.assertIn("privacy",result["subscores"])

    def test_disconnected_layout_is_penalized(self):
        good=evaluate_spatial_relationships(make_layout(),{"variant_id":"A"})
        bad=evaluate_spatial_relationships(make_layout(disconnect=True),{"variant_id":"B"})
        self.assertLess(bad["score"],good["score"])
        self.assertGreaterEqual(bad["metrics"]["isolated_room_count"],1)

    def test_variant_set_returns_ranking_and_spread(self):
        rows=[]
        for idx,vid in enumerate("ABCDE"):
            rows.append(evaluate_spatial_relationships(make_layout(idx*0.05),{"variant_id":vid}))
        report=evaluate_variant_set_spatial_quality(rows)
        self.assertEqual(report["variant_count"],5)
        self.assertEqual(len(report["ranking_best_to_worst"]),5)
        self.assertGreaterEqual(report["score_spread"],0)

    def test_report_is_written(self):
        rows=[
            evaluate_spatial_relationships(make_layout(i*0.05),{"variant_id":vid})
            for i,vid in enumerate("ABCDE")
        ]
        report=evaluate_variant_set_spatial_quality(rows)
        with tempfile.TemporaryDirectory() as td:
            paths=write_spatial_quality_report(Path(td),report)
            self.assertTrue(Path(paths["json"]).is_file())
            self.assertTrue(Path(paths["markdown"]).is_file())

if __name__=="__main__":
    unittest.main()
