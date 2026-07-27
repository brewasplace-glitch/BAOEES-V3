from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.req_107_occupancy_use_decision import (
    Req107OccupancyUseDecisionEngine,
    Req107OccupancyUseDecisionExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class Req107OccupancyUseDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads(
            (ROOT / relative).read_text(encoding="utf-8")
        )
        cls.engine = Req107OccupancyUseDecisionEngine()
        cls.exporter = Req107OccupancyUseDecisionExporter()
        cls.report = cls.engine.evaluate(
            closure_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "evidence_validation_closure_plan_v1_5_0/"
                "01_evidence_validation_summary.json"
            ),
            closure_register=load(
                "inputs/pilots/moskee_bunschoten/"
                "evidence_closure_plan_register_v1_5_0.json"
            ),
            owner_input=load(
                "inputs/pilots/moskee_bunschoten/"
                "req_107_owner_decision_input_v1_6_0.json"
            ),
        )

    def test_status(self):
        self.assertEqual(
            "REQ_107_OWNER_DECISION_APPROVED_FORMAL_COSIGN_PENDING",
            self.report["status"],
        )

    def test_four_req107_decisions_are_approved(self):
        self.assertEqual(
            4,
            self.report["approved_req107_decision_count"],
        )

    def test_four_other_decisions_remain_pending(self):
        self.assertEqual(
            4,
            self.report[
                "remaining_pending_strategic_decision_count"
            ],
        )

    def test_regular_occupancy(self):
        scenario = self.report["authoritative_program"][
            "occupancy_scenarios"
        ]["regular"]
        self.assertEqual(80, scenario["existing_persons"])
        self.assertEqual(150, scenario["future_persons"])
        self.assertEqual(70, scenario["increase_persons"])
        self.assertEqual(87.5, scenario["increase_percent"])

    def test_friday_occupancy(self):
        scenario = self.report["authoritative_program"][
            "occupancy_scenarios"
        ]["friday_prayer"]
        self.assertEqual(65, scenario["existing_persons"])
        self.assertEqual(125, scenario["future_persons"])
        self.assertEqual(60, scenario["increase_persons"])
        self.assertEqual(92.31, scenario["increase_percent"])

    def test_special_peak(self):
        scenario = self.report["authoritative_program"][
            "occupancy_scenarios"
        ]["special_peak"]
        self.assertEqual(200, scenario["maximum_persons"])
        self.assertEqual(1, scenario["frequency_per_year"])

    def test_six_schedule_periods(self):
        self.assertEqual(
            6,
            len(
                self.report["authoritative_program"][
                    "opening_hours"
                ]
            ),
        )

    def test_monday_thursday_hours(self):
        schedule = next(
            item
            for item in self.report["authoritative_program"][
                "opening_hours"
            ]
            if item["period"] == "monday_through_thursday"
        )
        self.assertEqual("07:00", schedule["start_time"])
        self.assertEqual("23:00", schedule["end_time"])

    def test_friday_hours(self):
        schedule = next(
            item
            for item in self.report["authoritative_program"][
                "opening_hours"
            ]
            if item["period"] == "friday"
        )
        self.assertEqual("16:00", schedule["start_time"])
        self.assertEqual("18:00", schedule["end_time"])

    def test_ramadan_hours(self):
        schedule = next(
            item
            for item in self.report["authoritative_program"][
                "opening_hours"
            ]
            if item["period"] == "ramadan"
        )
        self.assertEqual("06:00", schedule["start_time"])
        self.assertEqual("24:00", schedule["end_time"])

    def test_req107_strategic_decision_complete(self):
        self.assertTrue(
            self.report["req107_strategic_decision_complete"]
        )

    def test_formal_closure_is_not_complete(self):
        self.assertFalse(
            self.report["req107_formal_closure_complete"]
        )
        self.assertTrue(
            self.report["req107_formal_cosign_required"]
        )

    def test_downstream_preparation_is_allowed(self):
        self.assertEqual(
            {
                "REQ-105": True,
                "REQ-106": True,
                "REQ-108": True,
            },
            self.report["downstream_preparation_allowed"],
        )

    def test_downstream_finalization_is_blocked(self):
        self.assertEqual(
            {
                "REQ-105": False,
                "REQ-106": False,
                "REQ-108": False,
            },
            self.report["downstream_finalization_allowed"],
        )

    def test_remaining_blockers_stay_seven(self):
        self.assertEqual(
            7,
            self.report["remaining_blocking_input_count"],
        )

    def test_final_generation_is_blocked(self):
        self.assertFalse(
            self.report["final_generation_allowed"]
        )

    def test_bb36_is_locked(self):
        self.assertFalse(self.report["bb36_unlock_allowed"])

    def test_program_fingerprint_exists(self):
        fingerprint = self.report["authoritative_program"][
            "fingerprint_sha256"
        ]
        self.assertEqual(64, len(fingerprint))

    def test_exports_create_eleven_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            count = sum(
                1 for path in Path(tmp).rglob("*")
                if path.is_file()
            )
            self.assertEqual(11, count)

    def test_canonical_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, tmp)
            with zipfile.ZipFile(paths["dossier"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(
                info.compress_type == zipfile.ZIP_STORED
                and info.create_system == 3
                and info.date_time == (2020, 1, 1, 0, 0, 0)
                for info in infos
            ))

    def test_two_exports_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.exporter.export_all(self.report, first)
            self.exporter.export_all(self.report, second)
            first_root = Path(first)
            second_root = Path(second)
            first_names = sorted(
                path.relative_to(first_root).as_posix()
                for path in first_root.rglob("*")
                if path.is_file()
            )
            second_names = sorted(
                path.relative_to(second_root).as_posix()
                for path in second_root.rglob("*")
                if path.is_file()
            )
            self.assertEqual(first_names, second_names)
            self.assertTrue(all(
                (first_root / name).read_bytes()
                == (second_root / name).read_bytes()
                for name in first_names
            ))


if __name__ == "__main__":
    unittest.main()
