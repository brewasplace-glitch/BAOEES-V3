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
    Project Analyzer Launcher Bridge v4.7

    Doel:
    - Koppelt de centrale Project Analyzer Workflow aan outputs/projects/index.html.
    - Toont workflowdashboard, evidence dashboard, manifest, logs, rapporten en ZIP-pakket.
    - Voegt een veilige HTML-sectie toe met vaste markers.
    - Maakt een JSON-logbestand.
    - Wijzigt de launcher zonder bestaande inhoud te verwijderen.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer Launcher Bridge"
    ENGINE_VERSION = "v4.7"

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
            "purpose": "Centrale Project Analyzer Workflow koppelen aan de Project Phoenix Launcher.",
            "launcher_path": str(self.launcher_path),
            "project_output_root": str(self.project_output_root),
            "bridge_log_path": str(bridge_log_path),
            "outputs": outputs,
            "summary": self.build_summary(outputs),
            "warnings": self.build_warnings(outputs),
            "next_steps": [
                "Open outputs/projects/index.html.",
                "Controleer de sectie PROJECT ANALYZER WORKFLOW.",
                "Controleer workflowdashboard, evidence dashboard, manifest, logs, rapporten en ZIP-pakket.",
                "Koppel deze bridge later aan de echte Project Phoenix startknop.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(bridge_log_path, result)
        return result

    def collect_project_analyzer_outputs(self) -> List[Dict[str, Any]]:
        files = [
            {
                "category": "01 Centrale workflow",
                "label": "Open Project Analyzer Workflow Dashboard",
                "filename": "project_analyzer_workflow_dashboard.html",
                "description": "Hoofddashboard van de volledige centrale Project Analyzer Workflow v4.6/v4.7.",
                "type": "HTML dashboard",
                "required": True,
            },
            {
                "category": "01 Centrale workflow",
                "label": "Open Project Analyzer Workflow Log",
                "filename": "project_analyzer_workflow_log.json",
                "description": "JSON-log van de volledige centrale workflow.",
                "type": "JSON log",
                "required": True,
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Evidence Dashboard",
                "filename": "project_package_evidence_dashboard.html",
                "description": "Dashboard van het Project ZIP / Evidence pakket.",
                "type": "HTML dashboard",
                "required": True,
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Manifest",
                "filename": "project_package_manifest.json",
                "description": "Manifest met bestandscontrole, categorieën, hashes en ontbrekende bestanden.",
                "type": "JSON manifest",
                "required": True,
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Evidence Log",
                "filename": "project_package_evidence_log.json",
                "description": "Evidence log van het gegenereerde projectpakket.",
                "type": "JSON evidence log",
                "required": True,
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Download Project ZIP pakket",
                "filename": "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip",
                "description": "Officieel Project Phoenix projectpakket met rapporten, logs, dashboards en evidencebestanden.",
                "type": "ZIP pakket",
                "required": True,
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport DOCX",
                "filename": "project_report_bib_report.docx",
                "description": "Word-export van het automatisch gegenereerde projectrapport.",
                "type": "DOCX rapport",
                "required": True,
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport PDF",
                "filename": "project_report_bib_report.pdf",
                "description": "PDF-export van het automatisch gegenereerde projectrapport.",
                "type": "PDF rapport",
                "required": True,
            },
            {
                "category": "03 Rapportage",
                "label": "Open Project Report Export Dashboard",
                "filename": "project_report_export_dashboard.html",
                "description": "Dashboard met controle van DOCX/PDF-export.",
                "type": "HTML dashboard",
                "required": True,
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport Package JSON",
                "filename": "project_report_bib_package.json",
                "description": "JSON-bronpakket van het projectrapport.",
                "type": "JSON pakket",
                "required": True,
            },
            {
                "category": "04 Analyse",
                "label": "Open Geo/Foundation Analyse",
                "filename": "geo_foundation_bib_analysis.html",
                "description": "Geo- en funderingsanalyse met funderingsvarianten en uitgangspunten.",
                "type": "HTML analyse",
                "required": False,
            },
            {
                "category": "04 Analyse",
                "label": "Open Geo/Foundation Analyse JSON",
                "filename": "geo_foundation_bib_analysis.json",
                "description": "JSON-bronbestand van de geo- en funderingsanalyse.",
                "type": "JSON analyse",
                "required": True,
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open AAIE-aannames",
                "filename": "aaie_bib_assumptions.html",
                "description": "AAIE-aannames die automatisch uit de BIB-context komen.",
                "type": "HTML aannames",
                "required": False,
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open AAIE-aannames JSON",
                "filename": "aaie_bib_assumptions.json",
                "description": "JSON-bronbestand met AAIE-aannames.",
                "type": "JSON aannames",
                "required": True,
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open BIB Project Analyzer Context",
                "filename": "project_analyzer_bib_context.html",
                "description": "BIB-context die de Project Analyzer als basis gebruikt.",
                "type": "HTML context",
                "required": False,
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open BIB Project Analyzer Context JSON",
                "filename": "project_analyzer_bib_context.json",
                "description": "JSON-bronbestand van de BIB-context.",
                "type": "JSON context",
                "required": True,
            },
        ]

        result = []

        for item in files:
            path = self.project_output_root / item["filename"]
            exists = path.exists() and path.is_file()

            result.append(
                {
                    "category": item["category"],
                    "label": item["label"],
                    "filename": item["filename"],
                    "path": str(path),
                    "href": item["filename"],
                    "description": item["description"],
                    "type": item["type"],
                    "required": item["required"],
                    "exists": exists,
                    "size_bytes": path.stat().st_size if exists else 0,
                    "modified_at": (
                        datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
                        if exists
                        else None
                    ),
                }
            )

        return result

    def build_summary(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        required_outputs = [item for item in outputs if item.get("required")]
        existing_outputs = [item for item in outputs if item.get("exists")]
        missing_required = [
            item for item in outputs
            if item.get("required") and not item.get("exists")
        ]

        return {
            "total_outputs": len(outputs),
            "required_outputs": len(required_outputs),
            "existing_outputs": len(existing_outputs),
            "missing_required_outputs": len(missing_required),
            "status": "GEREED" if not missing_required else "WARNING",
        }

    def build_launcher_section(self, outputs: List[Dict[str, Any]]) -> str:
        summary = self.build_summary(outputs)
        grouped_outputs = self.group_outputs_by_category(outputs)

        category_sections = ""

        for category, items in grouped_outputs.items():
            cards = ""

            for item in items:
                exists = item.get("exists", False)
                status_class = "ok" if exists else "warn"
                status_text = "AANWEZIG" if exists else "ONTBREEKT"

                if exists:
                    title_html = (
                        f'<a href="{self.esc(item.get("href", ""))}">'
                        f'{self.esc(item.get("label", ""))}</a>'
                    )
                else:
                    title_html = f'<span class="muted">{self.esc(item.get("label", ""))}</span>'

                cards += f"""
                <div class="card">
                  <h3>{title_html}</h3>
                  <p><span class="badge {status_class}">{status_text}</span></p>
                  <p class="muted">{self.esc(item.get("description", ""))}</p>
                  <p class="muted"><strong>Type:</strong> {self.esc(item.get("type", ""))}</p>
                  <p class="muted"><strong>Bestand:</strong> <code>{self.esc(item.get("filename", ""))}</code></p>
                  <p class="muted"><strong>Bytes:</strong> {self.esc(item.get("size_bytes", 0))}</p>
                </div>
                """

            category_sections += f"""
            <section style="margin-top:24px;">
              <h3>{self.esc(category)}</h3>
              <div class="grid">
                {cards}
              </div>
            </section>
            """

        return f"""
{self.START_MARKER}
<section style="margin-top:34px;">
  <h2>PROJECT ANALYZER WORKFLOW</h2>
  <p class="muted">
    Centrale Project Phoenix / BAOEES workflow met BIB-context, AAIE-aannames,
    Geo/Foundation analyse, projectrapportage, DOCX/PDF-export, Project ZIP,
    manifest en evidence dashboard.
  </p>

  <div class="grid">
    <div class="card">
      <h3>Workflow status</h3>
      <p><span class="badge ok">{self.esc(summary.get("status", ""))}</span></p>
      <p class="muted">Aanwezige outputs: {self.esc(summary.get("existing_outputs", 0))} / {self.esc(summary.get("total_outputs", 0))}</p>
      <p class="muted">Ontbrekende verplichte outputs: {self.esc(summary.get("missing_required_outputs", 0))}</p>
    </div>
    <div class="card">
      <h3>Belangrijkste startpunten</h3>
      <p><a href="project_analyzer_workflow_dashboard.html">Project Analyzer Workflow Dashboard</a></p>
      <p><a href="project_package_evidence_dashboard.html">Project Package Evidence Dashboard</a></p>
      <p><a href="PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip">PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip</a></p>
    </div>
  </div>

  {category_sections}
</section>
{self.END_MARKER}
"""

    def group_outputs_by_category(
        self,
        outputs: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        for item in outputs:
            category = str(item.get("category", "Overig"))

            if category not in grouped:
                grouped[category] = []

            grouped[category].append(item)

        return grouped

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
            if item.get("required") and not item.get("exists"):
                warnings.append(f"Verplichte output ontbreekt: {item.get('path')}")

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