# PROJECT PHOENIX v6.3 UPDATE
# Automatische update zonder handmatig knip- en plakwerk.
# Plaats dit bestand in C:\BREWSTER-ENGINEERING-WIZARD en voer het uit met:
# powershell -ExecutionPolicy Bypass -File .\PROJECT_PHOENIX_v6_3_update.ps1

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.3 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location
$TargetFile = Join-Path $ProjectRoot "baoees\project_analyzer\project_analyzer_launcher_bridge.py"

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet worden uitgevoerd vanuit de projectmap C:\BREWSTER-ENGINEERING-WIZARD."
}

if (-not (Test-Path (Split-Path $TargetFile))) {
    New-Item -ItemType Directory -Path (Split-Path $TargetFile) -Force | Out-Null
}

if (Test-Path $TargetFile) {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupFile = "$TargetFile.backup_v6_3_$Timestamp"
    Copy-Item $TargetFile $BackupFile -Force
    Write-Host "Backup gemaakt: $BackupFile" -ForegroundColor Yellow
}

$PythonContent = @'
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectAnalyzerLauncherBridge:
    ENGINE_NAME = "Project Phoenix Project Analyzer Launcher Bridge"
    ENGINE_VERSION = "v6.3"

    def __init__(
        self,
        project_output_root: Optional[Union[str, Path]] = None,
    ) -> None:
        if project_output_root:
            self.project_output_root = Path(project_output_root)
        else:
            self.project_output_root = PROJECT_ROOT / "outputs" / "projects"

        self.project_start_dashboard_path = (
            self.project_output_root
            / "project_start_analysis_dashboard.html"
        )

        self.launcher_bridge_log_path = (
            self.project_output_root
            / "project_analyzer_launcher_bridge_log.json"
        )

        self.launcher_bridge_dashboard_path = (
            self.project_output_root
            / "project_analyzer_launcher_bridge_dashboard.html"
        )

        self.project_package_manifest_path = (
            self.project_output_root
            / "project_package_manifest.json"
        )

        self.project_package_evidence_dashboard_path = (
            self.project_output_root
            / "project_package_evidence_dashboard.html"
        )

        self.project_package_evidence_log_path = (
            self.project_output_root
            / "project_package_evidence_log.json"
        )

        self.project_package_zip_path = (
            self.project_output_root
            / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip"
        )

        self.project_report_export_dashboard_path = (
            self.project_output_root
            / "project_report_export_dashboard.html"
        )

        self.project_report_export_log_path = (
            self.project_output_root
            / "project_report_export_log.json"
        )

        self.project_report_docx_path = (
            self.project_output_root
            / "project_report_bib_report.docx"
        )

        self.project_report_pdf_path = (
            self.project_output_root
            / "project_report_bib_report.pdf"
        )

        self.bronvermelding_root = (
            self.project_output_root
            / "Bronvermelding_van_dit_project"
        )

        self.bronvermelding_log_path = (
            self.bronvermelding_root
            / "bronvermelding_log.json"
        )

        self.bronvermelding_readme_path = (
            self.bronvermelding_root
            / "README_Bronvermelding_van_dit_project.txt"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        package_manifest = self.read_json(self.project_package_manifest_path)
        evidence_log = self.read_json(self.project_package_evidence_log_path)
        export_log = self.read_json(self.project_report_export_log_path)
        bronvermelding_log = self.read_json(self.bronvermelding_log_path)

        launcher_items = self.build_launcher_items()

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "project_start_dashboard_path": str(self.project_start_dashboard_path),
            "launcher_bridge_log_path": str(self.launcher_bridge_log_path),
            "launcher_bridge_dashboard_path": str(self.launcher_bridge_dashboard_path),
            "project_package_manifest_path": str(self.project_package_manifest_path),
            "project_package_zip_path": str(self.project_package_zip_path),
            "project_package_evidence_dashboard_path": str(
                self.project_package_evidence_dashboard_path
            ),
            "project_report_export_dashboard_path": str(
                self.project_report_export_dashboard_path
            ),
            "bronvermelding_root": str(self.bronvermelding_root),
            "package_manifest_status": "GELEZEN" if package_manifest else "ONTBREEKT",
            "evidence_log_status": "GELEZEN" if evidence_log else "ONTBREEKT",
            "export_log_status": "GELEZEN" if export_log else "ONTBREEKT",
            "bronvermelding_log_status": (
                "GELEZEN" if bronvermelding_log else "ONTBREEKT"
            ),
            "launcher_item_count": len(launcher_items),
            "launcher_items": launcher_items,
            "next_steps": [
                "Controleer project_start_analysis_dashboard.html.",
                "Controleer project_analyzer_launcher_bridge_dashboard.html.",
                "Controleer projectpakket, evidence, export en bronvermelding.",
                "Koppel daarna deze bridge aan START_PROJECTANALYSE.bat.",
            ],
        }

        dashboard_html = self.build_dashboard(result)

        self.write_json(self.launcher_bridge_log_path, result)
        self.write_text(self.launcher_bridge_dashboard_path, dashboard_html)
        self.write_text(self.project_start_dashboard_path, dashboard_html)

        return result

    def build_launcher_items(self) -> List[Dict[str, Any]]:
        items = [
            {
                "name": "Project Start Analyse Dashboard",
                "path": self.project_start_dashboard_path,
                "category": "start_dashboard",
                "description": "Centraal START PROJECTANALYSE dashboard.",
            },
            {
                "name": "Project Package Manifest",
                "path": self.project_package_manifest_path,
                "category": "project_package",
                "description": "Manifest van alle projectpakketbestanden.",
            },
            {
                "name": "Project Package ZIP",
                "path": self.project_package_zip_path,
                "category": "project_package",
                "description": "Downloadbaar totaalpakket van projectanalyse en rapportage.",
            },
            {
                "name": "Evidence Dashboard",
                "path": self.project_package_evidence_dashboard_path,
                "category": "evidence",
                "description": "Dashboard met evidence-items en pakketstatus.",
            },
            {
                "name": "Evidence Log",
                "path": self.project_package_evidence_log_path,
                "category": "evidence",
                "description": "STEE evidence-log van projectbestanden.",
            },
            {
                "name": "Rapportage Export Dashboard",
                "path": self.project_report_export_dashboard_path,
                "category": "rapportage_export",
                "description": "Dashboard van DOCX/PDF-rapportage-export.",
            },
            {
                "name": "Rapportage Export Log",
                "path": self.project_report_export_log_path,
                "category": "rapportage_export",
                "description": "Logbestand van DOCX/PDF-export.",
            },
            {
                "name": "Projectrapport DOCX",
                "path": self.project_report_docx_path,
                "category": "rapportage_export",
                "description": "Gegenereerd Word-rapport.",
            },
            {
                "name": "Projectrapport PDF",
                "path": self.project_report_pdf_path,
                "category": "rapportage_export",
                "description": "Gegenereerd PDF-rapport.",
            },
            {
                "name": "Bronvermelding Log",
                "path": self.bronvermelding_log_path,
                "category": "bronvermelding",
                "description": "Bronvermelding van dit project.",
            },
            {
                "name": "Bronvermelding README",
                "path": self.bronvermelding_readme_path,
                "category": "bronvermelding",
                "description": "Leesbaar overzicht van bronnen en projectbestanden.",
            },
        ]

        described_items: List[Dict[str, Any]] = []

        for item in items:
            path = Path(item["path"])
            described_items.append(
                {
                    "name": item["name"],
                    "category": item["category"],
                    "description": item["description"],
                    "path": str(path),
                    "relative_path": self.safe_relative_path(path),
                    "exists": path.exists(),
                    "size_bytes": path.stat().st_size if path.exists() else 0,
                    "modified_at": (
                        datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                            timespec="seconds"
                        )
                        if path.exists()
                        else ""
                    ),
                }
            )

        return described_items

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        launcher_items = result.get("launcher_items", [])
        rows: List[str] = []

        for item in launcher_items:
            status = "AANWEZIG" if item.get("exists", False) else "ONTBREEKT"

            rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('name', ''))}</td>"
                f"<td>{self.esc(item.get('category', ''))}</td>"
                f"<td>{self.esc(status)}</td>"
                f"<td><code>{self.esc(item.get('relative_path', ''))}</code></td>"
                f"<td>{self.esc(item.get('description', ''))}</td>"
                "</tr>"
            )

        rows_text = "\n".join(rows)

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix START PROJECTANALYSE v6.3</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f172a;
      color: #e5e7eb;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px;
    }}
    section {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 18px;
    }}
    h1, h2 {{
      color: #f8fafc;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    td, th {{
      border: 1px solid #334155;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #1e293b;
    }}
    code {{
      color: #bfdbfe;
    }}
    .ok {{
      color: #86efac;
      font-weight: bold;
    }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Project Phoenix START PROJECTANALYSE v6.3</h1>
    <p>Status: <span class="ok">{self.esc(result.get("status", ""))}</span></p>
    <p>Het projectpakket, evidence-dashboard, rapportage-export en bronvermelding zijn gekoppeld aan het centrale startdashboard.</p>
  </section>

  <section>
    <h2>Gekoppelde onderdelen</h2>
    <p>Package manifest: {self.esc(result.get("package_manifest_status", ""))}</p>
    <p>Evidence-log: {self.esc(result.get("evidence_log_status", ""))}</p>
    <p>Export-log: {self.esc(result.get("export_log_status", ""))}</p>
    <p>Bronvermelding-log: {self.esc(result.get("bronvermelding_log_status", ""))}</p>
  </section>

  <section>
    <h2>Projectbestanden</h2>
    <table>
      <tr>
        <th>Onderdeel</th>
        <th>Categorie</th>
        <th>Status</th>
        <th>Pad</th>
        <th>Omschrijving</th>
      </tr>
      {rows_text}
    </table>
  </section>
</main>
</body>
</html>
"""

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


ProjectLauncherBridge = ProjectAnalyzerLauncherBridge
ProjectAnalyzerLauncher = ProjectAnalyzerLauncherBridge
LauncherBridge = ProjectAnalyzerLauncherBridge


def main() -> None:
    engine = ProjectAnalyzerLauncherBridge()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()

'@

Set-Content -Path $TargetFile -Value $PythonContent -Encoding UTF8

Write-Host "Bestand geschreven: $TargetFile" -ForegroundColor Green

Write-Host "Syntaxcontrole..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\project_analyzer_launcher_bridge.py

Write-Host "Engine uitvoeren..." -ForegroundColor Cyan
python baoees\project_analyzer\project_analyzer_launcher_bridge.py

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v6.3 UPDATE KLAAR" -ForegroundColor Green
