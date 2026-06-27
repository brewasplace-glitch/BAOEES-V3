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
    Project Analyzer Launcher Bridge v5.3

    Doel:
    - Maakt van de launcher een professioneler Home Dashboard.
    - Zet START PROJECTANALYSE bovenaan als hoofdactie.
    - Toont projectstatus, laatste run-informatie en huidig project.
    - Toont duidelijke instructies voor START_PROJECTANALYSE.bat.
    - Toont startdashboard, startlog, workflowdashboard, evidence dashboard,
      manifest, rapporten en ZIP-pakket.
    - Bereidt de latere BIB Import Wizard / Knowledge Library Builder voor.
    - Voegt een veilige HTML-sectie toe met vaste markers.
    - Maakt een JSON-logbestand.
    - Wijzigt de launcher zonder bestaande inhoud te verwijderen.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer Launcher Bridge"
    ENGINE_VERSION = "v5.3"

    START_MARKER = "<!-- PROJECT_ANALYZER_WORKFLOW_LAUNCHER_START -->"
    END_MARKER = "<!-- PROJECT_ANALYZER_WORKFLOW_LAUNCHER_END -->"

    START_COMMAND = "python -m baoees.project_analyzer.project_start_analysis_engine"
    BAT_COMMAND = ".\\START_PROJECTANALYSE.bat"
    BAT_FILE = "START_PROJECTANALYSE.bat"
    PS1_FILE = "START_PROJECTANALYSE.ps1"

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
                    f"Kan START PROJECTANALYSE niet koppelen, bestand ontbreekt: {self.launcher_path}"
                ],
                "extra_results": extra_results,
            }
            self.write_json(bridge_log_path, result)
            return result

        outputs = self.collect_project_analyzer_outputs()
        summary = self.build_summary(outputs)
        latest_run = self.build_latest_run_info()
        current_project = self.build_current_project_info()
        next_phase = self.build_next_phase_info()

        launcher_html = self.launcher_path.read_text(encoding="utf-8")
        launcher_section = self.build_launcher_section(
            outputs=outputs,
            summary=summary,
            latest_run=latest_run,
            current_project=current_project,
            next_phase=next_phase,
        )
        updated_html = self.insert_or_replace_section(launcher_html, launcher_section)

        self.launcher_path.write_text(updated_html, encoding="utf-8")

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Launcher/Home Dashboard professionaliseren met projectstatus, laatste run en huidig project.",
            "launcher_path": str(self.launcher_path),
            "project_output_root": str(self.project_output_root),
            "bridge_log_path": str(bridge_log_path),
            "start_command": self.START_COMMAND,
            "bat_command": self.BAT_COMMAND,
            "bat_file": str(PROJECT_ROOT / self.BAT_FILE),
            "ps1_file": str(PROJECT_ROOT / self.PS1_FILE),
            "summary": summary,
            "latest_run": latest_run,
            "current_project": current_project,
            "next_phase": next_phase,
            "outputs": outputs,
            "warnings": self.build_warnings(outputs),
            "next_steps": [
                "Open outputs/projects/index.html.",
                "Controleer dat START PROJECTANALYSE bovenaan als hoofdactie zichtbaar is.",
                "Controleer projectstatus, laatste run-informatie en huidig project.",
                "Controleer snelle links naar dashboard, rapporten, evidence en Project ZIP.",
                "Gebruik START_PROJECTANALYSE.bat als lokale Windows-startknop.",
                "Bereid daarna de BIB Import Wizard / Knowledge Library Builder voor.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(bridge_log_path, result)
        return result

    def collect_project_analyzer_outputs(self) -> List[Dict[str, Any]]:
        files = [
            {
                "category": "00 Lokale startbestanden",
                "label": "START_PROJECTANALYSE.bat",
                "filename": "START_PROJECTANALYSE.bat",
                "path": PROJECT_ROOT / "START_PROJECTANALYSE.bat",
                "href": "../../START_PROJECTANALYSE.bat",
                "description": "Dubbelklikbaar Windows-startbestand voor START PROJECTANALYSE.",
                "type": "Windows BAT startbestand",
                "required": True,
                "priority": "high",
            },
            {
                "category": "00 Lokale startbestanden",
                "label": "START_PROJECTANALYSE.ps1",
                "filename": "START_PROJECTANALYSE.ps1",
                "path": PROJECT_ROOT / "START_PROJECTANALYSE.ps1",
                "href": "../../START_PROJECTANALYSE.ps1",
                "description": "PowerShell-startscript dat de Python-engine uitvoert en dashboards opent.",
                "type": "PowerShell startscript",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "00 START PROJECTANALYSE",
                "label": "Open Start Projectanalyse Dashboard",
                "filename": "project_start_analysis_dashboard.html",
                "path": self.project_output_root / "project_start_analysis_dashboard.html",
                "href": "project_start_analysis_dashboard.html",
                "description": "Hoofddashboard van de centrale START PROJECTANALYSE-run.",
                "type": "HTML startdashboard",
                "required": True,
                "priority": "high",
            },
            {
                "category": "00 START PROJECTANALYSE",
                "label": "Open Start Projectanalyse Log",
                "filename": "project_start_analysis_log.json",
                "path": self.project_output_root / "project_start_analysis_log.json",
                "href": "project_start_analysis_log.json",
                "description": "JSON-log van de centrale START PROJECTANALYSE-run.",
                "type": "JSON startlog",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "00 START PROJECTANALYSE",
                "label": "Open lokale run-log",
                "filename": "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt",
                "path": self.project_output_root / "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt",
                "href": "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt",
                "description": "Lokale BAT/PowerShell-runlog van START PROJECTANALYSE.",
                "type": "TXT run-log",
                "required": False,
                "priority": "normal",
            },
            {
                "category": "01 Centrale workflow",
                "label": "Open Project Analyzer Workflow Dashboard",
                "filename": "project_analyzer_workflow_dashboard.html",
                "path": self.project_output_root / "project_analyzer_workflow_dashboard.html",
                "href": "project_analyzer_workflow_dashboard.html",
                "description": "Hoofddashboard van de volledige centrale Project Analyzer Workflow.",
                "type": "HTML dashboard",
                "required": True,
                "priority": "high",
            },
            {
                "category": "01 Centrale workflow",
                "label": "Open Project Analyzer Workflow Log",
                "filename": "project_analyzer_workflow_log.json",
                "path": self.project_output_root / "project_analyzer_workflow_log.json",
                "href": "project_analyzer_workflow_log.json",
                "description": "JSON-log van de volledige centrale workflow.",
                "type": "JSON log",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Evidence Dashboard",
                "filename": "project_package_evidence_dashboard.html",
                "path": self.project_output_root / "project_package_evidence_dashboard.html",
                "href": "project_package_evidence_dashboard.html",
                "description": "Dashboard van het Project ZIP / Evidence pakket.",
                "type": "HTML dashboard",
                "required": True,
                "priority": "high",
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Manifest",
                "filename": "project_package_manifest.json",
                "path": self.project_output_root / "project_package_manifest.json",
                "href": "project_package_manifest.json",
                "description": "Manifest met bestandscontrole, categorieën, hashes en ontbrekende bestanden.",
                "type": "JSON manifest",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Open Project Package Evidence Log",
                "filename": "project_package_evidence_log.json",
                "path": self.project_output_root / "project_package_evidence_log.json",
                "href": "project_package_evidence_log.json",
                "description": "Evidence log van het gegenereerde projectpakket.",
                "type": "JSON evidence log",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "02 Project Package Evidence",
                "label": "Download Project ZIP pakket",
                "filename": "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip",
                "path": self.project_output_root / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip",
                "href": "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip",
                "description": "Officieel Project Phoenix projectpakket met rapporten, logs, dashboards en evidencebestanden.",
                "type": "ZIP pakket",
                "required": True,
                "priority": "high",
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport DOCX",
                "filename": "project_report_bib_report.docx",
                "path": self.project_output_root / "project_report_bib_report.docx",
                "href": "project_report_bib_report.docx",
                "description": "Word-export van het automatisch gegenereerde projectrapport.",
                "type": "DOCX rapport",
                "required": True,
                "priority": "high",
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport PDF",
                "filename": "project_report_bib_report.pdf",
                "path": self.project_output_root / "project_report_bib_report.pdf",
                "href": "project_report_bib_report.pdf",
                "description": "PDF-export van het automatisch gegenereerde projectrapport.",
                "type": "PDF rapport",
                "required": True,
                "priority": "high",
            },
            {
                "category": "03 Rapportage",
                "label": "Open Project Report Export Dashboard",
                "filename": "project_report_export_dashboard.html",
                "path": self.project_output_root / "project_report_export_dashboard.html",
                "href": "project_report_export_dashboard.html",
                "description": "Dashboard met controle van DOCX/PDF-export.",
                "type": "HTML dashboard",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "03 Rapportage",
                "label": "Open Projectrapport Package JSON",
                "filename": "project_report_bib_package.json",
                "path": self.project_output_root / "project_report_bib_package.json",
                "href": "project_report_bib_package.json",
                "description": "JSON-bronpakket van het projectrapport.",
                "type": "JSON pakket",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "04 Analyse",
                "label": "Open Geo/Foundation Analyse",
                "filename": "geo_foundation_bib_analysis.html",
                "path": self.project_output_root / "geo_foundation_bib_analysis.html",
                "href": "geo_foundation_bib_analysis.html",
                "description": "Geo- en funderingsanalyse met funderingsvarianten en uitgangspunten.",
                "type": "HTML analyse",
                "required": False,
                "priority": "normal",
            },
            {
                "category": "04 Analyse",
                "label": "Open Geo/Foundation Analyse JSON",
                "filename": "geo_foundation_bib_analysis.json",
                "path": self.project_output_root / "geo_foundation_bib_analysis.json",
                "href": "geo_foundation_bib_analysis.json",
                "description": "JSON-bronbestand van de geo- en funderingsanalyse.",
                "type": "JSON analyse",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open AAIE-aannames",
                "filename": "aaie_bib_assumptions.html",
                "path": self.project_output_root / "aaie_bib_assumptions.html",
                "href": "aaie_bib_assumptions.html",
                "description": "AAIE-aannames die automatisch uit de BIB-context komen.",
                "type": "HTML aannames",
                "required": False,
                "priority": "normal",
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open AAIE-aannames JSON",
                "filename": "aaie_bib_assumptions.json",
                "path": self.project_output_root / "aaie_bib_assumptions.json",
                "href": "aaie_bib_assumptions.json",
                "description": "JSON-bronbestand met AAIE-aannames.",
                "type": "JSON aannames",
                "required": True,
                "priority": "normal",
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open BIB Project Analyzer Context",
                "filename": "project_analyzer_bib_context.html",
                "path": self.project_output_root / "project_analyzer_bib_context.html",
                "href": "project_analyzer_bib_context.html",
                "description": "BIB-context die de Project Analyzer als basis gebruikt.",
                "type": "HTML context",
                "required": False,
                "priority": "normal",
            },
            {
                "category": "05 AAIE en BIB",
                "label": "Open BIB Project Analyzer Context JSON",
                "filename": "project_analyzer_bib_context.json",
                "path": self.project_output_root / "project_analyzer_bib_context.json",
                "href": "project_analyzer_bib_context.json",
                "description": "JSON-bronbestand van de BIB-context.",
                "type": "JSON context",
                "required": True,
                "priority": "normal",
            },
        ]

        result = []

        for item in files:
            path = Path(item["path"])
            exists = path.exists() and path.is_file()

            result.append(
                {
                    "category": item["category"],
                    "label": item["label"],
                    "filename": item["filename"],
                    "path": str(path),
                    "relative_path": self.safe_relative(path),
                    "href": item["href"],
                    "description": item["description"],
                    "type": item["type"],
                    "required": item["required"],
                    "priority": item["priority"],
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
        high_priority_outputs = [
            item for item in outputs
            if item.get("priority") == "high"
        ]
        existing_high_priority_outputs = [
            item for item in high_priority_outputs
            if item.get("exists")
        ]

        return {
            "total_outputs": len(outputs),
            "required_outputs": len(required_outputs),
            "existing_outputs": len(existing_outputs),
            "missing_required_outputs": len(missing_required),
            "high_priority_outputs": len(high_priority_outputs),
            "existing_high_priority_outputs": len(existing_high_priority_outputs),
            "status": "GEREED" if not missing_required else "WARNING",
        }

    def build_latest_run_info(self) -> Dict[str, Any]:
        start_log_path = self.project_output_root / "project_start_analysis_log.json"
        workflow_log_path = self.project_output_root / "project_analyzer_workflow_log.json"
        evidence_log_path = self.project_output_root / "project_package_evidence_log.json"
        local_run_log_path = self.project_output_root / "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt"

        start_log = self.read_json(start_log_path)
        workflow_log = self.read_json(workflow_log_path)
        evidence_log = self.read_json(evidence_log_path)

        latest_run = {
            "status": start_log.get("status") or workflow_log.get("status") or "ONBEKEND",
            "engine_version": start_log.get("engine_version") or workflow_log.get("engine_version") or "ONBEKEND",
            "started_at": start_log.get("started_at") or workflow_log.get("started_at") or "",
            "finished_at": start_log.get("finished_at") or workflow_log.get("finished_at") or "",
            "workflow_status": workflow_log.get("status", "ONBEKEND"),
            "evidence_status": evidence_log.get("status", "ONBEKEND"),
            "local_run_log_exists": local_run_log_path.exists(),
            "local_run_log_path": str(local_run_log_path),
            "local_run_log_modified_at": (
                datetime.fromtimestamp(local_run_log_path.stat().st_mtime).isoformat(timespec="seconds")
                if local_run_log_path.exists()
                else ""
            ),
        }

        return latest_run

    def build_current_project_info(self) -> Dict[str, Any]:
        context_path = self.project_output_root / "project_analyzer_bib_context.json"
        package_path = self.project_output_root / "project_report_bib_package.json"

        context_data = self.read_json(context_path)
        package_data = self.read_json(package_path)

        project_name = (
            self.find_first_value(context_data, ["project_name", "project", "naam", "title"])
            or self.find_first_value(package_data, ["project_name", "project", "naam", "title"])
            or "Project Phoenix / BAOEES Projectanalyse"
        )

        project_type = (
            self.find_first_value(context_data, ["project_type", "type", "category"])
            or self.find_first_value(package_data, ["project_type", "type", "category"])
            or "Projectanalyse / Engineering workflow"
        )

        location = (
            self.find_first_value(context_data, ["location", "locatie", "address", "adres"])
            or self.find_first_value(package_data, ["location", "locatie", "address", "adres"])
            or "Nog niet projectspecifiek vastgelegd"
        )

        return {
            "project_name": str(project_name),
            "project_type": str(project_type),
            "location": str(location),
            "context_file": str(context_path),
            "context_exists": context_path.exists(),
            "package_file": str(package_path),
            "package_exists": package_path.exists(),
        }

    def build_next_phase_info(self) -> Dict[str, Any]:
        return {
            "next_phase": "BIB Import Wizard / Knowledge Library Builder",
            "purpose": "Bestaande kennis, oude chats, uploads en levenswerk-mappen systematisch importeren in de lokale BIB.",
            "status": "VOORBEREID",
            "candidate_version": "v5.4 of v6.0",
            "main_targets": [
                "Chats en samenvattingen structureren",
                "Bestanden en uploads inventariseren",
                "Projectkennis normaliseren",
                "BIB-indexen maken",
                "Bronnen/evidence vastleggen",
                "Kennis later herbruikbaar maken in START PROJECTANALYSE",
            ],
        }

    def build_launcher_section(
        self,
        outputs: List[Dict[str, Any]],
        summary: Dict[str, Any],
        latest_run: Dict[str, Any],
        current_project: Dict[str, Any],
        next_phase: Dict[str, Any],
    ) -> str:
        grouped_outputs = self.group_outputs_by_category(outputs)
        quick_links = self.build_quick_links(outputs)

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
                  <p class="muted"><strong>Pad:</strong> <code>{self.esc(item.get("relative_path", ""))}</code></p>
                  <p class="muted"><strong>Bytes:</strong> {self.esc(item.get("size_bytes", 0))}</p>
                </div>
                """

            category_sections += f"""
            <section style="margin-top:28px;">
              <h3>{self.esc(category)}</h3>
              <div class="grid">
                {cards}
              </div>
            </section>
            """

        return f"""
{self.START_MARKER}
<section style="margin-top:34px;">
  <div style="padding:30px;border-radius:20px;background:linear-gradient(135deg,#0f172a,#1e3a8a);border:1px solid #38bdf8;margin-bottom:28px;">
    <p style="margin:0 0 8px 0;color:#bfdbfe;font-weight:bold;letter-spacing:0.08em;">PROJECT PHOENIX / BAOEES</p>
    <h1 style="margin:0;font-size:36px;line-height:1.1;">START PROJECTANALYSE</h1>
    <p style="max-width:980px;color:#dbeafe;font-size:16px;">
      Professioneel Home Dashboard voor volledige projectanalyse, inclusief BIB-context,
      AAIE-aannames, Geo/Foundation analyse, projectrapportage, DOCX/PDF-export,
      Project ZIP, manifest, evidence dashboard en launcher-update.
    </p>

    <div class="grid" style="margin-top:22px;">
      <div class="card" style="border:2px solid #22c55e;background:#052e16;">
        <h2 style="margin-top:0;">Hoofdactie</h2>
        <p style="font-size:18px;"><strong>Dubbelklik in Windows Verkenner op:</strong></p>
        <p style="font-size:20px;"><code>{self.esc(self.BAT_FILE)}</code></p>
        <p class="muted">Dit is de normale lokale startknop voor Project Phoenix / BAOEES.</p>
      </div>

      <div class="card">
        <h2 style="margin-top:0;">GitKraken Terminal</h2>
        <p>Voer uit:</p>
        <p style="font-size:18px;"><code>{self.esc(self.BAT_COMMAND)}</code></p>
        <p class="muted">Dit doet hetzelfde als dubbelklikken op het BAT-bestand.</p>
      </div>

      <div class="card">
        <h2 style="margin-top:0;">Technisch commando</h2>
        <p>Python direct:</p>
        <p><code>{self.esc(self.START_COMMAND)}</code></p>
        <p class="muted">Gebruik dit vooral voor controle of debugging.</p>
      </div>
    </div>
  </div>

  <section style="margin-top:24px;">
    <h2>Projectstatus</h2>
    <div class="grid">
      <div class="card">
        <h3>Huidig project</h3>
        <p><strong>{self.esc(current_project.get("project_name", ""))}</strong></p>
        <p class="muted">Type: {self.esc(current_project.get("project_type", ""))}</p>
        <p class="muted">Locatie: {self.esc(current_project.get("location", ""))}</p>
      </div>

      <div class="card">
        <h3>Laatste run</h3>
        <p><strong>Status:</strong> {self.esc(latest_run.get("status", ""))}</p>
        <p class="muted">Engine: {self.esc(latest_run.get("engine_version", ""))}</p>
        <p class="muted">Start: {self.esc(latest_run.get("started_at", ""))}</p>
        <p class="muted">Einde: {self.esc(latest_run.get("finished_at", ""))}</p>
      </div>

      <div class="card">
        <h3>Workflowcontrole</h3>
        <p><strong>Workflow:</strong> {self.esc(latest_run.get("workflow_status", ""))}</p>
        <p><strong>Evidence:</strong> {self.esc(latest_run.get("evidence_status", ""))}</p>
        <p class="muted">Lokale run-log: {self.esc(latest_run.get("local_run_log_exists", ""))}</p>
        <p class="muted">Run-log datum: {self.esc(latest_run.get("local_run_log_modified_at", ""))}</p>
      </div>

      <div class="card">
        <h3>Outputstatus</h3>
        <p><span class="badge ok">{self.esc(summary.get("status", ""))}</span></p>
        <p class="muted">Aanwezige outputs: {self.esc(summary.get("existing_outputs", 0))} / {self.esc(summary.get("total_outputs", 0))}</p>
        <p class="muted">Belangrijke outputs: {self.esc(summary.get("existing_high_priority_outputs", 0))} / {self.esc(summary.get("high_priority_outputs", 0))}</p>
        <p class="muted">Ontbrekende verplichte outputs: {self.esc(summary.get("missing_required_outputs", 0))}</p>
      </div>
    </div>
  </section>

  <section style="margin-top:28px;">
    <h2>Snelle controle</h2>
    <div class="grid">
      <div class="card">
        <h3>Snelle start</h3>
        <p><strong>1.</strong> Open projectmap: <code>{self.esc(PROJECT_ROOT)}</code></p>
        <p><strong>2.</strong> Dubbelklik: <code>{self.esc(self.BAT_FILE)}</code></p>
        <p><strong>3.</strong> Wacht tot de run klaar is.</p>
        <p><strong>4.</strong> Dashboard en launcher openen automatisch.</p>
      </div>

      <div class="card">
        <h3>Belangrijkste links</h3>
        {quick_links}
      </div>

      <div class="card">
        <h3>Volgende fase</h3>
        <p><strong>{self.esc(next_phase.get("next_phase", ""))}</strong></p>
        <p class="muted">{self.esc(next_phase.get("purpose", ""))}</p>
        <p class="muted">Status: {self.esc(next_phase.get("status", ""))}</p>
        <p class="muted">Kandidaatversie: {self.esc(next_phase.get("candidate_version", ""))}</p>
      </div>
    </div>
  </section>

  <section style="margin-top:28px;">
    <h2>Praktische uitleg</h2>
    <div class="card">
      <p><strong>Normale werkwijze:</strong> gebruik <code>{self.esc(self.BAT_FILE)}</code>.</p>
      <p><strong>Waarom niet direct vanuit HTML?</strong> Een gewone HTML-pagina kan om veiligheidsredenen niet zelfstandig Python starten.</p>
      <p><strong>Daarom:</strong> het BAT-bestand is de lokale Windows-startknop. De launcher is het overzichts- en controlepaneel.</p>
      <p><strong>Na de run:</strong> controleer Start Dashboard, Workflow Dashboard, Evidence Dashboard, Project ZIP en rapporten.</p>
      <p><strong>Bibliotheekopbouw:</strong> de latere BIB Import Wizard gaat bestaande kennis, oude chats, uploads en levenswerk-mappen systematisch importeren.</p>
    </div>
  </section>

  {category_sections}
</section>
{self.END_MARKER}
"""

    def build_quick_links(self, outputs: List[Dict[str, Any]]) -> str:
        wanted_filenames = [
            "project_start_analysis_dashboard.html",
            "project_analyzer_workflow_dashboard.html",
            "project_package_evidence_dashboard.html",
            "project_report_bib_report.pdf",
            "project_report_bib_report.docx",
            "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip",
            "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt",
        ]

        links = ""

        for filename in wanted_filenames:
            item = next(
                (output for output in outputs if output.get("filename") == filename),
                None,
            )

            if not item:
                continue

            if item.get("exists"):
                links += (
                    f'<p><a href="{self.esc(item.get("href", ""))}">'
                    f'{self.esc(item.get("label", ""))}</a></p>'
                )
            else:
                links += f'<p class="muted">{self.esc(item.get("label", ""))} ontbreekt</p>'

        return links

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

    def find_first_value(self, data: Any, candidate_keys: List[str]) -> Optional[Any]:
        if isinstance(data, dict):
            for key in candidate_keys:
                if key in data and data[key]:
                    return data[key]

            for value in data.values():
                result = self.find_first_value(value, candidate_keys)
                if result:
                    return result

        if isinstance(data, list):
            for item in data:
                result = self.find_first_value(item, candidate_keys)
                if result:
                    return result

        return None

    def safe_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except Exception:
            return path.as_posix()

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    bridge = ProjectAnalyzerLauncherBridge()
    result = bridge.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()