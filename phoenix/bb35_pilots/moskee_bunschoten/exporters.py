"""BB35 Pilot 1 baseline JSON, CSV, HTML and evidence exports."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from pathlib import Path
from typing import Any


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class MoskeeBunschotenPilotExporter:
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
                root / "bb35_pilot_1_baseline_report.json",
            ),
            "evidence": self._csv(
                report["evidence_results"],
                root / "source_evidence_register.csv",
                [
                    "evidence_id",
                    "file_name",
                    "relative_path",
                    "role",
                    "available",
                    "sha256_valid",
                    "expected_sha256",
                    "actual_sha256",
                ],
            ),
            "deliverables": self._csv(
                report["commercial_deliverables"],
                root / "commercial_deliverable_readiness.csv",
                [
                    "deliverable_id",
                    "name",
                    "readiness",
                    "ready",
                    "available_evidence",
                    "remaining_work",
                ],
            ),
            "issues": self._csv(
                report["issues"],
                root / "pilot_blockers_and_issues.csv",
                [
                    "code",
                    "severity",
                    "blocking",
                    "source",
                    "message",
                ],
            ),
            "decisions": self._json(
                {
                    "pilot_id": report["pilot_id"],
                    "strategic_decisions": report[
                        "strategic_decisions"
                    ],
                },
                root / "strategic_decision_register.json",
            ),
            "html": self._html(
                report,
                root / "bb35_pilot_1_status.html",
            ),
        }
        paths["checksums"] = self._checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self._dossier(
            report,
            paths,
            root / "bb35_pilot_1_baseline_dossier.zip",
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
        deliverables = "".join(
            "<tr>"
            f"<td>{html.escape(item['name'])}</td>"
            f"<td>{html.escape(item['readiness'])}</td>"
            f"<td>{'yes' if item['ready'] else 'no'}</td>"
            f"<td>{html.escape('; '.join(item['remaining_work']))}</td>"
            "</tr>"
            for item in report["commercial_deliverables"]
        )
        issues = "".join(
            "<tr>"
            f"<td>{html.escape(item['severity'])}</td>"
            f"<td>{'yes' if item['blocking'] else 'no'}</td>"
            f"<td>{html.escape(item['message'])}</td>"
            "</tr>"
            for item in report["issues"]
        )
        path.write_text(
            "<!doctype html><html lang=\"nl\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(report['pilot_name'])}</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:1100px;"
            "margin:36px auto;color:#222}h1{border-bottom:3px solid #222;"
            "padding-bottom:8px}.status{padding:14px;border:1px solid #aaa;"
            "background:#f4f4f4}table{border-collapse:collapse;width:100%;"
            "margin:16px 0}th,td{border:1px solid #bbb;padding:7px;"
            "text-align:left;vertical-align:top}th{background:#263238;color:white}"
            "</style></head><body>"
            f"<h1>{html.escape(report['pilot_name'])}</h1>"
            "<div class=\"status\">"
            f"<strong>Status:</strong> {html.escape(report['status'])}<br>"
            f"<strong>Project:</strong> {html.escape(report['project_name'])}<br>"
            f"<strong>Adres:</strong> {html.escape(report['project_address'])}<br>"
            f"<strong>Geldig bronbewijs:</strong> "
            f"{report['source_evidence_valid_count']}/"
            f"{report['source_evidence_count']}<br>"
            f"<strong>Blokkerende punten:</strong> "
            f"{report['blocking_issue_count']}<br>"
            "<strong>BB36 ontgrendelen:</strong> nee"
            "</div><h2>Commerciële leveringsonderdelen</h2>"
            "<table><thead><tr><th>Onderdeel</th><th>Status</th>"
            "<th>Gereed</th><th>Resterend werk</th></tr></thead><tbody>"
            + deliverables
            + "</tbody></table><h2>Blokkades en bevindingen</h2>"
            "<table><thead><tr><th>Ernst</th><th>Blokkerend</th>"
            "<th>Bevinding</th></tr></thead><tbody>"
            + issues
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
                "PILOT_README.txt",
                (
                    "PROJECT-PHOENIX BB35 PILOT 1 — MOSKEE BUNSCHOTEN\n"
                    f"Status: {report['status']}\n"
                    "The real-project evidence baseline is valid.\n"
                    "The pilot is not completed and BB36 remains locked.\n"
                    "First gate: resolve the authoritative expansion scope.\n"
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
