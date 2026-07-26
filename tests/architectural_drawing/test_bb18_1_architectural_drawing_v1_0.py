from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.architectural_drawing import ArchitecturalDrawingEngine, DrawingType


def model() -> dict:
    return {
        "project_id": "PHX-DRAW-001",
        "name": "Drawing test",
        "levels": [
            {"id": "LVL-00", "name": "Ground floor", "elevation_m": 0.0},
            {"id": "LVL-01", "name": "First floor", "elevation_m": 3.2},
        ],
        "spaces": [
            {"id": "SPC-001", "level_id": "LVL-00", "name": "Room"},
        ],
        "elements": [
            {
                "id": "ELM-WALL-001",
                "level_id": "LVL-00",
                "category": "wall",
                "geometry": {"x_m": 0, "y_m": 0, "length_m": 5, "thickness_m": 0.2},
            }
        ],
    }


class ArchitecturalDrawingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ArchitecturalDrawingEngine()

    def test_package_contains_plan_per_level(self) -> None:
        package = self.engine.create_package(model())
        plans = [sheet for sheet in package.sheets if sheet.drawing_type == DrawingType.PLAN]
        self.assertEqual(2, len(plans))

    def test_package_contains_four_elevations_and_two_sections(self) -> None:
        package = self.engine.create_package(model())
        self.assertEqual(4, sum(sheet.drawing_type == DrawingType.ELEVATION for sheet in package.sheets))
        self.assertEqual(2, sum(sheet.drawing_type == DrawingType.SECTION for sheet in package.sheets))

    def test_sheet_ids_are_unique(self) -> None:
        package = self.engine.create_package(model())
        ids = [sheet.id for sheet in package.sheets]
        self.assertEqual(len(ids), len(set(ids)))

    def test_invalid_scale_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.create_package(model(), plan_scale=0)

    def test_manifest_export(self) -> None:
        package = self.engine.create_package(model())
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_manifest(package, Path(tmp) / "drawings.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("PHX-DRAW-001", data["project_id"])

    def test_svg_plan_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_plan_svg(model(), "LVL-00", Path(tmp) / "plan.svg")
            content = path.read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("ELM-WALL-001", content)

    def test_package_fingerprint_is_deterministic(self) -> None:
        first = self.engine.create_package(model())
        second = self.engine.create_package(model())
        self.assertEqual(
            first.metadata["package_fingerprint_sha256"],
            second.metadata["package_fingerprint_sha256"],
        )

    def test_to_dict_model_is_supported(self) -> None:
        class Model:
            def to_dict(self) -> dict:
                return model()
        package = self.engine.create_package(Model())
        self.assertEqual("PHX-DRAW-001", package.project_id)


if __name__ == "__main__":
    unittest.main()
