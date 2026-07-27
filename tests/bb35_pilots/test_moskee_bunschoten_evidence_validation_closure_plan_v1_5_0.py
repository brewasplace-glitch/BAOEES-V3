from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.evidence_validation_closure_plan import (
    EvidenceValidationClosurePlanEngine,
    EvidenceValidationClosurePlanExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class EvidenceValidationClosurePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads(
            (ROOT / relative).read_text(encoding="utf-8")
        )
        cls.engine = EvidenceValidationClosurePlanEngine()
        cls.exporter = EvidenceValidationClosurePlanExporter()
        cls.report = cls.engine.evaluate(
            intake_report=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "uploaded_evidence_intake_v1_4_1/"
                "01_uploaded_evidence_intake_report.json"
            ),
            verified_register=load(
                "inputs/pilots/moskee_bunschoten/"
                "verified_inputs_register_v1_2_0.json"
            ),
            review_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "concept_review_evidence_acquisition_v1_4_0/"
                "01_concept_review_summary.json"
            ),
            closure_register=load(
                "inputs/pilots/moskee_bunschoten/"
                "evidence_closure_plan_register_v1_5_0.json"
            ),
            config=load(
                "configs/projects/"
                "moskee_bunschoten_"
                "evidence_validation_closure_plan_v1_5_0.json"
            ),
        )

    def test_status_is_plan_ready(self):
        self.assertEqual(
            "EVIDENCE_VALIDATION_COMPLETE_CLOSURE_PLAN_READY",
            self.report["status"],
        )

    def test_scope_is_140m2(self):
        self.assertEqual(
            140.0,
            self.report["authoritative_scope"][
                "gross_extension_area_m2"
            ],
        )

    def test_seven_closure_items(self):
        self.assertEqual(7, self.report["closure_item_count"])

    def test_request_ids_are_102_through_108(self):
        self.assertEqual(
            [
                "REQ-102",
                "REQ-103",
                "REQ-104",
                "REQ-105",
                "REQ-106",
                "REQ-107",
                "REQ-108",
            ],
            [
                item["request_id"]
                for item in self.report["closure_items"]
            ],
        )

    def test_seven_blockers_remain(self):
        self.assertEqual(
            7,
            self.report["remaining_blocking_input_count"],
        )

    def test_source_counts_remain_one_two_five(self):
        self.assertEqual(1, self.report["closed_request_count"])
        self.assertEqual(2, self.report["partial_request_count"])
        self.assertEqual(5, self.report["open_request_count"])

    def test_eight_strategic_decisions(self):
        self.assertEqual(8, self.report["strategic_decision_count"])
        self.assertEqual(
            8,
            self.report["pending_strategic_decision_count"],
        )

    def test_all_strategic_values_are_unset(self):
        self.assertTrue(all(
            item["selected_value"] is None
            for item in self.report["strategic_decisions"]
        ))

    def test_six_professional_work_orders(self):
        self.assertEqual(
            6,
            self.report["professional_work_order_count"],
        )

    def test_req107_is_critical_path_root(self):
        self.assertEqual(
            "REQ-107",
            self.report["critical_path_root"],
        )

    def test_req107_downstream(self):
        self.assertEqual(
            ["REQ-105", "REQ-106", "REQ-108"],
            self.report["critical_path_downstream_requests"],
        )

    def test_execution_order_places_req107_before_dependants(self):
        order = self.report["recommended_execution_order"]
        for dependant in ("REQ-105", "REQ-106", "REQ-108"):
            self.assertLess(
                order.index("REQ-107"),
                order.index(dependant),
            )

    def test_req104_depends_on_req102(self):
        req104 = next(
            item for item in self.report["closure_items"]
            if item["request_id"] == "REQ-104"
        )
        self.assertEqual(["REQ-102"], req104["depends_on"])

    def test_every_item_has_internal_actions(self):
        self.assertTrue(all(
            item["internal_actions"]
            for item in self.report["closure_items"]
        ))

    def test_every_item_has_external_deliverables(self):
        self.assertTrue(all(
            item["external_deliverables"]
            for item in self.report["closure_items"]
        ))

    def test_every_item_has_acceptance_criteria(self):
        self.assertTrue(all(
            item["acceptance_criteria"]
            for item in self.report["closure_items"]
        ))

    def test_professional_signoff_policy(self):
        self.assertTrue(
            self.report["policy"]["rules"][
                "external_reports_require_signature"
            ]
        )

    def test_one_authoritative_occupancy_policy(self):
        self.assertTrue(
            self.report["policy"]["rules"][
                "one_authoritative_occupancy_version_across_disciplines"
            ]
        )

    def test_closure_execution_is_allowed(self):
        self.assertTrue(
            self.report["closure_execution_allowed"]
        )

    def test_final_generation_is_blocked(self):
        self.assertFalse(
            self.report["final_generation_allowed"]
        )

    def test_bb36_is_locked(self):
        self.assertFalse(self.report["bb36_unlock_allowed"])

    def test_exports_include_29_or_more_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            count = sum(
                1 for path in Path(tmp).rglob("*")
                if path.is_file()
            )
            self.assertGreaterEqual(count, 31)

    def test_seven_closure_package_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            directories = sorted(
                path.name
                for path in (
                    Path(tmp) / "closure_packages"
                ).iterdir()
                if path.is_dir()
            )
            self.assertEqual(
                [
                    "REQ-102",
                    "REQ-103",
                    "REQ-104",
                    "REQ-105",
                    "REQ-106",
                    "REQ-107",
                    "REQ-108",
                ],
                directories,
            )

    def test_each_closure_package_has_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            for request_id in (
                "REQ-102",
                "REQ-103",
                "REQ-104",
                "REQ-105",
                "REQ-106",
                "REQ-107",
                "REQ-108",
            ):
                files = list(
                    (
                        Path(tmp)
                        / "closure_packages"
                        / request_id
                    ).iterdir()
                )
                self.assertEqual(3, len(files))

    def test_dossier_uses_canonical_stored_headers(self):
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

    def test_two_generations_are_byte_identical(self):
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
