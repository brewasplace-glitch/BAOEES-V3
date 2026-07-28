"""BB35 professional evidence replacement programme."""

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


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ProfessionalEvidenceReplacementProgrammeEngine:
    VERSION = "2.2.0"

    def evaluate(
        self,
        *,
        review_summary: Mapping[str, Any],
        orchestrator_summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_predecessors(
            review_summary=review_summary,
            orchestrator_summary=orchestrator_summary,
            release_gate=release_gate,
            config=config,
        )
        workpacks = []
        for position, item in enumerate(config["requests"], start=1):
            workpacks.append({
                "sequence": position,
                "request_id": item["request_id"],
                "title": item["title"],
                "discipline": item["discipline"],
                "lead_role": item["lead_role"],
                "support_roles": list(item["support_roles"]),
                "concept_source": item["concept_source"],
                "required_input_count": len(item["required_inputs"]),
                "acceptance_criterion_count": len(item["criteria"]),
                "closure_condition": item["closure_condition"],
                "workpack_status": "READY_FOR_ISSUE",
                "evidence_status": "PENDING",
                "validation_status": "NOT_STARTED",
                "closure_status": "OPEN",
            })

        gate_checks = self._gate_checks(
            review_summary,
            orchestrator_summary,
            release_gate,
            config,
        )
        report = {
            "schema_version": (
                "phoenix.bb35.professional-evidence-replacement-"
                "programme-report/1.0"
            ),
            "engine_version": self.VERSION,
            "programme_id": config["programme_id"],
            "pilot_id": config["pilot_id"],
            "project_id": config["project_id"],
            "dossier_id": config["dossier_id"],
            "issue_date": config["issue_date"],
            "status": "PROFESSIONAL_EVIDENCE_REPLACEMENT_PROGRAMME_READY",
            "programme_status": config["programme_status"],
            "use_restriction": config["use_restriction"],
            "project_leader_approval_reference": (
                config["project_leader_approval_reference"]
            ),
            "occupancy_programme_reference": (
                config["occupancy_programme_reference"]
            ),
            "parking_basis_spaces": config["parking_basis_spaces"],
            "replacement_request_count": len(workpacks),
            "replacement_requests": [
                item["request_id"] for item in workpacks
            ],
            "excluded_closed_request": config["excluded_closed_request"],
            "req107_status": review_summary["req107_status"],
            "workpack_count": len(workpacks),
            "adviser_brief_count": len(workpacks),
            "input_template_count": len(workpacks),
            "acceptance_matrix_count": len(workpacks),
            "return_manifest_template_count": len(workpacks),
            "validation_checklist_count": len(workpacks),
            "closure_record_template_count": len(workpacks),
            "workpacks": workpacks,
            "gate_checks": gate_checks,
            "gate_check_count": len(gate_checks),
            "gate_checks_passed": sum(
                1 for item in gate_checks if item["passed"]
            ),
            "all_gate_checks_passed": all(
                item["passed"] for item in gate_checks
            ),
            "professional_evidence_blocker_count": 6,
            "professional_evidence_accepted_count": 0,
            "gates": {
                "programme_ready": True,
                "adviser_issue_allowed": True,
                "evidence_intake_allowed": True,
                "evidence_validation_complete": False,
                "all_professional_evidence_accepted": False,
                "final_permit_ready_generation_allowed": False,
                "bb36_production_release_allowed": False,
            },
            "next_gate": (
                "Issue the six workpacks, receive professional evidence, "
                "validate each return package and close REQ-102, REQ-103, "
                "REQ-104, REQ-105, REQ-106 and REQ-108."
            ),
        }
        report["programme_fingerprint_sha256"] = _fingerprint(report)
        return report

    @staticmethod
    def _validate_predecessors(
        *,
        review_summary: Mapping[str, Any],
        orchestrator_summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> None:
        checks = {
            "project_leader_review": (
                review_summary.get("status")
                == "CONCEPT_DOSSIER_REVIEWED_PROJECT_LEADER_APPROVED"
            ),
            "replacement_allowed": review_summary["gates"][
                "professional_evidence_replacement_allowed"
            ] is True,
            "six_review_blockers": (
                review_summary["professional_blocker_count"] == 6
            ),
            "req107_closed": (
                review_summary["req107_status"]
                == "CLOSED_PROJECT_LEADER_APPROVED"
            ),
            "parking_basis": (
                review_summary["parking_basis_spaces"]
                == config["parking_basis_spaces"]
            ),
            "orchestrator_ready": (
                orchestrator_summary.get("status")
                == "UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY"
            ),
            "orchestrator_checks": (
                orchestrator_summary["cross_checks_passed"]
                == orchestrator_summary["cross_check_count"]
            ),
            "release_still_blocked": (
                release_gate["gates"][
                    "final_permit_ready_generation_allowed"
                ] is False
            ),
            "bb36_locked": (
                release_gate["gates"][
                    "bb36_production_release_allowed"
                ] is False
            ),
            "six_config_requests": len(config["requests"]) == 6,
            "req107_excluded": config["excluded_closed_request"] == "REQ-107",
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(
                "Professional evidence programme predecessor validation "
                "failed: " + ", ".join(failed)
            )

    @staticmethod
    def _gate_checks(
        review_summary: Mapping[str, Any],
        orchestrator_summary: Mapping[str, Any],
        release_gate: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        checks = [
            ("PERP-01", "Project-leader concept approval exists.", review_summary["gates"]["project_leader_approval_recorded"]),
            ("PERP-02", "Professional evidence replacement is allowed.", review_summary["gates"]["professional_evidence_replacement_allowed"]),
            ("PERP-03", "REQ-107 remains closed.", review_summary["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"),
            ("PERP-04", "Parking basis remains 225 spaces.", review_summary["parking_basis_spaces"] == 225),
            ("PERP-05", "Unified concept issue is ready.", orchestrator_summary["status"] == "UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY"),
            ("PERP-06", "Cross-discipline checks passed.", orchestrator_summary["cross_checks_passed"] == orchestrator_summary["cross_check_count"]),
            ("PERP-07", "Exactly six replacement requests are defined.", len(config["requests"]) == 6),
            ("PERP-08", "All request IDs are unique.", len({item["request_id"] for item in config["requests"]}) == 6),
            ("PERP-09", "Each request has required inputs.", all(item["required_inputs"] for item in config["requests"])),
            ("PERP-10", "Each request has acceptance criteria.", all(item["criteria"] for item in config["requests"])),
            ("PERP-11", "Permit-ready generation remains blocked.", release_gate["gates"]["final_permit_ready_generation_allowed"] is False),
            ("PERP-12", "BB36 production remains locked.", release_gate["gates"]["bb36_production_release_allowed"] is False),
        ]
        return [
            {"check_id": check_id, "criterion": criterion, "passed": bool(passed)}
            for check_id, criterion, passed in checks
        ]


class ProfessionalEvidenceReplacementProgrammeExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        config: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        paths["summary"] = self._json(root / "01_programme_summary.json", {
            key: value for key, value in report.items()
            if key not in {"workpacks", "gate_checks"}
        })
        paths["programme_register"] = self._csv(
            root / "02_programme_register.csv",
            report["workpacks"],
            [
                "sequence", "request_id", "title", "discipline",
                "lead_role", "required_input_count",
                "acceptance_criterion_count", "workpack_status",
                "evidence_status", "validation_status", "closure_status",
            ],
        )
        paths["responsibility_matrix"] = self._csv(
            root / "03_responsibility_matrix.csv",
            self._responsibility_rows(config),
            ["request_id", "lead_role", "support_roles", "project_leader_role", "final_acceptance_role"],
        )
        paths["routing_matrix"] = self._csv(
            root / "04_intake_routing_matrix.csv",
            self._routing_rows(config),
            ["request_id", "intake_folder", "manifest_name", "validation_sequence", "quarantine_on_failure"],
        )
        paths["gate_matrix"] = self._csv(
            root / "05_programme_gate_checks.csv",
            report["gate_checks"],
            ["check_id", "criterion", "passed"],
        )
        paths["closure_sequence"] = self._markdown(
            root / "06_professional_evidence_closure_sequence.md",
            self._closure_sequence(report),
        )
        paths["dashboard"] = self._html(
            root / "07_professional_evidence_programme_dashboard.html",
            report,
        )
        paths["master_manifest"] = self._json(
            root / "08_master_return_manifest_template.json",
            self._master_manifest(config),
        )
        paths["naming_rules"] = self._markdown(
            root / "09_evidence_submission_naming_rules.md",
            self._naming_rules(config),
        )
        paths["gate_status"] = self._json(
            root / "10_gate_status.json",
            {
                "programme_id": report["programme_id"],
                "status": report["status"],
                "professional_evidence_blocker_count": report["professional_evidence_blocker_count"],
                "professional_evidence_accepted_count": report["professional_evidence_accepted_count"],
                "gates": report["gates"],
                "next_gate": report["next_gate"],
            },
        )

        for request in config["requests"]:
            request_id = request["request_id"]
            folder = root / request_id
            folder.mkdir(parents=True, exist_ok=True)
            prefix = request_id.replace('-', '_').lower()
            paths[f"{prefix}_brief"] = self._markdown(
                folder / f"01_{request_id}_adviser_brief.md",
                self._adviser_brief(report, request),
            )
            paths[f"{prefix}_inputs"] = self._csv(
                folder / f"02_{request_id}_required_inputs.csv",
                [
                    {
                        "input_id": item[0],
                        "description": item[1],
                        "accepted_formats": item[2],
                        "mandatory": item[3],
                        "submission_status": "PENDING",
                        "validation_status": "NOT_STARTED",
                    }
                    for item in request["required_inputs"]
                ],
                ["input_id", "description", "accepted_formats", "mandatory", "submission_status", "validation_status"],
            )
            paths[f"{prefix}_criteria"] = self._csv(
                folder / f"03_{request_id}_acceptance_criteria.csv",
                [
                    {
                        "criterion_id": item[0],
                        "criterion": item[1],
                        "classification": item[2],
                        "result": "NOT_ASSESSED",
                        "reviewer_comment": "",
                    }
                    for item in request["criteria"]
                ],
                ["criterion_id", "criterion", "classification", "result", "reviewer_comment"],
            )
            paths[f"{prefix}_manifest"] = self._json(
                folder / f"04_{request_id}_return_manifest_template.json",
                self._return_manifest(report, request),
            )
            paths[f"{prefix}_checklist"] = self._csv(
                folder / f"05_{request_id}_validation_checklist.csv",
                self._validation_rows(request),
                ["sequence", "validation_step", "required_result", "actual_result", "status"],
            )
            paths[f"{prefix}_closure"] = self._json(
                folder / f"06_{request_id}_closure_record_template.json",
                self._closure_record(report, request),
            )
            paths[f"{prefix}_readme"] = self._markdown(
                folder / "07_README.md",
                self._workpack_readme(request),
            )
            paths[f"{prefix}_package"] = self._request_zip(
                folder,
                root / f"BB35_PILOT_1_{request_id}_PROFESSIONAL_EVIDENCE_WORKPACK_v2_2_0.zip",
            )

        paths["checksums"] = self._checksums(paths, root / "checksums.sha256")
        paths["programme_package"] = self._programme_zip(
            paths,
            root / "BB35_PILOT_1_PROFESSIONAL_EVIDENCE_REPLACEMENT_PROGRAMME_v2_2_0.zip",
        )
        return paths

    @staticmethod
    def _responsibility_rows(config: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [{
            "request_id": item["request_id"],
            "lead_role": item["lead_role"],
            "support_roles": ";".join(item["support_roles"]),
            "project_leader_role": "issue_workpack_receive_return_coordinate_resolution",
            "final_acceptance_role": "phoenix_validation_gate_plus_project_leader_acceptance",
        } for item in config["requests"]]

    @staticmethod
    def _routing_rows(config: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [{
            "request_id": item["request_id"],
            "intake_folder": f"evidence_intake/{item['request_id']}",
            "manifest_name": f"{item['request_id']}_RETURN_MANIFEST.json",
            "validation_sequence": "manifest>file_inventory>format>completeness>criteria>signature>closure",
            "quarantine_on_failure": True,
        } for item in config["requests"]]

    @staticmethod
    def _master_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "phoenix.professional-evidence-return-manifest/1.0",
            "programme_id": config["programme_id"],
            "project_id": config["project_id"],
            "request_id": "REQ-XXX",
            "adviser": {
                "organisation": "",
                "contact_name": "",
                "discipline": "",
                "email": "",
                "professional_registration": "",
            },
            "submission": {
                "submission_id": "",
                "submission_date": "",
                "revision": "",
                "purpose": "PROFESSIONAL_EVIDENCE_REPLACEMENT",
            },
            "files": [
                {"relative_path": "", "document_type": "", "revision": "", "sha256": "", "signed": False}
            ],
            "declarations": {
                "information_complete": False,
                "concept_assumptions_checked": False,
                "professional_responsibility_accepted": False,
                "signature_method": "",
            },
        }

    @staticmethod
    def _return_manifest(report: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "phoenix.professional-evidence-return-manifest/1.0",
            "programme_id": report["programme_id"],
            "project_id": report["project_id"],
            "request_id": request["request_id"],
            "discipline": request["discipline"],
            "lead_role": request["lead_role"],
            "submission_id": "",
            "submission_date": "",
            "revision": "",
            "files": [
                {
                    "input_id": item[0],
                    "relative_path": "",
                    "document_type": item[1],
                    "sha256": "",
                    "signed": item[0].endswith(('06', '07', '08')),
                }
                for item in request["required_inputs"]
            ],
            "declarations": {
                "all_mandatory_inputs_included": False,
                "professional_review_completed": False,
                "concept_differences_identified": False,
                "professional_responsibility_accepted": False,
            },
        }

    @staticmethod
    def _validation_rows(request: Mapping[str, Any]) -> list[dict[str, Any]]:
        steps = [
            "Return manifest parses and identifies the correct request.",
            "All mandatory files are present and checksums match.",
            "File formats are accepted and files can be opened.",
            "Professional identity and responsibility are documented.",
            "Every acceptance criterion is assessed.",
            "Differences from Phoenix concept assumptions are registered.",
            "Model, drawings, reports and calculations are marked for replacement where affected.",
            "Project leader resolution is recorded for residual findings.",
            "Closure record is complete and signed/approved.",
        ]
        return [{
            "sequence": index,
            "validation_step": value,
            "required_result": "PASS",
            "actual_result": "NOT_RUN",
            "status": "PENDING",
        } for index, value in enumerate(steps, start=1)]

    @staticmethod
    def _closure_record(report: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "phoenix.professional-evidence-closure-record/1.0",
            "programme_id": report["programme_id"],
            "request_id": request["request_id"],
            "closure_condition": request["closure_condition"],
            "evidence_submission_id": "",
            "validation_result": "NOT_RUN",
            "acceptance_criteria_passed": 0,
            "acceptance_criteria_total": len(request["criteria"]),
            "residual_findings": [],
            "affected_products": [],
            "professional_evidence_status": "PENDING",
            "request_status_after_closure": "OPEN",
            "project_leader_acceptance": {
                "recorded": False,
                "date": "",
                "comment": "",
            },
        }

    @staticmethod
    def _adviser_brief(report: Mapping[str, Any], request: Mapping[str, Any]) -> str:
        inputs = "\n".join(
            f"- `{item[0]}` — {item[1]} ({item[2]})"
            for item in request["required_inputs"]
        )
        criteria = "\n".join(
            f"- `{item[0]}` — {item[1]}"
            for item in request["criteria"]
        )
        return f"""# Adviseursopdracht {request['request_id']}

## Project

- Project: Moskee Bunschoten — Bikkersweg 88
- Programma: `{report['programme_id']}`
- Dossier: `{report['dossier_id']}`
- Onderwerp: {request['title']}
- Hoofdrol: `{request['lead_role']}`
- Discipline: `{request['discipline']}`

## Doel

Vervang de Phoenix-conceptsimulatie voor `{request['request_id']}` door
professioneel, herleidbaar en ondertekend projectbewijs. Controleer de
conceptuitgangspunten en vermeld iedere afwijking die gevolgen heeft voor het
centrale model, tekeningen, rapporten of berekeningen.

## Projectuitgangspunten

- Uitbreiding: 7 × 10 m, twee bouwlagen, 140 m² bruto.
- Parkeerbasis: 225 projectleidersbevestigde plaatsen, verificatie vereist.
- REQ-107: gesloten op basis van HBM-OCC-2026-001.
- Conceptuitgifte en berekeningen zijn niet geschikt voor vergunningindiening
  of uitvoering zolang professioneel bewijs ontbreekt.

## Vereiste retourinformatie

{inputs}

## Acceptatiecriteria

{criteria}

## Retourprocedure

1. Vul het retourmanifest volledig in.
2. Bereken SHA-256 voor ieder retourbestand.
3. Voeg ondertekende verklaringen toe waar vereist.
4. Registreer afwijkingen ten opzichte van Phoenix-conceptdata.
5. Lever één gesloten retourpakket aan met dezelfde mappenstructuur.

## Sluitingsvoorwaarde

`{request['closure_condition']}`
"""

    @staticmethod
    def _workpack_readme(request: Mapping[str, Any]) -> str:
        return f"""# {request['request_id']} professioneel bewijswerkpakket

Status: `READY_FOR_ISSUE — EVIDENCE PENDING`

Gebruik de bestanden in deze map voor uitvraag, ontvangst, validatie en
sluiting van {request['request_id']}. Vul sjablonen in; verwijder geen
identificatievelden. Een conceptuitkomst mag nooit als professioneel bewijs
worden geregistreerd.
"""

    @staticmethod
    def _closure_sequence(report: Mapping[str, Any]) -> str:
        rows = "\n".join(
            f"{item['sequence']}. **{item['request_id']}** — {item['title']} — lead: `{item['lead_role']}`"
            for item in report["workpacks"]
        )
        return f"""# Professioneel bewijsvervangingsprogramma

Programma: `{report['programme_id']}`

## Volgorde

{rows}

## Gate per REQ

1. Werkpakket uitgeven.
2. Retourmanifest en bestanden ontvangen.
3. Bestandssamenstelling en checksums valideren.
4. Acceptatiecriteria toetsen.
5. Afwijkingen doorgeven aan orchestrator.
6. Getroffen model-, tekening-, rapport- en berekeningsproducten regenereren.
7. Projectleider registreert de sluitingsacceptatie.
8. REQ wordt alleen gesloten als alle verplichte criteria zijn geslaagd.

REQ-107 blijft gesloten en maakt geen deel uit van dit programma.
"""

    @staticmethod
    def _naming_rules(config: Mapping[str, Any]) -> str:
        return f"""# Naamgeving professionele bewijsretouren

Programma: `{config['programme_id']}`

Gebruik:

`HBM_<REQ-ID>_<DOCUMENTTYPE>_<ORGANISATIE>_<REV>_<YYYYMMDD>.<ext>`

Voorbeeld:

`HBM_REQ-106_PARKEERBALANS_ADVIESBUREAU_R01_20260815.pdf`

Regels:

- één retourmanifest per REQ;
- geen spaties in bestandsnamen;
- revisie verplicht;
- datum in formaat YYYYMMDD;
- ieder bestand krijgt een SHA-256 in het manifest;
- gewijzigde bestanden krijgen een nieuwe revisie en checksum;
- bronbestanden én leesbare PDF-export meesturen waar van toepassing.
"""

    @staticmethod
    def _html(path: Path, report: Mapping[str, Any]) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item['request_id'])}</td>"
            f"<td>{html.escape(item['title'])}</td>"
            f"<td>{html.escape(item['lead_role'])}</td>"
            f"<td>{item['required_input_count']}</td>"
            f"<td>{item['acceptance_criterion_count']}</td>"
            "<td>READY FOR ISSUE</td><td>EVIDENCE PENDING</td>"
            "</tr>"
            for item in report["workpacks"]
        )
        content = (
            "<!doctype html><html lang='nl'><head><meta charset='utf-8'>"
            "<title>BB35 Professional Evidence Programme</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:30px auto;color:#202124}"
            "h1{border-bottom:3px solid #263238;padding-bottom:8px}.status{background:#f4f6f8;border:1px solid #9aa0a6;padding:14px;margin:16px 0}"
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:7px;text-align:left}th{background:#263238;color:white}</style>"
            "</head><body><h1>Professioneel bewijsvervangingsprogramma</h1>"
            f"<div class='status'><b>Programma:</b> {html.escape(report['programme_id'])}<br>"
            "<b>Werkpakketten:</b> 6<br><b>REQ-107:</b> gesloten en uitgesloten<br>"
            "<b>Parkeerbasis:</b> 225 plaatsen<br><b>Geaccepteerd professioneel bewijs:</b> 0 van 6<br>"
            "<b>Vergunningklare generatie:</b> geblokkeerd<br><b>BB36 productie:</b> vergrendeld</div>"
            "<table><thead><tr><th>REQ</th><th>Onderwerp</th><th>Lead</th><th>Inputs</th><th>Criteria</th><th>Werkpakket</th><th>Bewijs</th></tr></thead><tbody>"
            + rows + "</tbody></table></body></html>"
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

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
                writer.writerow({field: row.get(field, "") for field in fields})
        return path

    @staticmethod
    def _markdown(path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _canonical_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.flag_bits = 0
        info.external_attr = 0o100644 << 16
        info.extra = b""
        info.comment = b""
        return info

    @classmethod
    def _request_zip(cls, folder: Path, destination: Path) -> Path:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.comment = b""
            for source in sorted(folder.rglob("*")):
                if source.is_file() and source != destination:
                    archive.writestr(cls._canonical_info(source.name), source.read_bytes())
        return destination

    @classmethod
    def _programme_zip(cls, paths: Mapping[str, Path], destination: Path) -> Path:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.comment = b""
            for key, source in sorted(paths.items()):
                if key == "programme_package":
                    continue
                archive.writestr(cls._canonical_info(source.name), source.read_bytes())
        return destination

    @staticmethod
    def _checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(destination.parent).as_posix()}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "programme_package"}
        ]
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return destination
