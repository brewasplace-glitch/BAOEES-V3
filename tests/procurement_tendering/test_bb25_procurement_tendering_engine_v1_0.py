from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.procurement_tendering import (
    ProcurementTenderingEngine,
    ProcurementTenderingExporter,
)


def metadata() -> dict:
    return {
        "project_id": "PHX-BB25-TEST",
        "project_name": "BB25 Test Project",
        "currency": "USD",
    }


def quantities() -> dict:
    return {
        "project_id": "PHX-BB25-TEST",
        "records": [
            {
                "quantity_id": "Q-FOUND",
                "source_object_id": "FOUND-001",
                "work_section": "02 Foundations",
                "quantity_type": "foundation_volume",
                "value": 20.0,
                "unit": "m3",
            },
            {
                "quantity_id": "Q-WALL",
                "source_object_id": "WALL-001",
                "work_section": "04 Walls and partitions",
                "quantity_type": "gross_wall_area",
                "value": 100.0,
                "unit": "m2",
            },
            {
                "quantity_id": "Q-DOOR",
                "source_object_id": "DOOR-001",
                "work_section": "07 Doors",
                "quantity_type": "count",
                "value": 10.0,
                "unit": "ea",
            },
        ],
    }


def costs() -> dict:
    return {
        "project_id": "PHX-BB25-TEST",
        "currency": "USD",
        "items": [
            {"cost_item_id": "C-FOUND", "quantity_id": "Q-FOUND", "total_cost": 40000.0},
            {"cost_item_id": "C-WALL", "quantity_id": "Q-WALL", "total_cost": 30000.0},
            {"cost_item_id": "C-DOOR", "quantity_id": "Q-DOOR", "total_cost": 12000.0},
        ],
    }


def planning() -> dict:
    return {
        "project_id": "PHX-BB25-TEST",
        "planning_passed": True,
        "baseline_scenario_id": "BASELINE",
        "scenarios": [
            {
                "scenario_id": "BASELINE",
                "activities": [
                    {
                        "activity_id": "A-FOUND",
                        "start_date": "2026-02-02",
                        "finish_date": "2026-02-13",
                        "quantity_ids": ["Q-FOUND"],
                    },
                    {
                        "activity_id": "A-WALL",
                        "start_date": "2026-03-02",
                        "finish_date": "2026-03-20",
                        "quantity_ids": ["Q-WALL"],
                    },
                    {
                        "activity_id": "A-DOOR",
                        "start_date": "2026-04-06",
                        "finish_date": "2026-04-10",
                        "quantity_ids": ["Q-DOOR"],
                    },
                ],
            }
        ],
    }


def coordination() -> dict:
    return {"project_id": "PHX-BB25-TEST", "coordination_passed": True}


def supplier_records() -> list[dict]:
    return [
        {"supplier_id": "SUP-A", "supplier_name": "Alpha Contractors", "approved": True},
        {"supplier_id": "SUP-B", "supplier_name": "Beta Builders", "approved": True},
        {"supplier_id": "SUP-C", "supplier_name": "Gamma Fast Track", "approved": True},
    ]


def build_base(engine: ProcurementTenderingEngine, *, bids: list[dict] | None = None):
    return engine.create_procurement(
        metadata(),
        quantity_report=quantities(),
        cost_report=costs(),
        planning_report=planning(),
        coordination_report=coordination(),
        suppliers=supplier_records(),
        bids=[] if bids is None else bids,
    )


def bid_set(engine: ProcurementTenderingEngine) -> list[dict]:
    report = build_base(engine)
    package = report.packages[0]
    line = next(item for item in report.tender_lines if item.package_id == package.package_id)
    return [
        {
            "bid_id": "BID-A",
            "package_id": package.package_id,
            "supplier_id": "SUP-A",
            "supplier_name": "Alpha Contractors",
            "currency": "USD",
            "submitted_date": "2026-01-10",
            "validity_days": 60,
            "delivery_workdays": 15,
            "line_items": [{"line_id": line.line_id, "total_price": 38000.0}],
        },
        {
            "bid_id": "BID-B",
            "package_id": package.package_id,
            "supplier_id": "SUP-B",
            "supplier_name": "Beta Builders",
            "currency": "USD",
            "submitted_date": "2026-01-11",
            "validity_days": 60,
            "delivery_workdays": 12,
            "line_items": [{"line_id": line.line_id, "total_price": 40000.0}],
        },
        {
            "bid_id": "BID-C",
            "package_id": package.package_id,
            "supplier_id": "SUP-C",
            "supplier_name": "Gamma Fast Track",
            "currency": "USD",
            "submitted_date": "2026-01-12",
            "validity_days": 60,
            "delivery_workdays": 8,
            "line_items": [{"line_id": line.line_id, "total_price": 45000.0}],
        },
    ]


class ProcurementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ProcurementTenderingEngine()
        self.exporter = ProcurementTenderingExporter()

    def test_packages_are_derived_by_work_section(self) -> None:
        self.assertEqual(3, len(build_base(self.engine).packages))

    def test_benchmark_budget_reconciles_to_cost_report(self) -> None:
        self.assertEqual(82000.0, build_base(self.engine).benchmark_budget_total)

    def test_schedule_dates_link_from_bb24(self) -> None:
        report = build_base(self.engine)
        package = next(item for item in report.packages if item.work_section == "02 Foundations")
        self.assertEqual("2026-02-02", package.planned_start_date)
        self.assertEqual("2026-02-13", package.planned_finish_date)

    def test_tender_line_ids_are_deterministic(self) -> None:
        first = build_base(self.engine)
        second = build_base(self.engine)
        self.assertEqual(
            [item.line_id for item in first.tender_lines],
            [item.line_id for item in second.tender_lines],
        )

    def test_project_identity_conflict_blocks(self) -> None:
        bad = costs()
        bad["project_id"] = "OTHER"
        report = self.engine.create_procurement(
            metadata(), quantity_report=quantities(), cost_report=bad,
            planning_report=planning(), coordination_report=coordination(),
        )
        self.assertFalse(report.procurement_passed)

    def test_currency_conflict_blocks(self) -> None:
        project = metadata()
        project["currency"] = "EUR"
        report = self.engine.create_procurement(
            project, quantity_report=quantities(), cost_report=costs(),
            planning_report=planning(), coordination_report=coordination(),
        )
        self.assertTrue(any(issue.code == "PROC-CURRENCY-001" for issue in report.issues))

    def test_default_currency_is_usd(self) -> None:
        project = metadata()
        project.pop("currency")
        cost = costs()
        cost.pop("currency")
        report = self.engine.create_procurement(
            project, quantity_report=quantities(), cost_report=cost,
            planning_report=planning(), coordination_report=coordination(),
        )
        self.assertEqual("USD", report.currency)

    def test_failed_planning_blocks(self) -> None:
        bad = planning()
        bad["planning_passed"] = False
        report = self.engine.create_procurement(
            metadata(), quantity_report=quantities(), cost_report=costs(),
            planning_report=bad, coordination_report=coordination(),
        )
        self.assertTrue(any(issue.code == "PROC-PLAN-001" for issue in report.issues))

    def test_failed_coordination_blocks(self) -> None:
        bad = coordination()
        bad["coordination_passed"] = False
        report = self.engine.create_procurement(
            metadata(), quantity_report=quantities(), cost_report=costs(),
            planning_report=planning(), coordination_report=bad,
        )
        self.assertTrue(any(issue.code == "PROC-COORD-001" for issue in report.issues))

    def test_duplicate_supplier_blocks(self) -> None:
        duplicate = supplier_records() + [supplier_records()[0]]
        report = self.engine.create_procurement(
            metadata(), quantity_report=quantities(), cost_report=costs(),
            planning_report=planning(), coordination_report=coordination(), suppliers=duplicate,
        )
        self.assertTrue(any(issue.code == "PROC-SUP-002" for issue in report.issues))

    def test_duplicate_bid_blocks(self) -> None:
        bids = bid_set(self.engine)
        bids.append(dict(bids[0]))
        report = build_base(self.engine, bids=bids)
        self.assertTrue(any(issue.code == "PROC-BID-010" for issue in report.issues))

    def test_complete_bids_receive_price_scores(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        alpha = next(item for item in report.evaluations if item.bid_id == "BID-A")
        self.assertEqual(100.0, alpha.price_score)

    def test_missing_line_adds_benchmark_allowance(self) -> None:
        base = build_base(self.engine)
        package = base.packages[0]
        report = build_base(self.engine, bids=[{
            "bid_id": "BID-MISSING",
            "package_id": package.package_id,
            "supplier_id": "SUP-A",
            "supplier_name": "Alpha Contractors",
            "currency": "USD",
            "submitted_date": "2026-01-10",
            "validity_days": 30,
            "delivery_workdays": 10,
            "line_items": [],
        }])
        self.assertGreater(report.evaluations[0].missing_line_allowance, 0)

    def test_extra_line_is_detected(self) -> None:
        bids = bid_set(self.engine)
        bids[0]["line_items"].append({"line_id": "EXTRA-001", "quantity": 1, "unit_rate": 500})
        report = build_base(self.engine, bids=bids)
        alpha = next(item for item in report.evaluations if item.bid_id == "BID-A")
        self.assertEqual(("EXTRA-001",), alpha.extra_line_ids)

    def test_exclusion_reduces_completeness(self) -> None:
        bids = bid_set(self.engine)
        bids[0]["exclusions"] = ["Testing excluded"]
        report = build_base(self.engine, bids=bids)
        alpha = next(item for item in report.evaluations if item.bid_id == "BID-A")
        self.assertEqual(95.0, alpha.completeness_score)

    def test_foreign_currency_bid_is_nonresponsive(self) -> None:
        bids = bid_set(self.engine)
        bids[0]["currency"] = "EUR"
        report = build_base(self.engine, bids=bids)
        alpha = next(item for item in report.evaluations if item.bid_id == "BID-A")
        self.assertFalse(alpha.responsive)

    def test_lowest_cost_scenario_recommends_alpha(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        rec = next(
            item for item in report.recommendations
            if item.scenario_id == "LOWEST_EVALUATED_COST" and item.recommended_bid_id
        )
        self.assertEqual("BID-A", rec.recommended_bid_id)

    def test_balanced_scenario_recommends_alpha(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        rec = next(
            item for item in report.recommendations
            if item.scenario_id == "BALANCED" and item.recommended_bid_id
        )
        self.assertEqual("BID-A", rec.recommended_bid_id)

    def test_schedule_priority_recommends_gamma(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        rec = next(
            item for item in report.recommendations
            if item.scenario_id == "SCHEDULE_PRIORITY" and item.recommended_bid_id
        )
        self.assertEqual("BID-C", rec.recommended_bid_id)

    def test_no_automatic_award(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        self.assertFalse(report.metadata["automatic_contract_award"])
        self.assertTrue(all(item.status != "awarded" for item in report.recommendations))

    def test_report_fingerprint_is_deterministic(self) -> None:
        first = build_base(self.engine, bids=bid_set(self.engine))
        second = build_base(self.engine, bids=bid_set(self.engine))
        self.assertEqual(
            self.engine.fingerprint_report(first),
            self.engine.fingerprint_report(second),
        )

    def test_all_exports_are_created(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            self.assertEqual(11, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_csv_bid_rows_match_evaluations(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            with paths["bids_csv"].open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(report.evaluations), len(rows))

    def test_xlsx_has_five_sheets(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        with tempfile.TemporaryDirectory() as tmp:
            path = self.exporter.export_xlsx(report, Path(tmp) / "workbook.xlsx")
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
            for index in range(1, 6):
                self.assertIn(f"xl/worksheets/sheet{index}.xml", names)

    def test_docx_pdf_and_dossier_structures(self) -> None:
        report = build_base(self.engine, bids=bid_set(self.engine))
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            with zipfile.ZipFile(paths["docx"]) as archive:
                self.assertIn("word/document.xml", archive.namelist())
            self.assertTrue(paths["pdf"].read_bytes().startswith(b"%PDF-1.4"))
            with zipfile.ZipFile(paths["dossier"]) as archive:
                names = set(archive.namelist())
            self.assertIn("request_for_tender.docx", names)
            self.assertIn("request_for_tender.pdf", names)
            self.assertIn("procurement_tendering_workbook.xlsx", names)


if __name__ == "__main__":
    unittest.main()
