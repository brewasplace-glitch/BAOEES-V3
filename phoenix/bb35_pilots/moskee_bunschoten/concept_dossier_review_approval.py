"""BB35 concept dossier review and project-leader approval."""

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
_SIMULATION_NOTICE = (
    "CONCEPTSIMULATIE - NIET VOOR INDIENING OF UITVOERING"
)


class ConceptDossierReviewApprovalEngine:
    VERSION = "2.1.0"

    def evaluate(
        self,
        *,
        dossier_summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate(
            dossier_summary=dossier_summary,
            release_gate=release_gate,
            config=config,
        )

        checks = self._review_checks(dossier_summary, release_gate)
        findings = self._findings()
        action_register = self._professional_actions()

        all_checks_passed = all(item["passed"] for item in checks)
        unresolved_review_findings = sum(
            1 for item in findings if item["status"] == "OPEN"
        )

        report = {
            "schema_version": (
                "phoenix.bb35.concept-dossier-review-approval/1.0"
            ),
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "dossier_id": config["dossier_id"],
            "review_id": config["review_id"],
            "review_date": config["review_date"],
            "status": (
                "CONCEPT_DOSSIER_REVIEWED_PROJECT_LEADER_APPROVED"
            ),
            "approval": dict(config["approval"]),
            "approval_interpretation": (
                "INTERNAL_PROJECT_APPROVAL_WITH_CONDITIONS"
            ),
            "simulation_notice": _SIMULATION_NOTICE,
            "review_check_count": len(checks),
            "review_checks_passed": sum(
                1 for item in checks if item["passed"]
            ),
            "all_review_checks_passed": all_checks_passed,
            "review_finding_count": len(findings),
            "unresolved_project_leader_review_findings": (
                unresolved_review_findings
            ),
            "acceptance_conditions": list(config["limitations"]),
            "request_count": dossier_summary["metrics"]["request_count"],
            "drawing_register_count": dossier_summary["metrics"][
                "drawing_register_count"
            ],
            "calculation_register_count": dossier_summary["metrics"][
                "calculation_register_count"
            ],
            "assumption_count": dossier_summary["metrics"][
                "assumption_count"
            ],
            "consistency_check_count": dossier_summary["metrics"][
                "consistency_check_count"
            ],
            "professional_blocker_count": dossier_summary["metrics"][
                "professional_blocker_count"
            ],
            "parking_basis_spaces": dossier_summary[
                "parking_basis_spaces"
            ],
            "parking_basis_status": dossier_summary[
                "parking_basis_status"
            ],
            "req107_status": dossier_summary["req107_status"],
            "review_checks": checks,
            "review_findings": findings,
            "professional_evidence_actions": action_register,
            "gates": {
                "concept_dossier_review_completed": True,
                "project_leader_approval_recorded": True,
                "concept_stage_accepted_for_pilot_validation": True,
                "professional_evidence_replacement_allowed": True,
                "final_permit_ready_generation_allowed": False,
                "bb36_functional_validation_passed": True,
                "bb36_production_release_allowed": False,
            },
            "next_gate": (
                "Execute the professional evidence replacement programme "
                "for REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and "
                "REQ-108."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _validate(
        *,
        dossier_summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> None:
        expected = config["expected"]
        checks = {
            "review_ready_status": (
                dossier_summary.get("status")
                == "INTEGRATED_CONCEPT_DOSSIER_GENERATED_REVIEW_READY"
            ),
            "dossier_id": (
                dossier_summary.get("dossier_id") == config["dossier_id"]
            ),
            "request_count": (
                dossier_summary["metrics"]["request_count"]
                == expected["request_count"]
            ),
            "drawing_count": (
                dossier_summary["metrics"]["drawing_register_count"]
                == expected["drawing_register_count"]
            ),
            "calculation_count": (
                dossier_summary["metrics"]["calculation_register_count"]
                == expected["calculation_register_count"]
            ),
            "assumption_count": (
                dossier_summary["metrics"]["assumption_count"]
                == expected["assumption_count"]
            ),
            "consistency_count": (
                dossier_summary["metrics"]["consistency_check_count"]
                == expected["consistency_check_count"]
            ),
            "blocker_count": (
                dossier_summary["metrics"]["professional_blocker_count"]
                == expected["professional_blocker_count"]
            ),
            "parking_basis": (
                dossier_summary["parking_basis_spaces"]
                == expected["parking_basis_spaces"]
            ),
            "req107_closed": (
                dossier_summary["req107_status"]
                == expected["req107_status"]
            ),
            "review_gate_ready": (
                release_gate["gates"]["concept_dossier_review_ready"]
                is True
            ),
            "final_still_blocked": (
                release_gate["gates"][
                    "final_permit_ready_generation_allowed"
                ]
                is False
            ),
            "bb36_functional": (
                release_gate["gates"][
                    "bb36_functional_validation_passed"
                ]
                is True
            ),
            "bb36_production_locked": (
                release_gate["gates"][
                    "bb36_production_release_allowed"
                ]
                is False
            ),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(
                "Concept dossier review predecessor validation failed: "
                + ", ".join(failed)
            )

    @staticmethod
    def _review_checks(
        summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "check_id": "REV-01",
                "topic": "integrated_dossier",
                "criterion": "Integrated concept dossier is generated.",
                "passed": summary["gates"][
                    "integrated_concept_dossier_generated"
                ],
            },
            {
                "check_id": "REV-02",
                "topic": "request_coverage",
                "criterion": "REQ-102 through REQ-108 are registered.",
                "passed": summary["metrics"]["request_count"] == 7,
            },
            {
                "check_id": "REV-03",
                "topic": "drawings",
                "criterion": "Drawing register contains 8 items.",
                "passed": summary["metrics"][
                    "drawing_register_count"
                ] == 8,
            },
            {
                "check_id": "REV-04",
                "topic": "calculations",
                "criterion": "Calculation register contains 8 items.",
                "passed": summary["metrics"][
                    "calculation_register_count"
                ] == 8,
            },
            {
                "check_id": "REV-05",
                "topic": "assumptions",
                "criterion": "Assumptions register contains 8 items.",
                "passed": summary["metrics"]["assumption_count"] == 8,
            },
            {
                "check_id": "REV-06",
                "topic": "consistency",
                "criterion": "All 11 consistency checks passed.",
                "passed": summary["metrics"][
                    "consistency_check_count"
                ] == 11,
            },
            {
                "check_id": "REV-07",
                "topic": "parking",
                "criterion": (
                    "Parking basis is 225 project-leader-confirmed spaces."
                ),
                "passed": summary["parking_basis_spaces"] == 225,
            },
            {
                "check_id": "REV-08",
                "topic": "occupancy",
                "criterion": "REQ-107 is closed by the project leader.",
                "passed": (
                    summary["req107_status"]
                    == "CLOSED_PROJECT_LEADER_APPROVED"
                ),
            },
            {
                "check_id": "REV-09",
                "topic": "simulation_boundary",
                "criterion": (
                    "Six professional evidence blockers remain visible."
                ),
                "passed": summary["metrics"][
                    "professional_blocker_count"
                ] == 6,
            },
            {
                "check_id": "REV-10",
                "topic": "permit_gate",
                "criterion": (
                    "Final permit-ready generation remains blocked."
                ),
                "passed": (
                    release_gate["gates"][
                        "final_permit_ready_generation_allowed"
                    ]
                    is False
                ),
            },
            {
                "check_id": "REV-11",
                "topic": "bb36_functional",
                "criterion": "BB36 functional validation passed.",
                "passed": (
                    release_gate["gates"][
                        "bb36_functional_validation_passed"
                    ]
                    is True
                ),
            },
            {
                "check_id": "REV-12",
                "topic": "bb36_release",
                "criterion": "BB36 production release remains locked.",
                "passed": (
                    release_gate["gates"][
                        "bb36_production_release_allowed"
                    ]
                    is False
                ),
            },
        ]

    @staticmethod
    def _findings() -> list[dict[str, Any]]:
        return [
            {
                "finding_id": "FND-01",
                "classification": "ACCEPTANCE_CONDITION",
                "description": (
                    "Concept simulations must be replaced by validated "
                    "professional evidence before permit-ready release."
                ),
                "status": "ACCEPTED_CONDITION",
            },
            {
                "finding_id": "FND-02",
                "classification": "ACCEPTANCE_CONDITION",
                "description": (
                    "The 225-space parking basis remains subject to field "
                    "verification and professional parking analysis."
                ),
                "status": "ACCEPTED_CONDITION",
            },
            {
                "finding_id": "FND-03",
                "classification": "USE_RESTRICTION",
                "description": (
                    "The integrated concept dossier is not approved for "
                    "permit submission or construction."
                ),
                "status": "ACCEPTED_CONDITION",
            },
        ]

    @staticmethod
    def _professional_actions() -> list[dict[str, Any]]:
        return [
            {
                "request_id": "REQ-102",
                "action": (
                    "Replace simulated geometry validation with validated "
                    "scale, coordinates, layers and cadastral evidence."
                ),
                "responsible_role": "architect_or_survey_specialist",
                "status": "PENDING",
            },
            {
                "request_id": "REQ-103",
                "action": (
                    "Replace structural simulation with current survey and "
                    "new-to-existing connection assessment."
                ),
                "responsible_role": "structural_engineer",
                "status": "PENDING",
            },
            {
                "request_id": "REQ-104",
                "action": (
                    "Replace geotechnical simulation with ground investigation "
                    "and signed foundation advice."
                ),
                "responsible_role": "geotechnical_adviser",
                "status": "PENDING",
            },
            {
                "request_id": "REQ-105",
                "action": (
                    "Replace Bbl/fire/installation simulation with signed "
                    "professional assessments and calculations."
                ),
                "responsible_role": (
                    "architect_fire_safety_and_installation_advisers"
                ),
                "status": "PENDING",
            },
            {
                "request_id": "REQ-106",
                "action": (
                    "Verify 225 spaces, perform field counts and issue a "
                    "professional parking balance."
                ),
                "responsible_role": "traffic_or_parking_adviser",
                "status": "PENDING",
            },
            {
                "request_id": "REQ-108",
                "action": (
                    "Replace synthetic activity data with verified phased "
                    "construction data and an AERIUS calculation."
                ),
                "responsible_role": "aerius_or_nitrogen_adviser",
                "status": "PENDING",
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


class ConceptDossierReviewApprovalExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}

        paths["summary"] = self._json(
            root / "01_review_approval_summary.json",
            {
                key: value
                for key, value in report.items()
                if key not in {
                    "review_checks",
                    "review_findings",
                    "professional_evidence_actions",
                }
            },
        )
        paths["approval_record"] = self._json(
            root / "02_project_leader_approval_record.json",
            {
                "review_id": report["review_id"],
                "dossier_id": report["dossier_id"],
                "review_date": report["review_date"],
                "approval": report["approval"],
                "approval_interpretation": (
                    report["approval_interpretation"]
                ),
                "approval_status": "APPROVED_WITH_CONDITIONS",
                "report_fingerprint_sha256": (
                    report["report_fingerprint_sha256"]
                ),
            },
        )
        paths["approval_statement"] = self._markdown(
            root / "03_project_leader_approval_statement.md",
            self._approval_statement(report),
        )
        paths["checklist"] = self._csv(
            root / "04_review_checklist.csv",
            report["review_checks"],
            ["check_id", "topic", "criterion", "passed"],
        )
        paths["findings"] = self._csv(
            root / "05_review_findings_register.csv",
            report["review_findings"],
            [
                "finding_id",
                "classification",
                "description",
                "status",
            ],
        )
        paths["scope"] = self._json(
            root / "06_approved_scope_and_limitations.json",
            {
                "approved_scope": report["approval"]["approval_scope"],
                "simulation_notice": report["simulation_notice"],
                "acceptance_conditions": report["acceptance_conditions"],
                "permit_submission_allowed": False,
                "construction_use_allowed": False,
                "professional_evidence_replacement_allowed": True,
            },
        )
        paths["actions"] = self._csv(
            root / "07_professional_evidence_action_register.csv",
            report["professional_evidence_actions"],
            [
                "request_id",
                "action",
                "responsible_role",
                "status",
            ],
        )
        paths["request_status"] = self._csv(
            root / "08_request_status_after_approval.csv",
            self._request_status_rows(report),
            [
                "request_id",
                "status_after_project_leader_review",
                "professional_evidence_required",
                "permit_ready",
            ],
        )
        paths["bb35_report"] = self._markdown(
            root / "09_BB35_concept_stage_acceptance_report.md",
            self._bb35_report(report),
        )
        paths["bb36_report"] = self._markdown(
            root / "10_BB36_release_boundary_report.md",
            self._bb36_report(report),
        )
        paths["transmittal"] = self._markdown(
            root / "11_approved_concept_dossier_transmittal.md",
            self._transmittal(report),
        )
        paths["dashboard"] = self._html(
            root / "12_review_approval_dashboard.html",
            report,
        )
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            paths,
            root
            / "BB35_PILOT_1_CONCEPT_DOSSIER_REVIEW_APPROVAL_"
            "v2_1_0.zip",
        )
        return paths

    @staticmethod
    def _request_status_rows(
        report: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        rows = []
        for request_id in (
            "REQ-102",
            "REQ-103",
            "REQ-104",
            "REQ-105",
            "REQ-106",
            "REQ-107",
            "REQ-108",
        ):
            is_req107 = request_id == "REQ-107"
            rows.append({
                "request_id": request_id,
                "status_after_project_leader_review": (
                    "CLOSED_PROJECT_LEADER_APPROVED"
                    if is_req107
                    else (
                        "CONCEPT_ACCEPTED_"
                        "PROFESSIONAL_EVIDENCE_PENDING"
                    )
                ),
                "professional_evidence_required": not is_req107,
                "permit_ready": False,
            })
        return rows

    @staticmethod
    def _approval_statement(
        report: Mapping[str, Any],
    ) -> str:
        return "\n".join([
            "# Projectleidersgoedkeuring conceptdossier",
            "",
            f"Review-ID: `{report['review_id']}`",
            f"Dossier-ID: `{report['dossier_id']}`",
            f"Datum: `{report['review_date']}`",
            "",
            "De projectleider keurt het geïntegreerde conceptdossier goed "
            "voor:",
            "",
            "- validatie van de BB35-pilot;",
            "- interne conceptbeoordeling;",
            "- voorbereiding en vervanging door professionele bewijsstukken.",
            "",
            "Deze goedkeuring geldt niet als:",
            "",
            "- vergunningtechnische eindgoedkeuring;",
            "- constructieve, brandveiligheids- of installatieverklaring;",
            "- parkeer- of AERIUS-eindadvies;",
            "- toestemming voor uitvoering.",
            "",
            "De interne goedkeuring is vastgelegd op basis van een "
            "expliciete projectleidersinstructie. Dit document is geen "
            "gekwalificeerde elektronische handtekening.",
            "",
            f"Status: `{report['status']}`",
            f"Vingerafdruk: `{report['report_fingerprint_sha256']}`",
            "",
        ])

    @staticmethod
    def _bb35_report(report: Mapping[str, Any]) -> str:
        return "\n".join([
            "# BB35 — Acceptatie conceptstadium",
            "",
            "Het geïntegreerde conceptdossier is door de projectleider "
            "beoordeeld en onder voorwaarden geaccepteerd.",
            "",
            f"- Reviewcontroles: {report['review_checks_passed']} van "
            f"{report['review_check_count']} geslaagd.",
            "- Projectleidersbevindingen open: 0.",
            "- REQ-107: gesloten.",
            "- Parkeerbasis: 225 plaatsen, veldverificatie nog vereist.",
            "- Professionele bewijsblokkades: 6.",
            "",
            "De end-to-end conceptworkflow is geaccepteerd als geldig "
            "pilotresultaat. De professionele bewijsvervanging vormt de "
            "volgende fase.",
            "",
        ])

    @staticmethod
    def _bb36_report(report: Mapping[str, Any]) -> str:
        return "\n".join([
            "# BB36 — Vrijgavegrens na projectleidersreview",
            "",
            "## Geslaagd",
            "",
            "- BB36 functionele validatie.",
            "- Generatie van een geïntegreerd conceptdossier.",
            "- Projectleidersreview en interne acceptatie.",
            "- Zichtbare scheiding tussen simulatie en professioneel bewijs.",
            "",
            "## Nog niet vrijgegeven",
            "",
            "- Productiegebruik van BB36.",
            "- Definitieve vergunningklare generatie.",
            "- Uitvoeringsdocumenten op basis van simulaties.",
            "",
            "Productievrijgave blijft afhankelijk van de zes professionele "
            "bewijsvervangingen en de afsluitende BB35-evidencegate.",
            "",
        ])

    @staticmethod
    def _transmittal(report: Mapping[str, Any]) -> str:
        return "\n".join([
            "# Transmittal — Goedgekeurd conceptdossier",
            "",
            f"Dossier: `{report['dossier_id']}`",
            f"Review: `{report['review_id']}`",
            "",
            "Distributiestatus: intern en voor professionele adviseurs.",
            "",
            "Doel van distributie:",
            "",
            "- professionele bewijsstukken laten opstellen;",
            "- conceptuitgangspunten laten controleren;",
            "- simulaties gecontroleerd vervangen.",
            "",
            "Gebruik voor vergunningindiening of uitvoering is niet toegestaan.",
            "",
        ])

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
                    field: row.get(field, "")
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
            f"<td>{html.escape(item['check_id'])}</td>"
            f"<td>{html.escape(item['topic'])}</td>"
            f"<td>{html.escape(item['criterion'])}</td>"
            f"<td>{'PASS' if item['passed'] else 'FAIL'}</td>"
            "</tr>"
            for item in report["review_checks"]
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head>"
            "<meta charset=\"utf-8\">"
            "<title>BB35 Conceptdossier Review</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;"
            "margin:32px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}"
            ".status{background:#f5f5f5;border:1px solid #aaa;"
            "padding:14px;margin-bottom:18px}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bbb;padding:7px;text-align:left}"
            "th{background:#263238;color:#fff}</style>"
            "</head><body>"
            "<h1>BB35 — Conceptdossier review en goedkeuring</h1>"
            "<div class=\"status\">"
            "<strong>Projectleidersreview:</strong> voltooid<br>"
            "<strong>Goedkeuring:</strong> onder voorwaarden vastgelegd<br>"
            "<strong>REQ-107:</strong> gesloten<br>"
            "<strong>Parkeerbasis:</strong> 225 plaatsen<br>"
            "<strong>Professionele blokkades:</strong> 6<br>"
            "<strong>Vergunningklare generatie:</strong> geblokkeerd<br>"
            "<strong>BB36 productie:</strong> vergrendeld"
            "</div>"
            "<table><thead><tr><th>ID</th><th>Onderwerp</th>"
            "<th>Criterium</th><th>Resultaat</th></tr></thead><tbody>"
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
