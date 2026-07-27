from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.downstream_preparation_decisions import (
    DownstreamPreparationDecisionsEngine,
    DownstreamPreparationDecisionsExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class DownstreamPreparationDecisionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads(
            (ROOT / relative).read_text(encoding="utf-8")
        )
        cls.engine = DownstreamPreparationDecisionsEngine()
        cls.exporter = DownstreamPreparationDecisionsExporter()
        cls.report = cls.engine.evaluate(
            req107_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "req_107_occupancy_use_decision_v1_6_0/"
                "01_req107_decision_summary.json"
            ),
            req107_program=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "req_107_occupancy_use_decision_v1_6_0/"
                "02_authoritative_occupancy_use_program.json"
            ),
            req107_decision_register=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "req_107_occupancy_use_decision_v1_6_0/"
                "03_updated_strategic_decision_register.json"
            ),
            closure_plan=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "evidence_validation_closure_plan_v1_5_0/"
                "01_evidence_validation_summary.json"
            ),
            owner_input=load(
                "inputs/pilots/moskee_bunschoten/"
                "downstream_preparation_owner_decisions_v1_7_0.json"
            ),
        )

    def test_status(self):
        self.assertEqual(
            (
                "ALL_STRATEGIC_DECISIONS_OWNER_APPROVED_"
                "DOWNSTREAM_PREPARATION_READY"
            ),
            self.report["status"],
        )

    def test_all_eight_decisions_are_approved(self):
        self.assertEqual(
            8,
            self.report["approved_strategic_decision_count"],
        )
        self.assertEqual(
            0,
            self.report["pending_strategic_decision_count"],
        )
        self.assertTrue(
            self.report["all_strategic_decisions_approved"]
        )

    def test_kitchen_choice(self):
        self.assertEqual(
            "geen_keukenfunctie",
            self.report["selected_strategic_basis"][
                "kitchen_function"
            ],
        )

    def test_installation_choice(self):
        self.assertEqual(
            "wettelijk_minimum",
            self.report["selected_strategic_basis"][
                "installation_sustainability_level"
            ],
        )

    def test_parking_choice(self):
        self.assertEqual(
            "openbare_capaciteit",
            self.report["selected_strategic_basis"][
                "parking_strategy"
            ],
        )

    def test_phasing_choice(self):
        basis = self.report["selected_strategic_basis"]
        self.assertEqual(
            "gefaseerde_uitvoering",
            basis["execution_phasing"],
        )
        self.assertTrue(
            basis["mosque_remains_in_use_during_construction"]
        )

    def test_three_workstreams(self):
        self.assertEqual(3, self.report["workstream_count"])
        self.assertEqual(
            {"REQ-105", "REQ-106", "REQ-108"},
            set(self.report["workstreams"]),
        )

    def test_req105_basis(self):
        basis = self.report["workstreams"]["REQ-105"][
            "strategic_basis"
        ]
        self.assertEqual("geen_keukenfunctie", basis["kitchen_function"])
        self.assertEqual(
            "wettelijk_minimum",
            basis["installation_sustainability_level"],
        )

    def test_req106_basis(self):
        self.assertEqual(
            "openbare_capaciteit",
            self.report["workstreams"]["REQ-106"][
                "strategic_basis"
            ]["parking_strategy"],
        )

    def test_req108_basis(self):
        basis = self.report["workstreams"]["REQ-108"][
            "strategic_basis"
        ]
        self.assertEqual(
            "gefaseerde_uitvoering",
            basis["execution_phasing"],
        )
        self.assertTrue(basis["mosque_remains_in_use"])

    def test_authoritative_program_is_propagated(self):
        for workstream in self.report["workstreams"].values():
            self.assertEqual(
                "HBM-OCC-2026-001",
                workstream["authoritative_inputs"][
                    "occupancy_program_id"
                ],
            )

    def test_parallel_preparation_allowed(self):
        self.assertTrue(
            self.report["parallel_preparation_allowed"]
        )

    def test_professional_evidence_still_required(self):
        self.assertTrue(
            self.report["professional_evidence_still_required"]
        )

    def test_req107_cosign_still_pending(self):
        self.assertTrue(
            self.report["req107_formal_cosign_still_pending"]
        )

    def test_seven_blockers_remain(self):
        self.assertEqual(
            7,
            self.report["remaining_blocking_input_count"],
        )

    def test_no_workstream_is_finalized(self):
        self.assertTrue(all(
            not workstream["finalization_allowed"]
            for workstream in self.report["workstreams"].values()
        ))

    def test_final_generation_is_blocked(self):
        self.assertFalse(
            self.report["final_generation_allowed"]
        )

    def test_bb36_is_locked(self):
        self.assertFalse(self.report["bb36_unlock_allowed"])

    def test_exports_create_thirteen_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            count = sum(
                1 for path in Path(tmp).rglob("*")
                if path.is_file()
            )
            self.assertEqual(14, count)

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
