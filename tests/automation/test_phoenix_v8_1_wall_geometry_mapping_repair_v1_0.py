from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT=Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0,str(REPOSITORY_ROOT))

from phoenix.autonomy.structural_session_chain import build_v81_input


class WallGeometryMappingRepairTests(unittest.TestCase):
    def _inputs(self,wall):
        wall=dict(wall)
        wall.setdefault("height_m",3.3)
        v80={
            "schema_version":"phoenix.structural-candidate-model/8.0.0",
            "walls":[{
                "structural_id":"SW-W1",
                "architectural_element_id":"W1",
                "candidate_type":"loadbearing_wall",
                "storey_id":"L00",
                "material_hypothesis":"masonry_candidate",
                "thickness_m":0.3,
            }],
        }
        storey={"storey_id":"L00","elevation_m":0.0}
        architectural={"storeys":[dict(storey)]}
        detailed={"storeys":[dict(storey,walls=[wall])]}
        return v80,architectural,detailed

    def test_canonical_start_end_maps_source_backed_wall_polygon(self):
        values=self._inputs({
            "element_id":"W1","storey_id":"L00",
            "start":[0.0,0.0],"end":[9.9,0.0],"length_m":9.9,
        })
        payload,mapping=build_v81_input(*values)
        wall=payload["structural_candidates"]["loadbearing_walls"][0]
        self.assertEqual(wall["polygon"],[[0.0,0.0,0.0],[9.9,0.0,0.0],[9.9,0.0,3.3],[0.0,0.0,3.3]])
        self.assertEqual(wall["source_geometry_schema"],"start_end_xy")
        self.assertEqual(wall["source_height_schema"],"detailed_wall_height_m")
        self.assertFalse(mapping["design_values_invented"])
        self.assertEqual(mapping["wall_geometry_contract"],{
            "source_backed":True,
            "mapped_wall_count":1,
            "source_schemas":["start_end_xy"],
            "height_sources":["detailed_wall_height_m"],
            "silent_zero_fallback":False,
        })

    def test_wall_height_uses_explicit_wall_source_without_storey_default(self):
        values=self._inputs({
            "element_id":"W1","start":[0.0,0.0],"end":[2.0,0.0],"length_m":2.0,"height_m":4.2,
        })
        payload,mapping=build_v81_input(*values)
        wall=payload["structural_candidates"]["loadbearing_walls"][0]
        self.assertEqual([point[2] for point in wall["polygon"]],[0.0,0.0,4.2,4.2])
        self.assertEqual(mapping["wall_geometry_contract"]["height_sources"],["detailed_wall_height_m"])

    def test_canonical_coordinates_take_precedence_over_legacy_fields(self):
        values=self._inputs({
            "element_id":"W1","start":[1.0,2.0],"end":[4.0,6.0],"length_m":5.0,
            "x1_m":0.0,"y1_m":0.0,"x2_m":0.0,"y2_m":0.0,
        })
        payload,_=build_v81_input(*values)
        polygon=payload["structural_candidates"]["loadbearing_walls"][0]["polygon"]
        self.assertEqual(polygon[0][:2],[1.0,2.0])
        self.assertEqual(polygon[1][:2],[4.0,6.0])

    def test_explicit_legacy_endpoint_scalars_remain_supported(self):
        values=self._inputs({
            "element_id":"W1","x1_m":1.0,"y1_m":2.0,"x2_m":4.0,"y2_m":6.0,"length_m":5.0,
        })
        payload,mapping=build_v81_input(*values)
        wall=payload["structural_candidates"]["loadbearing_walls"][0]
        self.assertEqual(wall["polygon"][0][:2],[1.0,2.0])
        self.assertEqual(wall["source_geometry_schema"],"legacy_explicit_endpoint_scalars")
        self.assertEqual(mapping["wall_geometry_contract"]["mapped_wall_count"],1)

    def test_missing_coordinates_fail_closed_without_silent_zero_fallback(self):
        values=self._inputs({"element_id":"W1"})
        with self.assertRaisesRegex(ValueError,"Wall geometry invalid for SW-W1"):
            build_v81_input(*values)

    def test_identical_endpoints_fail_closed(self):
        values=self._inputs({"element_id":"W1","start":[0.0,0.0],"end":[0.0,0.0]})
        with self.assertRaisesRegex(ValueError,"endpoints must be distinct"):
            build_v81_input(*values)

    def test_declared_length_must_match_endpoint_geometry(self):
        values=self._inputs({"element_id":"W1","start":[0.0,0.0],"end":[3.0,4.0],"length_m":6.0})
        with self.assertRaisesRegex(ValueError,"does not match length_m"):
            build_v81_input(*values)


if __name__ == "__main__":
    unittest.main()
