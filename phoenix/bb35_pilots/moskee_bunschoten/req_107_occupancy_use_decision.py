"""REQ-107 occupancy and use strategic decision engine."""

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
_REQ107_DECISION_IDS = {
    "DEC-107-01",
    "DEC-107-02",
    "DEC-107-03",
    "DEC-107-04",
}


class Req107OccupancyUseDecisionEngine:
    VERSION = "1.6.0"

    def evaluate(
        self,
        *,
        closure_summary: Mapping[str, Any],
        closure_register: Mapping[str, Any],
        owner_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessor(closure_summary, closure_register)
        self._validate_owner_input(owner_input)

        occupancy = owner_input["occupancy"]
        schedules = [dict(item) for item in owner_input["opening_hours"]]

        regular_existing = int(
            occupancy["regular"]["existing_persons"]
        )
        regular_future = int(
            occupancy["regular"]["future_persons"]
        )
        friday_existing = int(
            occupancy["friday_prayer"]["existing_persons"]
        )
        friday_future = int(
            occupancy["friday_prayer"]["future_persons"]
        )
        special_peak = int(
            occupancy["special_peak"]["maximum_persons"]
        )
        special_frequency = int(
            occupancy["special_peak"]["frequency_per_year"]
        )

        decisions = [
            dict(item) for item in closure_register["strategic_decisions"]
        ]
        decision_by_id = {
            item["decision_id"]: item for item in decisions
        }

        decision_values = {
            "DEC-107-01": {
                "existing_persons": regular_existing,
                "future_persons": regular_future,
                "increase_persons": regular_future - regular_existing,
                "increase_percent": self._percentage_increase(
                    regular_existing,
                    regular_future,
                ),
            },
            "DEC-107-02": {
                "existing_persons": friday_existing,
                "future_persons": friday_future,
                "increase_persons": friday_future - friday_existing,
                "increase_percent": self._percentage_increase(
                    friday_existing,
                    friday_future,
                ),
            },
            "DEC-107-03": {
                "maximum_persons": special_peak,
                "frequency_per_year": special_frequency,
            },
            "DEC-107-04": {
                "opening_hours": schedules,
            },
        }

        for decision_id, value in decision_values.items():
            decision = decision_by_id[decision_id]
            decision["status"] = "OWNER_APPROVED"
            decision["selected_value"] = value
            decision["approval"] = {
                "approved": True,
                "approved_by_role": "project_owner",
                "approval_basis": owner_input["approval_basis"],
                "approval_date": owner_input["decision_date"],
                "formal_cosign_status": "PENDING",
            }

        req107 = next(
            dict(item)
            for item in closure_register["closure_items"]
            if item["request_id"] == "REQ-107"
        )
        req107["closure_status"] = (
            "STRATEGIC_DECISION_APPROVED_FORMAL_COSIGN_PENDING"
        )
        req107["current_status"] = (
            "OWNER_APPROVED_AUTHORITATIVE_INPUT_FORMAL_COSIGN_PENDING"
        )

        pending_decisions = [
            item for item in decisions
            if item["status"] == "PENDING"
        ]
        approved_req107_decisions = [
            item for item in decisions
            if (
                item["decision_id"] in _REQ107_DECISION_IDS
                and item["status"] == "OWNER_APPROVED"
            )
        ]

        authoritative_program = {
            "schema_version": (
                "phoenix.bb35.authoritative-occupancy-use-program/1.0"
            ),
            "program_id": "HBM-OCC-2026-001",
            "version": "1.6.0",
            "status": (
                "OWNER_APPROVED_AUTHORITATIVE_"
                "FORMAL_PROFESSIONAL_COSIGN_PENDING"
            ),
            "decision_date": owner_input["decision_date"],
            "approval_basis": owner_input["approval_basis"],
            "project_id": owner_input["project_id"],
            "pilot_id": owner_input["pilot_id"],
            "occupancy_scenarios": {
                "regular": {
                    "existing_persons": regular_existing,
                    "future_persons": regular_future,
                    "increase_persons": (
                        regular_future - regular_existing
                    ),
                    "increase_percent": self._percentage_increase(
                        regular_existing,
                        regular_future,
                    ),
                },
                "friday_prayer": {
                    "existing_persons": friday_existing,
                    "future_persons": friday_future,
                    "increase_persons": (
                        friday_future - friday_existing
                    ),
                    "increase_percent": self._percentage_increase(
                        friday_existing,
                        friday_future,
                    ),
                },
                "special_peak": {
                    "maximum_persons": special_peak,
                    "frequency_per_year": special_frequency,
                },
            },
            "opening_hours": schedules,
            "authoritative_for_preparation": [
                "REQ-105",
                "REQ-106",
                "REQ-108",
                "fire_safety",
                "ventilation",
                "parking",
                "aerius",
            ],
            "limitations": [
                (
                    "Formal closure of REQ-107 still requires a "
                    "co-signed professional verification."
                ),
                (
                    "This decision does not itself complete fire, "
                    "parking or AERIUS calculations."
                ),
            ],
        }
        authoritative_program["fingerprint_sha256"] = self._fingerprint(
            authoritative_program
        )

        report = {
            "schema_version": (
                "phoenix.bb35.req107-occupancy-use-decision/1.0"
            ),
            "engine_version": self.VERSION,
            "pilot_id": owner_input["pilot_id"],
            "project_id": owner_input["project_id"],
            "status": (
                "REQ_107_OWNER_DECISION_APPROVED_"
                "FORMAL_COSIGN_PENDING"
            ),
            "req107_strategic_decision_complete": True,
            "req107_formal_closure_complete": False,
            "req107_formal_cosign_required": True,
            "approved_req107_decision_count": len(
                approved_req107_decisions
            ),
            "remaining_pending_strategic_decision_count": len(
                pending_decisions
            ),
            "remaining_pending_strategic_decision_ids": [
                item["decision_id"] for item in pending_decisions
            ],
            "authoritative_program": authoritative_program,
            "updated_req107_closure_item": req107,
            "updated_strategic_decisions": decisions,
            "downstream_preparation_allowed": {
                "REQ-105": True,
                "REQ-106": True,
                "REQ-108": True,
            },
            "downstream_finalization_allowed": {
                "REQ-105": False,
                "REQ-106": False,
                "REQ-108": False,
            },
            "remaining_blocking_input_count": int(
                closure_summary["remaining_blocking_input_count"]
            ),
            "concept_generation_allowed": True,
            "final_generation_allowed": False,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "next_gate": (
                "Obtain formal co-sign for REQ-107 and start the "
                "REQ-105, REQ-106 and REQ-108 preparation workstreams."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessor(
        closure_summary: Mapping[str, Any],
        closure_register: Mapping[str, Any],
    ) -> None:
        checks = {
            "closure_plan_ready": (
                closure_summary.get("status")
                == "EVIDENCE_VALIDATION_COMPLETE_CLOSURE_PLAN_READY"
            ),
            "seven_blockers": (
                int(
                    closure_summary.get(
                        "remaining_blocking_input_count",
                        0,
                    )
                )
                == 7
            ),
            "critical_path_req107": (
                closure_summary.get("critical_path_root") == "REQ-107"
            ),
            "eight_decisions": (
                len(closure_register.get("strategic_decisions", [])) == 8
            ),
            "req107_exists": any(
                item.get("request_id") == "REQ-107"
                for item in closure_register.get("closure_items", [])
            ),
        }
        failed = [
            key for key, passed in checks.items() if not passed
        ]
        if failed:
            raise ValueError(
                "REQ-107 predecessor validation failed: "
                + ", ".join(failed)
            )

        req107_decisions = [
            item
            for item in closure_register["strategic_decisions"]
            if item["decision_id"] in _REQ107_DECISION_IDS
        ]
        if len(req107_decisions) != 4:
            raise ValueError("Exactly four REQ-107 decisions are required.")
        if any(item["status"] != "PENDING" for item in req107_decisions):
            raise ValueError("REQ-107 decisions must still be pending.")

    @classmethod
    def _validate_owner_input(
        cls,
        owner_input: Mapping[str, Any],
    ) -> None:
        occupancy = owner_input["occupancy"]
        values = {
            "regular_existing": int(
                occupancy["regular"]["existing_persons"]
            ),
            "regular_future": int(
                occupancy["regular"]["future_persons"]
            ),
            "friday_existing": int(
                occupancy["friday_prayer"]["existing_persons"]
            ),
            "friday_future": int(
                occupancy["friday_prayer"]["future_persons"]
            ),
            "special_peak": int(
                occupancy["special_peak"]["maximum_persons"]
            ),
            "special_frequency": int(
                occupancy["special_peak"]["frequency_per_year"]
            ),
        }
        if any(value <= 0 for value in values.values()):
            raise ValueError("All occupancy and frequency values must be positive.")
        if values["regular_future"] < values["regular_existing"]:
            raise ValueError("Future regular occupancy cannot be lower.")
        if values["friday_future"] < values["friday_existing"]:
            raise ValueError("Future Friday occupancy cannot be lower.")
        if values["special_peak"] < max(
            values["regular_future"],
            values["friday_future"],
        ):
            raise ValueError(
                "Special peak must not be lower than future maxima."
            )

        schedules = owner_input["opening_hours"]
        expected_periods = {
            "monday_through_thursday",
            "friday",
            "saturday",
            "sunday",
            "ramadan",
            "holidays_and_special_activities",
        }
        actual_periods = {item["period"] for item in schedules}
        if actual_periods != expected_periods:
            raise ValueError("Opening-hour periods are incomplete.")

        for item in schedules:
            cls._validate_time(item["start_time"], allow_24=False)
            cls._validate_time(item["end_time"], allow_24=True)

    @staticmethod
    def _validate_time(value: str, *, allow_24: bool) -> None:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time: {value}")
        hour, minute = (int(part) for part in parts)
        if allow_24 and hour == 24 and minute == 0:
            return
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Invalid time: {value}")

    @staticmethod
    def _percentage_increase(existing: int, future: int) -> float:
        return round(((future - existing) / existing) * 100.0, 2)

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class Req107OccupancyUseDecisionExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        paths: dict[str, Path] = {}
        paths["summary"] = self._json(
            root / "01_req107_decision_summary.json",
            {
                key: value
                for key, value in report.items()
                if key not in {
                    "updated_strategic_decisions",
                    "authoritative_program",
                    "updated_req107_closure_item",
                }
            },
        )
        paths["authoritative_program"] = self._json(
            root / "02_authoritative_occupancy_use_program.json",
            report["authoritative_program"],
        )
        paths["decision_register"] = self._json(
            root / "03_updated_strategic_decision_register.json",
            {
                "approved_req107_decision_count": (
                    report["approved_req107_decision_count"]
                ),
                "remaining_pending_count": (
                    report[
                        "remaining_pending_strategic_decision_count"
                    ]
                ),
                "strategic_decisions": (
                    report["updated_strategic_decisions"]
                ),
            },
        )
        paths["occupancy_csv"] = self._occupancy_csv(
            root / "04_occupancy_scenarios.csv",
            report["authoritative_program"],
        )
        paths["schedule_csv"] = self._schedule_csv(
            root / "05_opening_hours.csv",
            report["authoritative_program"]["opening_hours"],
        )
        paths["downstream_csv"] = self._downstream_csv(
            root / "06_downstream_handoff_matrix.csv",
            report,
        )
        paths["approval_record"] = self._markdown(
            root / "07_owner_approval_record.md",
            self._approval_markdown(report),
        )
        paths["cosign_template"] = self._markdown(
            root / "08_professional_cosign_template.md",
            self._cosign_markdown(report),
        )
        paths["dashboard"] = self._html(
            root / "09_req107_dashboard.html",
            report,
        )
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            paths,
            root
            / "BB35_PILOT_1_REQ_107_OCCUPANCY_USE_DECISION_"
            "v1_6_0.zip",
        )
        return paths

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
    def _occupancy_csv(
        path: Path,
        program: Mapping[str, Any],
    ) -> Path:
        scenarios = program["occupancy_scenarios"]
        rows = [
            {
                "scenario": "regular",
                "existing_persons": scenarios["regular"][
                    "existing_persons"
                ],
                "future_persons": scenarios["regular"][
                    "future_persons"
                ],
                "increase_persons": scenarios["regular"][
                    "increase_persons"
                ],
                "increase_percent": scenarios["regular"][
                    "increase_percent"
                ],
                "frequency_per_year": "",
            },
            {
                "scenario": "friday_prayer",
                "existing_persons": scenarios["friday_prayer"][
                    "existing_persons"
                ],
                "future_persons": scenarios["friday_prayer"][
                    "future_persons"
                ],
                "increase_persons": scenarios["friday_prayer"][
                    "increase_persons"
                ],
                "increase_percent": scenarios["friday_prayer"][
                    "increase_percent"
                ],
                "frequency_per_year": "",
            },
            {
                "scenario": "special_peak",
                "existing_persons": "",
                "future_persons": scenarios["special_peak"][
                    "maximum_persons"
                ],
                "increase_persons": "",
                "increase_percent": "",
                "frequency_per_year": scenarios["special_peak"][
                    "frequency_per_year"
                ],
            },
        ]
        fields = [
            "scenario",
            "existing_persons",
            "future_persons",
            "increase_persons",
            "increase_percent",
            "frequency_per_year",
        ]
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
            writer.writerows(rows)
        return path

    @staticmethod
    def _schedule_csv(
        path: Path,
        schedules: list[dict[str, Any]],
    ) -> Path:
        fields = [
            "schedule_id",
            "period",
            "days",
            "start_time",
            "end_time",
        ]
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
            for item in schedules:
                writer.writerow({
                    **item,
                    "days": json.dumps(
                        item["days"],
                        ensure_ascii=False,
                    ),
                })
        return path

    @staticmethod
    def _downstream_csv(
        path: Path,
        report: Mapping[str, Any],
    ) -> Path:
        rows = [
            {
                "request_id": request_id,
                "preparation_allowed": report[
                    "downstream_preparation_allowed"
                ][request_id],
                "finalization_allowed": report[
                    "downstream_finalization_allowed"
                ][request_id],
                "authoritative_program_id": (
                    report["authoritative_program"]["program_id"]
                ),
                "remaining_requirement": (
                    "Professional calculations and signed evidence."
                ),
            }
            for request_id in ("REQ-105", "REQ-106", "REQ-108")
        ]
        fields = [
            "request_id",
            "preparation_allowed",
            "finalization_allowed",
            "authoritative_program_id",
            "remaining_requirement",
        ]
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
            writer.writerows(rows)
        return path

    @staticmethod
    def _markdown(path: Path, text: str) -> Path:
        path.write_text(
            text,
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _approval_markdown(
        report: Mapping[str, Any],
    ) -> str:
        program = report["authoritative_program"]
        scenarios = program["occupancy_scenarios"]
        schedule_lines = [
            (
                f"- {item['period']}: "
                f"{item['start_time']}–{item['end_time']}"
            )
            for item in program["opening_hours"]
        ]
        return "\n".join([
            "# REQ-107 — Owner Approval Record",
            "",
            f"Program ID: `{program['program_id']}`",
            f"Decision date: `{program['decision_date']}`",
            f"Status: `{program['status']}`",
            "",
            "## Approved occupancy",
            "",
            (
                "- Regular: existing "
                f"{scenarios['regular']['existing_persons']}, future "
                f"{scenarios['regular']['future_persons']}."
            ),
            (
                "- Friday prayer: existing "
                f"{scenarios['friday_prayer']['existing_persons']}, "
                "future "
                f"{scenarios['friday_prayer']['future_persons']}."
            ),
            (
                "- Special peak: "
                f"{scenarios['special_peak']['maximum_persons']} persons, "
                f"{scenarios['special_peak']['frequency_per_year']} "
                "time per year."
            ),
            "",
            "## Approved opening hours",
            "",
            *schedule_lines,
            "",
            "## Limitation",
            "",
            (
                "The owner decision is authoritative for preparation. "
                "Formal REQ-107 closure still requires professional co-sign."
            ),
            "",
        ])

    @staticmethod
    def _cosign_markdown(
        report: Mapping[str, Any],
    ) -> str:
        program = report["authoritative_program"]
        return "\n".join([
            "# REQ-107 — Professional Co-sign Template",
            "",
            f"Authoritative program: `{program['program_id']}`",
            f"Fingerprint: `{program['fingerprint_sha256']}`",
            "",
            "The undersigned confirms that:",
            "",
            "- the occupancy scenarios are internally consistent;",
            "- the programme can be used for the named discipline;",
            "- discrepancies and limitations have been recorded;",
            "- this confirmation does not replace discipline calculations.",
            "",
            "Reviewer name:",
            "",
            "Role / qualification:",
            "",
            "Discipline:",
            "",
            "Date:",
            "",
            "Signature:",
            "",
        ])

    @staticmethod
    def _html(
        path: Path,
        report: Mapping[str, Any],
    ) -> Path:
        program = report["authoritative_program"]
        scenarios = program["occupancy_scenarios"]
        schedule_rows = "".join(
            "<tr>"
            f"<td>{html.escape(item['period'])}</td>"
            f"<td>{html.escape(item['start_time'])}</td>"
            f"<td>{html.escape(item['end_time'])}</td>"
            "</tr>"
            for item in program["opening_hours"]
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head>"
            "<meta charset=\"utf-8\">"
            "<title>REQ-107 Occupancy & Use</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1000px;"
            "margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}"
            ".status{background:#f5f5f5;border:1px solid #aaa;"
            "padding:14px;margin-bottom:18px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bbb;padding:7px;text-align:left}"
            "th{background:#263238;color:#fff}</style>"
            "</head><body>"
            "<h1>REQ-107 — Occupancy & Use Decision v1.6.0</h1>"
            "<div class=\"status\">"
            f"<strong>Status:</strong> {html.escape(report['status'])}<br>"
            "<strong>Strategic decision:</strong> approved<br>"
            "<strong>Formal co-sign:</strong> pending<br>"
            "<strong>Final generation:</strong> blocked<br>"
            "<strong>BB36:</strong> locked"
            "</div>"
            "<h2>Occupancy</h2><ul>"
            f"<li>Regular: {scenarios['regular']['existing_persons']} → "
            f"{scenarios['regular']['future_persons']}</li>"
            f"<li>Friday: {scenarios['friday_prayer']['existing_persons']} → "
            f"{scenarios['friday_prayer']['future_persons']}</li>"
            f"<li>Special peak: {scenarios['special_peak']['maximum_persons']} "
            f"({scenarios['special_peak']['frequency_per_year']} per year)</li>"
            "</ul><h2>Opening hours</h2><table><thead><tr>"
            "<th>Period</th><th>Start</th><th>End</th>"
            "</tr></thead><tbody>"
            + schedule_rows
            + "</tbody></table></body></html>"
        )
        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _checksums(
        paths: Mapping[str, Path],
        destination: Path,
    ) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.name}"
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
                    cls._canonical_info(source.name),
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
