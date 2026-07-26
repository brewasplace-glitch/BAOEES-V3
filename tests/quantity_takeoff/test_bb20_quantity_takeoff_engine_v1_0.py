from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.quantity_takeoff import (
    QuantityTakeoffEngine,
    QuantityTakeoffExporter,
)


def building_model() -> dict:
    return {
        "project_id": "PHX-QTO-TEST",
        "schema_version": "phoenix.building-model/1.0",
        "units": "SI",
        "levels": [{"id": "LVL-00", "name": "Ground floor"}],
        "elements": [
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "length_m": 5.0,
                    "height_m": 3.0,
                    "thickness_m": 0.2,
                    "density_kg_m3": 1800.0,
                },
                "material": {"name": "masonry"},
                "drawing_refs": ["A-101"],
            },
            {
                "id": "SLAB-001",
                "category": "slab",
                "level_id": "LVL-00",
                "geometry": {
                    "length_m": 5.0,
                    "width_m": 4.0,
                    "thickness_m": 0.2,
                },
                "material": {"name": "concrete"},
            },
            {
                "id": "DOOR-001",
                "category": "door",
                "level_id": "LVL-00",
                "geometry": {"width_m": 1.0, "height_m": 2.1},
                "material": {"name": "timber"},
            },
        ],
    }


class QuantityTakeoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = QuantityTakeoffEngine()
        self.exporter = QuantityTakeoffExporter()

    def test_expected_wall_slab_and_door_quantities(self) -> None:
        report = self.engine.generate(building_model())
        values = {
            (record.source_object_id, record.quantity_type): record.value
            for record in report.records
        }
        self.assertEqual(15.0, values[("WALL-001", "gross_wall_area")])
        self.assertEqual(3.0, values[("WALL-001", "wall_volume")])
        self.assertEqual(20.0, values[("SLAB-001", "slab_area")])
        self.assertEqual(2.1, values[("DOOR-001", "door_area")])

    def test_material_mass_is_calculated_from_density(self) -> None:
        report = self.engine.generate(building_model())
        mass = next(
            record.value
            for record in report.records
            if record.quantity_type == "wall_mass"
        )
        self.assertEqual(5400.0, mass)

    def test_missing_dimensions_create_warning_but_keep_count(self) -> None:
        model = building_model()
        model["elements"].append(
            {
                "id": "WINDOW-002",
                "category": "window",
                "level_id": "LVL-00",
                "geometry": {},
            }
        )
        report = self.engine.generate(model)
        self.assertTrue(
            any(
                issue.source_object_id == "WINDOW-002"
                and issue.code == "QTO-DIM-002"
                for issue in report.issues
            )
        )
        self.assertTrue(
            any(
                record.source_object_id == "WINDOW-002"
                and record.quantity_type == "count"
                for record in report.records
            )
        )

    def test_structural_model_takes_precedence_for_duplicate_structural_id(self) -> None:
        structural = {
            "project_id": "PHX-QTO-TEST",
            "structural_elements": [
                {
                    "id": "SLAB-001",
                    "category": "slab",
                    "level_id": "LVL-00",
                    "geometry": {
                        "length_m": 6.0,
                        "width_m": 4.0,
                        "thickness_m": 0.25,
                    },
                    "material": {"name": "reinforced concrete"},
                }
            ],
        }
        report = self.engine.generate(
            building_model(),
            structural_model=structural,
        )
        slab_areas = [
            record.value
            for record in report.records
            if record.source_object_id == "SLAB-001"
            and record.quantity_type == "slab_area"
        ]
        self.assertEqual([24.0], slab_areas)
        self.assertTrue(
            any(issue.code == "QTO-SOURCE-001" for issue in report.issues)
        )

    def test_declared_quantities_are_ingested(self) -> None:
        model = building_model()
        model["elements"][0]["properties"] = {
            "declared_quantities": {
                "reinforcement": {"value": 125.0, "unit": "kg"}
            }
        }
        report = self.engine.generate(model)
        declared = next(
            record
            for record in report.records
            if record.quantity_type == "reinforcement"
        )
        self.assertEqual("declared", declared.basis.value)
        self.assertEqual(125.0, declared.value)

    def test_drawing_manifest_adds_traceability(self) -> None:
        drawings = {"element_drawing_map": {"SLAB-001": ["S-101", "A-102"]}}
        report = self.engine.generate(
            building_model(),
            drawing_manifest=drawings,
        )
        slab = next(
            record
            for record in report.records
            if record.source_object_id == "SLAB-001"
        )
        self.assertEqual(("A-102", "S-101"), slab.drawing_refs)

    def test_report_fingerprint_is_deterministic(self) -> None:
        first = self.engine.generate(building_model())
        second = self.engine.generate(building_model())
        self.assertEqual(
            self.engine.fingerprint_report(first),
            self.engine.fingerprint_report(second),
        )

    def test_object_with_to_dict_is_supported(self) -> None:
        class ModelObject:
            def to_dict(self) -> dict:
                return building_model()

        report = self.engine.generate(ModelObject())
        self.assertEqual("PHX-QTO-TEST", report.project_id)

    def test_json_csv_and_xlsx_exports(self) -> None:
        report = self.engine.generate(building_model())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = self.exporter.export_json(report, root / "qto.json")
            csv_path = self.exporter.export_csv(report, root / "qto.csv")
            xlsx_path = self.exporter.export_xlsx(report, root / "qto.xlsx")

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report.records), data["record_count"])

            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(report.records), len(rows))

            with zipfile.ZipFile(xlsx_path) as archive:
                names = set(archive.namelist())
            self.assertIn("xl/worksheets/sheet1.xml", names)
            self.assertIn("xl/worksheets/sheet2.xml", names)

    def test_totals_are_grouped_by_level_and_material(self) -> None:
        report = self.engine.generate(building_model())
        self.assertIn("LVL-00", report.totals_by_level)
        self.assertIn("masonry", report.totals_by_material)
        self.assertIn("m3", report.totals_by_material["masonry"])


if __name__ == "__main__":
    unittest.main()
