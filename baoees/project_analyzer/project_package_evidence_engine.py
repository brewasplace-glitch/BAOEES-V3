from __future__ import annotations

import hashlib
import html
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectPackageEvidenceEngine:
    """
    PROJECT PHOENIX / BAOEES
    Project Package Evidence Engine v4.5

    Doel:
    - Verzamelt Project Analyzer outputs.
    - Maakt een projectmanifest.
    - Maakt een evidence log.
    - Maakt een HTML evidence dashboard.
    - Maakt een officieel Project ZIP-pakket.
    """

    ENGINE_NAME = "Project Phoenix Project Package Evidence Engine"
    ENGINE_VERSION = "v4.5"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        bib_output_root: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.bib_output_root = (
            Path(bib_output_root)
            if bib_output_root
            else Path("outputs") / "bib"
        )

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        manifest_path = self.project_output_root / "project_package_manifest.json"
        evidence_log_path = self.project_output_root / "project_package_evidence_log.json"
        dashboard_path = self.project_output_root / "project_package_evidence_dashboard.html"
        zip_path = self.project_output_root / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip"

        package_files = self.collect_package_files()
        manifest = self.build_manifest(package_files)

        initial_result = {
            "status": "RUNNING",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Project Analyzer outputs bundelen in Project ZIP en evidencepakket.",
            "project_output_root": str(self.project_output_root),
            "bib_output_root": str(self.bib_output_root),
            "manifest_path": str(manifest_path),
            "evidence_log_path": str(evidence_log_path),
            "dashboard_path": str(dashboard_path),
            "zip_path": str(zip_path),
            "manifest": manifest,
            "warnings": self.build_warnings(manifest),
            "extra_results": extra_results,
        }

        self.write_json(manifest_path, manifest)
        self.write_json(evidence_log_path, initial_result)
        dashboard_path.write_text(
            self.build_html_dashboard(initial_result),
            encoding="utf-8",
        )

        final_files = self.collect_package_files()
        zip_result = self.build_zip_package(zip_path, final_files)
        final_manifest = self.build_manifest(self.collect_package_files())

        result = {
            "status": self.determine_status(final_manifest, zip_result),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Project Analyzer outputs gebundeld in Project ZIP en evidencepakket.",
            "project_output_root": str(self.project_output_root),
            "bib_output_root": str(self.bib_output_root),
            "outputs": {
                "manifest_path": str(manifest_path),
                "evidence_log_path": str(evidence_log_path),
                "dashboard_path": str(dashboard_path),
                "zip_path": str(zip_path),
            },
            "zip_result": zip_result,
            "manifest": final_manifest,
            "warnings": self.build_warnings(final_manifest),
            "next_steps": [
                "Open project_package_evidence_dashboard.html.",
                "Controleer PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip.",
                "Controleer of DOCX, PDF, workflow-log en dashboards in het ZIP-pakket zitten.",
                "Koppel deze engine later aan de centrale Project Phoenix workflow.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(manifest_path, final_manifest)
        self.write_json(evidence_log_path, result)
        dashboard_path.write_text(
            self.build_html_dashboard(result),
            encoding="utf-8",
        )

        return result

    def collect_package_files(self) -> List[Dict[str, Any]]:
        file_specs = [
            {
                "category": "workflow",
                "label": "Project Analyzer Workflow Dashboard",
                "path": self.project_output_root / "project_analyzer_workflow_dashboard.html",
                "required": True,
            },
            {
                "category": "workflow",
                "label": "Project Analyzer Workflow Log",
                "path": self.project_output_root / "project_analyzer_workflow_log.json",
                "required": True,
            },
            {
                "category": "report",
                "label": "Projectrapport DOCX",
                "path": self.project_output_root / "project_report_bib_report.docx",
                "required": True,
            },
            {
                "category": "report",
                "label": "Projectrapport PDF",
                "path": self.project_output_root / "project_report_bib_report.pdf",
                "required": True,
            },
            {
                "category": "report",
                "label": "Projectrapport HTML",
                "path": self.project_output_root / "project_report_bib_report.html",
                "required": False,
            },
            {
                "category": "report",
                "label": "Projectrapport Markdown",
                "path": self.project_output_root / "project_report_bib_report.md",
                "required": False,
            },
            {
                "category": "report",
                "label": "Projectrapport Package JSON",
                "path": self.project_output_root / "project_report_bib_package.json",
                "required": True,
            },
            {
                "category": "export",
                "label": "Project Report Export Dashboard",
                "path": self.project_output_root / "project_report_export_dashboard.html",
                "required": True,
            },
            {
                "category": "export",
                "label": "Project Report Export Log",
                "path": self.project_output_root / "project_report_export_log.json",
                "required": True,
            },
            {
                "category": "geo_foundation",
                "label": "Geo/Foundation Analyse HTML",
                "path": self.project_output_root / "geo_foundation_bib_analysis.html",
                "required": False,
            },
            {
                "category": "geo_foundation",
                "label": "Geo/Foundation Analyse JSON",
                "path": self.project_output_root / "geo_foundation_bib_analysis.json",
                "required": True,
            },
            {
                "category": "aaie",
                "label": "AAIE BIB Assumptions HTML",
                "path": self.project_output_root / "aaie_bib_assumptions.html",
                "required": False,
            },
            {
                "category": "aaie",
                "label": "AAIE BIB Assumptions JSON",
                "path": self.project_output_root / "aaie_bib_assumptions.json",
                "required": True,
            },
            {
                "category": "bib_context",
                "label": "Project Analyzer BIB Context HTML",
                "path": self.project_output_root / "project_analyzer_bib_context.html",
                "required": False,
            },
            {
                "category": "bib_context",
                "label": "Project Analyzer BIB Context JSON",
                "path": self.project_output_root / "project_analyzer_bib_context.json",
                "required": True,
            },
            {
                "category": "launcher",
                "label": "Project Phoenix Launcher",
                "path": self.project_output_root / "index.html",
                "required": True,
            },
            {
                "category": "launcher",
                "label": "Project Analyzer Launcher Bridge Log",
                "path": self.project_output_root / "project_analyzer_launcher_bridge_log.json",
                "required": True,
            },
            {
                "category": "bib_bridge",
                "label": "BIB Project Analyzer Bridge",
                "path": self.bib_output_root / "bib_project_analyzer_bridge.json",
                "required": False,
            },
        ]

        result = []

        for spec in file_specs:
            path = Path(spec["path"])
            exists = path.exists() and path.is_file()

            result.append(
                {
                    "category": spec["category"],
                    "label": spec["label"],
                    "path": str(path),
                    "relative_path": self.safe_relative(path),
                    "required": spec["required"],
                    "exists": exists,
                    "size_bytes": path.stat().st_size if exists else 0,
                    "sha256": self.sha256(path) if exists else None,
                    "modified_at": (
                        datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
                        if exists
                        else None
                    ),
                }
            )

        return result

    def build_manifest(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        existing_files = [item for item in files if item.get("exists")]
        missing_required = [
            item for item in files
            if item.get("required") and not item.get("exists")
        ]

        categories: Dict[str, Dict[str, Any]] = {}

        for item in files:
            category = item.get("category", "unknown")

            if category not in categories:
                categories[category] = {
                    "category": category,
                    "total": 0,
                    "existing": 0,
                    "missing": 0,
                    "size_bytes": 0,
                }

            categories[category]["total"] += 1

            if item.get("exists"):
                categories[category]["existing"] += 1
                categories[category]["size_bytes"] += int(item.get("size_bytes") or 0)
            else:
                categories[category]["missing"] += 1

        return {
            "status": "GEREED" if not missing_required else "WARNING",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "total_files": len(files),
                "existing_files": len(existing_files),
                "missing_required_files": len(missing_required),
                "total_size_bytes": sum(
                    int(item.get("size_bytes") or 0)
                    for item in existing_files
                ),
            },
            "categories": list(categories.values()),
            "files": files,
            "missing_required_files": missing_required,
        }

    def build_zip_package(
        self,
        zip_path: Path,
        files: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        included = []
        skipped = []

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as package_zip:
            for item in files:
                path = Path(item["path"])

                if not item.get("exists"):
                    skipped.append(
                        {
                            "path": str(path),
                            "reason": "bestand ontbreekt",
                        }
                    )
                    continue

                if path.resolve() == zip_path.resolve():
                    skipped.append(
                        {
                            "path": str(path),
                            "reason": "ZIP-bestand zelf wordt niet toegevoegd",
                        }
                    )
                    continue

                archive_name = Path("project_package") / item.get("category", "misc") / path.name
                package_zip.write(path, archive_name.as_posix())

                included.append(
                    {
                        "source_path": str(path),
                        "archive_name": archive_name.as_posix(),
                        "size_bytes": path.stat().st_size,
                        "sha256": self.sha256(path),
                    }
                )

        return {
            "status": "OPGESLAGEN",
            "zip_path": str(zip_path),
            "exists": zip_path.exists(),
            "size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
            "included_count": len(included),
            "skipped_count": len(skipped),
            "included_files": included,
            "skipped_files": skipped,
        }

    def determine_status(
        self,
        manifest: Dict[str, Any],
        zip_result: Dict[str, Any],
    ) -> str:
        if zip_result.get("status") != "OPGESLAGEN":
            return "FAILED"

        if not zip_result.get("exists"):
            return "FAILED"

        if manifest.get("status") == "WARNING":
            return "WARNING"

        return "OPGESLAGEN"

    def build_warnings(self, manifest: Dict[str, Any]) -> List[str]:
        warnings = []

        for item in manifest.get("missing_required_files", []):
            warnings.append(f"Verplicht bestand ontbreekt: {item.get('path')}")

        if not warnings:
            warnings.append("Geen kritieke Project Package Evidence-waarschuwingen.")

        return warnings

    def build_html_dashboard(self, result: Dict[str, Any]) -> str:
        manifest = result.get("manifest", {})
        summary = manifest.get("summary", {})
        zip_result = result.get("zip_result", {})
        outputs = result.get("outputs", {})
        files = manifest.get("files", [])
        categories = manifest.get("categories", [])
        warnings = result.get("warnings", [])

        category_rows = ""

        for category in categories:
            category_rows += (
                "<tr>"
                f"<td>{self.esc(category.get('category', ''))}</td>"
                f"<td>{self.esc(category.get('total', ''))}</td>"
                f"<td>{self.esc(category.get('existing', ''))}</td>"
                f"<td>{self.esc(category.get('missing', ''))}</td>"
                f"<td>{self.esc(category.get('size_bytes', ''))}</td>"
                "</tr>"
            )

        file_rows = ""

        for item in files:
            file_rows += (
                "<tr>"
                f"<td>{self.esc(item.get('category', ''))}</td>"
                f"<td>{self.esc(item.get('label', ''))}</td>"
                f"<td>{self.esc(item.get('exists', ''))}</td>"
                f"<td>{self.esc(item.get('size_bytes', ''))}</td>"
                f"<td><code>{self.esc(item.get('relative_path', ''))}</code></td>"
                "</tr>"
            )

        warning_items = ""

        for warning in warnings:
            warning_items += f"<li>{self.esc(warning)}</li>"

        zip_path = outputs.get("zip_path") or zip_result.get("zip_path", "")
        zip_name = Path(zip_path).name if zip_path else ""

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Package Evidence Dashboard</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #050816;
      color: #f8fafc;
      line-height: 1.5;
    }}
    header {{
      padding: 34px 42px;
      background: #0f172a;
      border-bottom: 1px solid #334155;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      margin-top: 18px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0f172a;
      color: #bfdbfe;
    }}
    a {{
      color: #93c5fd;
    }}
    code {{
      color: #cbd5e1;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PACKAGE EVIDENCE DASHBOARD</h1>
    <p>Project Phoenix / BAOEES Project ZIP, manifest en evidence log.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Bestanden</h3>
        <p>{self.esc(summary.get("existing_files", 0))} aanwezig / {self.esc(summary.get("total_files", 0))} totaal</p>
      </div>
      <div class="card">
        <h3>Project ZIP</h3>
        <p><a href="{self.esc(zip_name)}">{self.esc(zip_name)}</a></p>
        <p class="muted">{self.esc(zip_result.get("size_bytes", 0))} bytes</p>
      </div>
      <div class="card">
        <h3>Manifest</h3>
        <p class="muted">{self.esc(outputs.get("manifest_path", ""))}</p>
      </div>
    </section>

    <h2>Categorieën</h2>
    <table>
      <thead>
        <tr>
          <th>Categorie</th>
          <th>Totaal</th>
          <th>Aanwezig</th>
          <th>Ontbreekt</th>
          <th>Bytes</th>
        </tr>
      </thead>
      <tbody>
        {category_rows}
      </tbody>
    </table>

    <h2>Bestanden</h2>
    <table>
      <thead>
        <tr>
          <th>Categorie</th>
          <th>Label</th>
          <th>Bestaat</th>
          <th>Bytes</th>
          <th>Pad</th>
        </tr>
      </thead>
      <tbody>
        {file_rows}
      </tbody>
    </table>

    <h2>Waarschuwingen</h2>
    <ul>
      {warning_items}
    </ul>
  </main>
</body>
</html>
"""

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    def safe_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except Exception:
            return path.as_posix()

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = ProjectPackageEvidenceEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()