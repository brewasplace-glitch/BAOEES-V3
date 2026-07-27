from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.full_concept_evidence_simulation import (
    FullConceptEvidenceSimulationEngine,
    FullConceptEvidenceSimulationExporter,
)

ROOT = Path(__file__).resolve().parents[2]


class FullConceptEvidenceSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads((ROOT / relative).read_text(encoding="utf-8"))
        cls.report = FullConceptEvidenceSimulationEngine().evaluate(
            req107_program=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "req_107_occupancy_use_decision_v1_6_0/"
                "02_authoritative_occupancy_use_program.json"
            ),
            downstream_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "downstream_preparation_decisions_v1_7_0/"
                "01_downstream_decision_summary.json"
            ),
            parallel_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "parallel_preparation_workpacks_v1_8_0/"
                "01_parallel_preparation_summary.json"
            ),
            authorization=load(
                "inputs/pilots/moskee_bunschoten/"
                "full_concept_simulation_authorization_v1_9_0.json"
            ),
            config=load(
                "configs/projects/"
                "moskee_bunschoten_full_concept_evidence_simulation_v1_9_0.json"
            ),
        )
        cls.exporter = FullConceptEvidenceSimulationExporter()

    def test_status(self):
        self.assertEqual("FULL_CONCEPT_EVIDENCE_SIMULATION_RUN_PASSED", self.report["status"])

    def test_req_range(self):
        self.assertEqual([f"REQ-{value}" for value in range(102, 109)], self.report["req_range"])

    def test_six_simulated_concepts(self):
        self.assertEqual(6, self.report["concept_simulation_count"])

    def test_req107_is_closed(self):
        self.assertEqual("CLOSED_PROJECT_LEADER_APPROVED", self.report["req107_status"])

    def test_req107_not_simulated(self):
        self.assertEqual("AUTHORITATIVE_PROJECT_DECISION_NOT_SIMULATED", self.report["concepts"]["REQ-107"]["simulation_label"])

    def test_parking_corrected_to_225(self):
        self.assertEqual(225, self.report["parking_basis_spaces"])

    def test_previous_300_superseded(self):
        self.assertEqual(300, self.report["parking_previous_hypothesis_spaces"])

    def test_six_professional_blockers(self):
        self.assertEqual(6, self.report["remaining_professional_evidence_blockers"])

    def test_req102_area(self):
        geometry = self.report["concepts"]["REQ-102"]["geometry"]
        self.assertEqual(70.0, geometry["footprint_area_m2"])
        self.assertEqual(140.0, geometry["gross_floor_area_m2"])

    def test_req102_perimeter(self):
        self.assertEqual(34.0, self.report["concepts"]["REQ-102"]["geometry"]["perimeter_m"])

    def test_req103_total_load(self):
        self.assertEqual(1335.0, self.report["concepts"]["REQ-103"]["concept_calculations"]["total_service_gravity_load_kn"])

    def test_req103_nine_columns(self):
        self.assertEqual(9, self.report["concepts"]["REQ-103"]["scheme"]["column_count"])

    def test_req104_receives_structural_load(self):
        self.assertEqual(
            self.report["concepts"]["REQ-103"]["concept_calculations"]["total_service_gravity_load_kn"],
            self.report["concepts"]["REQ-104"]["concept_calculations"]["input_service_load_kn"],
        )

    def test_req104_groundwater(self):
        self.assertEqual(-0.5, self.report["concepts"]["REQ-104"]["groundwater_level_m"])

    def test_req105_uses_200_peak(self):
        self.assertEqual(200, self.report["concepts"]["REQ-105"]["occupancy_basis"]["special_peak_persons"])

    def test_req105_ventilation_test_flow(self):
        self.assertEqual(5040.0, self.report["concepts"]["REQ-105"]["ventilation_simulation"]["peak_flow_m3_h"])

    def test_req105_makes_no_compliance_conclusion(self):
        self.assertEqual("NOT_MADE_IN_SIMULATION", self.report["concepts"]["REQ-105"]["fire_egress_simulation"]["code_compliance_conclusion"])

    def test_req106_five_measurements(self):
        self.assertEqual(5, len(self.report["concepts"]["REQ-106"]["synthetic_measurements"]))

    def test_req106_minimum_available_55(self):
        self.assertEqual(55, min(item["available"] for item in self.report["concepts"]["REQ-106"]["synthetic_measurements"]))

    def test_req106_sensitivity_27_rows(self):
        self.assertEqual(27, len(self.report["concepts"]["REQ-106"]["sensitivity"]))

    def test_req106_special_demand_40(self):
        self.assertEqual(40, self.report["concepts"]["REQ-106"]["synthetic_demands"]["special_peak"])

    def test_req108_five_phases(self):
        self.assertEqual(5, len(self.report["concepts"]["REQ-108"]["phases"]))

    def test_req108_no_aerius_result(self):
        self.assertEqual("NOT_RUN_NO_DEPOSITION_RESULT_GENERATED", self.report["concepts"]["REQ-108"]["aerius_calculation_status"])

    def test_all_consistency_checks(self):
        self.assertTrue(self.report["all_consistency_checks_passed"])
        self.assertEqual(11, self.report["consistency_check_count"])

    def test_end_to_end_validated(self):
        self.assertTrue(self.report["end_to_end_workflow_validated"])

    def test_concept_dossier_allowed(self):
        self.assertTrue(self.report["concept_dossier_generation_allowed"])

    def test_final_permit_release_blocked(self):
        self.assertFalse(self.report["final_permit_ready_generation_allowed"])

    def test_bb36_functional_validation_passed(self):
        self.assertTrue(self.report["bb36_functional_validation_passed"])

    def test_bb36_production_locked(self):
        self.assertFalse(self.report["bb36_production_release_allowed"])

    def test_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            self.assertEqual(44, sum(1 for path in Path(tmp).rglob("*") if path.is_file()))

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
            names = sorted(path.relative_to(first_root).as_posix() for path in first_root.rglob("*") if path.is_file())
            self.assertEqual(names, sorted(path.relative_to(second_root).as_posix() for path in second_root.rglob("*") if path.is_file()))
            self.assertTrue(all((first_root / name).read_bytes() == (second_root / name).read_bytes() for name in names))


if __name__ == "__main__":
    unittest.main()
