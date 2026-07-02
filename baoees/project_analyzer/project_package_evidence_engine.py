from __future__ import annotations

import html
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectPackageEvidenceEngine:
    ENGINE_NAME = "Project Phoenix Project Package Evidence Engine"
    ENGINE_VERSION = "v6.2"

    def __init__(
        self,
        project_output_root: Optional[Union[str, Path]] = None,
    ) -> None:
        if project_output_root:
            self.project_output_root = Path(project_output_root)
        else:
            self.project_output_root = PROJECT_ROOT / "outputs" / "projects"

        self.bib_root = PROJECT_ROOT / "outputs" / "bib"

        self.bron_root = (
            self.project_output_root
            / "Bronvermelding_van_dit_project"
        )

        self.project_report_package_path = (
            self.project_output_root
            / "project_report_bib_package.json"
        )

        self.project_report_docx_path = (
            self.project_output_root
            / "project_report_bib_report.docx"
        )

        self.project_report_pdf_path = (
            self.project_output_root
            / "project_report_bib_report.pdf"
        )

        self.project_report_export_log_path = (
            self.project_output_root
            / "project_report_export_log.json"
        )

        self.project_report_export_dashboard_path = (
            self.project_output_root
            / "project_report_export_dashboard.html"
        )

        self.workflow_log_path = (
            self.project_output_root
            / "project_analyzer_workflow_log.json"
        )

        self.workflow_dashboard_path = (
            self.project_output_root
            / "project_analyzer_workflow_dashboard.html"
        )

        self.aaie_bib_assumptions_path = (
            self.project_output_root
            / "aaie_bib_assumptions.json"
        )

        self.bib_knowledge_index_path = (
            self.bib_root
            / "index"
            / "bib_knowledge_content_index.json"
        )

        self.package_manifest_path = (
            self.project_output_root
            / "project_package_manifest.json"
        )

        self.evidence_log_path = (
            self.project_output_root
            / "project_package_evidence_log.json"
        )

        self.evidence_dashboard_path = (
            self.project_output_root
            / "project_package_evidence_dashboard.html"
        )

        self.bronvermelding_log_path = (
            self.bron_root
            / "bronvermelding_log.json"
        )

        self.bronvermelding_readme_path = (
            self.bron_root
            / "README_Bronvermelding_van_dit_project.txt"
        )

        self.package_zip_path = (
            self.project_output_root
            / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)
        self.bron_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        first_files = self.collect_package_files()
        first_evidence_items = self.build_evidence_items(first_files)

        self.write_json(
            self.bronvermelding_log_path,
            self.build_bronvermelding_log(
                first_evidence_items,
                started_at,
            ),
        )

        self.write_text(
            self.bronvermelding_readme_path,
            self.build_bronvermelding_readme(first_evidence_items),
        )

        files = self.collect_package_files()
        evidence_items = self.build_evidence_items(files)
        manifest = self.build_manifest(
            files,
            evidence_items,
            started_at,
        )

        self.write_json(self.package_manifest_path, manifest)

        self.write_json(
            self.evidence_log_path,
            self.build_evidence_log(
                evidence_items,
                started_at,
            ),
        )

        self.write_text(
            self.evidence_dashboard_path,
            self.build_dashboard(
                manifest,
                evidence_items,
            ),
        )

        final_files = self.collect_package_files()
        final_evidence_items = self.build_evidence_items(final_files)
        final_manifest = self.build_manifest(
            final_files,
            final_evidence_items,
            started_at,
        )

        self.write_json(self.package_manifest_path, final_manifest)

        zip_status = self.write_project_zip(final_files)

        finished_at = datetime.now().isoformat(timespec="seconds")

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "bronvermelding_root": str(self.bron_root),
            "package_manifest_path": str(self.package_manifest_path),
            "evidence_log_path": str(self.evidence_log_path),
            "evidence_dashboard_path": str(self.evidence_dashboard_path),
            "bronvermelding_log_path": str(self.bronvermelding_log_path),
            "bronvermelding_readme_path": str(self.bronvermelding_readme_path),
            "package_zip_path": str(self.package_zip_path),
            "zip_status": zip_status,
            "file_count": len(final_files),
            "evidence_count": len(final_evidence_items),
            "files": final_files,
            "evidence_items": final_evidence_items,
            "next_steps": [
                "Controleer project_package_evidence_dashboard.html.",
                "Controleer project_package_manifest.json.",
                "Controleer Bronvermelding_van_dit_project.",
                "Controleer PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip.",
                "Koppel dit pakket daarna aan het centrale START PROJECTANALYSE dashboard.",
            ],
        }

        self.write_json(self.evidence_log_path, result)

        return result

    def collect_package_files(self) -> List[Dict[str, Any]]:
        candidate_paths = [
            self.project_report_package_path,
            self.project_report_docx_path,
            self.project_report_pdf_path,
            self.project_report_export_log_path,
            self.project_report_export_dashboard_path,
            self.workflow_log_path,
            self.workflow_dashboard_path,
            self.aaie_bib_assumptions_path,
            self.bib_knowledge_index_path,
            self.package_manifest_path,
            self.evidence_log_path,
            self.evidence_dashboard_path,
            self.bronvermelding_log_path,
            self.bronvermelding_readme_path,
            self.package_zip_path,
        ]

        files: List[Dict[str, Any]] = []

        for path in candidate_paths:
            files.append(self.describe_file(path))

        return files

    def describe_file(self, path: Path) -> Dict[str, Any]:
        exists = path.exists()

        if exists:
            stat = path.stat()
            size_bytes = stat.st_size
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(
                timespec="seconds"
            )
        else:
            size_bytes = 0
            modified_at = ""

        return {
            "name": path.name,
            "path": str(path),
            "relative_path": self.safe_relative_path(path),
            "exists": exists,
            "size_bytes": size_bytes,
            "modified_at": modified_at,
            "category": self.detect_category(path),
        }

    def detect_category(self, path: Path) -> str:
        name = path.name.lower()
        suffix = path.suffix.lower()

        if suffix in [".docx", ".pdf"] and "report" in name:
            return "rapportage_export"

        if "export" in name:
            return "export_log"

        if "workflow" in name:
            return "workflow"

        if "aaie" in name:
            return "aaie"

        if "bib" in name:
            return "bib"

        if "evidence" in name:
            return "evidence"

        if "manifest" in name:
            return "manifest"

        if "bronvermelding" in name or "readme" in name:
            return "bronvermelding"

        if suffix == ".zip":
            return "project_package"

        return "overig"

    def build_evidence_items(
        self,
        files: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        evidence_items: List[Dict[str, Any]] = []

        for index, file_item in enumerate(files, start=1):
            evidence_items.append(
                {
                    "evidence_id": f"EV-{index:03d}",
                    "name": file_item.get("name", ""),
                    "category": file_item.get("category", ""),
                    "path": file_item.get("path", ""),
                    "relative_path": file_item.get("relative_path", ""),
                    "exists": file_item.get("exists", False),
                    "size_bytes": file_item.get("size_bytes", 0),
                    "modified_at": file_item.get("modified_at", ""),
                    "source_type": self.source_type_for_category(
                        file_item.get("category", "")
                    ),
                    "reliability": self.reliability_for_file(file_item),
                    "included_in_package": bool(file_item.get("exists", False)),
                }
            )

        return evidence_items

    def source_type_for_category(self, category: str) -> str:
        mapping = {
            "rapportage_export": "gegenereerd_rapport",
            "export_log": "systeemlog_export",
            "workflow": "workflow_output",
            "aaie": "aaie_aannames",
            "bib": "bib_kennisindex",
            "evidence": "evidence_log",
            "manifest": "project_manifest",
            "bronvermelding": "bronvermelding",
            "project_package": "project_zip",
        }

        return mapping.get(category, "projectbestand")

    def reliability_for_file(self, file_item: Dict[str, Any]) -> str:
        if not file_item.get("exists", False):
            return "ontbreekt"

        category = file_item.get("category", "")

        if category in [
            "rapportage_export",
            "workflow",
            "aaie",
            "bib",
            "evidence",
            "manifest",
        ]:
            return "hoog"

        if category in [
            "export_log",
            "bronvermelding",
            "project_package",
        ]:
            return "middel"

        return "basis"

    def build_manifest(
        self,
        files: List[Dict[str, Any]],
        evidence_items: List[Dict[str, Any]],
        started_at: str,
    ) -> Dict[str, Any]:
        existing_files = [item for item in files if item.get("exists", False)]
        missing_files = [item for item in files if not item.get("exists", False)]

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "started_at": started_at,
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "bronvermelding_root": str(self.bron_root),
            "package_zip_path": str(self.package_zip_path),
            "file_count": len(files),
            "existing_file_count": len(existing_files),
            "missing_file_count": len(missing_files),
            "evidence_count": len(evidence_items),
            "files": files,
            "evidence_items": evidence_items,
            "package_policy": {
                "include_reports": True,
                "include_export_logs": True,
                "include_workflow_logs": True,
                "include_bib_index": True,
                "include_aaie_assumptions": True,
                "include_evidence_logs": True,
                "include_bronvermelding": True,
                "include_project_zip": True,
            },
        }

    def build_evidence_log(
        self,
        evidence_items: List[Dict[str, Any]],
        started_at: str,
    ) -> Dict[str, Any]:
        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "STEE / Evidence-log voor Project Phoenix projectpakket.",
            "evidence_count": len(evidence_items),
            "evidence_items": evidence_items,
        }

    def build_bronvermelding_log(
        self,
        evidence_items: List[Dict[str, Any]],
        started_at: str,
    ) -> Dict[str, Any]:
        sources: List[Dict[str, Any]] = []

        for item in evidence_items:
            if item.get("exists", False):
                sources.append(
                    {
                        "bron_id": item.get("evidence_id", ""),
                        "naam": item.get("name", ""),
                        "type": item.get("source_type", ""),
                        "bestand": item.get("relative_path", ""),
                        "datum_tijd": item.get("modified_at", ""),
                        "betrouwbaarheid": item.get("reliability", ""),
                    }
                )

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "map": str(self.bron_root),
            "bron_count": len(sources),
            "bronnen": sources,
        }

    def build_bronvermelding_readme(
        self,
        evidence_items: List[Dict[str, Any]],
    ) -> str:
        lines: List[str] = []

        lines.append("BRONVERMELDING VAN DIT PROJECT")
        lines.append("PROJECT PHOENIX / BAOEES")
        lines.append(f"Versie: {self.ENGINE_VERSION}")
        lines.append("")
        lines.append(
            "Deze map bevat de bronvermelding, evidence-log en verwijzingen naar projectbestanden."
        )
        lines.append("")
        lines.append("Bronnen en bestanden:")
        lines.append("")

        for item in evidence_items:
            if item.get("exists", False):
                lines.append(
                    f"- {item.get('evidence_id', '')}: {item.get('relative_path', '')}"
                )
                lines.append(f"  Type: {item.get('source_type', '')}")
                lines.append(f"  Betrouwbaarheid: {item.get('reliability', '')}")
                lines.append(f"  Gewijzigd: {item.get('modified_at', '')}")
                lines.append("")

        if len(lines) <= 8:
            lines.append("Er zijn nog geen bestaande projectbestanden gevonden.")

        return "\n".join(lines)

    def write_project_zip(self, files: List[Dict[str, Any]]) -> str:
        self.package_zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            self.package_zip_path,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as package_zip:
            for file_item in files:
                if not file_item.get("exists", False):
                    continue

                path = Path(file_item.get("path", ""))

                if not path.exists():
                    continue

                if path.resolve() == self.package_zip_path.resolve():
                    continue

                archive_name = file_item.get("relative_path", path.name)
                package_zip.write(path, archive_name)

        return "OPGESLAGEN"

    def build_dashboard(
        self,
        manifest: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
    ) -> str:
        rows: List[str] = []

        for item in evidence_items:
            rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('evidence_id', ''))}</td>"
                f"<td>{self.esc(item.get('name', ''))}</td>"
                f"<td>{self.esc(item.get('category', ''))}</td>"
                f"<td>{self.esc(item.get('exists', False))}</td>"
                f"<td>{self.esc(item.get('reliability', ''))}</td>"
                "</tr>"
            )

        rows_text = "\n".join(rows)

        html_parts = [
            "<!doctype html>",
            "<html lang=\"nl\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <title>Project Phoenix Evidence v6.2</title>",
            "  <style>",
            "    body { margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }",
            "    main { max-width: 1180px; margin: 0 auto; padding: 32px; }",
            "    section { background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }",
            "    h1, h2 { color: #f8fafc; }",
            "    table { width: 100%; border-collapse: collapse; }",
            "    td, th { border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }",
            "    th { background: #1e293b; }",
            "    code { color: #bfdbfe; }",
            "  </style>",
            "</head>",
            "<body>",
            "<main>",
            "  <section>",
            "    <h1>Project Phoenix Evidence v6.2</h1>",
            f"    <p>Status: {self.esc(manifest.get('status', ''))}</p>",
            "    <p>Bronvermelding en bijlagenpakket zijn gekoppeld aan de projectexport.</p>",
            "  </section>",
            "  <section>",
            "    <h2>Project package</h2>",
            f"    <p>Bestanden totaal: {self.esc(manifest.get('file_count', 0))}</p>",
            f"    <p>Bestaande bestanden: {self.esc(manifest.get('existing_file_count', 0))}</p>",
            f"    <p>Ontbrekende bestanden: {self.esc(manifest.get('missing_file_count', 0))}</p>",
            f"    <p>ZIP: <code>{self.esc(manifest.get('package_zip_path', ''))}</code></p>",
            "  </section>",
            "  <section>",
            "    <h2>Evidence-items</h2>",
            "    <table>",
            "      <tr>",
            "        <th>ID</th>",
            "        <th>Bestand</th>",
            "        <th>Categorie</th>",
            "        <th>Aanwezig</th>",
            "        <th>Betrouwbaarheid</th>",
            "      </tr>",
            f"      {rows_text}",
            "    </table>",
            "  </section>",
            "</main>",
            "</body>",
            "</html>",
        ]

        return "\n".join(html_parts)

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def safe_relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except Exception:
            return str(path)

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


ProjectPackageEvidence = ProjectPackageEvidenceEngine
ProjectEvidenceEngine = ProjectPackageEvidenceEngine
ProjectPackageEngine = ProjectPackageEvidenceEngine


def main() -> None:
    engine = ProjectPackageEvidenceEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()