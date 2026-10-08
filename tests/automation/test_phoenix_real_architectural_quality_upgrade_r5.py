from __future__ import annotations
import unittest

from phoenix.design.tropical_residential.aec_topology_quality import analyze_aec_topology


def make_layout():
    labels=["ENTRY","LIVING","CIRCULATION","BEDROOM","BATH","WC","KITCHEN","BEDROOM"]
    rooms=[]
    for i,label in enumerate(labels):
        rooms.append({
            "room_id":f"R{i+1}",
            "zone":label,
            "storey_index":0,
            "x":(i%4)*4.1,
            "y":(i//4)*4.1,
            "width":4.0,
            "depth":4.0,
        })
    return {"rooms":rooms,"openings":[],"walls":[]}


class AECTopologyQualityR5Tests(unittest.TestCase):
    def test_distance_sensitive_metrics_exist(self):
        result=analyze_aec_topology(make_layout(),{"variant_id":"A","strategy":"PASSIVE_COOLING"})
        m=result["metrics"]
        for key in (
            "connectivity",
            "circulation_access",
            "privacy",
            "wet_core_clustering",
            "route_efficiency",
            "public_private_mean_path",
            "wet_core_mean_path",
            "mean_room_to_circulation_path",
        ):
            self.assertIn(key,m)

    def test_primary_topologicpy_or_explicit_fallback(self):
        result=analyze_aec_topology(make_layout(),{"variant_id":"E","strategy":"BALANCED"})
        e=result["engine"]
        self.assertEqual(e["primary_engine"],"TopologicPy TGraph")
        self.assertEqual(e["fallback_engine"],"NetworkX + Shapely")
        self.assertIn(e["distance_backend"],(
            "TopologicPy TGraph.Distance",
            "NetworkX shortest_path_length",
        ))

    def test_storey_normalized_connectivity(self):
        result=analyze_aec_topology(make_layout(),{"variant_id":"B","strategy":"LOW_COST"})
        self.assertGreaterEqual(result["metrics"]["connectivity"],95.0)
        self.assertEqual(result["metrics"]["isolated_room_count"],0)

    def test_result_is_deterministic(self):
        a=analyze_aec_topology(make_layout(),{"variant_id":"C","strategy":"RESILIENCE"})
        b=analyze_aec_topology(make_layout(),{"variant_id":"C","strategy":"RESILIENCE"})
        self.assertEqual(a["metrics"],b["metrics"])


if __name__=="__main__":
    unittest.main()
