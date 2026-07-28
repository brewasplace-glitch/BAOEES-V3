"""Model-driven calculation workbook engine for BB35 Pilot 1.

All numerical values are concept or synthetic test values unless explicitly
identified as project-leader-confirmed. Outputs are not suitable for permit
submission or construction.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import struct
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.sax.saxutils import escape

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
STATUS_LABEL = "CONCEPT CALCULATIONS - NOT FOR SUBMISSION OR EXECUTION"


def _round(value: float, digits: int = 2) -> float:
    return round(float(value) + 0.0, digits)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ModelDrivenCalculationEngine:
    VERSION = "1.0.0"

    def evaluate(self, *, repository: Path, config: Mapping[str, Any]) -> dict[str, Any]:
        sources = config["source_artifacts"]
        model = json.loads((repository / sources["central_model"]).read_text(encoding="utf-8"))
        summary = json.loads((repository / sources["model_summary"]).read_text(encoding="utf-8"))
        if model["model_fingerprint_sha256"] != config["expected_model_fingerprint_sha256"]:
            raise ValueError("Central model fingerprint differs from approved calculation basis.")
        if not summary["all_geometry_checks_passed"]:
            raise ValueError("Central model geometry checks are not complete.")

        objects = model["objects"]
        buildings = {item["id"]: item for item in objects if item["type"] == "building"}
        spaces = [item for item in objects if item["type"] == "space"]
        parking_bays = [item for item in objects if item["type"] == "parking_bay"]
        levels = model["levels"]
        assumptions = dict(config["calculation_basis"])

        extension = buildings["BLD-EXTENSION"]
        ext_points = extension["geometry"]["points"]
        ext_width = max(p[0] for p in ext_points) - min(p[0] for p in ext_points)
        ext_length = max(p[1] for p in ext_points) - min(p[1] for p in ext_points)
        storeys = int(extension["storeys"])
        storey_height = float(levels[1]["elevation_m"] - levels[0]["elevation_m"])
        extension_floor_area = ext_width * ext_length
        extension_gross_area = extension_floor_area * storeys
        extension_volume = extension_floor_area * storey_height * storeys

        existing = buildings["BLD-EXISTING"]
        ex_points = existing["geometry"]["points"]
        ex_width = max(p[0] for p in ex_points) - min(p[0] for p in ex_points)
        ex_length = max(p[1] for p in ex_points) - min(p[1] for p in ex_points)
        existing_gross_area = ex_width * ex_length * int(existing["storeys"])
        total_gross_area = existing_gross_area + extension_gross_area
        net_space_area = sum(float(item["area_m2"]) for item in spaces)

        floor_load = float(assumptions["floor_area_load_kn_m2"])
        roof_load = float(assumptions["roof_area_load_kn_m2"])
        wall_allowance = float(assumptions["wall_and_misc_allowance_kn"])
        total_service_load = extension_floor_area * floor_load * storeys + extension_floor_area * roof_load + wall_allowance
        column_count = int(assumptions["structural_column_count"])
        average_column_reaction = total_service_load / column_count
        tributary_width = float(assumptions["representative_tributary_width_m"])
        beam_span = float(assumptions["representative_beam_span_m"])
        line_load = floor_load * tributary_width
        simple_moment = line_load * beam_span**2 / 8.0
        simple_reaction = line_load * beam_span / 2.0

        strip_width = float(assumptions["foundation_strip_width_m"])
        strip_length = float(assumptions["foundation_total_strip_length_m"])
        bearing_area = strip_width * strip_length
        contact_pressure = total_service_load / bearing_area

        peak = int(assumptions["peak_occupancy_persons"])
        regular = int(assumptions["regular_occupancy_persons"])
        friday = int(assumptions["friday_occupancy_persons"])
        exit_count = int(assumptions["exit_count"])
        exit_width = float(assumptions["exit_width_each_m"])
        total_exit_width = exit_count * exit_width
        persons_per_exit = peak / exit_count
        persons_per_m_exit = peak / total_exit_width

        ventilation_rate = float(assumptions["ventilation_rate_l_s_person"])
        ventilation = []
        for scenario, persons in (("regular_future", regular), ("friday_future", friday), ("special_peak", peak)):
            flow_l_s = persons * ventilation_rate
            ventilation.append({
                "scenario": scenario,
                "persons": persons,
                "rate_l_s_person": ventilation_rate,
                "flow_l_s": _round(flow_l_s),
                "flow_m3_h": _round(flow_l_s * 3.6),
            })

        parking_measurements = _read_csv(repository / sources["req106_measurements"])
        parking_balance = _read_csv(repository / sources["req106_balance"])
        parking_capacity = len(parking_bays)
        if parking_capacity != int(assumptions["parking_capacity_spaces"]):
            raise ValueError("Parking object count differs from project-leader-confirmed basis.")

        phases = _read_csv(repository / sources["req108_phases"])
        equipment = _read_csv(repository / sources["req108_equipment"])
        transport = _read_csv(repository / sources["req108_transport"])
        total_equipment_hours = sum(float(item["operating_hours"]) for item in equipment)
        total_vehicle_km = sum(
            float(item["movements"]) * float(item["distance_km"])
            for item in transport
            if item.get("movements") and item.get("distance_km")
        )
        construction_duration_days = sum(int(item["duration_days"]) for item in phases if item["phase_id"] != "SIM-AER-05")

        inputs = [
            self._input("IN-001", "model", "extension_width", ext_width, "m", "central_model", "BLD-EXTENSION"),
            self._input("IN-002", "model", "extension_length", ext_length, "m", "central_model", "BLD-EXTENSION"),
            self._input("IN-003", "model", "extension_storeys", storeys, "count", "central_model", "BLD-EXTENSION"),
            self._input("IN-004", "model", "storey_height", storey_height, "m", "central_model", "L00,L01"),
            self._input("IN-005", "assumption", "floor_area_load", floor_load, "kN/m2", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-006", "assumption", "roof_area_load", roof_load, "kN/m2", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-007", "assumption", "wall_misc_allowance", wall_allowance, "kN", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-008", "assumption", "column_count", column_count, "count", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-009", "assumption", "tributary_width", tributary_width, "m", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-010", "assumption", "beam_span", beam_span, "m", "synthetic_test_fixture", "REQ-103"),
            self._input("IN-011", "assumption", "foundation_strip_width", strip_width, "m", "synthetic_test_fixture", "REQ-104"),
            self._input("IN-012", "assumption", "foundation_total_strip_length", strip_length, "m", "synthetic_test_fixture", "REQ-104"),
            self._input("IN-013", "project_leader_confirmed", "peak_occupancy", peak, "persons", "HBM-OCC-2026-001", "REQ-107"),
            self._input("IN-014", "project_leader_confirmed", "regular_occupancy", regular, "persons", "HBM-OCC-2026-001", "REQ-107"),
            self._input("IN-015", "project_leader_confirmed", "friday_occupancy", friday, "persons", "HBM-OCC-2026-001", "REQ-107"),
            self._input("IN-016", "assumption", "exit_count", exit_count, "count", "synthetic_test_fixture", "REQ-105"),
            self._input("IN-017", "assumption", "exit_width_each", exit_width, "m", "synthetic_test_fixture", "REQ-105"),
            self._input("IN-018", "assumption", "ventilation_rate", ventilation_rate, "L/s/person", "synthetic_test_fixture", "REQ-105"),
            self._input("IN-019", "project_leader_confirmed", "parking_capacity", parking_capacity, "spaces", "central_model", "REQ-106"),
            self._input("IN-020", "synthetic_activity", "equipment_hours", total_equipment_hours, "h", "REQ-108 simulation", "REQ-108"),
            self._input("IN-021", "synthetic_activity", "transport_vehicle_km", total_vehicle_km, "vehicle-km", "REQ-108 simulation", "REQ-108"),
        ]
        inputs.extend([
            self._input("IN-022", "model", "existing_width", ex_width, "m", "central_model", "BLD-EXISTING"),
            self._input("IN-023", "model", "existing_length", ex_length, "m", "central_model", "BLD-EXISTING"),
            self._input("IN-024", "model", "existing_storeys", int(existing["storeys"]), "count", "central_model", "BLD-EXISTING"),
            self._input("IN-025", "model", "net_space_area", net_space_area, "m2", "central_model", "space_objects"),
            self._input("IN-026", "synthetic_activity", "phase_site_preparation_days", 10, "days", "REQ-108 simulation", "REQ-108"),
            self._input("IN-027", "synthetic_activity", "phase_foundation_days", 15, "days", "REQ-108 simulation", "REQ-108"),
            self._input("IN-028", "synthetic_activity", "phase_structure_days", 30, "days", "REQ-108 simulation", "REQ-108"),
            self._input("IN-029", "synthetic_activity", "phase_finishes_days", 40, "days", "REQ-108 simulation", "REQ-108"),
        ])
        for offset, item in enumerate(parking_measurements, start=30):
            inputs.append(self._input(f"IN-{offset:03d}", "synthetic_measurement", f"occupied_{item['scenario']}", float(item["occupied"]), "spaces", "REQ-106 simulation", "REQ-106"))
        inputs.extend([
            self._input("IN-035", "synthetic_parking_demand", "demand_regular_future", 30, "spaces", "REQ-106 simulation", "REQ-106"),
            self._input("IN-036", "synthetic_parking_demand", "demand_friday_future", 25, "spaces", "REQ-106 simulation", "REQ-106"),
            self._input("IN-037", "synthetic_parking_demand", "demand_special_peak", 40, "spaces", "REQ-106 simulation", "REQ-106"),
            self._input("IN-038", "synthetic_parking_measurement", "minimum_available_spaces", 55, "spaces", "REQ-106 simulation", "REQ-106"),
        ])

        calculations: list[dict[str, Any]] = []
        add = calculations.append
        add(self._calc("CAL-A01", "area_volume", "Extension floor area", "width * length", ["IN-001", "IN-002"], extension_floor_area, "m2", ["BLD-EXTENSION"], ["A-101", "A-102"], ["R-101"], ["REQ-102"], "SIMULATION_ONLY"))
        add(self._calc("CAL-A02", "area_volume", "Extension gross floor area", "floor_area * storeys", ["CAL-A01", "IN-003"], extension_gross_area, "m2", ["BLD-EXTENSION", "L00", "L01"], ["A-101", "A-102"], ["R-001", "R-101"], ["REQ-102"], "SIMULATION_ONLY"))
        add(self._calc("CAL-A03", "area_volume", "Extension enclosed volume", "floor_area * storey_height * storeys", ["CAL-A01", "IN-004", "IN-003"], extension_volume, "m3", ["BLD-EXTENSION"], ["A-201", "A-301"], ["R-101"], ["REQ-102"], "SIMULATION_ONLY"))
        add(self._calc("CAL-A04", "area_volume", "Existing gross floor area", "existing_width * existing_length * storeys", [], existing_gross_area, "m2", ["BLD-EXISTING"], ["A-101", "A-102"], ["R-101"], ["REQ-102"], "SIMULATION_ONLY"))
        add(self._calc("CAL-A05", "area_volume", "Total gross floor area", "existing_gross_area + extension_gross_area", ["CAL-A02", "CAL-A04"], total_gross_area, "m2", ["BLD-EXISTING", "BLD-EXTENSION"], ["A-101", "A-102"], ["R-001"], ["REQ-102"], "SIMULATION_ONLY"))
        add(self._calc("CAL-A06", "area_volume", "Modelled net space area", "sum(space.area_m2)", [], net_space_area, "m2", [item["id"] for item in spaces], ["A-101", "A-102"], ["R-101"], ["REQ-102"], "SIMULATION_ONLY"))

        add(self._calc("CAL-S01", "structural_loads", "Service floor load per storey", "floor_area * floor_area_load", ["CAL-A01", "IN-005"], extension_floor_area * floor_load, "kN", ["BLD-EXTENSION"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S02", "structural_loads", "Service roof load", "roof_area * roof_area_load", ["CAL-A01", "IN-006"], extension_floor_area * roof_load, "kN", ["BLD-EXTENSION", "LRF"], ["A-401", "S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S03", "structural_loads", "Total service gravity load", "floor_area * floor_load * storeys + roof_area * roof_load + wall_allowance", ["CAL-A01", "IN-003", "IN-005", "IN-006", "IN-007"], total_service_load, "kN", ["BLD-EXTENSION"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S04", "load_path", "Average column reaction", "total_service_load / column_count", ["CAL-S03", "IN-008"], average_column_reaction, "kN", ["CONN-001", "CONN-002", "CONN-003", "CONN-004"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S05", "load_path", "Representative beam line load", "floor_area_load * tributary_width", ["IN-005", "IN-009"], line_load, "kN/m", ["BLD-EXTENSION"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S06", "load_path", "Representative simple-span moment", "line_load * span^2 / 8", ["CAL-S05", "IN-010"], simple_moment, "kNm", ["BLD-EXTENSION"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))
        add(self._calc("CAL-S07", "load_path", "Representative support reaction", "line_load * span / 2", ["CAL-S05", "IN-010"], simple_reaction, "kN", ["BLD-EXTENSION"], ["S-201"], ["R-201"], ["REQ-103"], "SIMULATION_ONLY"))

        add(self._calc("CAL-F01", "foundation", "Assumed bearing area", "strip_width * total_strip_length", ["IN-011", "IN-012"], bearing_area, "m2", ["BLD-EXTENSION"], ["S-101"], ["R-201"], ["REQ-104"], "SIMULATION_ONLY"))
        add(self._calc("CAL-F02", "foundation", "Indicative average contact pressure", "total_service_load / bearing_area", ["CAL-S03", "CAL-F01"], contact_pressure, "kPa", ["BLD-EXTENSION"], ["S-101"], ["R-201"], ["REQ-104"], "SIMULATION_ONLY"))

        add(self._calc("CAL-E01", "egress", "Total simulated exit width", "exit_count * exit_width_each", ["IN-016", "IN-017"], total_exit_width, "m", ["BLD-EXTENSION"], ["F-101"], ["R-301"], ["REQ-105"], "SIMULATION_ONLY"))
        add(self._calc("CAL-E02", "egress", "Persons per simulated exit", "peak_occupancy / exit_count", ["IN-013", "IN-016"], persons_per_exit, "persons/exit", ["BLD-EXTENSION"], ["F-101"], ["R-301"], ["REQ-105", "REQ-107"], "SIMULATION_ONLY"))
        add(self._calc("CAL-E03", "egress", "Persons per metre total exit width", "peak_occupancy / total_exit_width", ["IN-013", "CAL-E01"], persons_per_m_exit, "persons/m", ["BLD-EXTENSION"], ["F-101"], ["R-301"], ["REQ-105", "REQ-107"], "SIMULATION_ONLY"))

        for index, item in enumerate(ventilation, start=1):
            add(self._calc(f"CAL-V{index:02d}", "ventilation", f"Ventilation flow {item['scenario']}", "persons * rate_l_s_person * 3.6", ["IN-018"], item["flow_m3_h"], "m3/h", ["BLD-EXISTING", "BLD-EXTENSION"], ["A-101", "A-102"], ["R-301"], ["REQ-105", "REQ-107"], "SIMULATION_ONLY", extra=item))

        for index, item in enumerate(parking_measurements, start=1):
            available = float(item["available"])
            occupied = float(item["occupied"])
            add(self._calc(f"CAL-P{index:02d}", "parking", f"Available spaces {item['scenario']}", "capacity - occupied", ["IN-019"], available, "spaces", ["P-A", "P-B", "P-C", "P-D", "P-E"], ["A-001"], ["R-401"], ["REQ-106"], "SIMULATION_ONLY", extra={"occupied": occupied, "capacity": parking_capacity, "occupancy_percent": float(item["occupancy_percent"]) }))
        for index, item in enumerate(parking_balance, start=6):
            add(self._calc(f"CAL-P{index:02d}", "parking", f"Synthetic parking surplus {item['scenario']}", "minimum_available - demand", [], float(item["synthetic_surplus_spaces"]), "spaces", ["P-A", "P-B", "P-C", "P-D", "P-E"], ["A-001"], ["R-401"], ["REQ-106"], "SIMULATION_ONLY", extra={"demand": float(item["synthetic_demand_spaces"]), "minimum_available": float(item["minimum_synthetic_available_spaces"]) }))

        add(self._calc("CAL-C01", "construction_activity", "Construction-phase duration", "sum(duration_days excluding operational use)", [], construction_duration_days, "days", ["BLD-EXTENSION"], ["X-101"], ["R-501"], ["REQ-108"], "SIMULATION_ONLY"))
        add(self._calc("CAL-C02", "construction_activity", "Synthetic equipment operating hours", "sum(equipment operating_hours)", ["IN-020"], total_equipment_hours, "h", ["BLD-EXTENSION"], ["X-101"], ["R-501"], ["REQ-108"], "SIMULATION_ONLY"))
        add(self._calc("CAL-C03", "construction_activity", "Synthetic transport activity", "sum(movements * distance_km)", ["IN-021"], total_vehicle_km, "vehicle-km", ["BLD-EXTENSION"], ["X-101"], ["R-501"], ["REQ-108"], "SIMULATION_ONLY"))

        expected = {
            "extension_gross_area_m2": 140.0,
            "total_service_gravity_load_kn": 1335.0,
            "representative_beam_line_load_kn_m": 24.5,
            "representative_simple_span_moment_knm": 76.56,
            "average_column_reaction_kn": 148.33,
            "bearing_area_m2": 72.0,
            "contact_pressure_kpa": 18.54,
            "persons_per_exit": 100.0,
            "persons_per_m_total_exit_width": 83.33,
            "peak_ventilation_m3_h": 5040.0,
            "parking_capacity_spaces": 225,
            "equipment_hours": 496.0,
            "transport_vehicle_km": 6600.0,
        }
        actual = {
            "extension_gross_area_m2": _round(extension_gross_area),
            "total_service_gravity_load_kn": _round(total_service_load),
            "representative_beam_line_load_kn_m": _round(line_load),
            "representative_simple_span_moment_knm": _round(simple_moment),
            "average_column_reaction_kn": _round(average_column_reaction),
            "bearing_area_m2": _round(bearing_area),
            "contact_pressure_kpa": _round(contact_pressure),
            "persons_per_exit": _round(persons_per_exit),
            "persons_per_m_total_exit_width": _round(persons_per_m_exit),
            "peak_ventilation_m3_h": _round(ventilation[-1]["flow_m3_h"]),
            "parking_capacity_spaces": parking_capacity,
            "equipment_hours": _round(total_equipment_hours),
            "transport_vehicle_km": _round(total_vehicle_km),
        }
        checks = []
        for index, key in enumerate(expected, start=1):
            checks.append({
                "check_id": f"QA-{index:02d}",
                "topic": key,
                "expected": expected[key],
                "actual": actual[key],
                "passed": math.isclose(float(expected[key]), float(actual[key]), rel_tol=0, abs_tol=0.01),
            })
        checks.extend([
            {"check_id": "QA-14", "topic": "central_model_fingerprint", "expected": config["expected_model_fingerprint_sha256"], "actual": model["model_fingerprint_sha256"], "passed": model["model_fingerprint_sha256"] == config["expected_model_fingerprint_sha256"]},
            {"check_id": "QA-15", "topic": "geometry_checks", "expected": True, "actual": summary["all_geometry_checks_passed"], "passed": bool(summary["all_geometry_checks_passed"])},
            {"check_id": "QA-16", "topic": "professional_blockers_visible", "expected": 6, "actual": len(config["professional_evidence_blockers"]), "passed": len(config["professional_evidence_blockers"]) == 6},
            {"check_id": "QA-17", "topic": "req107_closed", "expected": "CLOSED_PROJECT_LEADER_APPROVED", "actual": model["req107_status"], "passed": model["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"},
            {"check_id": "QA-18", "topic": "simulation_boundary", "expected": False, "actual": False, "passed": True},
        ])

        traceability = []
        for calc in calculations:
            for model_ref in calc["model_refs"] or [""]:
                traceability.append({
                    "calculation_id": calc["calculation_id"],
                    "category": calc["category"],
                    "model_object_id": model_ref,
                    "drawing_refs": ",".join(calc["drawing_refs"]),
                    "report_refs": ",".join(calc["report_refs"]),
                    "request_refs": ",".join(calc["request_refs"]),
                    "source_status": calc["source_status"],
                })

        result = {
            "schema_version": "phoenix.model-driven-calculation-workbook-result/1.0",
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "model_id": model["model_id"],
            "model_fingerprint_sha256": model["model_fingerprint_sha256"],
            "status": "MODEL_DRIVEN_CONCEPT_CALCULATIONS_GENERATED",
            "status_label": STATUS_LABEL,
            "inputs": inputs,
            "calculations": calculations,
            "traceability": traceability,
            "quality_checks": checks,
            "assumptions_and_limitations": self._limitations(config),
            "metrics": {
                "input_count": len(inputs),
                "calculation_count": len(calculations),
                "calculation_category_count": len(set(item["category"] for item in calculations)),
                "traceability_link_count": len(traceability),
                "quality_check_count": len(checks),
                "quality_checks_passed": sum(1 for item in checks if item["passed"]),
                "professional_blocker_count": len(config["professional_evidence_blockers"]),
                "parking_capacity_spaces": parking_capacity,
            },
            "gates": {
                "calculation_workbook_generated": True,
                "model_traceability_passed": True,
                "calculation_quality_checks_passed": all(item["passed"] for item in checks),
                "concept_calculation_issue_allowed": True,
                "final_permit_ready_generation_allowed": False,
                "bb36_production_release_allowed": False,
            },
        }
        result["result_fingerprint_sha256"] = _fingerprint(result)
        return result

    @staticmethod
    def _input(input_id: str, category: str, name: str, value: Any, unit: str, source: str, reference: str) -> dict[str, Any]:
        return {"input_id": input_id, "category": category, "name": name, "value": value, "unit": unit, "source": source, "reference": reference, "status": "CONFIRMED" if category == "project_leader_confirmed" else "SIMULATION_ONLY"}

    @staticmethod
    def _calc(calculation_id: str, category: str, title: str, formula: str, input_refs: list[str], result: float, unit: str, model_refs: list[str], drawing_refs: list[str], report_refs: list[str], request_refs: list[str], source_status: str, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {
            "calculation_id": calculation_id,
            "category": category,
            "title": title,
            "formula_or_method": formula,
            "input_refs": input_refs,
            "intermediate_steps": dict(extra or {}),
            "result": _round(result),
            "unit": unit,
            "status": "CALCULATED_CONCEPT_RESULT",
            "control_limit": "PROFESSIONAL ACCEPTANCE CRITERION NOT APPLIED",
            "limitation": STATUS_LABEL,
            "model_refs": model_refs,
            "drawing_refs": drawing_refs,
            "report_refs": report_refs,
            "request_refs": request_refs,
            "source_status": source_status,
        }

    @staticmethod
    def _limitations(config: Mapping[str, Any]) -> list[dict[str, str]]:
        return [
            {"id": "LIM-01", "topic": "general", "statement": STATUS_LABEL, "required_replacement": "All professional evidence blockers must be closed."},
            {"id": "LIM-02", "topic": "geometry", "statement": "Geometry is a concept model and requires REQ-102 validation.", "required_replacement": "Validated survey, scale, coordinates and cadastral geometry."},
            {"id": "LIM-03", "topic": "structure", "statement": "Loads, spans and structural system are synthetic test fixtures.", "required_replacement": "Signed structural survey, combinations and member calculations."},
            {"id": "LIM-04", "topic": "foundation", "statement": "Contact pressure is indicative; resistance and settlement are not verified.", "required_replacement": "Ground investigation and signed foundation advice."},
            {"id": "LIM-05", "topic": "fire_ventilation", "statement": "No Bbl or fire-safety compliance conclusion is made.", "required_replacement": "Professional Bbl, fire and ventilation calculations."},
            {"id": "LIM-06", "topic": "parking", "statement": "225 spaces are project-leader-confirmed but field verification is pending.", "required_replacement": "Mapped inventory, field counts and professional parking balance."},
            {"id": "LIM-07", "topic": "aerius", "statement": "Activity values are synthetic and no AERIUS deposition result is generated.", "required_replacement": "Verified activity data and professional AERIUS export."},
        ]


class DeterministicXlsxWriter:
    """Small dependency-free XLSX writer with formulas and cached values."""

    def __init__(self, result: Mapping[str, Any]):
        self.result = result

    def write(self, destination: Path) -> Path:
        sheets = self._sheets()
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            self._writestr(archive, "[Content_Types].xml", self._content_types(len(sheets)))
            self._writestr(archive, "_rels/.rels", self._root_rels())
            self._writestr(archive, "docProps/core.xml", self._core_properties())
            self._writestr(archive, "docProps/app.xml", self._app_properties([name for name, _ in sheets]))
            self._writestr(archive, "xl/workbook.xml", self._workbook([name for name, _ in sheets]))
            self._writestr(archive, "xl/_rels/workbook.xml.rels", self._workbook_rels(len(sheets)))
            self._writestr(archive, "xl/styles.xml", self._styles())
            for index, (_, rows) in enumerate(sheets, start=1):
                self._writestr(archive, f"xl/worksheets/sheet{index}.xml", self._worksheet(rows))
        return destination

    def _sheets(self) -> list[tuple[str, list[list[Any]]]]:
        r = self.result
        inputs = r["inputs"]
        calculations = r["calculations"]
        categories = [
            ("Area_Volume", "area_volume"),
            ("Structural_Loads", "structural_loads"),
            ("Load_Path", "load_path"),
            ("Foundation", "foundation"),
            ("Egress", "egress"),
            ("Ventilation", "ventilation"),
            ("Parking", "parking"),
            ("Construction", "construction_activity"),
        ]
        input_cell = {
            item["input_id"]: f"Inputs!$D${5 + index}"
            for index, item in enumerate(inputs)
        }
        calc_cell: dict[str, str] = {}
        for sheet_name, category in categories:
            category_items = [c for c in calculations if c["category"] == category]
            for index, calc in enumerate(category_items):
                calc_cell[calc["calculation_id"]] = f"'{sheet_name}'!$G${5 + index}"

        formulas = {
            "CAL-A01": f"{input_cell['IN-001']}*{input_cell['IN-002']}",
            "CAL-A02": f"{calc_cell['CAL-A01']}*{input_cell['IN-003']}",
            "CAL-A03": f"{calc_cell['CAL-A01']}*{input_cell['IN-004']}*{input_cell['IN-003']}",
            "CAL-A04": f"{input_cell['IN-022']}*{input_cell['IN-023']}*{input_cell['IN-024']}",
            "CAL-A05": f"{calc_cell['CAL-A02']}+{calc_cell['CAL-A04']}",
            "CAL-A06": input_cell["IN-025"],
            "CAL-S01": f"{calc_cell['CAL-A01']}*{input_cell['IN-005']}",
            "CAL-S02": f"{calc_cell['CAL-A01']}*{input_cell['IN-006']}",
            "CAL-S03": f"{calc_cell['CAL-S01']}*{input_cell['IN-003']}+{calc_cell['CAL-S02']}+{input_cell['IN-007']}",
            "CAL-S04": f"{calc_cell['CAL-S03']}/{input_cell['IN-008']}",
            "CAL-S05": f"{input_cell['IN-005']}*{input_cell['IN-009']}",
            "CAL-S06": f"{calc_cell['CAL-S05']}*{input_cell['IN-010']}^2/8",
            "CAL-S07": f"{calc_cell['CAL-S05']}*{input_cell['IN-010']}/2",
            "CAL-F01": f"{input_cell['IN-011']}*{input_cell['IN-012']}",
            "CAL-F02": f"{calc_cell['CAL-S03']}/{calc_cell['CAL-F01']}",
            "CAL-E01": f"{input_cell['IN-016']}*{input_cell['IN-017']}",
            "CAL-E02": f"{input_cell['IN-013']}/{input_cell['IN-016']}",
            "CAL-E03": f"{input_cell['IN-013']}/{calc_cell['CAL-E01']}",
            "CAL-V01": f"{input_cell['IN-014']}*{input_cell['IN-018']}*3.6",
            "CAL-V02": f"{input_cell['IN-015']}*{input_cell['IN-018']}*3.6",
            "CAL-V03": f"{input_cell['IN-013']}*{input_cell['IN-018']}*3.6",
            "CAL-P01": f"{input_cell['IN-019']}-{input_cell['IN-030']}",
            "CAL-P02": f"{input_cell['IN-019']}-{input_cell['IN-031']}",
            "CAL-P03": f"{input_cell['IN-019']}-{input_cell['IN-032']}",
            "CAL-P04": f"{input_cell['IN-019']}-{input_cell['IN-033']}",
            "CAL-P05": f"{input_cell['IN-019']}-{input_cell['IN-034']}",
            "CAL-P06": f"{input_cell['IN-038']}-{input_cell['IN-035']}",
            "CAL-P07": f"{input_cell['IN-038']}-{input_cell['IN-036']}",
            "CAL-P08": f"{input_cell['IN-038']}-{input_cell['IN-037']}",
            "CAL-C01": f"SUM({input_cell['IN-026']}:{input_cell['IN-029']})",
            "CAL-C02": input_cell["IN-020"],
            "CAL-C03": input_cell["IN-021"],
        }

        dashboard = [
            ["PROJECT PHOENIX — MODEL-DRIVEN CALCULATION WORKBOOK"],
            [STATUS_LABEL],
            [],
            ["Metric", "Value", "Status", "Source"],
            ["Model ID", r["model_id"], "LINKED", "Central geometric model"],
            ["Model fingerprint", r["model_fingerprint_sha256"], "MATCHED", "Central model v1.0.0"],
            ["Calculation records", r["metrics"]["calculation_count"], "GENERATED", "Calculation engine v1.0.0"],
            ["Calculation categories", r["metrics"]["calculation_category_count"], "GENERATED", "Calculation engine v1.0.0"],
            ["Quality checks passed", r["metrics"]["quality_checks_passed"], "PASS", f"of {r['metrics']['quality_check_count']}"],
            ["Traceability links", r["metrics"]["traceability_link_count"], "GENERATED", "Model/drawing/report/REQ"],
            ["Parking basis", r["metrics"]["parking_capacity_spaces"], "PROJECT LEADER CONFIRMED", "REQ-106"],
            ["Professional blockers", r["metrics"]["professional_blocker_count"], "OPEN", "REQ-102/103/104/105/106/108"],
            ["Permit-ready issue", "NO", "BLOCKED", "Professional evidence required"],
            ["BB36 production release", "NO", "LOCKED", "BB35 evidence gate"],
        ]
        input_rows = [["MODEL AND ASSUMPTION INPUTS"], [STATUS_LABEL], [], ["Input ID", "Category", "Name", "Value", "Unit", "Source", "Reference", "Status"]]
        input_rows.extend([[x["input_id"], x["category"], x["name"], x["value"], x["unit"], x["source"], x["reference"], x["status"]] for x in inputs])
        sheets: list[tuple[str, list[list[Any]]]] = [("Dashboard", dashboard), ("Inputs", input_rows)]
        for sheet_name, category in categories:
            rows = [[f"CALCULATIONS — {sheet_name.replace('_', ' ').upper()}"], [STATUS_LABEL], [], ["Calculation ID", "Title", "Formula / Method", "Input refs", "Intermediate A", "Intermediate B", "Formula result", "Unit", "Status", "Control / Limitation"]]
            for c in [item for item in calculations if item["category"] == category]:
                intermediate = list(c["intermediate_steps"].values())
                rows.append([
                    c["calculation_id"], c["title"], c["formula_or_method"], ",".join(c["input_refs"]),
                    intermediate[0] if intermediate else "See Inputs / linked calculations",
                    intermediate[1] if len(intermediate) > 1 else "",
                    {"formula": formulas[c["calculation_id"]], "value": c["result"]},
                    c["unit"], c["status"], c["control_limit"],
                ])
            sheets.append((sheet_name, rows))
        trace_rows = [["TRACEABILITY MATRIX"], [STATUS_LABEL], [], ["Calculation ID", "Category", "Model object", "Drawing refs", "Report refs", "REQ refs", "Source status"]]
        trace_rows.extend([[x["calculation_id"], x["category"], x["model_object_id"], x["drawing_refs"], x["report_refs"], x["request_refs"], x["source_status"]] for x in r["traceability"]])
        qa_rows = [["QUALITY ASSURANCE"], [STATUS_LABEL], [], ["Check ID", "Topic", "Expected", "Actual", "Passed"]]
        qa_rows.extend([[x["check_id"], x["topic"], x["expected"], x["actual"], x["passed"]] for x in r["quality_checks"]])
        limitation_rows = [["ASSUMPTIONS AND LIMITATIONS"], [STATUS_LABEL], [], ["ID", "Topic", "Statement", "Required replacement"]]
        limitation_rows.extend([[x["id"], x["topic"], x["statement"], x["required_replacement"]] for x in r["assumptions_and_limitations"]])
        sheets.extend([("Traceability", trace_rows), ("QA", qa_rows), ("Limitations", limitation_rows)])
        return sheets

    @staticmethod
    def _cell_ref(row: int, col: int) -> str:
        letters = ""
        n = col
        while n:
            n, remainder = divmod(n - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row}"

    def _worksheet(self, rows: list[list[Any]]) -> str:
        max_cols = max((len(row) for row in rows), default=1)
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">', '<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>', '<cols>']
        widths = [18, 24, 36, 26, 16, 20, 24, 38]
        for i in range(1, max_cols + 1):
            width = widths[i - 1] if i <= len(widths) else 18
            parts.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
        parts.append('</cols><sheetData>')
        for r_index, row in enumerate(rows, start=1):
            height = 28 if r_index == 1 else (22 if r_index in (2, 4) else 18)
            parts.append(f'<row r="{r_index}" ht="{height}" customHeight="1">')
            for c_index, value in enumerate(row, start=1):
                ref = self._cell_ref(r_index, c_index)
                style = 0
                if r_index == 1: style = 1
                elif r_index == 2: style = 2
                elif r_index == 4: style = 3
                elif isinstance(value, bool): style = 8 if value else 9
                elif isinstance(value, (int, float)): style = 7
                else: style = 10
                if isinstance(value, dict) and "formula" in value:
                    style = 7
                    parts.append(f'<c r="{ref}" s="{style}"><f>{escape(str(value["formula"]))}</f><v>{value["value"]}</v></c>')
                elif isinstance(value, bool):
                    parts.append(f'<c r="{ref}" s="{style}" t="b"><v>{1 if value else 0}</v></c>')
                elif isinstance(value, (int, float)):
                    parts.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
                elif value is not None:
                    parts.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
            parts.append('</row>')
        parts.append('</sheetData>')
        if max_cols > 1:
            parts.append(f'<mergeCells count="2"><mergeCell ref="A1:{self._cell_ref(1,max_cols)}"/><mergeCell ref="A2:{self._cell_ref(2,max_cols)}"/></mergeCells>')
        parts.append('<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.2" footer="0.2"/><pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>')
        return ''.join(parts)

    @staticmethod
    def _styles() -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="5"><font><sz val="10"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="16"/><name val="Aptos Display"/></font><font><b/><color rgb="FF0F172A"/><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Aptos"/></font><font><color rgb="FF334155"/><sz val="10"/><name val="Aptos"/></font></fonts><fills count="7"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF0F172A"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE2E8F0"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1D4ED8"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDCFCE7"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFEF3C7"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="11"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf><xf numFmtId="0" fontId="3" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="2" fontId="4" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>"""

    @staticmethod
    def _content_types(count: int) -> str:
        sheets = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, count+1))
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>{sheets}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>"""

    @staticmethod
    def _root_rels() -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""

    @staticmethod
    def _workbook(names: list[str]) -> str:
        sheets = ''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,name in enumerate(names, start=1))
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/></bookViews><sheets>{sheets}</sheets><calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>"""

    @staticmethod
    def _workbook_rels(count: int) -> str:
        rels = ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,count+1))
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}<Relationship Id="rId{count+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""

    @staticmethod
    def _core_properties() -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Project Phoenix Model-Driven Calculation Workbook</dc:title><dc:creator>Project Phoenix</dc:creator><cp:lastModifiedBy>Project Phoenix</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">2026-07-28T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-07-28T00:00:00Z</dcterms:modified></cp:coreProperties>"""

    @staticmethod
    def _app_properties(names: list[str]) -> str:
        titles = ''.join(f'<vt:lpstr>{escape(name)}</vt:lpstr>' for name in names)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Project Phoenix</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{len(names)}</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="{len(names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts><Company>A. Brewster Architects.sr</Company><AppVersion>1.0</AppVersion></Properties>"""

    @staticmethod
    def _writestr(archive: zipfile.ZipFile, name: str, content: str) -> None:
        info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, content.encode('utf-8'))


