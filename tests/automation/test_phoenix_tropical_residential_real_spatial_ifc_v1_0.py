from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.design.tropical_residential.engine import generate_variants, select_balanced
from phoenix.design.tropical_residential.ifc_author import author_ifc4
from phoenix.design.tropical_residential.real_spatial import build_real_layout
from phoenix.design.tropical_residential.tool_discovery import discover_tools


ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"tests/fixtures/phoenix_tropical_residential_demo_v1_0.json"


class TestTropicalRealSpatialIfcV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project=json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.variants=generate_variants(cls.project)
        cls.layouts=[build_real_layout(cls.project,v.to_dict()) for v in cls.variants]

    def test_five_real_layouts(self):
        self.assertEqual([x["variant_id"] for x in self.layouts],["A","B","C","D","E"])
        for x in self.layouts:
            self.assertGreater(len(x["rooms"]),5)
            self.assertGreater(len(x["walls"]),4)
            self.assertGreater(len(x["openings"]),2)

    def test_shapely_geometry_is_valid(self):
        for x in self.layouts:
            self.assertTrue(x["geometry_validation"]["valid"],x["geometry_validation"])

    def test_rooms_have_real_coordinates(self):
        for x in self.layouts:
            for r in x["rooms"]:
                self.assertGreater(r["width"],0)
                self.assertGreater(r["depth"],0)
                self.assertGreater(r["area_m2"],0)
                self.assertGreaterEqual(r["x"],0)
                self.assertGreaterEqual(r["y"],0)

    def test_doors_and_windows_exist(self):
        for x in self.layouts:
            kinds={o["kind"] for o in x["openings"]}
            self.assertIn("door",kinds)
            self.assertIn("window",kinds)

    def test_tool_discovery_contract(self):
        tools=discover_tools()
        self.assertIn("freecad",tools)
        self.assertIn("blender",tools)
        for k in ("freecad","blender"):
            self.assertIn("found",tools[k])
            self.assertIn("role",tools[k])

    def test_actual_ifc4_authoring_and_reopen(self):
        recommended=select_balanced(self.variants)
        layout=next(x for x in self.layouts if x["variant_id"]==recommended.variant_id)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"authoritative.ifc"
            ev=author_ifc4(self.project,layout,p)
            self.assertTrue(p.is_file())
            self.assertGreater(ev["bytes"],3000)
            self.assertEqual(ev["IfcProject"],1)
            self.assertEqual(ev["IfcSite"],1)
            self.assertEqual(ev["IfcBuilding"],1)
            self.assertEqual(ev["IfcBuildingStorey"],layout["storeys"])
            self.assertGreaterEqual(ev["IfcWall"],4*layout["storeys"])
            self.assertGreater(ev["IfcSpace"],5)
            self.assertGreater(ev["IfcOpeningElement"],0)
            self.assertGreater(ev["IfcDoor"],0)
            self.assertGreater(ev["IfcWindow"],0)
            self.assertEqual(ev["release_status"],"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")

    def test_release_governance(self):
        for x in self.layouts:
            g=x["governance"]
            self.assertEqual(g["professional_approval"],"NOT_AUTOMATIC")
            self.assertEqual(g["code_compliance"],"NOT_AUTOMATIC")
            self.assertEqual(g["for_construction"],"LOCKED")


if __name__=="__main__":
    unittest.main(verbosity=2)
