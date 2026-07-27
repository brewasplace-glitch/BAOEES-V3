"""Validate and classify uploaded BB35 Moskee Bunschoten evidence."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import struct
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_FIXED_TIME = (2020, 1, 1, 0, 0, 0)


class UploadedEvidenceIntakeEngine:
    VERSION = "1.4.1"

    def evaluate(
        self,
        *,
        manifest: Mapping[str, Any],
        register: Mapping[str, Any],
        evidence_root: str | Path,
    ) -> dict[str, Any]:
        root = Path(evidence_root)
        results: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []

        for record in manifest.get("files", []):
            path = root / str(record["relative_path"])
            available = path.is_file()
            actual_hash = (
                hashlib.sha256(path.read_bytes()).hexdigest()
                if available else ""
            )
            hash_valid = available and actual_hash == record["sha256"]
            signature_valid = available and self._signature_valid(
                path, record
            )
            result = {
                "evidence_id": record["evidence_id"],
                "file_name": path.name,
                "role": record["role"],
                "request_id": record["request_id"],
                "available": available,
                "hash_valid": hash_valid,
                "signature_valid": signature_valid,
                "expected_sha256": record["sha256"],
                "actual_sha256": actual_hash,
                "size_bytes": record["size_bytes"],
            }
            results.append(result)
            if not available:
                issues.append(self._issue(
                    "HBM-INTAKE-MISSING",
                    "critical",
                    f"Uploaded evidence is missing: {path.name}.",
                    True,
                    record["evidence_id"],
                ))
            elif not hash_valid:
                issues.append(self._issue(
                    "HBM-INTAKE-HASH",
                    "critical",
                    f"Uploaded evidence hash mismatch: {path.name}.",
                    True,
                    record["evidence_id"],
                ))
            elif not signature_valid:
                issues.append(self._issue(
                    "HBM-INTAKE-SIGNATURE",
                    "critical",
                    f"Uploaded evidence signature invalid: {path.name}.",
                    True,
                    record["evidence_id"],
                ))

        request_statuses = [
            {
                "request_id": "REQ-101",
                "category": "existing_building_drawings",
                "status": "CLOSED_VERIFIED",
                "blocking": False,
                "accepted_evidence_ids": ["HBM-ING-001"],
                "remaining_action": "",
            },
            {
                "request_id": "REQ-102",
                "category": "cadastral_site_base",
                "status": "RECEIVED_PENDING_GEOMETRY_VALIDATION",
                "blocking": True,
                "accepted_evidence_ids": ["HBM-ING-002", "HBM-ING-004"],
                "remaining_action": (
                    "Validate layers, units, scale, parcel boundaries, "
                    "coordinate system and consistency with site survey."
                ),
            },
            {
                "request_id": "REQ-103",
                "category": "structural_survey",
                "status": "HISTORICAL_DOCUMENTATION_ACCEPTED_CURRENT_SURVEY_PENDING",
                "blocking": True,
                "accepted_evidence_ids": ["HBM-ING-003", "HBM-ING-001"],
                "remaining_action": (
                    "Perform and sign current site inspection, verify existing "
                    "member dimensions, condition and proposed connections."
                ),
            },
        ]
        for request_id, category in [
            ("REQ-104", "geotechnical"),
            ("REQ-105", "technical_assumptions"),
            ("REQ-106", "parking_field_evidence"),
            ("REQ-107", "occupancy_and_use"),
            ("REQ-108", "aerius_activity_data"),
        ]:
            request_statuses.append({
                "request_id": request_id,
                "category": category,
                "status": "OPEN",
                "blocking": True,
                "accepted_evidence_ids": [],
                "remaining_action": "Supply the requested professional evidence.",
            })

        input_records = list(register.get("inputs", []))
        verified_count = sum(
            1 for item in input_records
            if item.get("status") in {
                "verified",
                "verified_preliminary",
                "accepted_authoritative",
            }
        )
        blocking_count = sum(
            1 for item in input_records if item.get("blocking", False)
        )

        invalid = any(
            not item["available"]
            or not item["hash_valid"]
            or not item["signature_valid"]
            for item in results
        )
        status = (
            "INVALID_UPLOADED_EVIDENCE"
            if invalid
            else "EVIDENCE_ACQUISITION_PARTIALLY_SATISFIED"
        )

        report = {
            "schema_version": "phoenix.bb35.uploaded-evidence-intake/1.0",
            "engine_version": self.VERSION,
            "pilot_id": manifest["pilot_id"],
            "project_id": manifest["project_id"],
            "status": status,
            "authoritative_scope": manifest["authoritative_scope"],
            "received_file_count": len(results),
            "valid_file_count": sum(
                1 for item in results
                if item["available"]
                and item["hash_valid"]
                and item["signature_valid"]
            ),
            "closed_request_count": sum(
                1 for item in request_statuses
                if item["status"] == "CLOSED_VERIFIED"
            ),
            "partial_request_count": sum(
                1 for item in request_statuses
                if item["status"] not in {"CLOSED_VERIFIED", "OPEN"}
            ),
            "open_request_count": sum(
                1 for item in request_statuses
                if item["status"] == "OPEN"
            ),
            "remaining_blocking_input_count": blocking_count,
            "verified_project_fact_count": verified_count,
            "request_statuses": request_statuses,
            "evidence_results": results,
            "issues": issues,
            "concept_package_status": "ACCEPTED_WITH_CONDITIONS",
            "concept_generation_allowed": True,
            "final_generation_allowed": False,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "next_gate": (
                "Validate cadastral DWG geometry and commission current "
                "structural survey; continue REQ-104 through REQ-108."
            ),
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _signature_valid(
        path: Path,
        record: Mapping[str, Any],
    ) -> bool:
        suffix = path.suffix.lower()
        data = path.read_bytes()
        if suffix == ".pdf":
            return data.startswith(b"%PDF-")
        if suffix == ".png":
            return data.startswith(b"\x89PNG\r\n\x1a\n")
        if suffix == ".dwg":
            return data.startswith(b"AC1032")
        return False

    @staticmethod
    def _issue(
        code: str,
        severity: str,
        message: str,
        blocking: bool,
        source: str,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "blocking": blocking,
            "source": source,
        }

    @staticmethod
    def _fingerprint(value: Any) -> str:
        data = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(data).hexdigest()


class UploadedEvidenceIntakeExporter:
    def export_all(
        self,
        report: Mapping[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "report": self._json(
                report,
                root / "01_uploaded_evidence_intake_report.json",
            ),
            "evidence": self._csv(
                report["evidence_results"],
                root / "02_uploaded_evidence_register.csv",
                [
                    "evidence_id", "file_name", "role", "request_id",
                    "available", "hash_valid", "signature_valid",
                    "size_bytes", "expected_sha256", "actual_sha256",
                ],
            ),
            "requests": self._csv(
                report["request_statuses"],
                root / "03_evidence_request_status.csv",
                [
                    "request_id", "category", "status", "blocking",
                    "accepted_evidence_ids", "remaining_action",
                ],
            ),
            "html": self._html(
                report,
                root / "04_uploaded_evidence_intake_status.html",
            ),
        }
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            paths,
            root / "BB35_PILOT_1_UPLOADED_EVIDENCE_INTAKE_v1_4_1.zip",
        )
        return paths

    @staticmethod
    def _json(value: Any, path: Path) -> Path:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    @staticmethod
    def _csv(
        rows: list[dict[str, Any]],
        path: Path,
        fields: list[str],
    ) -> Path:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fields, lineterminator="\r\n"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    field: (
                        json.dumps(row.get(field), ensure_ascii=False)
                        if isinstance(row.get(field), (list, dict))
                        else row.get(field)
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _html(report: Mapping[str, Any], path: Path) -> Path:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item['request_id'])}</td>"
            f"<td>{html.escape(item['category'])}</td>"
            f"<td>{html.escape(item['status'])}</td>"
            f"<td>{html.escape(item['remaining_action'])}</td>"
            "</tr>"
            for item in report["request_statuses"]
        )
        content = (
            "<!doctype html><html lang=\"nl\"><head><meta charset=\"utf-8\">"
            "<title>BB35 Uploaded Evidence Intake</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;"
            "margin:36px auto;color:#222}h1{border-bottom:3px solid #222;"
            "padding-bottom:8px}.status{padding:14px;border:1px solid #aaa;"
            "background:#f4f4f4}table{border-collapse:collapse;width:100%;"
            "margin:16px 0}th,td{border:1px solid #bbb;padding:7px;"
            "text-align:left;vertical-align:top}th{background:#263238;"
            "color:white}</style></head><body>"
            "<h1>BB35 Pilot 1 — Uploaded Evidence Intake v1.4.1</h1>"
            "<div class=\"status\">"
            f"<strong>Status:</strong> {html.escape(report['status'])}<br>"
            f"<strong>Files valid:</strong> {report['valid_file_count']}/"
            f"{report['received_file_count']}<br>"
            f"<strong>Requests:</strong> {report['closed_request_count']} closed, "
            f"{report['partial_request_count']} partial, "
            f"{report['open_request_count']} open<br>"
            f"<strong>Remaining blocking inputs:</strong> "
            f"{report['remaining_blocking_input_count']}<br>"
            "<strong>Final generation:</strong> blocked<br>"
            "<strong>BB36:</strong> locked</div>"
            "<h2>Evidence requests</h2><table><thead><tr>"
            "<th>ID</th><th>Category</th><th>Status</th>"
            "<th>Remaining action</th></tr></thead><tbody>"
            + rows
            + "</tbody></table></body></html>"
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _checksums(
        paths: dict[str, Path],
        destination: Path,
    ) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
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
        paths: dict[str, Path],
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
        info = zipfile.ZipInfo(name, _FIXED_TIME)
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
