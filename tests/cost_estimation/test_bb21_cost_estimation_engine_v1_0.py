from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.cost_estimation import (
    CostEstimateExporter,
    CostEstimationEngine,
    CostScenario,
    RateBookLoader,
)


ROOT = Path(__file__).resolve().parents[2]
RATEBOOK_PATH = (
    ROOT
    / "configs"
    / "phoenix"
    / "cost_ratebooks"
    / "phoenix_synthetic_test_ratebook_v1_0.json"
)


def quantity_report() -> dict:
    return {
        "project_id": "PHX-COST-TEST",
        "schema_version": "phoenix.quantity-takeoff-report/1.0",
        "records": [
            {
                "quantity_id": "QTO-WALL-VOLUME",
                "source_object_id": "WALL-001",
                "source_model": "building_model",
                "source_level_id": "LVL-00",
                "category": "wall",
                "work_section": "04 Walls and partitions",
                "material": "masonry",
                "quantity_type": "wall_volume",
                "value": 3.0,
                "unit": "m3",
                "drawing_refs": ["A-101"],
                "metadata": {},
            },
            {
                "quantity_id": "QTO-SLAB-VOLUME",
                "source_object_id": "SLAB-001",
                "source_model": "structural_model",
                "source_level_id": "LVL-00",
                "category": "slab",
                "work_section": "05 Floors and slabs",
                "material": "concrete",
                "quantity_type": "slab_volume",
                "value": 4.0,
                "unit": "m3",
                "drawing_refs": ["S-101"],
                "metadata": {},
            },
            {
                "quantity_id": "QTO-DOOR-COUNT",
                "source_object_id": "DOOR-001",
                "source_model": "building_model",
                "source_level_id": "LVL-00",
                "category": "door",
                "work_section": "07 Doors",
                "material": "timber",
                "quantity_type": "count",
                "value": 2.0,
                "unit": "ea",
                "drawing_refs": ["A-201"],
                "metadata": {},
            },
            {
                "quantity_id": "QTO-UNMATCHED",
                "source_object_id": "WINDOW-001",
                "source_model": "building_model",
                "source_level_id": "LVL-00",
                "category": "window",
                "work_section": "08 Windows",
                "material": "glass",
                "quantity_type": "window_area",
                "value": 5.0,
                "unit": "m2",
                "drawing_refs": [],
                "metadata": {},
            },
        ],
    }


def base_scenario() -> CostScenario:
    return CostScenario(
        id="SCENARIO-BASE",
        name="Base",
        currency="EUR",
        overhead_percent=10.0,
        risk_percent=5.0,
        contingency_percent=3.0,
        profit_percent=4.0,
    )


class CostEstimationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = RateBookLoader()
        self.ratebook = self.loader.load_file(RATEBOOK_PATH)
        self.engine = CostEstimationEngine()
        self.exporter = CostEstimateExporter()

    def test_ratebook_loads_and_fingerprint_is_deterministic(self) -> None:
        self.assertEqual("EUR", self.ratebook.currency)
        self.assertEqual(
            self.loader.fingerprint(self.ratebook),
            self.loader.fingerprint(self.ratebook),
        )

    def test_base_estimate_prices_three_lines(self) -> None:
        report = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        estimate = report.scenarios[0]
        self.assertEqual(3, len(estimate.lines))
        self.assertEqual(["QTO-UNMATCHED"], estimate.unmatched_quantities)
        self.assertGreater(estimate.total_cost, estimate.direct_cost)

    def test_expected_direct_cost(self) -> None:
        report = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        estimate = report.scenarios[0]
        # Wall: 3 * 1.05 * 160 = 504
        # Slab: 4 * 1.02 * 180 = 734.4
        # Doors: 2 * 400 = 800
        self.assertEqual(2038.40, estimate.direct_cost)

    def test_allowance_sequence_is_applied(self) -> None:
        report = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        estimate = report.scenarios[0]
        self.assertEqual(203.84, estimate.overhead_cost)
        self.assertEqual(112.11, estimate.risk_cost)
        self.assertEqual(70.63, estimate.contingency_cost)
        self.assertEqual(97.00, estimate.profit_cost)
        self.assertEqual(2521.98, estimate.total_cost)

    def test_conservative_scenario_is_higher_than_base(self) -> None:
        conservative = CostScenario(
            id="SCENARIO-HIGH",
            name="High",
            currency="EUR",
            quantity_factor=1.05,
            location_factor=1.05,
            escalation_percent=3.0,
            material_factor=1.05,
            labor_factor=1.05,
            equipment_factor=1.05,
            subcontract_factor=1.05,
            other_factor=1.05,
            overhead_percent=12.0,
            risk_percent=8.0,
            contingency_percent=5.0,
            profit_percent=5.0,
        )
        report = self.engine.estimate(
            quantity_report(), self.ratebook, [base_scenario(), conservative]
        )
        self.assertGreater(report.scenarios[1].total_cost, report.scenarios[0].total_cost)

    def test_currency_mismatch_is_rejected(self) -> None:
        scenario = CostScenario(id="USD", name="USD", currency="USD")
        with self.assertRaises(ValueError):
            self.engine.estimate(quantity_report(), self.ratebook, [scenario])

    def test_draft_ratebook_is_blocked_by_default(self) -> None:
        data = json.loads(RATEBOOK_PATH.read_text(encoding="utf-8"))
        data["status"] = "draft"
        draft = self.loader.load_dict(data)
        with self.assertRaises(ValueError):
            self.engine.estimate(quantity_report(), draft, [base_scenario()])

    def test_ambiguous_rate_match_creates_issue(self) -> None:
        data = json.loads(RATEBOOK_PATH.read_text(encoding="utf-8"))
        duplicate = dict(data["rates"][0])
        duplicate["id"] = "RATE-WALL-MASONRY-M3-DUP"
        duplicate["cost_code"] = "04.10.101"
        data["rates"].append(duplicate)
        ambiguous_book = self.loader.load_dict(data)
        report = self.engine.estimate(quantity_report(), ambiguous_book, [base_scenario()])
        estimate = report.scenarios[0]
        self.assertIn("QTO-WALL-VOLUME", estimate.ambiguous_quantities)
        self.assertTrue(any(issue.code == "COST-RATE-AMBIGUOUS" for issue in report.issues))

    def test_traceability_is_preserved(self) -> None:
        report = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        wall = next(line for line in report.scenarios[0].lines if line.source_object_id == "WALL-001")
        self.assertEqual("QTO-WALL-VOLUME", wall.quantity_id)
        self.assertEqual(("A-101",), wall.drawing_refs)
        self.assertEqual("04.10.100", wall.cost_code)

    def test_report_fingerprint_is_deterministic(self) -> None:
        first = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        second = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        self.assertEqual(
            self.engine.fingerprint_report(first),
            self.engine.fingerprint_report(second),
        )

    def test_to_dict_quantity_report_is_supported(self) -> None:
        class QuantityObject:
            def to_dict(self) -> dict:
                return quantity_report()

        report = self.engine.estimate(QuantityObject(), self.ratebook, [base_scenario()])
        self.assertEqual("PHX-COST-TEST", report.project_id)

    def test_negative_rate_is_rejected(self) -> None:
        data = json.loads(RATEBOOK_PATH.read_text(encoding="utf-8"))
        data["rates"][0]["labor_rate"] = -1
        with self.assertRaises(ValueError):
            self.loader.load_dict(data)

    def test_json_csv_and_xlsx_exports(self) -> None:
        report = self.engine.estimate(quantity_report(), self.ratebook, [base_scenario()])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = self.exporter.export_json(report, root / "estimate.json")
            csv_path = self.exporter.export_csv(report, root / "estimate.csv")
            xlsx_path = self.exporter.export_xlsx(report, root / "estimate.xlsx")

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(1, data["scenario_count"])

            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(3, len(rows))

            with zipfile.ZipFile(xlsx_path) as archive:
                names = set(archive.namelist())
            self.assertIn("xl/worksheets/sheet1.xml", names)
            self.assertIn("xl/worksheets/sheet2.xml", names)
            self.assertIn("xl/worksheets/sheet3.xml", names)


if __name__ == "__main__":
    unittest.main()
