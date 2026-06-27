from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectAnalyzerLauncherBridge:
    """
    PROJECT PHOENIX / BAOEES
    Project Analyzer Launcher Bridge v4.4

    Doel:
    - Koppelt de Project Analyzer Workflow aan outputs/projects/index.html.
    - Voegt een veilige HTML-sectie toe met vaste markers.
    - Maakt een JSON-logbestand.
    - Wijzigt de launcher zonder bestaande inhoud te verwijderen.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer Launcher Bridge"
    ENGINE_VERSION = "v4.4"

    START_MARKER = "<!-- PROJECT_ANALYZER_WORKFLOW_LAUNCHER_START -->"
    END_MARKER = "<!-- PROJECT_ANALYZER_WORKFLOW_LAUNCHER_END -->"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        launcher_path: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.launcher_path = (
            Path(launcher_path)
            if launcher_path
            else self.project_output_root / "index.html"
        )

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        bridge_log_path = self.project_output_root / "project_analyzer_launcher_bridge_log.json"

        if not self.launcher_path.exists():
            result = {
                "status": "FOUT",
                "engine": self.ENGINE_NAME,
                "engine_version": self.ENGINE_VERSION,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "message": "Launcher index.html bestaat niet.",
                "launcher_path": str(self.launcher_path),
                "bridge_log_path": str(bridge_log_path),
                "warnings": [
                    f"Kan Project Analyzer Workflow niet koppelen, bestand ontbreekt: {self.launcher_path}"
                ],
                "extra_results": extra_results,
            }
            self.write_json(bridge_log_path, result)
            return result

        outputs = self.collect_project_analyzer_outputs()
        launcher_html = self.launcher_path.read_text(encoding="utf-8")
        launcher_section = self.build_launcher_section(outputs)
        updated_html = self.insert_or_replace_section(launcher_html, launcher_section)

        self.launcher_path.write_text(updated_html, encoding="utf-8")

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Project Analyzer Workflow koppelen aan de Project Phoenix Launcher.",
            "launcher_path": str(self.launcher_path),
            "project_output_root": str(self.project_output_root),
            "bridge_log_path": str(bridge_log_path),
            "outputs": outputs,
            "warnings": self.build_warnings(outputs),
            "next_steps": [
                "Open outputs/projects/index.html.",
                "Controleer de sectie PROJECT ANALYZER WORKFLOW.",
                "Controleer of dashboard, log, DOCX en PDF openen.",
                "Koppel deze bridge later aan de centrale Project Phoenix workflow.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(bridge_log_path, result)
        return result

    def collect_project_analyzer_outputs(self) -> List[Dict[str, Any]]:
        files = [
            {
                "label": "Open Project Analyzer Workflow Dashboard",
                "filename": "project_analyzer_workflow_dashboard.html",
                "description": "Hoofddashboard van de volledige Project Analyzer workflow.",
                "type": "HTML dashboard",
            },
            {
                "label": "Open Project Analyzer Workflow Log",
                "filename": "project_analyzer_workflow_log.json",
                "description": "JSON-log van de volledige Project Analyzer workflow.",
                "type": "JSON log",
            },
            {
                "label": "Open Projectrapport DOCX",
                "filename": "project_report_bib_report.docx",
                "description": "Word-export van het automatisch gegenereerde projectrapport.",
                "type": "DOCX rapport",
            },
            {
                "label": "Open Projectrapport PDF",
                "filename": "project_report_bib_report.pdf",
                "description": "PDF-export van het automatisch gegenereerde projectrapport.",
                "type": "PDF rapport",
            },
            {
                "label": "Open Project Report Export Dashboard",
                "filename": "project_report_export_dashboard.html",
                "description": "Dashboard met controle van DOCX/PDF-export.",
                "type": "HTML dashboard",
            },
            {
                "label": "Open Geo/Foundation Analyse",
                "filename": "geo_foundation_bib_analysis.html",
                "description": "Geo- en funderingsanalyse met F1/F2 vergelijking.",
                "type": "HTML analyse",
            },
            {
                "label": "Open AAIE-aannames",
                "filename": "aaie_bib_assumptions.html",
                "description": "AAIE-aannames die automatisch uit de BIB-context komen.",
                "type": "HTML aannames",
            },
            {
                "label": "Open BIB Project Analyzer Context",
                "filename": "project_analyzer_bib_context.html",
                "description": "BIB-context die de Project Analyzer als basis gebruikt.",
                "type": "HTML context",
            },
            {
                "label": "Open Projectrapport pakket JSON",
                "filename": "project_report_bib_package.json",
                "description": "JSON-bronpakket van het projectrapport.",
                "type": "JSON pakket",
            },
        ]

        result = []

        for item in files:
            path = self.project_output_root / item["filename"]

            result.append(
                {
                    "label": item["label"],
                    "filename": item["filename"],
                    "path": str(path),
                    "href": item["filename"],
                    "description": item["description"],
                    "type": item["type"],
                    "exists": path.exists(),
                    "size_bytes": path.stat().st_size if path.exists() else 0,
                }
            )

        return result

    def build_launcher_section(self, outputs: List[Dict[str, Any]]) -> str:
        cards = ""

        for item in outputs:
            exists = item.get("exists", False)
            status_class = "ok" if exists else "warn"
            status_text = "AANWEZIG" if exists else "ONTBREEKT"

            if exists:
                title_html = f'<a href="{self.esc(item.get("href", ""))}">{self.esc(item.get("label", ""))}</a>'
            else:
                title_html = f'<span class="muted">{self.esc(item.get("label", ""))}</span>'

            cards += f"""
            <div class="card">
              <h3>{title_html}</h3>
              <p><span class="badge {status_class}">{status_text}</span></p>
              <p class="muted">{self.esc(item.get("description", ""))}</p>
              <p class="muted"><strong>Type:</strong> {self.esc(item.get("type", ""))}</p>
              <p class="muted"><code>{self.esc(item.get("filename", ""))}</code></p>
            </div>
            """

        return f"""
{self.START_MARKER}
<section style="margin-top:34px;">
  <h2>PROJECT ANALYZER WORKFLOW</h2>
  <p class="muted">
    Centrale Project Phoenix / BAOEES workflow met BIB-context, AAIE-aannames,
    Geo/Foundation analyse, projectrapportage en DOCX/PDF-export.
  </p>

  <div class="grid">
    {cards}
  </div>
</section>
{self.END_MARKER}
"""

    def insert_or_replace_section(self, html_text: str, section: str) -> str:
        if self.START_MARKER in html_text and self.END_MARKER in html_text:
            before = html_text.split(self.START_MARKER)[0]
            after = html_text.split(self.END_MARKER, 1)[1]
            return before + section + after

        if "</main>" in html_text:
            return html_text.replace("</main>", section + "\n</main>", 1)

        if "</body>" in html_text:
            return html_text.replace("</body>", section + "\n</body>", 1)

        return html_text + "\n" + section

    def build_warnings(self, outputs: List[Dict[str, Any]]) -> List[str]:
        warnings = []

        for item in outputs:
            if not item.get("exists"):
                warnings.append(f"Output ontbreekt: {item.get('path')}")

        if not warnings:
            warnings.append("Geen kritieke Project Analyzer Launcher Bridge-waarschuwingen.")

        return warnings

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    bridge = ProjectAnalyzerLauncherBridge()
    result = bridge.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()