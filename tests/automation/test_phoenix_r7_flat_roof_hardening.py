from __future__ import annotations
import json
from pathlib import Path
import unittest

from phoenix.design.tropical_residential.canonical_host_geometry import finalize_canonical_host_geometry
from phoenix.design.tropical_residential.ifc_author import author_ifc4


class R7FlatRoofHardeningTests(unittest.TestCase):
    def _source_layout(self):
        repo=Path(__file__).resolve().parents[2]
        roots=[
            repo/"outputs"/"runtime"/"r7_runtime_facade_roof_opening_qa",
            repo/"outputs"/"runtime"/"phase19_start_screen_bridge",
        ]
        files=[]
        for root in roots:
            if root.exists():
                files.extend(root.rglob("real_spatial_layout.json"))
        files=sorted(files,key=lambda p:p.stat().st_mtime,reverse=True)
        self.assertTrue(files)
        for p in files:
            data=json.loads(p.read_text(encoding="utf-8-sig"))
            if float((data.get("roof") or {}).get("pitch_deg") or 0.0)==0.0:
                return data
        self.fail("No zero-pitch real layout found")

    def test_zero_pitch_is_explicit_flat_roof(self):
        layout=self._source_layout()
        finalize_canonical_host_geometry(layout)
        roof=layout["roof"]
        self.assertEqual(roof["roof_type"],"FLAT")
        self.assertEqual(roof["architectural_form"],"FLAT")
        self.assertEqual(float(roof["architectural_pitch_deg"]),0.0)
        self.assertEqual(roof["representation_stage"],"CANONICAL_FLAT_ROOF_IFC_VOLUME")
        self.assertEqual(roof["drainage_fall_model"],"SEPARATE_FROM_ARCHITECTURAL_FORM")

    def test_ifc_uses_flat_roof_semantics(self):
        repo=Path(__file__).resolve().parents[2]
        layout=self._source_layout()
        finalize_canonical_host_geometry(layout)
        out=repo/"outputs"/"runtime"/"r7_flat_roof_unit"/"flat_roof_test.ifc"
        ev=author_ifc4({"project_id":"R7-FLAT-ROOF-TEST"},layout,out)
        self.assertEqual(ev["IfcRoof"],1)
        import ifcopenshell
        model=ifcopenshell.open(str(out))
        roofs=model.by_type("IfcRoof")
        self.assertEqual(len(roofs),1)
        self.assertEqual(str(roofs[0].PredefinedType),"FLAT_ROOF")
        self.assertEqual(str(roofs[0].Name),"Flat Roof")

    def test_blender_zero_pitch_has_true_flat_path(self):
        repo=Path(__file__).resolve().parents[2]
        p=repo/"phoenix"/"design"/"tropical_residential"/"blender_tropical_scene_script.py"
        text=p.read_text(encoding="utf-8-sig")
        self.assertIn("def flat_roof(",text)
        self.assertGreaterEqual(text.count("pitch <= 0.01"),3)
        self.assertIn('mesh_object("Roof_Flat"',text)


if __name__=="__main__":
    unittest.main()
