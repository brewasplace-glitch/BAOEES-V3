from __future__ import annotations
import unittest
from phoenix.design.tropical_residential.strategy_topology import apply_strategy_topology
from phoenix.design.tropical_residential.spatial_quality import evaluate_spatial_relationships

def layout():
    labels=["LIVING","KITCHEN","BEDROOM","BEDROOM","BATH","CIRCULATION","STUDY","WC"]
    slots=[(0,0),(4.2,0),(8.4,0),(12.6,0),(0,4.2),(4.2,4.2),(8.4,4.2),(12.6,4.2)]
    rooms=[]
    for i,(label,(x,y)) in enumerate(zip(labels,slots)):
        rooms.append({"room_id":f"R{i+1}","zone":label,"storey_index":0,"x":x,"y":y,"width":4.0,"depth":4.0})
    openings=[{"opening_id":f"O{i}","x":slots[i%8][0]+1.0,"y":slots[i%8][1]+0.2,"width_m":1.2,"kind":"WINDOW"} for i in range(16)]
    return {"rooms":rooms,"walls":[{"wall_id":f"W{i}"} for i in range(20)],"openings":openings}

class StrategyTopologyR3Tests(unittest.TestCase):
    def test_preserves_slot_geometry(self):
        base=layout();out=apply_strategy_topology(base,{"variant_id":"C","strategy":"RESILIENCE"})
        before=sorted((r["x"],r["y"],r["width"],r["depth"]) for r in base["rooms"])
        after=sorted((r["x"],r["y"],r["width"],r["depth"]) for r in out["rooms"])
        self.assertEqual(before,after)

    def test_preserves_room_program(self):
        base=layout();out=apply_strategy_topology(base,{"variant_id":"D","strategy":"INDOOR_OUTDOOR"})
        self.assertEqual(sorted(r["zone"] for r in base["rooms"]),sorted(r["zone"] for r in out["rooms"]))

    def test_strategies_differ(self):
        base=layout();fps=[]
        for vid,strategy in [("A","PASSIVE_COOLING"),("B","LOW_COST"),("C","RESILIENCE"),("D","INDOOR_OUTDOOR"),("E","BALANCED")]:
            out=apply_strategy_topology(base,{"variant_id":vid,"strategy":strategy})
            fps.append(tuple(r["zone"] for r in out["rooms"]))
        self.assertGreaterEqual(len(set(fps)),4)

    def test_spatial_scores_can_differ(self):
        base=layout();scores=[]
        for vid,strategy in [("A","PASSIVE_COOLING"),("B","LOW_COST"),("C","RESILIENCE"),("D","INDOOR_OUTDOOR"),("E","BALANCED")]:
            out=apply_strategy_topology(base,{"variant_id":vid,"strategy":strategy})
            scores.append(evaluate_spatial_relationships(out,{"variant_id":vid,"strategy":strategy})["score"])
        self.assertGreater(len(set(scores)),1)

if __name__=="__main__":
    unittest.main()
