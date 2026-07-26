from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from phoenix.building_model import BuildingModelEngine, ElementCategory
from phoenix.building_model.adapters import SciaEngineerAdapter, SketchUpAdapter

class BuildingModelEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BuildingModelEngine()
        self.model = self.engine.create_model("PHX-TEST-001", "BB16 Test")
        self.engine.add_level(self.model, level_id="LVL-00", name="Ground floor",
                              elevation_m=0.0, height_m=3.2)

    def test_roundtrip_and_fingerprint(self) -> None:
        self.engine.add_space(self.model, space_id="SPC-001", name="Main room",
                              level_id="LVL-00", area_m2=42.5)
        self.engine.add_element(
            self.model, element_id="ELM-WALL-001", name="Wall 1",
            category=ElementCategory.WALL, level_id="LVL-00",
            geometry={"length_m": 5.0, "height_m": 3.2, "thickness_m": 0.2},
            material={"name": "masonry"})
        first = self.engine.fingerprint(self.model)
        self.assertEqual(first, self.engine.fingerprint(self.model))
        self.assertEqual([], [i for i in self.engine.validate(self.model) if i.severity == "error"])
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_json(self.model, Path(tmp) / "model.json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(first, data["fingerprint_sha256"])

    def test_duplicate_ids_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.add_level(self.model, level_id="LVL-00", name="Duplicate", elevation_m=3.2)

    def test_unknown_level_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.engine.add_space(self.model, space_id="SPC-002", name="Invalid", level_id="LVL-99")

    def test_adapters_return_status(self) -> None:
        for adapter in (SketchUpAdapter(), SciaEngineerAdapter()):
            status = adapter.detect().to_dict()
            self.assertIn("available", status)
            self.assertIn("mode", status)

if __name__ == "__main__":
    unittest.main()
