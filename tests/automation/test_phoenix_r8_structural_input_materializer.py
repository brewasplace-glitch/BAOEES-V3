from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from phoenix.design.tropical_residential.structural_input_materializer import materialization_eligibility, materialize_structural_adapter_inputs

class R8StructuralInputMaterializerFixR1Tests(unittest.TestCase):
    def _valid(self, root: Path):
        layout={"variant_id":"E","strategy":"BALANCED","storeys":2,"storey_height_m":3.0,
                "elevation":{"raised_floor_m":0.25},"footprint":{"width_m":10.0,"depth_m":8.0},
                "rooms":[{"room_id":"R1","storey_index":0,"area_m2":20.0},{"room_id":"R2","storey_index":1,"area_m2":16.0}],
                "walls":[{"wall_id":"W1","storey_index":0},{"wall_id":"W2","storey_index":1}],
                "openings":[{"opening_id":"D1","kind":"door","storey_index":0},{"opening_id":"WIN1","kind":"window","storey_index":1}],
                "roof":{"roof_type":"FLAT","architectural_pitch_deg":0.0}}
        p=root/"layout.json"; p.write_text(json.dumps(layout),encoding="utf-8")
        i=root/"a.ifc"; i.write_bytes(b"IFC4")
        return p,i

    def test_minimal_fixture_is_ineligible(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"minimal.json"; p.write_text('{"variant_id":"E"}',encoding="utf-8")
            e=materialization_eligibility(p)
            self.assertFalse(e["eligible"])
            self.assertIn("STOREY_COUNT_REQUIRED",e["reasons"])

    def test_valid_shape_materializes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p,i=self._valid(root)
            result=materialize_structural_adapter_inputs(
                project_id="P",recommended_variant_id="E",
                canonical_layout_json=p,authoritative_ifc=i,output_dir=root/"out")
            self.assertEqual(result["status"],"MATERIALIZED_READY_FOR_EXISTING_STRUCTURAL_ADAPTER")
            self.assertFalse(result["solver_execution_started"])

if __name__=="__main__":
    unittest.main()
