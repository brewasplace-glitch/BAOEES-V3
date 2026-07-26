"""Dependency-free BB31-BB36 dashboard, gate matrix and dossier exports."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from pathlib import Path
from typing import Any


_FIXED_TIME = (2020, 1, 1, 0, 0, 0)


class CommercialReleaseMasterpackExporter:
    def export_all(
        self,
        report: dict[str, Any],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "json": self.export_json(
                report,
                root / "commercial_release_masterpack_report.json",
            ),
            "csv": self.export_gate_csv(
                report,
                root / "commercial_release_gate_matrix.csv",
            ),
            "html": self.export_dashboard(
                report,
                root / "phoenix_commercial_release_dashboard.html",
            ),
        }
        paths["checksums"] = self.export_checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self.export_dossier(
            report,
            paths,
            root / "commercial_release_masterpack_dossier.zip",
        )
        return paths

    @staticmethod
    def export_json(report: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def export_gate_csv(report: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["build_block", "passed", "meaning"],
            )
            writer.writeheader()
            meanings = {
                "BB31": "Commercial Product Shell",
                "BB32": "Autonomous Building Package Generator",
                "BB33": "Security & Project Data Protection",
                "BB34": "Installer, Updates, Licensing & Release Candidate",
                "BB35": "Real Project Validation",
                "BB36": "Commercial Production Release",
            }
            for block, passed in sorted(report["block_status"].items()):
                writer.writerow({
                    "build_block": block,
                    "passed": passed,
                    "meaning": meanings[block],
                })
        return path

    @staticmethod
    def export_dashboard(report: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(block)}</td>"
            f"<td>{'PASSED' if passed else 'LOCKED/PENDING'}</td>"
            "</tr>"
            for block, passed in sorted(report["block_status"].items())
        )
        status = (
            "Framework installed; real-pilot validation pending."
            if report["framework_installed"] and report["pilot_validation_pending"]
            else "Review gate matrix."
        )
        path.write_text(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>Phoenix Commercial Release Dashboard</title>"
            "<style>body{font-family:Arial,sans-serif;max-width:950px;margin:40px auto;"
            "color:#222}h1{border-bottom:4px solid #222;padding-bottom:8px}"
            ".status{padding:16px;border:1px solid #aaa;background:#f3f3f3}"
            "table{border-collapse:collapse;width:100%;margin-top:22px}"
            "th,td{border:1px solid #bbb;padding:9px;text-align:left}"
            "th{background:#1f4e78;color:white}</style></head><body>"
            "<h1>PROJECT-PHOENIX Commercial Release</h1>"
            f"<div class=\"status\"><strong>Status:</strong> {html.escape(status)}<br>"
            f"<strong>Next action:</strong> {html.escape(report['next_required_action'])}</div>"
            "<table><thead><tr><th>Build block</th><th>Gate status</th></tr>"
            "</thead><tbody>"
            + rows
            + "</tbody></table></body></html>",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def export_checksums(
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        lines = [
            f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}"
            for key, source in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_dossier(
        self,
        report: dict[str, Any],
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                self._write(archive, source.name, source.read_bytes())
            self._write(
                archive,
                "PACKAGE_README.txt",
                (
                    "PROJECT-PHOENIX BB31-BB36 COMMERCIAL RELEASE MASTERPACK\n"
                    f"Framework installed: {report['framework_installed']}\n"
                    f"BB35 pilot validation pending: {report['pilot_validation_pending']}\n"
                    f"BB36 production release locked: {report['production_release_locked']}\n"
                    "The software framework is installed, but production release may not "
                    "be declared until real-project evidence passes BB35.\n"
                ).encode("utf-8"),
            )
        return path

    @staticmethod
    def _write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(name, _FIXED_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)
