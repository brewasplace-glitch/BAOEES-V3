from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.construction_planning import (
    ConstructionPlanningEngine,
    ConstructionPlanningExporter,
)


def metadata() -> dict:
    return {
        "project_id": "PHX-BB24-TEST",
        "project_name": "BB24 Test Project",
        "currency": "USD",
    }


def activities() -> list[dict]:
    return [
        {
            "activity_id": "A",
            "name": "Mobilisation",
            "wbs_code": "01.1",
            "discipline": "construction",
            "duration_workdays": 2,
            "resource_requirements": {"site_crew": 3},
            "direct_cost": 2000,
        },
        {
            "activity_id": "B",
            "name": "Foundations",
            "wbs_code": "02.1",
            "discipline": "construction",
            "duration_workdays": 5,
            "predecessor_ids": ["A"],
            "resource_requirements": {"concrete_crew": 6},
            "direct_cost": 10000,
        },
        {
            "activity_id": "C",
            "name": "Frame",
            "wbs_code": "03.1",
            "discipline": "construction",
            "duration_workdays": 4,
            "predecessor_ids": ["B"],
            "resource_requirements": {"structural_crew": 5},
            "direct_cost": 15000,
        },
        {
            "activity_id": "D",
            "name": "Procurement support",
            "wbs_code": "03.2",
            "discipline": "procurement",
            "duration_workdays": 2,
            "predecessor_ids": ["A"],
            "resource_requirements": {"procurement": 1},
            "direct_cost": 1000,
        },
        {
            "activity_id": "M",
            "name": "Completion",
            "wbs_code": "90.1",
            "discipline": "project_controls",
            "duration_workdays": 0,
            "predecessor_ids": ["C", "D"],
            "milestone": True,
        },
    ]


def quantity_report() -> dict:
    return {
        "project_id": "PHX-BB24-TEST",
        "records": [
            {
                "quantity_id": "Q-FOUND",
                "source_object_id": "FOUND-001",
                "work_section": "02 Foundations",
                "category": "foundation",
                "value": 24.0,
                "unit": "m3",
            },
            {
                "quantity_id": "Q-WALL",
                "source_object_id": "WALL-001",
                "work_section": "04 Walls and partitions",
                "category": "wall",
                "value": 90.0,
                "unit": "m2",
            },
        ],
    }


def cost_report() -> dict:
    return {
        "project_id": "PHX-BB24-TEST",
        "currency": "USD",
        "items": [
            {
                "cost_item_id": "C-FOUND",
                "quantity_id": "Q-FOUND",
                "total_cost": 24000,
            },
            {
                "cost_item_id": "C-WALL",
                "quantity_id": "Q-WALL",
                "total_cost": 18000,
            },
        ],
    }


class PlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ConstructionPlanningEngine()
        self.exporter = ConstructionPlanningExporter()

    def test_critical_path_and_duration(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
            project_start_date="2026-01-05",
        )
        baseline = report.baseline
        self.assertEqual(11, baseline.project_duration_workdays)
        self.assertEqual(["A", "B", "C", "M"], baseline.critical_path)

    def test_parallel_activity_has_float(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        activity_d = next(
            item for item in report.baseline.activities
            if item.activity_id == "D"
        )
        self.assertGreater(activity_d.total_float_workdays, 0)
        self.assertFalse(activity_d.critical)

    def test_milestone_has_zero_duration_and_same_dates(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        milestone = next(
            item for item in report.baseline.activities
            if item.activity_id == "M"
        )
        self.assertEqual(0, milestone.duration_workdays)
        self.assertEqual(milestone.start_date, milestone.finish_date)

    def test_weekend_is_skipped(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=[
                {
                    "activity_id": "A",
                    "name": "Five-day task",
                    "wbs_code": "01.1",
                    "duration_workdays": 5,
                }
            ],
            project_start_date="2026-01-09",
        )
        item = report.baseline.activities[0]
        self.assertEqual("2026-01-09", item.start_date)
        self.assertEqual("2026-01-15", item.finish_date)

    def test_cycle_blocks_planning(self) -> None:
        cyclic = [
            {
                "activity_id": "A",
                "name": "A",
                "wbs_code": "1",
                "duration_workdays": 1,
                "predecessor_ids": ["B"],
            },
            {
                "activity_id": "B",
                "name": "B",
                "wbs_code": "2",
                "duration_workdays": 1,
                "predecessor_ids": ["A"],
            },
        ]
        report = self.engine.create_plan(metadata(), activities=cyclic)
        self.assertFalse(report.planning_passed)
        self.assertTrue(
            any(issue.code == "PLAN-DEP-003" for issue in report.issues)
        )

    def test_unknown_predecessor_blocks_planning(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=[
                {
                    "activity_id": "A",
                    "name": "A",
                    "wbs_code": "1",
                    "duration_workdays": 1,
                    "predecessor_ids": ["UNKNOWN"],
                }
            ],
        )
        self.assertTrue(
            any(issue.code == "PLAN-DEP-001" for issue in report.issues)
        )

    def test_duplicate_id_blocks_planning(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=[
                {
                    "activity_id": "A",
                    "name": "A1",
                    "wbs_code": "1",
                    "duration_workdays": 1,
                },
                {
                    "activity_id": "A",
                    "name": "A2",
                    "wbs_code": "2",
                    "duration_workdays": 1,
                },
            ],
        )
        self.assertTrue(
            any(issue.code == "PLAN-ID-002" for issue in report.issues)
        )

    def test_activities_are_derived_from_bb20_and_bb21(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            quantity_report=quantity_report(),
            cost_report=cost_report(),
        )
        baseline = report.baseline
        self.assertEqual(3, len(baseline.activities))
        self.assertEqual(42000.0, baseline.total_direct_cost)
        self.assertTrue(
            any(
                item.quantity_ids == ("Q-FOUND",)
                for item in baseline.activities
            )
        )

    def test_resources_have_peak_and_resource_days(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        summary = report.baseline.resource_summary
        self.assertEqual(30.0, summary["concrete_crew"]["total_resource_days"])
        self.assertEqual(6.0, summary["concrete_crew"]["peak_concurrent"])

    def test_cashflow_reconciles_to_direct_cost(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        total = report.baseline.cashflow_by_month[-1]["cumulative_cost"]
        self.assertEqual(report.baseline.total_direct_cost, total)

    def test_accelerated_scenario_is_shorter_and_more_expensive(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        baseline = report.baseline
        accelerated = next(
            item for item in report.scenarios
            if item.scenario_id == "ACCELERATED"
        )
        self.assertLessEqual(
            accelerated.project_duration_workdays,
            baseline.project_duration_workdays,
        )
        self.assertGreater(
            accelerated.total_direct_cost,
            baseline.total_direct_cost,
        )

    def test_delayed_scenario_is_longer(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        delayed = next(
            item for item in report.scenarios
            if item.scenario_id == "DELAYED"
        )
        self.assertGreater(
            delayed.project_duration_workdays,
            report.baseline.project_duration_workdays,
        )

    def test_project_identity_conflict_blocks_planning(self) -> None:
        costs = cost_report()
        costs["project_id"] = "OTHER"
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
            cost_report=costs,
        )
        self.assertFalse(report.planning_passed)
        self.assertTrue(
            any(
                issue.code == "PLAN-PROJECT-001"
                for issue in report.issues
            )
        )

    def test_failed_coordination_blocks_planning(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
            coordination_report={
                "project_id": "PHX-BB24-TEST",
                "coordination_passed": False,
            },
        )
        self.assertTrue(
            any(issue.code == "PLAN-COORD-001" for issue in report.issues)
        )

    def test_report_fingerprint_is_deterministic(self) -> None:
        first = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        second = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        self.assertEqual(
            self.engine.fingerprint_report(first),
            self.engine.fingerprint_report(second),
        )

    def test_all_exports_are_created(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            self.assertEqual(9, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_csv_contains_all_scenario_activity_rows(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = self.exporter.export_schedule_csv(
                report,
                Path(tmp) / "schedule.csv",
            )
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(
                sum(len(item.activities) for item in report.scenarios),
                len(rows),
            )

    def test_xlsx_contains_four_worksheets(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = self.exporter.export_xlsx(
                report,
                Path(tmp) / "schedule.xlsx",
            )
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
            self.assertTrue(
                {
                    "xl/worksheets/sheet1.xml",
                    "xl/worksheets/sheet2.xml",
                    "xl/worksheets/sheet3.xml",
                    "xl/worksheets/sheet4.xml",
                    "xl/styles.xml",
                }.issubset(names)
            )

    def test_gantt_exports_contain_activity_content(self) -> None:
        report = self.engine.create_plan(
            metadata(),
            activities=activities(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            html_path = self.exporter.export_html(
                report,
                Path(tmp) / "gantt.html",
            )
            svg_path = self.exporter.export_svg(
                report,
                Path(tmp) / "gantt.svg",
            )
            self.assertIn(
                "Foundations",
                html_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Foundations",
                svg_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
