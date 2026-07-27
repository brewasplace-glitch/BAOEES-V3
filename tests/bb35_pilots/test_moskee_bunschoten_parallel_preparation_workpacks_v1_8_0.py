from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.parallel_preparation_workpacks import (
    ParallelPreparationWorkpacksEngine,
    ParallelPreparationWorkpacksExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class ParallelPreparationWorkpacksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads(
            (ROOT / relative).read_text(encoding="utf-8")
        )
        cls.engine = ParallelPreparationWorkpacksEngine()
        cls.exporter = ParallelPreparationWorkpacksExporter()
        cls.report = cls.engine.evaluate(
            downstream_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "downstream_preparation_decisions_v1_7_0/"
                "01_downstream_decision_summary.json"
            ),
            downstream_basis=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "downstream_preparation_decisions_v1_7_0/"
                "03_authoritative_downstream_preparation_basis.json"
            ),
            occupancy_program=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "req_107_occupancy_use_decision_v1_6_0/"
                "02_authoritative_occupancy_use_program.json"
            ),
            config=load(
                "configs/projects/"
                "moskee_bunschoten_"
                "parallel_preparation_workpacks_v1_8_0.json"
            ),
        )

    def test_status(self):
        self.assertEqual(
            (
                "PARALLEL_PREPARATION_WORKPACKS_GENERATED_"
                "EXTERNAL_EVIDENCE_PENDING"
            ),
            self.report["status"],
        )

    def test_three_workpacks(self):
        self.assertEqual(3, self.report["workpack_count"])
        self.assertEqual(
            {"REQ-105", "REQ-106", "REQ-108"},
            set(self.report["workpacks"]),
        )

    def test_parallel_execution_allowed(self):
        self.assertTrue(self.report["parallel_execution_allowed"])

    def test_all_strategic_decisions_approved(self):
        self.assertTrue(
            self.report["all_strategic_decisions_approved"]
        )

    def test_req105_basis(self):
        basis = self.report["workpacks"]["REQ-105"][
            "strategic_basis"
        ]
        self.assertEqual("geen_keukenfunctie", basis["kitchen_function"])
        self.assertEqual(
            "wettelijk_minimum",
            basis["installation_sustainability_level"],
        )

    def test_req105_has_eight_requirements(self):
        self.assertEqual(
            8,
            len(
                self.report["workpacks"]["REQ-105"][
                    "requirements_matrix"
                ]
            ),
        )

    def test_req106_parking_hypothesis(self):
        workpack = self.report["workpacks"]["REQ-106"]
        self.assertEqual(
            300,
            workpack["parking_hypothesis"]["total_spaces"],
        )
        self.assertEqual(
            "PROVISIONAL_FIELD_HYPOTHESIS_NOT_VERIFIED",
            workpack["parking_hypothesis"]["status"],
        )

    def test_req106_subareas_total_300(self):
        subareas = self.report["workpacks"]["REQ-106"][
            "parking_hypothesis"
        ]["subareas"]
        self.assertEqual(
            300,
            sum(item["provisional_spaces"] for item in subareas),
        )

    def test_req106_has_five_measurements(self):
        self.assertEqual(
            5,
            len(
                self.report["workpacks"]["REQ-106"][
                    "measurement_windows"
                ]
            ),
        )

    def test_req106_has_seven_protocol_steps(self):
        self.assertEqual(
            7,
            len(
                self.report["workpacks"]["REQ-106"][
                    "field_protocol"
                ]
            ),
        )

    def test_req108_is_phased(self):
        basis = self.report["workpacks"]["REQ-108"][
            "strategic_basis"
        ]
        self.assertEqual(
            "gefaseerde_uitvoering",
            basis["execution_phasing"],
        )
        self.assertTrue(
            basis["mosque_remains_in_use_during_construction"]
        )

    def test_req108_has_five_phases(self):
        self.assertEqual(
            5,
            len(
                self.report["workpacks"]["REQ-108"][
                    "phase_templates"
                ]
            ),
        )

    def test_every_workpack_propagates_occupancy(self):
        for workpack in self.report["workpacks"].values():
            inputs = workpack["authoritative_inputs"]
            self.assertEqual(
                "HBM-OCC-2026-001",
                inputs["occupancy_program_id"],
            )
            self.assertEqual(150, inputs["regular_future_persons"])
            self.assertEqual(125, inputs["friday_future_persons"])
            self.assertEqual(200, inputs["special_peak_persons"])

    def test_no_workpack_finalized(self):
        self.assertTrue(all(
            not workpack["finalization_allowed"]
            for workpack in self.report["workpacks"].values()
        ))

    def test_professional_evidence_required(self):
        self.assertTrue(
            self.report["professional_evidence_still_required"]
        )

    def test_req107_cosign_pending(self):
        self.assertTrue(
            self.report["req107_formal_cosign_still_pending"]
        )

    def test_final_generation_blocked(self):
        self.assertFalse(
            self.report["final_generation_allowed"]
        )

    def test_bb36_locked(self):
        self.assertFalse(self.report["bb36_unlock_allowed"])

    def test_export_file_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            count = sum(
                1 for path in Path(tmp).rglob("*")
                if path.is_file()
            )
            self.assertEqual(28, count)

    def test_req105_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            self.assertEqual(
                6,
                len(list((Path(tmp) / "REQ-105").iterdir())),
            )

    def test_req106_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            self.assertEqual(
                9,
                len(list((Path(tmp) / "REQ-106").iterdir())),
            )

    def test_req108_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            self.assertEqual(
                8,
                len(list((Path(tmp) / "REQ-108").iterdir())),
            )

    def test_count_sheet_has_25_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            path = (
                Path(tmp)
                / "REQ-106/04_REQ_106_field_count_sheet.csv"
            )
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual(26, len(lines))

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

    def test_two_exports_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.exporter.export_all(self.report, first)
            self.exporter.export_all(self.report, second)
            first_root = Path(first)
            second_root = Path(second)
            names = sorted(
                path.relative_to(first_root).as_posix()
                for path in first_root.rglob("*")
                if path.is_file()
            )
            self.assertEqual(
                names,
                sorted(
                    path.relative_to(second_root).as_posix()
                    for path in second_root.rglob("*")
                    if path.is_file()
                ),
            )
            self.assertTrue(all(
                (first_root / name).read_bytes()
                == (second_root / name).read_bytes()
                for name in names
            ))


if __name__ == "__main__":
    unittest.main()
