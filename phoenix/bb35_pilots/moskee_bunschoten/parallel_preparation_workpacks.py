"""Generate BB35 parallel preparation workpacks for REQ-105/106/108."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class ParallelPreparationWorkpacksEngine:
    VERSION = "1.8.0"

    def evaluate(
        self,
        *,
        downstream_summary: Mapping[str, Any],
        downstream_basis: Mapping[str, Any],
        occupancy_program: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessors(
            downstream_summary=downstream_summary,
            downstream_basis=downstream_basis,
            occupancy_program=occupancy_program,
            config=config,
        )

        occupancy = occupancy_program["occupancy_scenarios"]
        opening_hours = occupancy_program["opening_hours"]
        strategic = config["strategic_basis"]

        req105 = {
            "request_id": "REQ-105",
            "title": "Bbl, brandveiligheid en installaties",
            "workpack_status": (
                "PREPARATION_WORKPACK_COMPLETE_"
                "PROFESSIONAL_ASSESSMENT_PENDING"
            ),
            "strategic_basis": {
                "kitchen_function": strategic["kitchen_function"],
                "installation_sustainability_level": strategic[
                    "installation_sustainability_level"
                ],
            },
            "authoritative_inputs": {
                "occupancy_program_id": occupancy_program["program_id"],
                "regular_future_persons": occupancy["regular"][
                    "future_persons"
                ],
                "friday_future_persons": occupancy["friday_prayer"][
                    "future_persons"
                ],
                "special_peak_persons": occupancy["special_peak"][
                    "maximum_persons"
                ],
                "opening_hours": opening_hours,
            },
            "requirements_matrix": self._req105_requirements(),
            "professional_deliverables": [
                "Ondertekende Bbl-uitgangspuntennotitie.",
                "Brandveiligheids- en vluchtroutebeoordeling.",
                "Ventilatieberekening en installatieconcept.",
                "Toegankelijkheids- en sanitaire verificatie.",
            ],
            "finalization_allowed": False,
        }

        req106 = {
            "request_id": "REQ-106",
            "title": "Parkeerdrukmeting en parkeerbalans",
            "workpack_status": (
                "FIELD_PREPARATION_WORKPACK_COMPLETE_"
                "MEASUREMENTS_PENDING"
            ),
            "strategic_basis": {
                "parking_strategy": strategic["parking_strategy"],
            },
            "authoritative_inputs": {
                "occupancy_program_id": occupancy_program["program_id"],
                "regular_future_persons": occupancy["regular"][
                    "future_persons"
                ],
                "friday_future_persons": occupancy["friday_prayer"][
                    "future_persons"
                ],
                "special_peak_persons": occupancy["special_peak"][
                    "maximum_persons"
                ],
                "opening_hours": opening_hours,
            },
            "parking_hypothesis": config["parking_hypothesis"],
            "measurement_windows": config["measurement_windows"],
            "field_protocol": self._req106_protocol(),
            "professional_deliverables": [
                "Gevalideerde parkeerinventaris per deelgebied.",
                "Ruwe tellingen en bewijsfoto's voor vijf meetmomenten.",
                "Bevestiging dat getelde plaatsen openbaar beschikbaar zijn.",
                "Ondertekende parkeerbalans en advies parkeerregime.",
            ],
            "finalization_allowed": False,
        }

        req108 = {
            "request_id": "REQ-108",
            "title": "AERIUS aanleg- en gebruiksfase",
            "workpack_status": (
                "ACTIVITY_DATA_WORKPACK_COMPLETE_"
                "SOURCE_DATA_PENDING"
            ),
            "strategic_basis": {
                "execution_phasing": strategic["execution_phasing"],
                "mosque_remains_in_use_during_construction": strategic[
                    "mosque_remains_in_use_during_construction"
                ],
            },
            "authoritative_inputs": {
                "occupancy_program_id": occupancy_program["program_id"],
                "regular_future_persons": occupancy["regular"][
                    "future_persons"
                ],
                "friday_future_persons": occupancy["friday_prayer"][
                    "future_persons"
                ],
                "special_peak_persons": occupancy["special_peak"][
                    "maximum_persons"
                ],
                "opening_hours": opening_hours,
            },
            "phase_templates": self._req108_phases(),
            "professional_deliverables": [
                "Definitieve bouwfasering en bouwduur.",
                "Materieel, draaiuren, vermogen en brandstof per fase.",
                "Aan- en afvoerbewegingen per fase.",
                "AERIUS-berekening plus bron- en exportbestanden.",
            ],
            "finalization_allowed": False,
        }

        workpacks = {
            "REQ-105": req105,
            "REQ-106": req106,
            "REQ-108": req108,
        }

        report = {
            "schema_version": (
                "phoenix.bb35.parallel-preparation-workpacks/1.0"
            ),
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "status": (
                "PARALLEL_PREPARATION_WORKPACKS_GENERATED_"
                "EXTERNAL_EVIDENCE_PENDING"
            ),
            "workpack_count": len(workpacks),
            "workpacks": workpacks,
            "parallel_execution_allowed": True,
            "all_strategic_decisions_approved": True,
            "professional_evidence_still_required": True,
            "req107_formal_cosign_still_pending": True,
            "parking_provisional_capacity_spaces": config[
                "parking_hypothesis"
            ]["total_spaces"],
            "parking_hypothesis_status": config[
                "parking_hypothesis"
            ]["status"],
            "parking_measurement_count": len(
                config["measurement_windows"]
            ),
            "aerius_phase_template_count": len(
                req108["phase_templates"]
            ),
            "final_generation_allowed": False,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "policy": config["policy"],
            "next_gate": (
                "Issue the three workpacks, collect REQ-105 professional "
                "assessments, complete REQ-106 field measurements, and "
                "obtain REQ-108 activity data."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessors(
        *,
        downstream_summary: Mapping[str, Any],
        downstream_basis: Mapping[str, Any],
        occupancy_program: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> None:
        checks = {
            "downstream_ready": (
                downstream_summary.get("status")
                == (
                    "ALL_STRATEGIC_DECISIONS_OWNER_APPROVED_"
                    "DOWNSTREAM_PREPARATION_READY"
                )
            ),
            "eight_approved": (
                int(
                    downstream_summary.get(
                        "approved_strategic_decision_count",
                        0,
                    )
                )
                == 8
            ),
            "none_pending": (
                int(
                    downstream_summary.get(
                        "pending_strategic_decision_count",
                        -1,
                    )
                )
                == 0
            ),
            "basis_program": (
                downstream_basis.get("occupancy_program_id")
                == "HBM-OCC-2026-001"
            ),
            "occupancy_program": (
                occupancy_program.get("program_id")
                == "HBM-OCC-2026-001"
            ),
            "regular_150": (
                occupancy_program["occupancy_scenarios"]["regular"][
                    "future_persons"
                ]
                == 150
            ),
            "friday_125": (
                occupancy_program["occupancy_scenarios"][
                    "friday_prayer"
                ]["future_persons"]
                == 125
            ),
            "special_200": (
                occupancy_program["occupancy_scenarios"]["special_peak"][
                    "maximum_persons"
                ]
                == 200
            ),
            "parking_300_hypothesis": (
                config["parking_hypothesis"]["total_spaces"] == 300
            ),
        }
        failed = [key for key, passed in checks.items() if not passed]
        if failed:
            raise ValueError(
                "Parallel workpack predecessor validation failed: "
                + ", ".join(failed)
            )

        subareas = config["parking_hypothesis"]["subareas"]
        if sum(item["provisional_spaces"] for item in subareas) != 300:
            raise ValueError("Provisional parking subareas do not total 300.")
        if len(config["measurement_windows"]) != 5:
            raise ValueError("Exactly five parking measurements are required.")

    @staticmethod
    def _req105_requirements() -> list[dict[str, Any]]:
        return [
            {
                "requirement_id": "105-R-01",
                "discipline": "use_and_occupancy",
                "topic": "authoritative occupancy",
                "input_status": "AVAILABLE",
                "professional_action": (
                    "Confirm applicability and use as common calculation basis."
                ),
            },
            {
                "requirement_id": "105-R-02",
                "discipline": "fire_safety",
                "topic": "escape routes and capacities",
                "input_status": "CALCULATION_REQUIRED",
                "professional_action": (
                    "Calculate route widths, travel distances and exits."
                ),
            },
            {
                "requirement_id": "105-R-03",
                "discipline": "fire_safety",
                "topic": "compartmentation and fire resistance",
                "input_status": "ASSESSMENT_REQUIRED",
                "professional_action": (
                    "Define required compartments and performance."
                ),
            },
            {
                "requirement_id": "105-R-04",
                "discipline": "ventilation",
                "topic": "ventilation capacity",
                "input_status": "CALCULATION_REQUIRED",
                "professional_action": (
                    "Calculate statutory minimum ventilation by room and use."
                ),
            },
            {
                "requirement_id": "105-R-05",
                "discipline": "installations",
                "topic": "no kitchen function",
                "input_status": "OWNER_APPROVED",
                "professional_action": (
                    "Exclude kitchen-specific extraction and gas systems."
                ),
            },
            {
                "requirement_id": "105-R-06",
                "discipline": "accessibility",
                "topic": "routes and sanitary provisions",
                "input_status": "ASSESSMENT_REQUIRED",
                "professional_action": (
                    "Verify accessibility and sanitary requirements."
                ),
            },
            {
                "requirement_id": "105-R-07",
                "discipline": "energy",
                "topic": "statutory minimum",
                "input_status": "OWNER_APPROVED",
                "professional_action": (
                    "Apply statutory minimum without enhanced claims."
                ),
            },
            {
                "requirement_id": "105-R-08",
                "discipline": "coordination",
                "topic": "drawing coordination",
                "input_status": "CURRENT_DRAWINGS_REQUIRED",
                "professional_action": (
                    "Coordinate calculations with validated current drawings."
                ),
            },
        ]

    @staticmethod
    def _req106_protocol() -> list[dict[str, Any]]:
        return [
            {
                "protocol_id": "106-P-01",
                "step": "inventory",
                "instruction": (
                    "Confirm each parking space physically and assign a "
                    "subarea and availability classification."
                ),
            },
            {
                "protocol_id": "106-P-02",
                "step": "baseline",
                "instruction": (
                    "Record occupied, free, inaccessible and disputed spaces."
                ),
            },
            {
                "protocol_id": "106-P-03",
                "step": "mosque_use",
                "instruction": (
                    "Record mosque attendance or a traceable proxy for each "
                    "measurement."
                ),
            },
            {
                "protocol_id": "106-P-04",
                "step": "other_users",
                "instruction": (
                    "Record significant simultaneous use by surrounding "
                    "facilities."
                ),
            },
            {
                "protocol_id": "106-P-05",
                "step": "evidence",
                "instruction": (
                    "Attach time-stamped photographs and a signed count sheet."
                ),
            },
            {
                "protocol_id": "106-P-06",
                "step": "legal_availability",
                "instruction": (
                    "Verify whether every counted space is public, private or "
                    "subject to restrictions."
                ),
            },
            {
                "protocol_id": "106-P-07",
                "step": "analysis",
                "instruction": (
                    "Calculate occupancy by subarea and total without treating "
                    "the provisional 300-space hypothesis as proven."
                ),
            },
        ]

    @staticmethod
    def _req108_phases() -> list[dict[str, Any]]:
        return [
            {
                "phase_id": "AER-PH-01",
                "phase_name": "site_preparation_and_temporary_measures",
                "mosque_operational": True,
                "activity_data_status": "PENDING",
            },
            {
                "phase_id": "AER-PH-02",
                "phase_name": "substructure_and_foundation",
                "mosque_operational": True,
                "activity_data_status": "PENDING",
            },
            {
                "phase_id": "AER-PH-03",
                "phase_name": "superstructure_and_enclosure",
                "mosque_operational": True,
                "activity_data_status": "PENDING",
            },
            {
                "phase_id": "AER-PH-04",
                "phase_name": "installations_and_finishes",
                "mosque_operational": True,
                "activity_data_status": "PENDING",
            },
            {
                "phase_id": "AER-PH-05",
                "phase_name": "operational_use",
                "mosque_operational": True,
                "activity_data_status": "PENDING",
            },
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


class ParallelPreparationWorkpacksExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}

        paths["summary"] = self._json(
            root / "01_parallel_preparation_summary.json",
            {
                key: value
                for key, value in report.items()
                if key != "workpacks"
            },
        )
        paths["orchestration"] = self._json(
            root / "02_parallel_orchestration_plan.json",
            {
                "parallel_execution_allowed": (
                    report["parallel_execution_allowed"]
                ),
                "workstream_order": ["REQ-105", "REQ-106", "REQ-108"],
                "shared_authoritative_input": "HBM-OCC-2026-001",
                "independent_completion_gates": True,
                "final_generation_allowed": False,
                "bb36_unlock_allowed": False,
            },
        )

        paths.update(self._export_req105(report["workpacks"]["REQ-105"], root))
        paths.update(self._export_req106(report["workpacks"]["REQ-106"], root))
        paths.update(self._export_req108(report["workpacks"]["REQ-108"], root))

        paths["dashboard"] = self._html(
            root / "03_parallel_workpacks_dashboard.html",
            report,
        )
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            paths,
            root
            / "BB35_PILOT_1_PARALLEL_PREPARATION_WORKPACKS_"
            "v1_8_0.zip",
        )
        return paths

    def _export_req105(
        self,
        workpack: Mapping[str, Any],
        root: Path,
    ) -> dict[str, Path]:
        target = root / "REQ-105"
        target.mkdir(parents=True, exist_ok=True)
        result: dict[str, Path] = {}

        result["105_brief"] = self._markdown(
            target / "01_REQ_105_preparation_brief.md",
            self._brief(workpack),
        )
        result["105_matrix"] = self._csv(
            target / "02_REQ_105_requirements_matrix.csv",
            workpack["requirements_matrix"],
            [
                "requirement_id",
                "discipline",
                "topic",
                "input_status",
                "professional_action",
            ],
        )
        result["105_occupancy"] = self._json(
            target / "03_REQ_105_authoritative_occupancy_handoff.json",
            workpack["authoritative_inputs"],
        )
        result["105_request"] = self._json(
            target / "04_REQ_105_professional_evidence_request.json",
            {
                "request_id": "REQ-105",
                "deliverables": workpack["professional_deliverables"],
                "signature_required": True,
                "submission_status": "NOT_RECEIVED",
            },
        )
        result["105_signoff"] = self._markdown(
            target / "05_REQ_105_signoff_template.md",
            self._signoff("REQ-105", workpack["title"]),
        )
        result["105_manifest"] = self._json(
            target / "06_REQ_105_submission_manifest_template.json",
            self._manifest("REQ-105"),
        )
        return result

    def _export_req106(
        self,
        workpack: Mapping[str, Any],
        root: Path,
    ) -> dict[str, Path]:
        target = root / "REQ-106"
        target.mkdir(parents=True, exist_ok=True)
        result: dict[str, Path] = {}

        result["106_brief"] = self._markdown(
            target / "01_REQ_106_preparation_brief.md",
            self._brief(workpack),
        )
        result["106_inventory"] = self._csv(
            target / "02_REQ_106_provisional_parking_inventory.csv",
            [
                {
                    **item,
                    "hypothesis_status": workpack[
                        "parking_hypothesis"
                    ]["status"],
                }
                for item in workpack["parking_hypothesis"]["subareas"]
            ],
            [
                "area_id",
                "name",
                "provisional_spaces",
                "hypothesis_status",
            ],
        )
        result["106_windows"] = self._csv(
            target / "03_REQ_106_measurement_schedule.csv",
            workpack["measurement_windows"],
            [
                "measurement_id",
                "scenario",
                "proposed_window",
                "status",
            ],
        )
        result["106_count_sheet"] = self._csv(
            target / "04_REQ_106_field_count_sheet.csv",
            [
                {
                    "measurement_id": measurement["measurement_id"],
                    "area_id": area["area_id"],
                    "count_date": "",
                    "count_start": "",
                    "count_end": "",
                    "occupied_spaces": "",
                    "free_spaces": "",
                    "inaccessible_spaces": "",
                    "public_availability_verified": "",
                    "mosque_attendance": "",
                    "other_user_notes": "",
                    "photo_reference": "",
                    "counter_name": "",
                    "signature": "",
                }
                for measurement in workpack["measurement_windows"]
                for area in workpack["parking_hypothesis"]["subareas"]
            ],
            [
                "measurement_id",
                "area_id",
                "count_date",
                "count_start",
                "count_end",
                "occupied_spaces",
                "free_spaces",
                "inaccessible_spaces",
                "public_availability_verified",
                "mosque_attendance",
                "other_user_notes",
                "photo_reference",
                "counter_name",
                "signature",
            ],
        )
        result["106_protocol"] = self._json(
            target / "05_REQ_106_field_protocol.json",
            {
                "protocol": workpack["field_protocol"],
                "provisional_capacity_spaces": workpack[
                    "parking_hypothesis"
                ]["total_spaces"],
                "warning": (
                    "The 300-space figure is a provisional field hypothesis."
                ),
            },
        )
        result["106_legal"] = self._csv(
            target / "06_REQ_106_legal_availability_register.csv",
            [
                {
                    "area_id": area["area_id"],
                    "name": area["name"],
                    "ownership_or_manager": "",
                    "availability_class": "",
                    "restrictions": "",
                    "source_document": "",
                    "verified_by": "",
                    "verification_date": "",
                }
                for area in workpack["parking_hypothesis"]["subareas"]
            ],
            [
                "area_id",
                "name",
                "ownership_or_manager",
                "availability_class",
                "restrictions",
                "source_document",
                "verified_by",
                "verification_date",
            ],
        )
        result["106_balance"] = self._csv(
            target / "07_REQ_106_parking_balance_template.csv",
            [
                {
                    "scenario": scenario,
                    "authoritative_persons": persons,
                    "verified_public_capacity": "",
                    "measured_occupied_by_other_users": "",
                    "measured_available_capacity": "",
                    "calculated_project_demand": "",
                    "surplus_or_deficit": "",
                    "professional_conclusion": "",
                }
                for scenario, persons in (
                    ("regular_future", 150),
                    ("friday_prayer_future", 125),
                    ("special_peak", 200),
                )
            ],
            [
                "scenario",
                "authoritative_persons",
                "verified_public_capacity",
                "measured_occupied_by_other_users",
                "measured_available_capacity",
                "calculated_project_demand",
                "surplus_or_deficit",
                "professional_conclusion",
            ],
        )
        result["106_signoff"] = self._markdown(
            target / "08_REQ_106_signoff_template.md",
            self._signoff("REQ-106", workpack["title"]),
        )
        result["106_manifest"] = self._json(
            target / "09_REQ_106_submission_manifest_template.json",
            self._manifest("REQ-106"),
        )
        return result

    def _export_req108(
        self,
        workpack: Mapping[str, Any],
        root: Path,
    ) -> dict[str, Path]:
        target = root / "REQ-108"
        target.mkdir(parents=True, exist_ok=True)
        result: dict[str, Path] = {}

        result["108_brief"] = self._markdown(
            target / "01_REQ_108_preparation_brief.md",
            self._brief(workpack),
        )
        result["108_phases"] = self._csv(
            target / "02_REQ_108_phase_register.csv",
            workpack["phase_templates"],
            [
                "phase_id",
                "phase_name",
                "mosque_operational",
                "activity_data_status",
            ],
        )
        result["108_equipment"] = self._csv(
            target / "03_REQ_108_equipment_activity_template.csv",
            [
                {
                    "phase_id": phase["phase_id"],
                    "equipment_id": "",
                    "equipment_type": "",
                    "fuel_or_energy": "",
                    "power_kw": "",
                    "operating_hours": "",
                    "load_factor": "",
                    "source_reference": "",
                    "verified_by": "",
                }
                for phase in workpack["phase_templates"][:-1]
            ],
            [
                "phase_id",
                "equipment_id",
                "equipment_type",
                "fuel_or_energy",
                "power_kw",
                "operating_hours",
                "load_factor",
                "source_reference",
                "verified_by",
            ],
        )
        result["108_transport"] = self._csv(
            target / "04_REQ_108_transport_activity_template.csv",
            [
                {
                    "phase_id": phase["phase_id"],
                    "movement_type": "",
                    "vehicle_class": "",
                    "movements_total": "",
                    "distance_km": "",
                    "route_reference": "",
                    "source_reference": "",
                    "verified_by": "",
                }
                for phase in workpack["phase_templates"]
            ],
            [
                "phase_id",
                "movement_type",
                "vehicle_class",
                "movements_total",
                "distance_km",
                "route_reference",
                "source_reference",
                "verified_by",
            ],
        )
        result["108_overlap"] = self._csv(
            target / "05_REQ_108_operational_overlap_matrix.csv",
            [
                {
                    "phase_id": phase["phase_id"],
                    "mosque_operational": phase["mosque_operational"],
                    "regular_future_persons": 150,
                    "friday_future_persons": 125,
                    "special_peak_persons": 200,
                    "operational_traffic_source": "HBM-OCC-2026-001",
                    "double_count_check": "",
                }
                for phase in workpack["phase_templates"]
            ],
            [
                "phase_id",
                "mosque_operational",
                "regular_future_persons",
                "friday_future_persons",
                "special_peak_persons",
                "operational_traffic_source",
                "double_count_check",
            ],
        )
        result["108_checklist"] = self._markdown(
            target / "06_REQ_108_AERIUS_submission_checklist.md",
            "\n".join([
                "# REQ-108 — AERIUS submission checklist",
                "",
                "- [ ] Definitive phased construction schedule.",
                "- [ ] Equipment and operating hours per phase.",
                "- [ ] Fuel or energy source per equipment item.",
                "- [ ] Construction transport movements and routes.",
                "- [ ] Operational traffic based on HBM-OCC-2026-001.",
                "- [ ] Construction and use phase kept separate.",
                "- [ ] Double-count check completed.",
                "- [ ] AERIUS source file included.",
                "- [ ] Calculation PDF included.",
                "- [ ] Professional declaration signed.",
                "",
            ]),
        )
        result["108_signoff"] = self._markdown(
            target / "07_REQ_108_signoff_template.md",
            self._signoff("REQ-108", workpack["title"]),
        )
        result["108_manifest"] = self._json(
            target / "08_REQ_108_submission_manifest_template.json",
            self._manifest("REQ-108"),
        )
        return result

    @staticmethod
    def _brief(workpack: Mapping[str, Any]) -> str:
        lines = [
            f"# {workpack['request_id']} — {workpack['title']}",
            "",
            f"Status: `{workpack['workpack_status']}`",
            "",
            "## Strategic basis",
            "",
        ]
        lines.extend(
            f"- `{key}`: `{value}`"
            for key, value in workpack["strategic_basis"].items()
        )
        lines.extend([
            "",
            "## Professional deliverables still required",
            "",
        ])
        lines.extend(
            f"- {item}" for item in workpack["professional_deliverables"]
        )
        lines.extend([
            "",
            "## Gate",
            "",
            "- Preparation workpack is complete.",
            "- Professional evidence is not yet received.",
            "- Finalization is not allowed.",
            "- Final generation and BB36 remain locked.",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _signoff(request_id: str, title: str) -> str:
        return "\n".join([
            f"# {request_id} — Professional sign-off",
            "",
            f"Workstream: {title}",
            "",
            "Reviewer name:",
            "",
            "Role / qualification:",
            "",
            "Organization:",
            "",
            "Documents reviewed:",
            "",
            "Limitations and deviations:",
            "",
            "Conclusion:",
            "",
            "Date:",
            "",
            "Signature:",
            "",
        ])

    @staticmethod
    def _manifest(request_id: str) -> dict[str, Any]:
        return {
            "schema_version": (
                "phoenix.bb35.professional-evidence-submission/1.0"
            ),
            "request_id": request_id,
            "submission_id": None,
            "provider": {
                "name": None,
                "organization": None,
                "qualification": None,
            },
            "submission_date": None,
            "source_files": [],
            "signature": {
                "signed": False,
                "signatory": None,
            },
            "verification": {
                "checksums_complete": False,
                "professional_scope_complete": False,
                "accepted": False,
            },
        }

    @staticmethod
    def _json(path: Path, value: Any) -> Path:
        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _csv(
        path: Path,
        rows: list[dict[str, Any]],
        fields: list[str],
    ) -> Path:
        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
                lineterminator="\r\n",
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field: (
                        json.dumps(
                            row.get(field),
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        if isinstance(row.get(field), (list, dict))
                        else row.get(field, "")
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _markdown(path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _html(
        path: Path,
        report: Mapping[str, Any],
    ) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(request_id)}</td>"
            f"<td>{html.escape(workpack['title'])}</td>"
            f"<td>{html.escape(workpack['workpack_status'])}</td>"
            "<td>Pending</td>"
            "</tr>"
            for request_id, workpack
            in sorted(report["workpacks"].items())
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head>"
            "<meta charset=\"utf-8\">"
            "<title>BB35 Parallel Preparation Workpacks</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;"
            "margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}"
            ".status{background:#f5f5f5;border:1px solid #aaa;"
            "padding:14px;margin-bottom:18px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bbb;padding:7px;text-align:left}"
            "th{background:#263238;color:#fff}</style>"
            "</head><body>"
            "<h1>BB35 — Parallel Preparation Workpacks v1.8.0</h1>"
            "<div class=\"status\">"
            "<strong>Workpacks:</strong> 3 generated<br>"
            "<strong>Parallel execution:</strong> allowed<br>"
            "<strong>Parking hypothesis:</strong> 300 spaces, unverified<br>"
            "<strong>Professional evidence:</strong> pending<br>"
            "<strong>Final generation:</strong> blocked<br>"
            "<strong>BB36:</strong> locked"
            "</div>"
            "<table><thead><tr><th>ID</th><th>Workstream</th>"
            "<th>Preparation status</th><th>Evidence</th>"
            "</tr></thead><tbody>"
            + rows
            + "</tbody></table></body></html>"
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _checksums(
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(destination.parent).as_posix()}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        destination.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return destination

    @classmethod
    def _dossier(
        cls,
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        root = destination.parent
        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.comment = b""
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                archive.writestr(
                    cls._canonical_info(
                        source.relative_to(root).as_posix()
                    ),
                    source.read_bytes(),
                )
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