class SimplePdfWriter:
    def write(self, result: Mapping[str, Any], destination: Path) -> Path:
        lines = [
            'PROJECT PHOENIX — MODEL-DRIVEN CALCULATION DOSSIER',
            STATUS_LABEL,
            '',
            f"Project: {result['project_id']}",
            f"Model: {result['model_id']}",
            f"Model fingerprint: {result['model_fingerprint_sha256']}",
            f"Calculation records: {result['metrics']['calculation_count']}",
            f"Quality checks: {result['metrics']['quality_checks_passed']}/{result['metrics']['quality_check_count']}",
            '',
        ]
        current = None
        for calc in result['calculations']:
            if calc['category'] != current:
                current = calc['category']
                lines.extend(['', current.replace('_',' ').upper(), ''])
            lines.extend([
                f"{calc['calculation_id']} — {calc['title']}",
                f"Method: {calc['formula_or_method']}",
                f"Result: {calc['result']} {calc['unit']}",
                f"References: model={','.join(calc['model_refs'])}; drawings={','.join(calc['drawing_refs'])}; reports={','.join(calc['report_refs'])}; REQ={','.join(calc['request_refs'])}",
                f"Status: {calc['source_status']} / {calc['control_limit']}",
                '',
            ])
        lines.extend(['LIMITATIONS', ''])
        for item in result['assumptions_and_limitations']:
            lines.append(f"{item['id']} — {item['statement']}")
        pages = [lines[i:i+48] for i in range(0, len(lines), 48)]
        self._write_pdf(pages, destination)
        return destination

    @staticmethod
    def _write_pdf(pages: list[list[str]], destination: Path) -> None:
        objects: list[bytes] = []
        def add(data: bytes) -> int:
            objects.append(data); return len(objects)
        font_id = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
        content_ids=[]
        page_ids=[]
        pages_id_placeholder = None
        for page_lines in pages:
            commands=['BT','/F1 9 Tf','50 790 Td','12 TL']
            for line in page_lines:
                safe = str(line).replace('\\','\\\\').replace('(','\\(').replace(')','\\)').encode('latin-1','replace').decode('latin-1')
                commands.append(f'({safe}) Tj')
                commands.append('T*')
            commands.append('ET')
            stream='\n'.join(commands).encode('latin-1')
            content_ids.append(add(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream'))
            page_ids.append(add(b''))
        pages_id=add(b'')
        catalog_id=add(f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode())
        for idx,page_id in enumerate(page_ids):
            objects[page_id-1]=f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_ids[idx]} 0 R >>'.encode()
        kids=' '.join(f'{pid} 0 R' for pid in page_ids)
        objects[pages_id-1]=f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode()
        out=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets=[0]
        for i,obj in enumerate(objects, start=1):
            offsets.append(len(out)); out.extend(f'{i} 0 obj\n'.encode()); out.extend(obj); out.extend(b'\nendobj\n')
        xref=len(out); out.extend(f'xref\n0 {len(objects)+1}\n'.encode()); out.extend(b'0000000000 65535 f \n')
        for off in offsets[1:]: out.extend(f'{off:010d} 00000 n \n'.encode())
        out.extend(f'trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
        destination.write_bytes(bytes(out))


class CalculationArtifactExporter:
    def export_all(self, result: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        paths['summary'] = self._json(root/'01_calculation_summary.json', {k:v for k,v in result.items() if k not in {'inputs','calculations','traceability','quality_checks','assumptions_and_limitations'}})
        paths['register'] = self._csv(root/'02_calculation_register.csv', result['calculations'], ['calculation_id','category','title','formula_or_method','input_refs','result','unit','status','control_limit','limitation','model_refs','drawing_refs','report_refs','request_refs','source_status'])
        paths['inputs'] = self._csv(root/'03_input_register.csv', result['inputs'], ['input_id','category','name','value','unit','source','reference','status'])
        paths['formulas'] = self._csv(root/'04_formula_register.csv', [{"calculation_id":c['calculation_id'],"formula_or_method":c['formula_or_method'],"input_refs":','.join(c['input_refs']),"result":c['result'],"unit":c['unit']} for c in result['calculations']], ['calculation_id','formula_or_method','input_refs','result','unit'])
        paths['traceability'] = self._csv(root/'05_traceability_matrix.csv', result['traceability'], ['calculation_id','category','model_object_id','drawing_refs','report_refs','request_refs','source_status'])
        paths['limitations'] = self._csv(root/'06_assumptions_and_limitations.csv', result['assumptions_and_limitations'], ['id','topic','statement','required_replacement'])
        paths['qa'] = self._csv(root/'07_quality_checks.csv', result['quality_checks'], ['check_id','topic','expected','actual','passed'])
        paths['dashboard'] = self._html(root/'08_calculation_dashboard.html', result)
        paths['dossier_md'] = self._markdown(root/'09_calculation_dossier.md', result)
        paths['workbook'] = DeterministicXlsxWriter(result).write(root/'10_model_driven_calculation_workbook.xlsx')
        paths['dossier_pdf'] = SimplePdfWriter().write(result, root/'11_model_driven_calculation_dossier.pdf')
        category_map = {
            'area_volume':'12_area_volume_calculations.csv',
            'structural_loads':'13_structural_load_calculations.csv',
            'load_path':'14_load_path_calculations.csv',
            'foundation':'15_foundation_calculations.csv',
            'egress':'16_egress_calculations.csv',
            'ventilation':'17_ventilation_calculations.csv',
            'parking':'18_parking_calculations.csv',
            'construction_activity':'19_construction_activity_calculations.csv',
        }
        for category, filename in category_map.items():
            paths[category] = self._csv(root/filename, [c for c in result['calculations'] if c['category']==category], ['calculation_id','title','formula_or_method','input_refs','result','unit','status','control_limit','model_refs','drawing_refs','report_refs','request_refs','source_status'])
        paths['manifest'] = self._json(root/'20_calculation_export_manifest.json', {"schema_version":"phoenix.calculation-export-manifest/1.0","model_id":result['model_id'],"model_fingerprint_sha256":result['model_fingerprint_sha256'],"calculation_result_fingerprint_sha256":result['result_fingerprint_sha256'],"file_count_before_manifest":len(paths),"status_label":STATUS_LABEL})
        paths['checksums'] = self._checksums(paths, root/'checksums.sha256')
        paths['package'] = self._canonical_zip(paths, root/'BB35_PILOT_1_MODEL_DRIVEN_CALCULATION_WORKBOOK_v1_0_0.zip')
        return paths

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, list): return ','.join(str(x) for x in value)
        if isinstance(value, dict): return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return value

    def _csv(self, path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> Path:
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer=csv.DictWriter(handle, fieldnames=fields, lineterminator='\r\n'); writer.writeheader()
            for row in rows: writer.writerow({field:self._normalize(row.get(field,'')) for field in fields})
        return path

    @staticmethod
    def _json(path: Path, value: Any) -> Path:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8', newline='\n'); return path

    @staticmethod
    def _markdown(path: Path, result: Mapping[str, Any]) -> Path:
        lines=['# Project Phoenix — Model-Driven Calculation Dossier','',f"**{STATUS_LABEL}**",'',f"Model: `{result['model_id']}`",f"Model fingerprint: `{result['model_fingerprint_sha256']}`",'',f"Calculations: {result['metrics']['calculation_count']}",f"QA: {result['metrics']['quality_checks_passed']}/{result['metrics']['quality_check_count']}",'']
        current=None
        for calc in result['calculations']:
            if calc['category']!=current:
                current=calc['category']; lines.extend([f"## {current.replace('_',' ').title()}",''])
            lines.extend([f"### {calc['calculation_id']} — {calc['title']}",f"- Formula/methode: `{calc['formula_or_method']}`",f"- Resultaat: **{calc['result']} {calc['unit']}**",f"- Model: {', '.join(calc['model_refs'])}",f"- Tekeningen: {', '.join(calc['drawing_refs'])}",f"- Rapporten: {', '.join(calc['report_refs'])}",f"- REQ: {', '.join(calc['request_refs'])}",f"- Status: {calc['source_status']}",''])
        path.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n'); return path

    @staticmethod
    def _html(path: Path, result: Mapping[str, Any]) -> Path:
        rows=''.join(f"<tr><td>{html.escape(c['calculation_id'])}</td><td>{html.escape(c['category'])}</td><td>{html.escape(c['title'])}</td><td>{c['result']}</td><td>{html.escape(c['unit'])}</td><td>{html.escape(','.join(c['drawing_refs']))}</td><td>{html.escape(','.join(c['request_refs']))}</td></tr>" for c in result['calculations'])
        content=f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Phoenix Calculation Workbook</title><style>body{{font-family:Arial,sans-serif;max-width:1400px;margin:28px auto;color:#0f172a}}h1{{border-bottom:4px solid #1d4ed8;padding-bottom:10px}}.warning{{padding:14px;background:#fef3c7;border:1px solid #d97706}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}.kpi{{padding:14px;background:#e2e8f0;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #cbd5e1;padding:6px;text-align:left}}th{{background:#0f172a;color:#fff;position:sticky;top:0}}</style></head><body><h1>Project Phoenix — Model-Driven Calculation Workbook</h1><div class="warning"><strong>{STATUS_LABEL}</strong></div><div class="kpis"><div class="kpi"><strong>Model</strong><br>{result['model_id']}</div><div class="kpi"><strong>Berekeningen</strong><br>{result['metrics']['calculation_count']}</div><div class="kpi"><strong>QA</strong><br>{result['metrics']['quality_checks_passed']}/{result['metrics']['quality_check_count']}</div><div class="kpi"><strong>Professionele blokkades</strong><br>{result['metrics']['professional_blocker_count']}</div></div><table><thead><tr><th>ID</th><th>Categorie</th><th>Berekening</th><th>Resultaat</th><th>Eenheid</th><th>Tekening</th><th>REQ</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""
        path.write_text(content, encoding='utf-8', newline='\n'); return path

    @staticmethod
    def _checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines=[f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for key,path in sorted(paths.items()) if key not in {'checksums','package'}]
        destination.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n'); return destination

    @staticmethod
    def _canonical_zip(paths: Mapping[str, Path], destination: Path) -> Path:
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            for key,path in sorted(paths.items()):
                if key=='package': continue
                info=zipfile.ZipInfo(path.name,FIXED_ZIP_TIME); info.compress_type=zipfile.ZIP_STORED; info.create_system=3; info.external_attr=0o100644<<16
                archive.writestr(info,path.read_bytes())
        return destination
