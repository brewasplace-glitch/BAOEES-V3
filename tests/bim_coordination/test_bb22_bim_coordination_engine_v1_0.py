from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bim_coordination import (
    BimCoordinationEngine,
    BimCoordinationExporter,
)


def architectural_model() -> dict:
    return {
        "project_id": "PHX-BB22-TEST",
        "elements": [
            {
                "id": "DOOR-001",
                "category": "door",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [2.0, 0.0, 0.0, 3.0, 0.3, 2.1]
                },
            },
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [0.0, 0.0, 0.0, 5.0, 0.2, 3.0]
                },
            },
        ],
    }


def structural_model() -> dict:
    return {
        "project_id": "PHX-BB22-TEST",
        "structural_elements": [
            {
                "id": "BEAM-001",
                "category": "beam",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [2.2, 0.0, 1.8, 4.0, 0.4, 2.3]
                },
            },
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [0.0, 0.0, 0.0, 5.1, 0.2, 3.0]
                },
            },
        ],
    }


def quantity_report() -> dict:
    return {
        "records": [
            {
                "quantity_id": "Q-DOOR-COUNT",
                "source_object_id": "DOOR-001",
                "quantity_type": "count",
                "value": 1,
                "unit": "ea",
            },
            {
                "quantity_id": "Q-BEAM-VOLUME",
                "source_object_id": "BEAM-001",
                "quantity_type": "beam_volume",
                "value": 0.18,
                "unit": "m3",
            },
            {
                "quantity_id": "Q-WALL-AREA",
                "source_object_id": "WALL-001",
                "quantity_type": "gross_wall_area",
                "value": 15,
                "unit": "m2",
            },
        ]
    }


def cost_report() -> dict:
    return {
        "items": [
            {
                "cost_item_id": "C-001",
                "quantity_id": "Q-DOOR-COUNT",
                "total_cost": 500,
            },
            {
                "cost_item_id": "C-002",
                "quantity_id": "Q-BEAM-VOLUME",
                "total_cost": 200,
            },
        ]
    }


class BimCoordinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BimCoordinationEngine()
        self.exporter = BimCoordinationExporter()

    def test_hard_clash_is_detected(self) -> None:
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            }
        )
        clashes = [
            issue
            for issue in report.issues
            if issue.issue_type == "hard_geometric_clash"
        ]
        self.assertEqual(1, len(clashes))
        self.assertEqual("DOOR-001", clashes[0].source_object_id)
        self.assertEqual("BEAM-001", clashes[0].target_object_id)

    def test_shared_geometry_drift_is_detected(self) -> None:
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            }
        )
        self.assertTrue(
            any(
                issue.issue_type == "shared_geometry_drift"
                and issue.source_object_id == "WALL-001"
                for issue in report.issues
            )
        )

    def test_different_project_ids_are_critical(self) -> None:
        structure = structural_model()
        structure["project_id"] = "OTHER-PROJECT"
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structure,
            }
        )
        issue = next(
            item
            for item in report.issues
            if item.issue_type == "project_identity_conflict"
        )
        self.assertEqual("critical", issue.severity.value)
        self.assertFalse(report.coordination_passed)

    def test_duplicate_object_id_is_detected(self) -> None:
        architecture = architectural_model()
        architecture["elements"].append(
            dict(architecture["elements"][0])
        )
        report = self.engine.coordinate({"architecture": architecture})
        self.assertTrue(
            any(
                issue.issue_type == "duplicate_object_id"
                for issue in report.issues
            )
        )

    def test_orphan_quantity_is_detected(self) -> None:
        quantities = quantity_report()
        quantities["records"].append(
            {
                "quantity_id": "Q-ORPHAN",
                "source_object_id": "UNKNOWN-001",
                "quantity_type": "count",
                "value": 1,
                "unit": "ea",
            }
        )
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            },
            quantity_report=quantities,
        )
        self.assertTrue(
            any(
                issue.issue_type == "orphan_quantity"
                for issue in report.issues
            )
        )

    def test_cost_reconciliation_detects_missing_cost(self) -> None:
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            },
            quantity_report=quantity_report(),
            cost_report=cost_report(),
        )
        missing = [
            issue
            for issue in report.issues
            if issue.issue_type == "quantity_without_cost"
        ]
        self.assertEqual(1, len(missing))
        self.assertIn("Q-WALL-AREA", missing[0].description)

    def test_orphan_cost_item_is_detected(self) -> None:
        costs = cost_report()
        costs["items"].append(
            {
                "cost_item_id": "C-ORPHAN",
                "quantity_id": "Q-UNKNOWN",
                "total_cost": 100,
            }
        )
        report = self.engine.coordinate(
            {"architecture": architectural_model()},
            quantity_report=quantity_report(),
            cost_report=costs,
        )
        self.assertTrue(
            any(
                issue.issue_type == "orphan_cost_item"
                for issue in report.issues
            )
        )

    def test_issue_ids_and_report_fingerprint_are_deterministic(self) -> None:
        first = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            },
            quantity_report=quantity_report(),
            cost_report=cost_report(),
        )
        second = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            },
            quantity_report=quantity_report(),
            cost_report=cost_report(),
        )
        self.assertEqual(
            [issue.issue_id for issue in first.issues],
            [issue.issue_id for issue in second.issues],
        )
        self.assertEqual(
            self.engine.fingerprint_report(first),
            self.engine.fingerprint_report(second),
        )

    def test_object_with_to_dict_is_supported(self) -> None:
        class ModelObject:
            def to_dict(self) -> dict:
                return architectural_model()

        report = self.engine.coordinate({"architecture": ModelObject()})
        self.assertEqual("PHX-BB22-TEST", report.project_id)

    def test_negative_tolerance_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.coordinate(
                {"architecture": architectural_model()},
                tolerance_m=-0.001,
            )

    def test_json_csv_xlsx_and_bcf_exports(self) -> None:
        report = self.engine.coordinate(
            {
                "architecture": architectural_model(),
                "structure": structural_model(),
            },
            quantity_report=quantity_report(),
            cost_report=cost_report(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = self.exporter.export_json(
                report,
                root / "coordination.json",
            )
            csv_path = self.exporter.export_csv(
                report,
                root / "issues.csv",
            )
            xlsx_path = self.exporter.export_xlsx(
                report,
                root / "issues.xlsx",
            )
            bcf_path = self.exporter.export_bcfzip(
                report,
                root / "issues.bcfzip",
            )

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report.issues), data["issue_count"])

            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(report.issues), len(rows))

            with zipfile.ZipFile(xlsx_path) as archive:
                xlsx_names = set(archive.namelist())
            self.assertIn("xl/worksheets/sheet1.xml", xlsx_names)

            with zipfile.ZipFile(bcf_path) as archive:
                bcf_names = set(archive.namelist())
            self.assertIn("bcf.version", bcf_names)
            self.assertIn("project.bcfp", bcf_names)
            self.assertTrue(
                any(name.endswith("/markup.bcf") for name in bcf_names)
            )

    def test_clean_models_can_pass(self) -> None:
        clean_architecture = {
            "project_id": "PHX-CLEAN",
            "elements": [
                {
                    "id": "WALL-A",
                    "category": "wall",
                    "level_id": "L0",
                    "geometry": {
                        "bbox": [0, 0, 0, 5, 0.2, 3]
                    },
                }
            ],
        }
        clean_structure = {
            "project_id": "PHX-CLEAN",
            "structural_elements": [
                {
                    "id": "BEAM-A",
                    "category": "beam",
                    "level_id": "L0",
                    "geometry": {
                        "bbox": [0, 1, 2.5, 5, 1.3, 3]
                    },
                }
            ],
        }
        report = self.engine.coordinate(
            {
                "architecture": clean_architecture,
                "structure": clean_structure,
            }
        )
        self.assertTrue(report.coordination_passed)


if __name__ == "__main__":
    unittest.main()
