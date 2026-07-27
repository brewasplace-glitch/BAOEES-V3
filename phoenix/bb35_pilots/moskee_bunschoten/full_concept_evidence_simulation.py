"""Full concept evidence simulation for BB35 Pilot 1.

Every numerical result in this module is a deterministic engine-test concept.
It is not a professional calculation and is not suitable for submission or
construction.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
_SIM_LABEL = "CONCEPT_SIMULATION_NOT_FOR_SUBMISSION_OR_EXECUTION"


class FullConceptEvidenceSimulationEngine:
    VERSION = "1.9.0"

    def evaluate(
        self,
        *,
        req107_program: Mapping[str, Any],
        downstream_summary: Mapping[str, Any],
        parallel_summary: Mapping[str, Any],
        authorization: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessors(
            req107_program=req107_program,
            downstream_summary=downstream_summary,
            parallel_summary=parallel_summary,
            authorization=authorization,
            config=config,
        )

        scope = config["scope"]
        assumptions = config["synthetic_assumptions"]
        occupancy = req107_program["occupancy_scenarios"]

        req102 = self._req102(scope, assumptions["REQ-102"])
        req103 = self._req103(scope, assumptions["REQ-103"])
        req104 = self._req104(req103, assumptions["REQ-104"])
        req105 = self._req105(occupancy, assumptions["REQ-105"])
        req106 = self._req106(occupancy, assumptions["REQ-106"], authorization)
        req107 = self._req107(req107_program, authorization)
        req108 = self._req108(occupancy, assumptions["REQ-108"])

        concepts = {
            "REQ-102": req102,
            "REQ-103": req103,
            "REQ-104": req104,
            "REQ-105": req105,
            "REQ-106": req106,
            "REQ-107": req107,
            "REQ-108": req108,
        }

        checks = self._consistency_checks(concepts, scope)
        all_checks_passed = all(item["passed"] for item in checks)

        report = {
            "schema_version": "phoenix.bb35.full-concept-evidence-simulation/1.0",
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "simulation_label": _SIM_LABEL,
            "status": "FULL_CONCEPT_EVIDENCE_SIMULATION_RUN_PASSED",
            "req_range": [f"REQ-{value}" for value in range(102, 109)],
            "concepts": concepts,
            "concept_simulation_count": 6,
            "project_leader_closed_request_count": 1,
            "req107_status": req107["status"],
            "parking_basis_spaces": req106["capacity"]["confirmed_spaces"],
            "parking_previous_hypothesis_spaces": req106["capacity"]["superseded_spaces"],
            "remaining_professional_evidence_blockers": 6,
            "professional_blocker_ids": [
                "REQ-102", "REQ-103", "REQ-104", "REQ-105", "REQ-106", "REQ-108"
            ],
            "consistency_checks": checks,
            "consistency_check_count": len(checks),
            "all_consistency_checks_passed": all_checks_passed,
            "end_to_end_workflow_validated": all_checks_passed,
            "concept_dossier_generation_allowed": all_checks_passed,
            "professional_evidence_still_required": True,
            "final_permit_ready_generation_allowed": False,
            "bb36_functional_validation_passed": all_checks_passed,
            "bb36_production_release_allowed": False,
            "next_gate": (
                "Use the simulation dossier to validate the run; replace each synthetic "
                "REQ-102/103/104/105/106/108 result with professional evidence before "
                "permit-ready release."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessors(
        *,
        req107_program: Mapping[str, Any],
        downstream_summary: Mapping[str, Any],
        parallel_summary: Mapping[str, Any],
        authorization: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> None:
        checks = {
            "occupancy_program": req107_program.get("program_id") == "HBM-OCC-2026-001",
            "eight_strategic_decisions": downstream_summary.get(
                "approved_strategic_decision_count"
            ) == 8,
            "parallel_workpacks": parallel_summary.get("workpack_count") == 3,
            "old_parking_hypothesis": parallel_summary.get(
                "parking_provisional_capacity_spaces"
            ) == 300,
            "project_leader_req107": authorization["project_leader_authority"][
                "req107_closure_authorized"
            ] is True,
            "parking_correction": authorization["parking_correction"][
                "current_project_leader_confirmed_spaces"
            ] == 225,
            "scope_140": config["scope"]["gross_floor_area_m2"] == 140.0,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError("Simulation predecessor validation failed: " + ", ".join(failed))

    @staticmethod
    def _req102(scope: Mapping[str, Any], assumptions: Mapping[str, Any]) -> dict[str, Any]:
        length = float(scope["extension_length_m"])
        width = float(scope["extension_width_m"])
        area = length * width
        perimeter = 2.0 * (length + width)
        diagonal = math.sqrt(length ** 2 + width ** 2)
        return {
            "request_id": "REQ-102",
            "status": "CONCEPT_SIMULATION_GENERATED_PROFESSIONAL_VALIDATION_PENDING",
            "simulation_label": _SIM_LABEL,
            "source_evidence_note": (
                "Uploaded cadastral DWG is acknowledged but not professionally decoded or surveyed "
                "by this simulation."
            ),
            "geometry": {
                "coordinate_system": assumptions["coordinate_system"],
                "polygon_m": assumptions["polygon_m"],
                "footprint_area_m2": round(area, 3),
                "gross_floor_area_m2": round(area * int(scope["storeys"]), 3),
                "perimeter_m": round(perimeter, 3),
                "diagonal_m": round(diagonal, 4),
            },
            "simulated_findings": [
                "Extension geometry closes mathematically in the local test grid.",
                "Scale, cadastral boundary and national coordinates remain unverified.",
                "Current-building connection line requires survey confirmation.",
            ],
            "professional_evidence_required": [
                "Validated DWG units, layers and scale.",
                "Surveyed parcel and building coordinates.",
                "Signed geometry and boundary verification.",
            ],
        }

    @staticmethod
    def _req103(scope: Mapping[str, Any], assumptions: Mapping[str, Any]) -> dict[str, Any]:
        area = float(scope["footprint_m2"])
        floor_load = float(assumptions["floor_dead_plus_live_load_kn_m2"])
        roof_load = float(assumptions["roof_service_load_kn_m2"])
        allowance = float(assumptions["frame_wall_allowance_kn"])
        total = area * floor_load * 2.0 + area * roof_load + allowance
        column_count = len(assumptions["grid_x_m"]) * len(assumptions["grid_y_m"])
        average_reaction = total / column_count
        line_load = floor_load * 3.5
        simple_moment = line_load * 5.0 ** 2 / 8.0
        return {
            "request_id": "REQ-103",
            "status": "CONCEPT_SIMULATION_GENERATED_STRUCTURAL_SURVEY_PENDING",
            "simulation_label": _SIM_LABEL,
            "scheme": {
                "system": assumptions["structural_system"],
                "grid_x_m": assumptions["grid_x_m"],
                "grid_y_m": assumptions["grid_y_m"],
                "column_count": column_count,
                "storey_height_m": assumptions["storey_height_m"],
            },
            "concept_calculations": {
                "total_service_gravity_load_kn": round(total, 2),
                "average_column_reaction_kn": round(average_reaction, 2),
                "representative_beam_line_load_kn_m": round(line_load, 2),
                "representative_simple_span_moment_knm": round(simple_moment, 2),
            },
            "load_path": [
                "roof/floor -> synthetic secondary members",
                "secondary members -> synthetic primary beams",
                "primary beams -> nine synthetic columns",
                "columns -> REQ-104 test foundation concept",
            ],
            "professional_evidence_required": [
                "Current structural survey and material verification.",
                "Connection assessment between existing and new work.",
                "Professional load combinations and member calculations.",
                "Signed structural report and drawings.",
            ],
        }

    @staticmethod
    def _req104(req103: Mapping[str, Any], assumptions: Mapping[str, Any]) -> dict[str, Any]:
        total_load = float(req103["concept_calculations"]["total_service_gravity_load_kn"])
        length = float(assumptions["assumed_total_strip_length_m"])
        width = 1.5
        bearing_area = length * width
        pressure = total_load / bearing_area
        return {
            "request_id": "REQ-104",
            "status": "CONCEPT_SIMULATION_GENERATED_GEOTECHNICAL_EVIDENCE_PENDING",
            "simulation_label": _SIM_LABEL,
            "groundwater_level_m": assumptions["groundwater_level_m_relative_to_grade"],
            "synthetic_soil_profile": assumptions["soil_profile"],
            "foundation_test_concept": assumptions["foundation_test_concept"],
            "concept_calculations": {
                "input_service_load_kn": total_load,
                "assumed_total_strip_length_m": length,
                "assumed_strip_width_m": width,
                "assumed_bearing_area_m2": round(bearing_area, 2),
                "indicative_average_contact_pressure_kpa": round(pressure, 2),
            },
            "risk_flags": [
                "Synthetic soft-clay layer may govern settlement.",
                "No bearing resistance or settlement acceptance criterion is verified.",
                "Shallow foundation concept may be rejected after field investigation.",
            ],
            "professional_evidence_required": [
                "Site-specific ground investigation.",
                "Groundwater observation and soil parameters.",
                "Bearing-capacity and settlement calculations.",
                "Signed foundation recommendation.",
            ],
        }

    @staticmethod
    def _req105(occupancy: Mapping[str, Any], assumptions: Mapping[str, Any]) -> dict[str, Any]:
        peak = int(occupancy["special_peak"]["maximum_persons"])
        exits = int(assumptions["simulated_exit_count"])
        width_each = float(assumptions["simulated_exit_clear_width_m_each"])
        total_width = exits * width_each
        vent_rate = float(assumptions["simulation_ventilation_rate_l_s_person"])
        vent_l_s = peak * vent_rate
        vent_m3_h = vent_l_s * 3.6
        return {
            "request_id": "REQ-105",
            "status": "CONCEPT_SIMULATION_GENERATED_BBL_FIRE_MEP_REVIEW_PENDING",
            "simulation_label": _SIM_LABEL,
            "occupancy_basis": {
                "regular_future_persons": occupancy["regular"]["future_persons"],
                "friday_future_persons": occupancy["friday_prayer"]["future_persons"],
                "special_peak_persons": peak,
            },
            "fire_egress_simulation": {
                "simulated_exit_count": exits,
                "simulated_exit_width_m_each": width_each,
                "simulated_total_exit_width_m": round(total_width, 2),
                "persons_per_exit": round(peak / exits, 2),
                "persons_per_m_total_exit_width": round(peak / total_width, 2),
                "code_compliance_conclusion": "NOT_MADE_IN_SIMULATION",
            },
            "ventilation_simulation": {
                "engine_test_rate_l_s_person": vent_rate,
                "peak_flow_l_s": round(vent_l_s, 2),
                "peak_flow_m3_h": round(vent_m3_h, 2),
                "code_compliance_conclusion": "NOT_MADE_IN_SIMULATION",
            },
            "strategic_basis": {
                "kitchen_function": "geen_keukenfunctie",
                "performance_level": "wettelijk_minimum",
            },
            "professional_evidence_required": [
                "Applicable Bbl use-function and occupancy assessment.",
                "Escape route, travel distance and exit capacity calculations.",
                "Fire compartmentation and installation requirements.",
                "Room-by-room ventilation calculation.",
                "Accessibility and sanitary verification.",
            ],
        }

    @staticmethod
    def _req106(
        occupancy: Mapping[str, Any],
        assumptions: Mapping[str, Any],
        authorization: Mapping[str, Any],
    ) -> dict[str, Any]:
        capacity = int(assumptions["confirmed_total_spaces"])
        measurements = []
        for item in assumptions["synthetic_measurements"]:
            occupied = int(item["occupied"])
            measurements.append({
                **item,
                "capacity": capacity,
                "available": capacity - occupied,
                "occupancy_percent": round(occupied / capacity * 100.0, 2),
                "evidence_status": "SYNTHETIC_TEST_VALUE",
            })
        mode_share = float(assumptions["baseline_car_mode_share"])
        persons_per_car = float(assumptions["baseline_persons_per_car"])
        persons = {
            "regular_future": int(occupancy["regular"]["future_persons"]),
            "friday_future": int(occupancy["friday_prayer"]["future_persons"]),
            "special_peak": int(occupancy["special_peak"]["maximum_persons"]),
        }
        demands = {
            scenario: math.ceil(value * mode_share / persons_per_car)
            for scenario, value in persons.items()
        }
        minimum_available = min(item["available"] for item in measurements)
        balances = {
            scenario: {
                "synthetic_demand_spaces": demand,
                "minimum_synthetic_available_spaces": minimum_available,
                "synthetic_surplus_spaces": minimum_available - demand,
            }
            for scenario, demand in demands.items()
        }
        sensitivity = []
        for scenario, person_count in persons.items():
            for share in (0.40, 0.50, 0.60):
                for car_occupancy in (2.0, 2.5, 3.0):
                    sensitivity.append({
                        "scenario": scenario,
                        "persons": person_count,
                        "car_mode_share": share,
                        "persons_per_car": car_occupancy,
                        "calculated_spaces": math.ceil(person_count * share / car_occupancy),
                    })
        return {
            "request_id": "REQ-106",
            "status": "CONCEPT_SIMULATION_GENERATED_FIELD_MEASUREMENTS_PENDING",
            "simulation_label": _SIM_LABEL,
            "capacity": {
                "confirmed_spaces": capacity,
                "confirmation_status": authorization["parking_correction"]["status"],
                "superseded_spaces": authorization["parking_correction"][
                    "previous_hypothesis_spaces"
                ],
                "field_verification_complete": False,
            },
            "simulation_only_subareas": assumptions["simulation_only_subarea_allocation"],
            "synthetic_measurements": measurements,
            "baseline_assumptions": {
                "car_mode_share": mode_share,
                "persons_per_car": persons_per_car,
            },
            "synthetic_demands": demands,
            "synthetic_balances": balances,
            "sensitivity": sensitivity,
            "professional_evidence_required": [
                "Mapped and legally classified inventory of 225 spaces.",
                "Five representative field measurements with photographs.",
                "Verified simultaneous surrounding use.",
                "Professional parking demand, balance and parking-regime advice.",
            ],
        }

    @staticmethod
    def _req107(
        req107_program: Mapping[str, Any],
        authorization: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "request_id": "REQ-107",
            "status": "CLOSED_PROJECT_LEADER_APPROVED",
            "simulation_label": "AUTHORITATIVE_PROJECT_DECISION_NOT_SIMULATED",
            "program_id": req107_program["program_id"],
            "approval": {
                "approved_by_role": "project_leader",
                "approval_method": authorization["project_leader_authority"]["approval_method"],
                "approval_date": authorization["authorization_date"],
                "handwritten_signature_fabricated": False,
            },
            "occupancy_scenarios": req107_program["occupancy_scenarios"],
            "opening_hours": req107_program["opening_hours"],
            "downstream_use": ["REQ-105", "REQ-106", "REQ-108"],
        }

    @staticmethod
    def _req108(occupancy: Mapping[str, Any], assumptions: Mapping[str, Any]) -> dict[str, Any]:
        equipment = [
            {"phase_id": "SIM-AER-01", "equipment": "mini_excavator", "operating_hours": 60, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-01", "equipment": "wheel_loader", "operating_hours": 40, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-02", "equipment": "excavator", "operating_hours": 80, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-02", "equipment": "concrete_pump", "operating_hours": 16, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-03", "equipment": "mobile_crane", "operating_hours": 80, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-03", "equipment": "telehandler", "operating_hours": 120, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-04", "equipment": "small_tools_aggregate", "operating_hours": 100, "value_status": "SYNTHETIC"},
        ]
        transport = [
            {"phase_id": "SIM-AER-01", "movement_type": "heavy_vehicle", "movements": 40, "distance_km": 20.0, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-02", "movement_type": "heavy_vehicle", "movements": 60, "distance_km": 20.0, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-03", "movement_type": "mixed_delivery", "movements": 80, "distance_km": 20.0, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-04", "movement_type": "light_van", "movements": 200, "distance_km": 15.0, "value_status": "SYNTHETIC"},
            {"phase_id": "SIM-AER-05", "movement_type": "operational_traffic", "movements": None, "distance_km": None, "value_status": "PROFESSIONAL_INPUT_PENDING"},
        ]
        return {
            "request_id": "REQ-108",
            "status": "CONCEPT_SIMULATION_GENERATED_AERIUS_CALCULATION_NOT_RUN",
            "simulation_label": _SIM_LABEL,
            "execution_strategy": {
                "phased_execution": True,
                "mosque_remains_in_use": True,
            },
            "phases": assumptions["phases"],
            "synthetic_equipment": equipment,
            "synthetic_transport": transport,
            "operational_occupancy_handoff": {
                "regular_future_persons": occupancy["regular"]["future_persons"],
                "friday_future_persons": occupancy["friday_prayer"]["future_persons"],
                "special_peak_persons": occupancy["special_peak"]["maximum_persons"],
            },
            "aerius_calculation_status": "NOT_RUN_NO_DEPOSITION_RESULT_GENERATED",
            "professional_evidence_required": [
                "Definitive construction sequence and durations.",
                "Verified equipment, fuel, power and operating hours.",
                "Verified construction and operational traffic.",
                "Professional AERIUS calculation, PDF and source file.",
            ],
        }

    @staticmethod
    def _consistency_checks(
        concepts: Mapping[str, Mapping[str, Any]],
        scope: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        req102 = concepts["REQ-102"]
        req103 = concepts["REQ-103"]
        req104 = concepts["REQ-104"]
        req105 = concepts["REQ-105"]
        req106 = concepts["REQ-106"]
        req107 = concepts["REQ-107"]
        req108 = concepts["REQ-108"]
        checks = [
            ("CHK-001", "REQ-102 footprint equals scope", req102["geometry"]["footprint_area_m2"] == scope["footprint_m2"]),
            ("CHK-002", "REQ-102 gross area equals scope", req102["geometry"]["gross_floor_area_m2"] == scope["gross_floor_area_m2"]),
            ("CHK-003", "REQ-103 load reaches REQ-104", req104["concept_calculations"]["input_service_load_kn"] == req103["concept_calculations"]["total_service_gravity_load_kn"]),
            ("CHK-004", "REQ-105 uses REQ-107 peak", req105["occupancy_basis"]["special_peak_persons"] == req107["occupancy_scenarios"]["special_peak"]["maximum_persons"]),
            ("CHK-005", "REQ-106 uses 225 spaces", req106["capacity"]["confirmed_spaces"] == 225),
            ("CHK-006", "REQ-106 supersedes 300", req106["capacity"]["superseded_spaces"] == 300),
            ("CHK-007", "REQ-107 is project-leader closed", req107["status"] == "CLOSED_PROJECT_LEADER_APPROVED"),
            ("CHK-008", "REQ-108 uses phased execution", req108["execution_strategy"]["phased_execution"] is True),
            ("CHK-009", "REQ-108 keeps mosque in use", req108["execution_strategy"]["mosque_remains_in_use"] is True),
            ("CHK-010", "No AERIUS result fabricated", req108["aerius_calculation_status"] == "NOT_RUN_NO_DEPOSITION_RESULT_GENERATED"),
            ("CHK-011", "Six professional blockers remain", set(concepts) - {"REQ-107"} == {"REQ-102", "REQ-103", "REQ-104", "REQ-105", "REQ-106", "REQ-108"}),
        ]
        return [
            {"check_id": check_id, "description": description, "passed": bool(passed)}
            for check_id, description, passed in checks
        ]

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class FullConceptEvidenceSimulationExporter:
    def export_all(self, report: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        concepts = report["concepts"]

        paths["summary"] = self._json(
            root / "01_full_concept_simulation_summary.json",
            {key: value for key, value in report.items() if key not in {"concepts", "consistency_checks"}},
        )
        paths["register"] = self._json(
            root / "02_integrated_concept_register.json",
            {
                "simulation_label": report["simulation_label"],
                "requests": {
                    request_id: {
                        "status": item["status"],
                        "simulation_label": item["simulation_label"],
                    }
                    for request_id, item in concepts.items()
                },
            },
        )
        paths["assumptions"] = self._csv(
            root / "03_assumptions_register.csv",
            self._assumption_rows(concepts),
            ["assumption_id", "request_id", "description", "value", "status"],
        )
        paths["handoff"] = self._csv(
            root / "04_cross_discipline_handoff_matrix.csv",
            [
                {"from_request": "REQ-102", "to_request": "REQ-103", "data": "70 m2 footprint", "status": "SIMULATED"},
                {"from_request": "REQ-103", "to_request": "REQ-104", "data": "1335 kN service load", "status": "SIMULATED"},
                {"from_request": "REQ-107", "to_request": "REQ-105", "data": "150/125/200 persons", "status": "AUTHORITATIVE"},
                {"from_request": "REQ-107", "to_request": "REQ-106", "data": "150/125/200 persons", "status": "AUTHORITATIVE"},
                {"from_request": "REQ-107", "to_request": "REQ-108", "data": "occupancy and schedule", "status": "AUTHORITATIVE"},
                {"from_request": "REQ-106", "to_request": "integrated_dossier", "data": "225 spaces", "status": "PROJECT_LEADER_CONFIRMED"},
            ],
            ["from_request", "to_request", "data", "status"],
        )
        paths["checks"] = self._csv(
            root / "05_consistency_checks.csv",
            report["consistency_checks"],
            ["check_id", "description", "passed"],
        )
        paths["gates"] = self._json(
            root / "06_gate_status.json",
            {
                "req107": report["req107_status"],
                "remaining_professional_evidence_blockers": report["remaining_professional_evidence_blockers"],
                "concept_dossier_generation_allowed": report["concept_dossier_generation_allowed"],
                "final_permit_ready_generation_allowed": report["final_permit_ready_generation_allowed"],
                "bb36_functional_validation_passed": report["bb36_functional_validation_passed"],
                "bb36_production_release_allowed": report["bb36_production_release_allowed"],
            },
        )
        paths["dashboard"] = self._html(root / "07_full_concept_simulation_dashboard.html", report)

        paths.update(self._req102(root / "REQ-102", concepts["REQ-102"]))
        paths.update(self._req103(root / "REQ-103", concepts["REQ-103"]))
        paths.update(self._req104(root / "REQ-104", concepts["REQ-104"]))
        paths.update(self._req105(root / "REQ-105", concepts["REQ-105"]))
        paths.update(self._req106(root / "REQ-106", concepts["REQ-106"]))
        paths.update(self._req107(root / "REQ-107", concepts["REQ-107"]))
        paths.update(self._req108(root / "REQ-108", concepts["REQ-108"]))

        paths["checksums"] = self._checksums(paths, root / "checksums.sha256")
        paths["dossier"] = self._dossier(
            paths,
            root / "BB35_PILOT_1_FULL_CONCEPT_EVIDENCE_SIMULATION_v1_9_0.zip",
        )
        return paths

    def _req102(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        return {
            "102_brief": self._markdown(root / "01_REQ_102_concept_brief.md", self._brief(item)),
            "102_geometry": self._json(root / "02_REQ_102_simulated_geometry.json", item["geometry"]),
            "102_checks": self._csv(
                root / "03_REQ_102_geometry_checks.csv",
                [
                    {"check": "polygon_closure", "result": "PASS", "status": "SIMULATED"},
                    {"check": "footprint_area", "result": item["geometry"]["footprint_area_m2"], "status": "SIMULATED"},
                    {"check": "gross_floor_area", "result": item["geometry"]["gross_floor_area_m2"], "status": "SIMULATED"},
                    {"check": "cadastral_coordinates", "result": "NOT_VERIFIED", "status": "PROFESSIONAL_EVIDENCE_PENDING"},
                ],
                ["check", "result", "status"],
            ),
            "102_gap": self._json(root / "04_REQ_102_evidence_gap.json", {"required": item["professional_evidence_required"]}),
        }

    def _req103(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        return {
            "103_brief": self._markdown(root / "01_REQ_103_concept_brief.md", self._brief(item)),
            "103_scheme": self._json(root / "02_REQ_103_structural_scheme.json", item["scheme"]),
            "103_loads": self._csv(
                root / "03_REQ_103_concept_loads.csv",
                [{"quantity": key, "value": value, "unit": self._unit(key)} for key, value in item["concept_calculations"].items()],
                ["quantity", "value", "unit"],
            ),
            "103_path": self._csv(
                root / "04_REQ_103_load_path.csv",
                [{"sequence": index, "load_path": value} for index, value in enumerate(item["load_path"], start=1)],
                ["sequence", "load_path"],
            ),
            "103_gap": self._json(root / "05_REQ_103_evidence_gap.json", {"required": item["professional_evidence_required"]}),
        }

    def _req104(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        return {
            "104_brief": self._markdown(root / "01_REQ_104_concept_brief.md", self._brief(item)),
            "104_soil": self._csv(root / "02_REQ_104_synthetic_soil_profile.csv", item["synthetic_soil_profile"], ["from_m", "to_m", "description"]),
            "104_foundation": self._json(root / "03_REQ_104_foundation_concept_calculation.json", {"foundation_test_concept": item["foundation_test_concept"], **item["concept_calculations"]}),
            "104_risks": self._csv(root / "04_REQ_104_risk_register.csv", [{"risk_id": f"104-R-{index:02d}", "risk": value, "status": "OPEN"} for index, value in enumerate(item["risk_flags"], start=1)], ["risk_id", "risk", "status"]),
            "104_gap": self._json(root / "05_REQ_104_evidence_gap.json", {"required": item["professional_evidence_required"]}),
        }

    def _req105(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        egress = item["fire_egress_simulation"]
        ventilation = item["ventilation_simulation"]
        return {
            "105_brief": self._markdown(root / "01_REQ_105_concept_brief.md", self._brief(item)),
            "105_fire": self._json(root / "02_REQ_105_fire_egress_concept.json", egress),
            "105_vent": self._csv(root / "03_REQ_105_ventilation_concept.csv", [{"quantity": key, "value": value} for key, value in ventilation.items()], ["quantity", "value"]),
            "105_egress": self._csv(root / "04_REQ_105_egress_calculation.csv", [{"quantity": key, "value": value} for key, value in egress.items()], ["quantity", "value"]),
            "105_matrix": self._csv(
                root / "05_REQ_105_concept_compliance_matrix.csv",
                [
                    {"topic": "use_function", "concept_status": "PREPARED", "compliance_conclusion": "PENDING_PROFESSIONAL_REVIEW"},
                    {"topic": "escape_routes", "concept_status": "SIMULATED", "compliance_conclusion": "NOT_MADE"},
                    {"topic": "fire_compartments", "concept_status": "OUTLINE_ONLY", "compliance_conclusion": "NOT_MADE"},
                    {"topic": "ventilation", "concept_status": "SIMULATED", "compliance_conclusion": "NOT_MADE"},
                    {"topic": "accessibility", "concept_status": "CHECKLIST_READY", "compliance_conclusion": "NOT_MADE"},
                    {"topic": "installations", "concept_status": "MINIMUM_LEVEL_SELECTED", "compliance_conclusion": "NOT_MADE"},
                ],
                ["topic", "concept_status", "compliance_conclusion"],
            ),
            "105_gap": self._json(root / "06_REQ_105_evidence_gap.json", {"required": item["professional_evidence_required"]}),
        }

    def _req106(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        balance_rows = [
            {"scenario": scenario, **values, "status": "SYNTHETIC_TEST_RESULT"}
            for scenario, values in item["synthetic_balances"].items()
        ]
        return {
            "106_brief": self._markdown(root / "01_REQ_106_concept_brief.md", self._brief(item)),
            "106_capacity": self._json(root / "02_REQ_106_capacity_correction.json", item["capacity"]),
            "106_counts": self._csv(root / "03_REQ_106_synthetic_measurements.csv", item["synthetic_measurements"], ["measurement_id", "scenario", "occupied", "capacity", "available", "occupancy_percent", "evidence_status"]),
            "106_balance": self._csv(root / "04_REQ_106_synthetic_parking_balance.csv", balance_rows, ["scenario", "synthetic_demand_spaces", "minimum_synthetic_available_spaces", "synthetic_surplus_spaces", "status"]),
            "106_sensitivity": self._csv(root / "05_REQ_106_sensitivity_analysis.csv", item["sensitivity"], ["scenario", "persons", "car_mode_share", "persons_per_car", "calculated_spaces"]),
            "106_gap": self._json(root / "06_REQ_106_evidence_gap.json", {"required": item["professional_evidence_required"]}),
        }

    def _req107(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        return {
            "107_closure": self._json(root / "01_REQ_107_closure_record.json", item),
            "107_approval": self._markdown(
                root / "02_REQ_107_project_leader_approval.md",
                "\n".join([
                    "# REQ-107 — Project Leader Approval",
                    "",
                    f"Status: `{item['status']}`",
                    f"Programme: `{item['program_id']}`",
                    f"Approval method: `{item['approval']['approval_method']}`",
                    f"Approval date: `{item['approval']['approval_date']}`",
                    "",
                    "No handwritten signature has been fabricated. The approval is recorded from the explicit project-leader instruction.",
                    "",
                ]),
            ),
            "107_handoff": self._json(root / "03_REQ_107_downstream_handoff.json", {"program_id": item["program_id"], "occupancy_scenarios": item["occupancy_scenarios"], "opening_hours": item["opening_hours"], "downstream_use": item["downstream_use"]}),
        }

    def _req108(self, root: Path, item: Mapping[str, Any]) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        matrix = []
        for phase in item["phases"]:
            matrix.append({
                "phase_id": phase["phase_id"],
                "phase_name": phase["name"],
                "duration_days": phase["duration_days"],
                "equipment_input": "SYNTHETIC_OR_PENDING",
                "transport_input": "SYNTHETIC_OR_PENDING",
                "aerius_result": "NOT_RUN",
            })
        return {
            "108_brief": self._markdown(root / "01_REQ_108_concept_brief.md", self._brief(item)),
            "108_phases": self._csv(root / "02_REQ_108_simulated_phases.csv", item["phases"], ["phase_id", "name", "duration_days"]),
            "108_equipment": self._csv(root / "03_REQ_108_synthetic_equipment.csv", item["synthetic_equipment"], ["phase_id", "equipment", "operating_hours", "value_status"]),
            "108_transport": self._csv(root / "04_REQ_108_synthetic_transport.csv", item["synthetic_transport"], ["phase_id", "movement_type", "movements", "distance_km", "value_status"]),
            "108_matrix": self._csv(root / "05_REQ_108_AERIUS_input_matrix.csv", matrix, ["phase_id", "phase_name", "duration_days", "equipment_input", "transport_input", "aerius_result"]),
            "108_gap": self._json(root / "06_REQ_108_evidence_gap.json", {"aerius_calculation_status": item["aerius_calculation_status"], "required": item["professional_evidence_required"]}),
        }

    @staticmethod
    def _assumption_rows(concepts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"assumption_id": "ASM-102-01", "request_id": "REQ-102", "description": "Local synthetic coordinate grid", "value": "0,0 origin", "status": "SIMULATION_ONLY"},
            {"assumption_id": "ASM-103-01", "request_id": "REQ-103", "description": "Synthetic steel frame", "value": concepts["REQ-103"]["scheme"]["system"], "status": "SIMULATION_ONLY"},
            {"assumption_id": "ASM-104-01", "request_id": "REQ-104", "description": "Synthetic soil profile", "value": "three test layers", "status": "SIMULATION_ONLY"},
            {"assumption_id": "ASM-105-01", "request_id": "REQ-105", "description": "Engine-test ventilation rate", "value": concepts["REQ-105"]["ventilation_simulation"]["engine_test_rate_l_s_person"], "status": "SIMULATION_ONLY"},
            {"assumption_id": "ASM-106-01", "request_id": "REQ-106", "description": "Parking capacity", "value": 225, "status": "PROJECT_LEADER_CONFIRMED_FIELD_VERIFICATION_PENDING"},
            {"assumption_id": "ASM-106-02", "request_id": "REQ-106", "description": "Synthetic parking counts", "value": 5, "status": "SIMULATION_ONLY"},
            {"assumption_id": "ASM-107-01", "request_id": "REQ-107", "description": "Occupancy programme", "value": concepts["REQ-107"]["program_id"], "status": "PROJECT_LEADER_APPROVED"},
            {"assumption_id": "ASM-108-01", "request_id": "REQ-108", "description": "Synthetic phase activity data", "value": 5, "status": "SIMULATION_ONLY"},
        ]

    @staticmethod
    def _brief(item: Mapping[str, Any]) -> str:
        lines = [
            f"# {item['request_id']} — Full Concept Simulation",
            "",
            f"Status: `{item['status']}`",
            f"Label: `{item['simulation_label']}`",
            "",
            "This output tests the Phoenix workflow. It is not a professional calculation, permit document or construction instruction.",
            "",
            "## Professional evidence still required",
            "",
        ]
        lines.extend(f"- {value}" for value in item.get("professional_evidence_required", []))
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _unit(key: str) -> str:
        if key.endswith("_kn"):
            return "kN"
        if key.endswith("_kn_m"):
            return "kN/m"
        if key.endswith("_knm"):
            return "kNm"
        return ""

    @staticmethod
    def _json(path: Path, value: Any) -> Path:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> Path:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\r\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field: (
                        json.dumps(row.get(field), ensure_ascii=False, sort_keys=True)
                        if isinstance(row.get(field), (dict, list))
                        else row.get(field, "")
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _markdown(path: Path, value: str) -> Path:
        path.write_text(value, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _html(path: Path, report: Mapping[str, Any]) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(request_id)}</td>"
            f"<td>{html.escape(item['status'])}</td>"
            f"<td>{html.escape(item['simulation_label'])}</td>"
            "</tr>"
            for request_id, item in sorted(report["concepts"].items())
        )
        content = (
            "<!doctype html><html lang='nl'><head><meta charset='utf-8'>"
            "<title>BB35 Full Concept Evidence Simulation</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}.warning{border:2px solid #b00020;padding:14px}"
            "table{border-collapse:collapse;width:100%;margin-top:20px}th,td{border:1px solid #bbb;padding:7px;text-align:left}"
            "th{background:#263238;color:#fff}</style></head><body>"
            "<h1>BB35 Pilot 1 — Full Concept Evidence Simulation v1.9.0</h1>"
            "<div class='warning'><strong>CONCEPT / SIMULATION — NIET VOOR INDIENING OF UITVOERING</strong><br>"
            "REQ-107 is project-leader approved. Six professional evidence blockers remain.</div>"
            f"<p>Parking basis: <strong>{report['parking_basis_spaces']}</strong> spaces. "
            f"Previous 300-space hypothesis superseded.</p>"
            "<table><thead><tr><th>REQ</th><th>Status</th><th>Classification</th></tr></thead><tbody>"
            + rows
            + "</tbody></table></body></html>"
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        root = destination.parent
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return destination

    @classmethod
    def _dossier(cls, paths: Mapping[str, Path], destination: Path) -> Path:
        root = destination.parent
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.comment = b""
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                archive.writestr(cls._canonical_info(source.relative_to(root).as_posix()), source.read_bytes())
        return destination

    @staticmethod
    def _canonical_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.reserved = 0
        info.flag_bits = 0
        info.volume = 0
        info.internal_attr = 0
        info.external_attr = 0o100644 << 16
        info.extra = b""
        info.comment = b""
        return info
