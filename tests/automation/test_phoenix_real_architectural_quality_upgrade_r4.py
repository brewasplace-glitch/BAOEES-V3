from __future__ import annotations

import unittest

from phoenix.design.tropical_residential.geometry_topology import apply_geometry_topology
from phoenix.design.tropical_residential.spatial_quality import evaluate_spatial_relationships


def layout():
    labels=[
        "LIVING","KITCHEN","BEDROOM","BEDROOM","BATH","CIRCULATION",
        "STUDY","WC","DINING","BEDROOM","LAUNDRY","LOUNGE",
    ]
    dims=[
        (4.2,4.0),(3.2,3.8),(3.5,3.6),(3.7,3.4),(2.4,2.8),(2.0,4.5),
        (3.1,3.2),(1.8,2.2),(3.5,3.5),(3.4,3.2),(2.2,2.8),(4.0,3.8),
    ]
    rooms=[]
    for i,(label,(w,d)) in enumerate(zip(labels,dims)):
        rooms.append({
            "room_id":f"R{i+1}",
            "zone":label,
            "storey_index":0,
            "x":(i%4)*4.5,
            "y":(i//4)*4.5,
            "width":w,
            "depth":d,
        })
    openings=[
        {"opening_id":f"O{i}","x":rooms[i%12]["x"]+0.5,"y":rooms[i%12]["y"]+0.1,"kind":"WINDOW"}
        for i in range(24)
    ]
    return {"rooms":rooms,"walls":[],"openings":openings}


class OpenSourceSpatialR4FixR3Tests(unittest.TestCase):
    def test_open_source_stack_is_bound(self):
        out=apply_geometry_topology(layout(),{"variant_id":"A","strategy":"PASSIVE_COOLING"})
        meta=out["open_source_spatial_engine"]
        self.assertEqual(meta["solver"],"OR-Tools CP-SAT")
        self.assertEqual(meta["geometry_engine"],"Shapely")
        self.assertEqual(meta["graph_engine"],"NetworkX")
        self.assertEqual(meta["custom_code_role"],"ORCHESTRATION_ADAPTER_GOVERNANCE_ONLY")

    def test_variable_room_sizes_have_no_isolates(self):
        for vid,strategy in [
            ("A","PASSIVE_COOLING"),
            ("B","LOW_COST"),
            ("C","RESILIENCE"),
            ("D","INDOOR_OUTDOOR"),
            ("E","BALANCED"),
        ]:
            out=apply_geometry_topology(layout(),{"variant_id":vid,"strategy":strategy})
            self.assertEqual(out["circulation_graph"]["isolated_room_count"],0)

    def test_all_variants_spatial_hard_pass(self):
        for vid,strategy in [
            ("A","PASSIVE_COOLING"),
            ("B","LOW_COST"),
            ("C","RESILIENCE"),
            ("D","INDOOR_OUTDOOR"),
            ("E","BALANCED"),
        ]:
            out=apply_geometry_topology(layout(),{"variant_id":vid,"strategy":strategy})
            qa=evaluate_spatial_relationships(out,{"variant_id":vid,"strategy":strategy})
            self.assertTrue(qa["hard_pass"],msg=f"{vid}:{qa}")

    def test_strategies_produce_different_geometry(self):
        signatures=[]
        for vid,strategy in [
            ("A","PASSIVE_COOLING"),
            ("B","LOW_COST"),
            ("C","RESILIENCE"),
            ("D","INDOOR_OUTDOOR"),
            ("E","BALANCED"),
        ]:
            out=apply_geometry_topology(layout(),{"variant_id":vid,"strategy":strategy})
            signatures.append(tuple(
                (r.get("room_id"),r.get("x"),r.get("y"))
                for r in out["rooms"]
            ))
        self.assertGreaterEqual(len(set(signatures)),4)

    def test_spatial_scores_are_not_all_identical(self):
        scores=[]
        for vid,strategy in [
            ("A","PASSIVE_COOLING"),
            ("B","LOW_COST"),
            ("C","RESILIENCE"),
            ("D","INDOOR_OUTDOOR"),
            ("E","BALANCED"),
        ]:
            out=apply_geometry_topology(layout(),{"variant_id":vid,"strategy":strategy})
            qa=evaluate_spatial_relationships(out,{"variant_id":vid,"strategy":strategy})
            scores.append(qa["score"])
        self.assertGreater(len(set(scores)),1)


if __name__=="__main__":
    unittest.main()
