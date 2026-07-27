from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.integrated_concept_dossier import (
    IntegratedConceptDossierEngine,
    IntegratedConceptDossierExporter,
    load_source_manifest_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / (
    "artifacts/bb35/pilot_1_moskee_bunschoten/"
    "full_concept_evidence_simulation_v1_9_0"
)
BASE = "artifacts/bb35/pilot_1_moskee_bunschoten/full_concept_evidence_simulation_v1_9_0/"


def load_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_csv(relative):
    with (ROOT / relative).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


SNAPSHOT_PATH = ROOT / (
    "inputs/pilots/moskee_bunschoten/"
    "integrated_concept_dossier_source_manifest_snapshot_v2_0_2.json"
)


def sources():
    return load_source_manifest_snapshot(SNAPSHOT_PATH, SOURCE_ROOT)


class IntegratedConceptDossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = IntegratedConceptDossierEngine()
        cls.exporter = IntegratedConceptDossierExporter()
        cls.report = cls.engine.evaluate(
            simulation_summary=load_json(BASE + "01_full_concept_simulation_summary.json"),
            concept_register=load_json(BASE + "02_integrated_concept_register.json"),
            gate_status=load_json(BASE + "06_gate_status.json"),
            assumptions=load_csv(BASE + "03_assumptions_register.csv"),
            handoffs=load_csv(BASE + "04_cross_discipline_handoff_matrix.csv"),
            checks=load_csv(BASE + "05_consistency_checks.csv"),
            req102_geometry=load_json(BASE + "REQ-102/02_REQ_102_simulated_geometry.json"),
            req103_structure=load_json(BASE + "REQ-103/02_REQ_103_structural_scheme.json"),
            req104_foundation=load_json(BASE + "REQ-104/03_REQ_104_foundation_concept_calculation.json"),
            req105_fire=load_json(BASE + "REQ-105/02_REQ_105_fire_egress_concept.json"),
            req106_parking=load_json(BASE + "REQ-106/02_REQ_106_capacity_correction.json"),
            req107_closure=load_json(BASE + "REQ-107/01_REQ_107_closure_record.json"),
            req108_gap=load_json(BASE + "REQ-108/06_REQ_108_evidence_gap.json"),
            source_files=sources(),
            config=load_json("configs/projects/moskee_bunschoten_integrated_concept_dossier_v2_0_2.json"),
        )

    def test_status(self):
        self.assertEqual("INTEGRATED_CONCEPT_DOSSIER_GENERATED_REVIEW_READY", self.report["status"])

    def test_dossier_id(self):
        self.assertEqual("HBM-CD-2026-001", self.report["dossier_id"])

    def test_seven_requests(self):
        self.assertEqual(7, self.report["metrics"]["request_count"])

    def test_six_simulations_one_authoritative(self):
        self.assertEqual(6, self.report["metrics"]["concept_simulation_count"])
        self.assertEqual(1, self.report["metrics"]["authoritative_request_count"])

    def test_parking_basis(self):
        self.assertEqual(225, self.report["parking_basis_spaces"])
        self.assertEqual(300, self.report["previous_parking_hypothesis_spaces"])

    def test_req107_closed(self):
        self.assertEqual("CLOSED_PROJECT_LEADER_APPROVED", self.report["req107_status"])

    def test_scope(self):
        self.assertEqual(70.0, self.report["project_scope"]["footprint_area_m2"])
        self.assertEqual(140.0, self.report["project_scope"]["gross_floor_area_m2"])

    def test_occupancy(self):
        self.assertEqual(150, self.report["occupancy_program"]["regular"]["future_persons"])
        self.assertEqual(125, self.report["occupancy_program"]["friday_prayer"]["future_persons"])
        self.assertEqual(200, self.report["occupancy_program"]["special_peak"]["maximum_persons"])

    def test_drawing_register_count(self):
        self.assertEqual(8, len(self.report["drawing_register"]))

    def test_calculation_register_count(self):
        self.assertEqual(8, len(self.report["calculation_register"]))

    def test_assumption_count(self):
        self.assertEqual(8, len(self.report["assumptions"]))

    def test_handoff_count(self):
        self.assertEqual(6, len(self.report["handoffs"]))

    def test_consistency_count(self):
        self.assertEqual(11, len(self.report["consistency_checks"]))

    def test_all_consistency_checks_pass(self):
        self.assertTrue(all(row["passed"].lower() == "true" for row in self.report["consistency_checks"]))

    def test_six_professional_blockers(self):
        self.assertEqual(6, len(self.report["professional_blockers"]))

    def test_replacement_plan_count(self):
        self.assertEqual(6, len(self.report["evidence_replacement_plan"]))

    def test_source_manifest_count(self):
        self.assertEqual(44, len(self.report["source_files"]))

    def test_review_ready(self):
        self.assertTrue(self.report["gates"]["concept_dossier_review_ready"])

    def test_final_release_blocked(self):
        self.assertFalse(self.report["gates"]["final_permit_ready_generation_allowed"])

    def test_bb36_functional_passed(self):
        self.assertTrue(self.report["gates"]["bb36_functional_validation_passed"])

    def test_bb36_production_locked(self):
        self.assertFalse(self.report["gates"]["bb36_production_release_allowed"])

    def test_all_requests_not_submittable(self):
        self.assertTrue(all(not item["submission_allowed"] for item in self.report["request_register"]))

    def test_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            self.assertEqual(20, sum(1 for path in Path(tmp).rglob("*") if path.is_file()))

    def test_markdown_contains_all_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, tmp)
            text = paths["dossier_md"].read_text(encoding="utf-8")
            for request_id in ["REQ-102", "REQ-103", "REQ-104", "REQ-105", "REQ-106", "REQ-107", "REQ-108"]:
                self.assertIn(request_id, text)
            self.assertIn("NIET VOOR INDIENING OF UITVOERING", text)

    def test_html_contains_release_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, tmp)
            text = paths["dossier_html"].read_text(encoding="utf-8")
            self.assertIn("BB36", text)
            self.assertIn("VERGRENDELD", text)
            self.assertIn("225", text)

    def test_canonical_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, tmp)
            with zipfile.ZipFile(paths["dossier_zip"]) as archive:
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
            names = sorted(path.relative_to(first_root).as_posix() for path in first_root.rglob("*") if path.is_file())
            self.assertEqual(names, sorted(path.relative_to(second_root).as_posix() for path in second_root.rglob("*") if path.is_file()))
            self.assertTrue(all((first_root / name).read_bytes() == (second_root / name).read_bytes() for name in names))


    def test_source_manifest_uses_packaged_reference_snapshot(self):
        self.assertTrue(all(
            item["hash_mode"] == "PACKAGED_REFERENCE_SNAPSHOT_SHA256"
            for item in self.report["source_files"]
        ))

    def test_source_inventory_matches_snapshot(self):
        expected = sorted(
            item["relative_path"] for item in self.report["source_files"]
        )
        actual = sorted(
            path.relative_to(SOURCE_ROOT).as_posix()
            for path in SOURCE_ROOT.rglob("*")
            if path.is_file()
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
