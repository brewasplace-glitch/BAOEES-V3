"""BB35 downstream preparation strategic decisions engine."""

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
_TARGET_DECISIONS = {
    "DEC-105-01",
    "DEC-105-02",
    "DEC-106-01",
    "DEC-108-01",
}


class DownstreamPreparationDecisionsEngine:
    VERSION = "1.7.0"

    EXPECTED_VALUES = {
        "DEC-105-01": "geen_keukenfunctie",
        "DEC-105-02": "wettelijk_minimum",
        "DEC-106-01": "openbare_capaciteit",
        "DEC-108-01": "gefaseerde_uitvoering",
    }

    def evaluate(
        self,
        *,
        req107_summary: Mapping[str, Any],
        req107_program: Mapping[str, Any],
        req107_decision_register: Mapping[str, Any],
        closure_plan: Mapping[str, Any],
        owner_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessors(
            req107_summary=req107_summary,
            req107_program=req107_program,
            req107_decision_register=req107_decision_register,
            closure_plan=closure_plan,
        )
        self._validate_owner_input(owner_input)

        decisions = [
            dict(item)
            for item in req107_decision_register["strategic_decisions"]
        ]
        by_id = {item["decision_id"]: item for item in decisions}

        for decision_id, selected in owner_input["decisions"].items():
            decision = by_id[decision_id]
            decision["status"] = "OWNER_APPROVED"
            decision["selected_value"] = selected["selected_value"]
            decision["selected_option"] = selected["selected_option"]
            decision["selected_label_nl"] = selected["label_nl"]
            decision["approval"] = {
                "approved": True,
                "approved_by_role": "project_owner",
                "approval_basis": owner_input["approval_basis"],
                "approval_date": owner_input["decision_date"],
                "formal_professional_validation_status": (
                    "NOT_APPLICABLE_TO_STRATEGIC_CHOICE"
                ),
            }

        pending = [item for item in decisions if item["status"] == "PENDING"]
        approved = [
            item for item in decisions if item["status"] == "OWNER_APPROVED"
        ]

        program_id = req107_program["program_id"]
        occupancy = req107_program["occupancy_scenarios"]
        schedules = req107_program["opening_hours"]

        workstreams = {
            "REQ-105": {
                "title": (
                    "Bbl, brandveiligheid en installaties — voorbereiding"
                ),
                "status": "PREPARATION_READY_PROFESSIONAL_EVIDENCE_PENDING",
                "strategic_basis": {
                    "kitchen_function": "geen_keukenfunctie",
                    "installation_sustainability_level": "wettelijk_minimum",
                },
                "authoritative_inputs": {
                    "occupancy_program_id": program_id,
                    "regular_future_persons": occupancy["regular"][
                        "future_persons"
                    ],
                    "friday_future_persons": occupancy["friday_prayer"][
                        "future_persons"
                    ],
                    "special_peak_persons": occupancy["special_peak"][
                        "maximum_persons"
                    ],
                    "opening_hours": schedules,
                },
                "phoenix_preparation_actions": [
                    (
                        "Prepare a requirements matrix for applicable "
                        "building, fire, ventilation and accessibility items."
                    ),
                    (
                        "Use no kitchen function as the spatial and "
                        "installation boundary condition."
                    ),
                    (
                        "Use statutory minimum as the selected performance "
                        "level; no enhanced sustainability claim is permitted."
                    ),
                ],
                "external_requirements": [
                    "Signed Bbl assumptions memorandum.",
                    "Professional fire-safety and escape-route assessment.",
                    "Ventilation and installation calculations.",
                    "Accessibility and sanitary verification.",
                ],
                "finalization_allowed": False,
            },
            "REQ-106": {
                "title": "Parkeeronderzoek en parkeerbalans — voorbereiding",
                "status": "PREPARATION_READY_FIELD_EVIDENCE_PENDING",
                "strategic_basis": {
                    "parking_strategy": "openbare_capaciteit",
                },
                "authoritative_inputs": {
                    "occupancy_program_id": program_id,
                    "regular_future_persons": occupancy["regular"][
                        "future_persons"
                    ],
                    "friday_future_persons": occupancy["friday_prayer"][
                        "future_persons"
                    ],
                    "special_peak_persons": occupancy["special_peak"][
                        "maximum_persons"
                    ],
                    "opening_hours": schedules,
                },
                "phoenix_preparation_actions": [
                    (
                        "Prepare a public-capacity parking measurement and "
                        "evidence protocol."
                    ),
                    (
                        "Require separate counts for Friday, regular use and "
                        "the annual special peak scenario."
                    ),
                    (
                        "Keep provisional desktop counts non-final until "
                        "field evidence and legal availability are verified."
                    ),
                ],
                "external_requirements": [
                    "Representative parking-pressure field measurements.",
                    "Traceable count per public parking subarea.",
                    "Verification that counted spaces are publicly available.",
                    "Final professional parking balance and conclusion.",
                ],
                "finalization_allowed": False,
            },
            "REQ-108": {
                "title": "AERIUS aanleg en gebruik — voorbereiding",
                "status": "PREPARATION_READY_ACTIVITY_DATA_PENDING",
                "strategic_basis": {
                    "execution_phasing": "gefaseerde_uitvoering",
                    "mosque_remains_in_use": True,
                },
                "authoritative_inputs": {
                    "occupancy_program_id": program_id,
                    "regular_future_persons": occupancy["regular"][
                        "future_persons"
                    ],
                    "friday_future_persons": occupancy["friday_prayer"][
                        "future_persons"
                    ],
                    "special_peak_persons": occupancy["special_peak"][
                        "maximum_persons"
                    ],
                    "opening_hours": schedules,
                },
                "phoenix_preparation_actions": [
                    (
                        "Prepare separate construction-phase activity tables "
                        "for each execution phase."
                    ),
                    (
                        "Record concurrent mosque operation during the "
                        "phased works."
                    ),
                    (
                        "Keep construction and operational emissions as "
                        "separate, traceable scenarios."
                    ),
                ],
                "external_requirements": [
                    "Phased construction duration and sequence.",
                    "Equipment, operating hours and fuel data per phase.",
                    "Transport movements per phase.",
                    "Professional AERIUS calculation and source files.",
                ],
                "finalization_allowed": False,
            },
        }

        report = {
            "schema_version": (
                "phoenix.bb35.downstream-preparation-decisions/1.0"
            ),
            "engine_version": self.VERSION,
            "pilot_id": owner_input["pilot_id"],
            "project_id": owner_input["project_id"],
            "status": (
                "ALL_STRATEGIC_DECISIONS_OWNER_APPROVED_"
                "DOWNSTREAM_PREPARATION_READY"
            ),
            "approved_strategic_decision_count": len(approved),
            "pending_strategic_decision_count": len(pending),
            "all_strategic_decisions_approved": len(pending) == 0,
            "newly_approved_decision_ids": sorted(_TARGET_DECISIONS),
            "updated_strategic_decisions": decisions,
            "authoritative_occupancy_program_id": program_id,
            "selected_strategic_basis": {
                "kitchen_function": "geen_keukenfunctie",
                "installation_sustainability_level": "wettelijk_minimum",
                "parking_strategy": "openbare_capaciteit",
                "execution_phasing": "gefaseerde_uitvoering",
                "mosque_remains_in_use_during_construction": True,
            },
            "workstreams": workstreams,
            "workstream_count": len(workstreams),
            "parallel_preparation_allowed": True,
            "professional_evidence_still_required": True,
            "req107_formal_cosign_still_pending": True,
            "remaining_blocking_input_count": int(
                closure_plan["remaining_blocking_input_count"]
            ),
            "final_generation_allowed": False,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "next_gate": (
                "Generate and issue the REQ-105, REQ-106 and REQ-108 "
                "preparation workpacks while pursuing formal REQ-107 co-sign."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessors(
        *,
        req107_summary: Mapping[str, Any],
        req107_program: Mapping[str, Any],
        req107_decision_register: Mapping[str, Any],
        closure_plan: Mapping[str, Any],
    ) -> None:
        checks = {
            "req107_approved": (
                req107_summary.get("status")
                == "REQ_107_OWNER_DECISION_APPROVED_FORMAL_COSIGN_PENDING"
            ),
            "four_req107_approved": (
                int(
                    req107_summary.get(
                        "approved_req107_decision_count",
                        0,
                    )
                )
                == 4
            ),
            "four_remaining": (
                int(
                    req107_summary.get(
                        "remaining_pending_strategic_decision_count",
                        -1,
                    )
                )
                == 4
            ),
            "program_id": (
                req107_program.get("program_id") == "HBM-OCC-2026-001"
            ),
            "program_owner_approved": (
                req107_program.get("status")
                == (
                    "OWNER_APPROVED_AUTHORITATIVE_"
                    "FORMAL_PROFESSIONAL_COSIGN_PENDING"
                )
            ),
            "eight_decisions": (
                len(
                    req107_decision_register.get(
                        "strategic_decisions",
                        [],
                    )
                )
                == 8
            ),
            "seven_blockers": (
                int(
                    closure_plan.get(
                        "remaining_blocking_input_count",
                        0,
                    )
                )
                == 7
            ),
        }
        failed = [key for key, passed in checks.items() if not passed]
        if failed:
            raise ValueError(
                "Downstream predecessor validation failed: "
                + ", ".join(failed)
            )

        decisions = {
            item["decision_id"]: item
            for item in req107_decision_register["strategic_decisions"]
        }
        for decision_id in _TARGET_DECISIONS:
            if decisions[decision_id]["status"] != "PENDING":
                raise ValueError(
                    f"{decision_id} must still be pending."
                )

    @classmethod
    def _validate_owner_input(
        cls,
        owner_input: Mapping[str, Any],
    ) -> None:
        decisions = owner_input.get("decisions", {})
        if set(decisions) != _TARGET_DECISIONS:
            raise ValueError(
                "Owner input must contain exactly the four downstream decisions."
            )
        for decision_id, expected in cls.EXPECTED_VALUES.items():
            actual = decisions[decision_id].get("selected_value")
            if actual != expected:
                raise ValueError(
                    f"Unexpected value for {decision_id}: {actual!r}"
                )

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class DownstreamPreparationDecisionsExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        paths: dict[str, Path] = {}
        paths["summary"] = self._json(
            root / "01_downstream_decision_summary.json",
            {
                key: value
                for key, value in report.items()
                if key not in {
                    "updated_strategic_decisions",
                    "workstreams",
                }
            },
        )
        paths["decision_register"] = self._json(
            root / "02_all_strategic_decisions_approved.json",
            {
                "approved_count": (
                    report["approved_strategic_decision_count"]
                ),
                "pending_count": (
                    report["pending_strategic_decision_count"]
                ),
                "all_approved": (
                    report["all_strategic_decisions_approved"]
                ),
                "strategic_decisions": (
                    report["updated_strategic_decisions"]
                ),
            },
        )
        paths["basis"] = self._json(
            root / "03_authoritative_downstream_preparation_basis.json",
            {
                "occupancy_program_id": (
                    report["authoritative_occupancy_program_id"]
                ),
                "selected_strategic_basis": (
                    report["selected_strategic_basis"]
                ),
                "parallel_preparation_allowed": (
                    report["parallel_preparation_allowed"]
                ),
                "limitations": [
                    "Professional evidence remains required.",
                    "REQ-107 formal co-sign remains pending.",
                    "Final generation remains blocked.",
                    "BB36 remains locked.",
                ],
            },
        )
        paths["workstream_matrix"] = self._workstream_csv(
            root / "04_workstream_preparation_matrix.csv",
            report["workstreams"],
        )

        for request_id, workstream in report["workstreams"].items():
            paths[f"{request_id}_json"] = self._json(
                root / f"05_{request_id.lower()}_preparation_workpack.json",
                {
                    "request_id": request_id,
                    **workstream,
                },
            )
            paths[f"{request_id}_md"] = self._markdown(
                root / f"06_{request_id.lower()}_preparation_brief.md",
                self._workstream_markdown(request_id, workstream),
            )

        paths["owner_record"] = self._markdown(
            root / "07_owner_decision_record.md",
            self._owner_record(report),
        )
        paths["dashboard"] = self._html(
            root / "08_downstream_preparation_dashboard.html",
            report,
        )
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            paths,
            root
            / "BB35_PILOT_1_DOWNSTREAM_PREPARATION_DECISIONS_"
            "v1_7_0.zip",
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
    def _markdown(path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _workstream_csv(
        path: Path,
        workstreams: Mapping[str, Mapping[str, Any]],
    ) -> Path:
        fields = [
            "request_id",
            "title",
            "status",
            "strategic_basis",
            "professional_evidence_required",
            "finalization_allowed",
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
            for request_id, workstream in sorted(workstreams.items()):
                writer.writerow({
                    "request_id": request_id,
                    "title": workstream["title"],
                    "status": workstream["status"],
                    "strategic_basis": json.dumps(
                        workstream["strategic_basis"],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "professional_evidence_required": True,
                    "finalization_allowed": (
                        workstream["finalization_allowed"]
                    ),
                })
        return path

    @staticmethod
    def _workstream_markdown(
        request_id: str,
        workstream: Mapping[str, Any],
    ) -> str:
        lines = [
            f"# {request_id} — {workstream['title']}",
            "",
            f"Status: `{workstream['status']}`",
            "",
            "## Strategic basis",
            "",
        ]
        for key, value in workstream["strategic_basis"].items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend([
            "",
            "## Phoenix preparation actions",
            "",
        ])
        lines.extend(
            f"- {item}"
            for item in workstream["phoenix_preparation_actions"]
        )
        lines.extend([
            "",
            "## External professional evidence still required",
            "",
        ])
        lines.extend(
            f"- {item}"
            for item in workstream["external_requirements"]
        )
        lines.extend([
            "",
            "## Gate",
            "",
            "- Preparation is allowed.",
            "- Finalization is not allowed.",
            "- Final generation remains blocked.",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _owner_record(report: Mapping[str, Any]) -> str:
        basis = report["selected_strategic_basis"]
        return "\n".join([
            "# Downstream Preparation — Owner Decision Record",
            "",
            "- Kitchen function: no kitchen function.",
            "- Installation and sustainability level: statutory minimum.",
            (
                "- Parking strategy: substantiate available public "
                "parking capacity."
            ),
            (
                "- Execution phasing: phased construction while the "
                "mosque remains in use."
            ),
            "",
            "All eight strategic decisions are now owner-approved.",
            "",
            f"Authoritative occupancy programme: "
            f"`{report['authoritative_occupancy_program_id']}`",
            "",
            "Professional evidence and calculations remain required.",
            "REQ-107 formal co-sign remains pending.",
            "Final generation and BB36 remain locked.",
            "",
            f"Decision fingerprint: "
            f"`{report['report_fingerprint_sha256']}`",
            "",
        ])

    @staticmethod
    def _html(
        path: Path,
        report: Mapping[str, Any],
    ) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(request_id)}</td>"
            f"<td>{html.escape(workstream['title'])}</td>"
            f"<td>{html.escape(workstream['status'])}</td>"
            "<td>Pending</td>"
            "</tr>"
            for request_id, workstream
            in sorted(report["workstreams"].items())
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head>"
            "<meta charset=\"utf-8\">"
            "<title>Downstream Preparation Decisions</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;"
            "margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}"
            ".status{background:#f5f5f5;border:1px solid #aaa;"
            "padding:14px;margin-bottom:18px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bbb;padding:7px;text-align:left}"
            "th{background:#263238;color:#fff}</style>"
            "</head><body>"
            "<h1>BB35 — Downstream Preparation Decisions v1.7.0</h1>"
            "<div class=\"status\">"
            "<strong>Strategic decisions:</strong> 8/8 approved<br>"
            "<strong>Parallel preparation:</strong> allowed<br>"
            "<strong>Professional evidence:</strong> pending<br>"
            "<strong>Final generation:</strong> blocked<br>"
            "<strong>BB36:</strong> locked"
            "</div>"
            "<table><thead><tr><th>ID</th><th>Workstream</th>"
            "<th>Status</th><th>Professional evidence</th>"
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
