"""Exports for the BB35 Moskee Bunschoten verified-input gate."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from pathlib import Path
from typing import Any


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class MoskeeBunschotenVerifiedInputsExporter:
    def export_all(
        self,
        report: dict[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        paths = {
            "report": self._json(
                report,
                root / "verified_inputs_gate_report.json",
            ),
            "verified": self._csv(
                report["verified_facts"],
                root / "verified_project_facts.csv",
                [
                    "input_id",
                    "category",
                    "description",
                    "status",
                    "blocking",
                    "evidence_ids",
                ],
            ),
            "pending": self._csv(
                report["pending_inputs"],
                root / "pending_external_inputs.csv",
                [
                    "input_id",
                    "category",
                    "description",
                    "status",
                    "severity",
                    "blocking",
                    "responsible_party",
                    "required_file_types",
                ],
            ),
            "readiness": self._csv(
                report["downstream_readiness"],
                root / "downstream_module_readiness.csv",
                [
                    "module",
                    "final_ready",
                    "concept_allowed",
                    "blocking_input_ids",
                ],
            ),
            "evidence": self._csv(
                report["evidence_results"],
                root / "verified_input_evidence_register.csv",
                [
                    "evidence_id",
                    "evidence_class",
                    "file_name",
                    "relative_path",
                    "role",
                    "available",
                    "sha256_valid",
                    "expected_sha256",
                    "actual_sha256",
                ],
            ),
            "request": self._json(
                {
                    "pilot_id": report["pilot_id"],
                    "project_id": report["project_id"],
                    "status": report["status"],
                    "requested_inputs": report["pending_inputs"],
                    "submission_rule": (
                        "Supply original files or signed professional reports. "
                        "References inside an offer letter do not count as "
                        "technical evidence."
                    ),
                },
                root / "external_input_request_register.json",
            ),
            "html": self._html(
                report,
                root / "verified_inputs_gate_status.html",
            ),
        }
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            report,
            paths,
            root / "verified_inputs_gate_dossier.zip",
        )
        return paths

    @staticmethod
    def _json(value: Any, path: Path) -> Path:
        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _csv(
        records: list[dict[str, Any]],
        path: Path,
        fields: list[str],
    ) -> Path:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in records:
                writer.writerow({
                    field: (
                        json.dumps(
                            record.get(field),
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                        if isinstance(record.get(field), (list, dict))
                        else record.get(field)
                    )
                    for field in fields
                })
        return path

    @staticmethod
    def _html(report: dict[str, Any], path: Path) -> Path:
        verified = "".join(
            "<tr>"
            f"<td>{html.escape(item['category'])}</td>"
            f"<td>{html.escape(item['description'])}</td>"
            f"<td>{html.escape(item['status'])}</td>"
            "</tr>"
            for item in report["verified_facts"]
        )
        pending = "".join(
            "<tr>"
            f"<td>{html.escape(item['category'])}</td>"
            f"<td>{html.escape(item['description'])}</td>"
            f"<td>{html.escape(item['responsible_party'])}</td>"
            f"<td>{'yes' if item['blocking'] else 'no'}</td>"
            "</tr>"
            for item in report["pending_inputs"]
        )
        downstream = "".join(
            "<tr>"
            f"<td>{html.escape(item['module'])}</td>"
            f"<td>{'yes' if item['concept_allowed'] else 'no'}</td>"
            f"<td>{'yes' if item['final_ready'] else 'no'}</td>"
            f"<td>{html.escape(', '.join(item['blocking_input_ids']))}</td>"
            "</tr>"
            for item in report["downstream_readiness"]
        )
        path.write_text(
            "<!doctype html><html lang=\"nl\"><head><meta charset=\"utf-8\">"
            "<title>BB35 Moskee Bunschoten — Verified Inputs</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1150px;"
            "margin:36px auto;color:#222}h1{border-bottom:3px solid #222;"
            "padding-bottom:8px}.status{padding:14px;border:1px solid #aaa;"
            "background:#f4f4f4}table{border-collapse:collapse;width:100%;"
            "margin:16px 0}th,td{border:1px solid #bbb;padding:7px;"
            "text-align:left;vertical-align:top}th{background:#263238;"
            "color:white}</style></head><body>"
            f"<h1>{html.escape(report['project_name'])}</h1>"
            "<div class=\"status\">"
            f"<strong>Status:</strong> {html.escape(report['status'])}<br>"
            "<strong>Scope:</strong> 7.00 x 10.00 m, two storeys, "
            "140 m² gross<br>"
            f"<strong>Valid evidence:</strong> {report['valid_evidence_count']}/"
            f"{report['evidence_count']}<br>"
            f"<strong>Verified facts:</strong> {report['verified_fact_count']}<br>"
            f"<strong>Pending inputs:</strong> {report['pending_input_count']}<br>"
            "<strong>Concept generation:</strong> allowed with explicit "
            "assumptions<br><strong>Final generation:</strong> blocked<br>"
            "<strong>BB36:</strong> locked"
            "</div><h2>Verified project basis</h2><table><thead><tr>"
            "<th>Category</th><th>Verified fact</th><th>Status</th>"
            "</tr></thead><tbody>"
            + verified
            + "</tbody></table><h2>External technical evidence required</h2>"
            "<table><thead><tr><th>Category</th><th>Requirement</th>"
            "<th>Responsible party</th><th>Blocking</th></tr></thead><tbody>"
            + pending
            + "</tbody></table><h2>Downstream readiness</h2><table>"
            "<thead><tr><th>Module</th><th>Concept allowed</th>"
            "<th>Final ready</th><th>Blocking input IDs</th></tr></thead>"
            "<tbody>"
            + downstream
            + "</tbody></table></body></html>",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _checksums(
        paths: dict[str, Path],
        output_path: Path,
    ) -> Path:
        lines = [
            f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}"
            for key, source in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        output_path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def _dossier(
        cls,
        report: dict[str, Any],
        paths: dict[str, Path],
        output_path: Path,
    ) -> Path:
        with zipfile.ZipFile(
            output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                cls._write_bytes(
                    archive,
                    source.name,
                    source.read_bytes(),
                )
            cls._write_bytes(
                archive,
                "VERIFIED_INPUTS_README.txt",
                (
                    "PROJECT-PHOENIX BB35 PILOT 1 VERIFIED INPUTS GATE\n"
                    f"Status: {report['status']}\n"
                    "The 7x10 m, two-storey, 140 m² gross scope is authoritative.\n"
                    "Administrative and baseline evidence is valid.\n"
                    "Final generation remains blocked by external technical evidence.\n"
                    "BB36 remains locked.\n"
                ).encode("utf-8"),
            )
        return output_path

    @staticmethod
    def _write_bytes(
        archive: zipfile.ZipFile,
        name: str,
        data: bytes,
    ) -> None:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)
