from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class ProjectHtmlDashboardExportEngine:
    """
    PROJECT PHOENIX / BAOEES V3
    Project HTML Dashboard Export Engine v1.6

    Deze engine maakt per project een lokaal HTML-dashboard.

    Belangrijk:
    - Compatibel met BAOEES Core.
    - Accepteert storage_result, audit_result, checksum_result,
      git_evidence_result en index_result.
    - Heeft een run() methode omdat BAOEES Core deze aanroept.
    - Vangt toekomstige extra keyword arguments op met **extra_results.
    """

    ENGINE_NAME = "Project HTML Dashboard Export Engine"
    ENGINE_VERSION = "v1.6"

    def __init__(self, output_root: Optional[Union[str, Path]] = None) -> None:
        self.output_root = Path(output_root) if output_root else Path("outputs") / "projects"

    def run(
        self,
        project_result: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Compatibility runner voor BAOEES Core.

        BAOEES Core roept deze engine soms aan met:
            self.project_html_dashboard_export.run()

        Zonder deze methode ontstaat:
            AttributeError: object has no attribute 'run'

        Als project_result wordt meegegeven, maakt run() een dashboard.
        Zonder project_result voert run() een veilige statuscontrole uit.
        """

        self.output_root.mkdir(parents=True, exist_ok=True)

        if project_result:
            return self.export_project_dashboard(
                project_result=project_result,
                **kwargs,
            )

        dashboard_files = sorted(self.output_root.rglob("*_dashboard.html"))
        index_file = self.output_root / "index.html"

        return {
            "status": "ACTIEF",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "message": "HTML Dashboard Export Engine compatibility run uitgevoerd.",
            "output_root": str(self.output_root),
            "dashboard_count": len(dashboard_files),
            "dashboards": [str(path) for path in dashboard_files],
            "index_html": str(index_file),
            "index_exists": index_file.exists(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "warnings": [
                "Geen nieuw projectdashboard gegenereerd via run() zonder project_result; bestaande dashboards zijn gecontroleerd."
            ],
            "recommendation": self.build_recommendation(),
        }

    def export_project_dashboard(
        self,
        project_result: Optional[Dict[str, Any]] = None,
        report_result: Optional[Dict[str, Any]] = None,
        drawing_result: Optional[Dict[str, Any]] = None,
        cad_result: Optional[Dict[str, Any]] = None,
        calculation_result: Optional[Dict[str, Any]] = None,
        source_result: Optional[Dict[str, Any]] = None,
        digital_twin_result: Optional[Dict[str, Any]] = None,
        qa_qc_result: Optional[Dict[str, Any]] = None,
        export_result: Optional[Dict[str, Any]] = None,
        zip_result: Optional[Dict[str, Any]] = None,
        storage_result: Optional[Dict[str, Any]] = None,
        audit_result: Optional[Dict[str, Any]] = None,
        checksum_result: Optional[Dict[str, Any]] = None,
        git_evidence_result: Optional[Dict[str, Any]] = None,
        index_result: Optional[Dict[str, Any]] = None,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        """
        Genereert een projectdashboard.

        Deze signature is bewust ruim opgezet zodat BAOEES Core extra
        engine-resultaten kan meesturen zonder dat deze engine crasht.
        """

        project_result = project_result or {}
        report_result = report_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        calculation_result = calculation_result or {}
        source_result = source_result or {}
        digital_twin_result = digital_twin_result or {}
        qa_qc_result = qa_qc_result or {}
        export_result = export_result or {}
        zip_result = zip_result or {}
        storage_result = storage_result or {}
        audit_result = audit_result or {}
        checksum_result = checksum_result or {}
        git_evidence_result = git_evidence_result or {}
        index_result = index_result or {}
        extra_results = extra_results or {}

        project_id = self._project_id(project_result, storage_result, export_result)
        project_name = self._project_name(project_result, project_id)

        project_dir = self.output_root / project_id
        export_dir = project_dir / "09_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        dashboard_path = export_dir / f"{project_id}_dashboard.html"

        context = {
            "project_result": project_result,
            "report_result": report_result,
            "drawing_result": drawing_result,
            "cad_result": cad_result,
            "calculation_result": calculation_result,
            "source_result": source_result,
            "digital_twin_result": digital_twin_result,
            "qa_qc_result": qa_qc_result,
            "export_result": export_result,
            "zip_result": zip_result,
            "storage_result": storage_result,
            "audit_result": audit_result,
            "checksum_result": checksum_result,
            "git_evidence_result": git_evidence_result,
            "index_result": index_result,
            "extra_results": extra_results,
        }

        html_content = self._build_dashboard_html(
            project_id=project_id,
            project_name=project_name,
            project_dir=project_dir,
            dashboard_path=dashboard_path,
            context=context,
        )

        dashboard_path.write_text(html_content, encoding="utf-8")

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "project_id": project_id,
            "project_name": project_name,
            "dashboard_path": str(dashboard_path),
            "dashboard_file": str(dashboard_path),
            "dashboard_html": str(dashboard_path),
            "relative_dashboard_path": self._safe_relative(dashboard_path, self.output_root),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "warnings": self.build_warnings(
                {
                    "status": "OPGESLAGEN",
                    "dashboard_path": str(dashboard_path),
                }
            ),
            "recommendation": self.build_recommendation(),
        }

        return result

    def _project_id(
        self,
        project_result: Dict[str, Any],
        storage_result: Dict[str, Any],
        export_result: Dict[str, Any],
    ) -> str:
        candidates = [
            project_result.get("project_id"),
            project_result.get("id"),
            self._dig(project_result, "project", "project_id"),
            self._dig(project_result, "project", "id"),
            self._dig(project_result, "input", "project_id"),
            self._dig(project_result, "input", "id"),
            storage_result.get("project_id"),
            export_result.get("project_id"),
        ]

        for candidate in candidates:
            if candidate:
                return self._slug(str(candidate))

        return "unknown_project"

    def _project_name(self, project_result: Dict[str, Any], project_id: str) -> str:
        candidates = [
            project_result.get("project_name"),
            project_result.get("name"),
            project_result.get("title"),
            self._dig(project_result, "project", "project_name"),
            self._dig(project_result, "project", "name"),
            self._dig(project_result, "input", "project_name"),
            self._dig(project_result, "input", "name"),
        ]

        for candidate in candidates:
            if candidate:
                return str(candidate)

        return project_id.replace("_", " ").title()

    def _build_dashboard_html(
        self,
        project_id: str,
        project_name: str,
        project_dir: Path,
        dashboard_path: Path,
        context: Dict[str, Any],
    ) -> str:
        project_result = context["project_result"]
        report_result = context["report_result"]
        drawing_result = context["drawing_result"]
        cad_result = context["cad_result"]
        calculation_result = context["calculation_result"]
        source_result = context["source_result"]
        digital_twin_result = context["digital_twin_result"]
        qa_qc_result = context["qa_qc_result"]
        export_result = context["export_result"]
        zip_result = context["zip_result"]
        storage_result = context["storage_result"]
        audit_result = context["audit_result"]
        checksum_result = context["checksum_result"]
        git_evidence_result = context["git_evidence_result"]
        index_result = context["index_result"]
        extra_results = context["extra_results"]

        generated_at = datetime.now().isoformat(timespec="seconds")

        project_type = self._first_value(
            project_result.get("project_type"),
            project_result.get("type"),
            self._dig(project_result, "project", "type"),
            self._dig(project_result, "input", "project_type"),
            "Onbekend",
        )

        location = self._first_value(
            project_result.get("location"),
            project_result.get("locatie"),
            self._dig(project_result, "project", "location"),
            self._dig(project_result, "input", "location"),
            "Onbekend",
        )

        qa_status, qa_score = self._qa_summary(qa_qc_result, project_dir)
        source_count = self._source_count(source_result, project_dir)

        digital_twin_status = self._file_exists(project_dir / "07_digital_twin" / "digital_twin.json")
        runtime_status = self._file_exists(project_dir / "08_runtime_logs" / "runtime_log.json")
        audit_status = self._file_exists(project_dir / "08_runtime_logs" / f"{project_id}_audit_trail.json")
        git_status = self._file_exists(project_dir / "08_runtime_logs" / f"{project_id}_git_evidence.json")

        links = self._collect_project_links(project_id, project_dir, dashboard_path)

        cards_html = self._build_status_cards(
            qa_status=qa_status,
            qa_score=qa_score,
            source_count=source_count,
            digital_twin_status=digital_twin_status,
            runtime_status=runtime_status,
            audit_status=audit_status,
            git_status=git_status,
        )

        links_html = self._build_links_section(links)
        project_summary_html = self._build_project_summary(project_result)
        variant_html = self._build_variants_section(project_result)

        evidence_html = self._build_evidence_section(
            report_result=report_result,
            drawing_result=drawing_result,
            cad_result=cad_result,
            calculation_result=calculation_result,
            source_result=source_result,
            digital_twin_result=digital_twin_result,
            qa_qc_result=qa_qc_result,
            export_result=export_result,
            zip_result=zip_result,
            storage_result=storage_result,
            audit_result=audit_result,
            checksum_result=checksum_result,
            git_evidence_result=git_evidence_result,
            index_result=index_result,
            extra_results=extra_results,
        )

        file_manifest_html = self._build_file_manifest(project_dir, dashboard_path)

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{self._esc(project_name)} — Project Phoenix Dashboard</title>
  <style>
    :root {{
      --bg: #050816;
      --panel: #111827;
      --panel2: #0f172a;
      --text: #f8fafc;
      --muted: #cbd5e1;
      --line: #334155;
      --blue: #60a5fa;
      --green: #10b981;
      --yellow: #f59e0b;
      --red: #ef4444;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header {{
      padding: 34px 40px;
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
      border-bottom: 1px solid var(--line);
    }}
    header h1 {{
      margin: 0;
      font-size: 34px;
      letter-spacing: -0.03em;
    }}
    header p {{
      margin: 8px 0 0;
      color: #dbeafe;
      font-size: 16px;
    }}
    main {{
      padding: 30px 36px 50px;
    }}
    h2 {{
      margin-top: 34px;
      margin-bottom: 14px;
      font-size: 23px;
    }}
    h3 {{
      margin: 0 0 10px;
      color: #bfdbfe;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
      min-height: 110px;
    }}
    .muted {{
      color: var(--muted);
    }}
    .badge {{
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: bold;
      margin: 4px 6px 4px 0;
      background: #1e293b;
      border: 1px solid var(--line);
    }}
    .ok {{
      background: rgba(16, 185, 129, 0.16);
      color: #86efac;
      border-color: rgba(16, 185, 129, 0.45);
    }}
    .warn {{
      background: rgba(245, 158, 11, 0.16);
      color: #fcd34d;
      border-color: rgba(245, 158, 11, 0.45);
    }}
    .bad {{
      background: rgba(239, 68, 68, 0.16);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.45);
    }}
    a {{
      color: #93c5fd;
      text-decoration: none;
      font-weight: 700;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel2);
      color: #bfdbfe;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #020617;
      border: 1px solid var(--line);
      padding: 14px;
      border-radius: 12px;
      color: #e2e8f0;
      max-height: 420px;
      overflow: auto;
    }}
    footer {{
      border-top: 1px solid var(--line);
      padding: 22px 36px;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX</h1>
    <p>Brewster Engineering Wizard — projectdashboard voor {self._esc(project_name)}</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Project</h3>
        <p><strong>{self._esc(project_name)}</strong></p>
        <p class="muted">Project-ID: {self._esc(project_id)}</p>
      </div>
      <div class="card">
        <h3>Type</h3>
        <p>{self._esc(project_type)}</p>
      </div>
      <div class="card">
        <h3>Locatie</h3>
        <p>{self._esc(location)}</p>
      </div>
      <div class="card">
        <h3>Gegenereerd</h3>
        <p>{self._esc(generated_at)}</p>
      </div>
    </section>

    <h2>Projectstatus</h2>
    {cards_html}

    <h2>Projectlinks</h2>
    {links_html}

    <h2>Projectsamenvatting</h2>
    {project_summary_html}

    <h2>Varianten</h2>
    {variant_html}

    <h2>Evidence / Engine-resultaten</h2>
    {evidence_html}

    <h2>Bestandsmanifest</h2>
    {file_manifest_html}
  </main>

  <footer>
    {self._esc(self.ENGINE_NAME)} {self._esc(self.ENGINE_VERSION)} —
    automatisch gegenereerd door BAOEES V3 / Project Phoenix.
  </footer>
</body>
</html>
"""

    def _build_status_cards(
        self,
        qa_status: str,
        qa_score: str,
        source_count: int,
        digital_twin_status: bool,
        runtime_status: bool,
        audit_status: bool,
        git_status: bool,
    ) -> str:
        qa_badge = self._badge(qa_status, qa_status.upper() not in {"ONTBREEKT", "FAILED", "FOUT", "ERROR"})
        source_badge = self._badge(f"BRONNEN: {source_count}", source_count > 0)
        dt_badge = self._badge(
            "DIGITAL TWIN BESCHIKBAAR" if digital_twin_status else "DIGITAL TWIN ONTBREEKT",
            digital_twin_status,
        )
        runtime_badge = self._badge(
            "RUNTIME LOG BESCHIKBAAR" if runtime_status else "RUNTIME LOG ONTBREEKT",
            runtime_status,
        )
        audit_badge = self._badge(
            "AUDIT TRAIL BESCHIKBAAR" if audit_status else "AUDIT TRAIL ONTBREEKT",
            audit_status,
        )
        git_badge = self._badge(
            "GIT EVIDENCE BESCHIKBAAR" if git_status else "GIT EVIDENCE ONTBREEKT",
            git_status,
        )

        return f"""
<section class="grid">
  <div class="card">
    <h3>QA/QC</h3>
    <p>{qa_badge}</p>
    <p class="muted">Score/status: {self._esc(qa_score)}</p>
  </div>
  <div class="card">
    <h3>Digital Twin</h3>
    <p>{dt_badge}</p>
  </div>
  <div class="card">
    <h3>Bronnenregister</h3>
    <p>{source_badge}</p>
  </div>
  <div class="card">
    <h3>Runtime / Audit / Git</h3>
    <p>{runtime_badge}</p>
    <p>{audit_badge}</p>
    <p>{git_badge}</p>
  </div>
</section>
"""

    def _build_links_section(self, links: List[Tuple[str, Path, bool]]) -> str:
        rows = []

        for label, path, exists in links:
            badge = self._badge("AANWEZIG" if exists else "ONTBREEKT", exists)
            href = self._esc(path.as_posix())

            if exists:
                link_html = f'<a href="{href}">{self._esc(label)}</a>'
            else:
                link_html = f'<span class="muted">{self._esc(label)}</span>'

            rows.append(
                f"<tr><td>{link_html}</td><td>{badge}</td><td>{self._esc(path.as_posix())}</td></tr>"
            )

        return f"""
<table>
  <thead>
    <tr>
      <th>Onderdeel</th>
      <th>Status</th>
      <th>Pad</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
"""

    def _build_project_summary(self, project_result: Dict[str, Any]) -> str:
        summary_candidates = [
            project_result.get("summary"),
            project_result.get("project_summary"),
            project_result.get("description"),
            self._dig(project_result, "project", "description"),
            self._dig(project_result, "input", "description"),
        ]

        for item in summary_candidates:
            if item:
                if isinstance(item, (dict, list)):
                    return f"<pre>{self._esc(json.dumps(item, ensure_ascii=False, indent=2, default=str))}</pre>"
                return f"<p>{self._esc(str(item))}</p>"

        compact = {
            key: value
            for key, value in project_result.items()
            if key not in {"variants"} and not callable(value)
        }

        if compact:
            return f"<pre>{self._esc(json.dumps(compact, ensure_ascii=False, indent=2, default=str))}</pre>"

        return '<p class="muted">Geen projectsamenvatting beschikbaar.</p>'

    def _build_variants_section(self, project_result: Dict[str, Any]) -> str:
        variants = (
            project_result.get("variants")
            or project_result.get("design_variants")
            or self._dig(project_result, "project", "variants")
            or []
        )

        if not variants:
            return '<p class="muted">Geen varianten gevonden in projectresultaat.</p>'

        if isinstance(variants, dict):
            variants_iterable = []
            for key, value in variants.items():
                if isinstance(value, dict):
                    item = {"variant": key}
                    item.update(value)
                else:
                    item = {"variant": key, "value": value}
                variants_iterable.append(item)
        elif isinstance(variants, list):
            variants_iterable = variants
        else:
            return f"<pre>{self._esc(str(variants))}</pre>"

        rows = []

        for variant in variants_iterable:
            if isinstance(variant, dict):
                code = self._first_value(variant.get("variant"), variant.get("code"), variant.get("id"), "-")
                name = self._first_value(variant.get("name"), variant.get("naam"), variant.get("title"), "-")
                note = self._first_value(
                    variant.get("permit_note"),
                    variant.get("note"),
                    variant.get("description"),
                    variant.get("omschrijving"),
                    "",
                )
                rows.append(
                    f"<tr><td>{self._esc(code)}</td><td>{self._esc(name)}</td><td>{self._esc(note)}</td></tr>"
                )
            else:
                rows.append(f"<tr><td>-</td><td>{self._esc(str(variant))}</td><td></td></tr>")

        return f"""
<table>
  <thead>
    <tr>
      <th>Variant</th>
      <th>Naam</th>
      <th>Toelichting</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
"""

    def _build_evidence_section(
        self,
        report_result: Dict[str, Any],
        drawing_result: Dict[str, Any],
        cad_result: Dict[str, Any],
        calculation_result: Dict[str, Any],
        source_result: Dict[str, Any],
        digital_twin_result: Dict[str, Any],
        qa_qc_result: Dict[str, Any],
        export_result: Dict[str, Any],
        zip_result: Dict[str, Any],
        storage_result: Dict[str, Any],
        audit_result: Dict[str, Any],
        checksum_result: Dict[str, Any],
        git_evidence_result: Dict[str, Any],
        index_result: Dict[str, Any],
        extra_results: Dict[str, Any],
    ) -> str:
        sections = [
            ("Rapportage", report_result),
            ("Tekeningen", drawing_result),
            ("CAD / DXF", cad_result),
            ("Berekeningen", calculation_result),
            ("Bronnenregister", source_result),
            ("Digital Twin", digital_twin_result),
            ("QA/QC", qa_qc_result),
            ("Exports", export_result),
            ("ZIP", zip_result),
            ("Storage", storage_result),
            ("Audit Trail", audit_result),
            ("Checksum", checksum_result),
            ("Git Evidence", git_evidence_result),
            ("Index", index_result),
        ]

        if extra_results:
            sections.append(("Extra resultaten", extra_results))

        rows = []

        for title, result in sections:
            status = self._result_status(result)
            badge = self._badge(status, status not in {"ONTBREEKT", "FAILED", "FOUT", "ERROR"})
            short = self._compact_result(result)

            rows.append(
                f"<tr><td>{self._esc(title)}</td><td>{badge}</td><td><pre>{self._esc(short)}</pre></td></tr>"
            )

        return f"""
<table>
  <thead>
    <tr>
      <th>Engine</th>
      <th>Status</th>
      <th>Resultaat</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
"""

    def _build_file_manifest(self, project_dir: Path, dashboard_path: Path) -> str:
        if not project_dir.exists():
            return '<p class="muted">Projectmap niet gevonden.</p>'

        files: List[Path] = []

        for path in sorted(project_dir.rglob("*")):
            if path.is_file():
                files.append(path)

        if not files:
            return '<p class="muted">Geen projectbestanden gevonden.</p>'

        rows = []

        for path in files[:250]:
            rel = self._safe_relative(path, dashboard_path.parent)
            size = path.stat().st_size if path.exists() else 0

            rows.append(
                f"<tr>"
                f"<td><a href='{self._esc(rel)}'>{self._esc(path.name)}</a></td>"
                f"<td>{self._esc(path.suffix or '-')}</td>"
                f"<td>{size}</td>"
                f"<td>{self._esc(self._safe_relative(path, project_dir))}</td>"
                f"</tr>"
            )

        if len(files) > 250:
            rows.append(
                f"<tr><td colspan='4' class='muted'>Alleen eerste 250 bestanden getoond van {len(files)}.</td></tr>"
            )

        return f"""
<table>
  <thead>
    <tr>
      <th>Bestand</th>
      <th>Type</th>
      <th>Bytes</th>
      <th>Relatief pad</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
"""

    def _collect_project_links(
        self,
        project_id: str,
        project_dir: Path,
        dashboard_path: Path,
    ) -> List[Tuple[str, Path, bool]]:
        candidates = [
            ("PDF-rapport", project_dir / "01_reports" / f"{project_id}_project_report.pdf"),
            ("DOCX-rapport", project_dir / "01_reports" / f"{project_id}_project_report.docx"),
            ("Markdown-rapport", project_dir / "01_reports" / f"{project_id}_project_report.md"),
            ("Tekst-rapport", project_dir / "01_reports" / f"{project_id}_project_report.txt"),
            ("Situatietekening PDF", project_dir / "02_drawings" / f"{project_id}_situatie.pdf"),
            ("Plattegrond PDF", project_dir / "02_drawings" / f"{project_id}_plattegrond.pdf"),
            ("Doorsnede PDF", project_dir / "02_drawings" / f"{project_id}_doorsnede.pdf"),
            ("Situatie DXF", project_dir / "03_cad" / f"{project_id}_situatie.dxf"),
            ("Plattegrond DXF", project_dir / "03_cad" / f"{project_id}_plattegrond.dxf"),
            ("Doorsnede DXF", project_dir / "03_cad" / f"{project_id}_doorsnede.dxf"),
            ("Berekeningen CSV", project_dir / "04_calculations" / f"{project_id}_calculation_index.csv"),
            ("QA/QC JSON", project_dir / "04_calculations" / "qa_qc_report.json"),
            ("Bronnenregister JSON", project_dir / "06_sources" / "source_register.json"),
            ("Digital Twin JSON", project_dir / "07_digital_twin" / "digital_twin.json"),
            ("Runtime log JSON", project_dir / "08_runtime_logs" / "runtime_log.json"),
            ("Audit trail JSON", project_dir / "08_runtime_logs" / f"{project_id}_audit_trail.json"),
            ("File manifest JSON", project_dir / "08_runtime_logs" / f"{project_id}_file_manifest.json"),
            ("Git evidence JSON", project_dir / "08_runtime_logs" / f"{project_id}_git_evidence.json"),
            ("Kostenraming CSV", project_dir / "09_exports" / f"{project_id}_cost_estimate.csv"),
            ("Planning CSV", project_dir / "09_exports" / f"{project_id}_planning.csv"),
            ("Project summary CSV", project_dir / "09_exports" / f"{project_id}_project_summary.csv"),
            ("Excel-werkboek", project_dir / "09_exports" / f"{project_id}_project_tables.xlsx"),
            ("Project ZIP", project_dir / "10_zip" / f"{project_id}_project_export.zip"),
        ]

        result: List[Tuple[str, Path, bool]] = []
        base = dashboard_path.parent

        for label, absolute_path in candidates:
            exists = absolute_path.exists()
            relative = Path(self._safe_relative(absolute_path, base))
            result.append((label, relative, exists))

        return result

    def _qa_summary(self, qa_qc_result: Dict[str, Any], project_dir: Path) -> Tuple[str, str]:
        if qa_qc_result:
            status = self._result_status(qa_qc_result)
            score = self._first_value(
                qa_qc_result.get("score"),
                qa_qc_result.get("qa_score"),
                qa_qc_result.get("health_score"),
                qa_qc_result.get("status"),
                status,
            )
            return str(status), str(score)

        qa_file = project_dir / "04_calculations" / "qa_qc_report.json"
        data = self._read_json_file(qa_file)

        if isinstance(data, dict):
            status = self._result_status(data)
            score = self._first_value(
                data.get("score"),
                data.get("qa_score"),
                data.get("health_score"),
                data.get("status"),
                status,
            )
            return str(status), str(score)

        return "ONTBREEKT", "-"

    def _source_count(self, source_result: Dict[str, Any], project_dir: Path) -> int:
        if source_result:
            for key in ("sources", "source_register", "items", "records"):
                value = source_result.get(key)

                if isinstance(value, list):
                    return len(value)

                if isinstance(value, dict):
                    return len(value)

        source_file = project_dir / "06_sources" / "source_register.json"
        data = self._read_json_file(source_file)

        if isinstance(data, dict):
            for key in ("sources", "source_register", "items", "records"):
                value = data.get(key)

                if isinstance(value, list):
                    return len(value)

                if isinstance(value, dict):
                    return len(value)

            return len(data)

        if isinstance(data, list):
            return len(data)

        return 0

    def _read_json_file(self, path: Path) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

        return None

    def _result_status(self, result: Any) -> str:
        if not result:
            return "ONTBREEKT"

        if isinstance(result, dict):
            status = result.get("status") or result.get("state") or result.get("result")

            if status:
                return str(status).upper()

            if result.get("success") is True:
                return "OK"

            if result.get("success") is False:
                return "FAILED"

            return "AANWEZIG"

        return "AANWEZIG"

    def _compact_result(self, result: Any) -> str:
        if not result:
            return "-"

        try:
            if isinstance(result, dict):
                compact: Dict[str, Any] = {}

                preferred_keys = [
                    "status",
                    "engine",
                    "engine_version",
                    "project_id",
                    "project_name",
                    "path",
                    "file",
                    "report_path",
                    "dashboard_path",
                    "zip_path",
                    "generated_at",
                    "warnings",
                    "recommendation",
                    "score",
                    "qa_score",
                    "health_score",
                ]

                for key in preferred_keys:
                    if key in result:
                        compact[key] = result[key]

                if not compact:
                    for key, value in list(result.items())[:12]:
                        compact[key] = value

                return json.dumps(compact, ensure_ascii=False, indent=2, default=str)

            if isinstance(result, list):
                return json.dumps(result[:12], ensure_ascii=False, indent=2, default=str)

            return str(result)

        except Exception as exc:
            return f"Kon resultaat niet compact maken: {exc}"

    def build_warnings(self, dashboard_file_result: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []

        if dashboard_file_result.get("status") != "OPGESLAGEN":
            warnings.append("HTML-dashboard is niet opgeslagen.")

        dashboard_path = dashboard_file_result.get("dashboard_path") or dashboard_file_result.get("dashboard_file")

        if dashboard_path and not Path(str(dashboard_path)).exists():
            warnings.append("Dashboardbestand kon niet worden teruggevonden na schrijven.")

        if not warnings:
            warnings.append("Geen kritieke HTML-dashboardexportwaarschuwingen.")

        return warnings

    def build_recommendation(self) -> Dict[str, Any]:
        return {
            "status": "PROJECT_HTML_DASHBOARD_ADVIES",
            "advice": [
                "Gebruik dit dashboard als lokale projectstartpagina.",
                "Controleer per project de links naar rapporten, tekeningen, Digital Twin, QA/QC en ZIP.",
                "Gebruik audit trail, checksum en git evidence voor projectverantwoording.",
            ],
            "next_steps": [
                "Dashboard visueel controleren.",
                "Indexpagina opnieuw openen na iedere projectrun.",
                "Bij foutloze test committen en pushen.",
            ],
        }

    def _badge(self, text: str, ok: bool) -> str:
        css = "ok" if ok else "warn"

        if text.upper() in {"FAILED", "FOUT", "ERROR"}:
            css = "bad"

        return f'<span class="badge {css}">{self._esc(text)}</span>'

    def _file_exists(self, path: Path) -> bool:
        return path.exists() and path.is_file()

    def _safe_relative(self, path: Path, start: Path) -> str:
        try:
            return path.resolve().relative_to(start.resolve()).as_posix()
        except Exception:
            try:
                return path.relative_to(start).as_posix()
            except Exception:
                return path.as_posix()

    def _dig(self, data: Any, *keys: str) -> Any:
        current = data

        for key in keys:
            if not isinstance(current, dict):
                return None

            current = current.get(key)

        return current

    def _first_value(self, *values: Any) -> Any:
        for value in values:
            if value is not None and value != "":
                return value

        return ""

    def _slug(self, value: str) -> str:
        value = value.strip().lower()
        allowed = []
        previous_underscore = False

        for char in value:
            if char.isalnum():
                allowed.append(char)
                previous_underscore = False
            else:
                if not previous_underscore:
                    allowed.append("_")
                    previous_underscore = True

        slug = "".join(allowed).strip("_")
        return slug or "unknown_project"

    def _esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    """
    Standalone test:
        python baoees\\project_html_dashboard_export_engine\\main.py

    Normale test:
        python run_baoees_v3.py
    """

    engine = ProjectHtmlDashboardExportEngine()

    result = engine.export_project_dashboard(
        project_result={
            "project_id": "plutostraat",
            "project_name": "Plutostraat met BAOEES V3",
            "project_type": "Bouw",
            "location": "Plutostraat, Paramaribo, Suriname",
            "variants": [
                {
                    "variant": "A",
                    "name": "Laagste kosten",
                    "permit_note": "Kostenoptimalisatie.",
                },
                {
                    "variant": "B",
                    "name": "Hoogste vergunningkans",
                    "permit_note": "Vergunningstechnische prioriteit.",
                },
                {
                    "variant": "C",
                    "name": "Duurzaamste",
                    "permit_note": "Klimaat, water en milieu.",
                },
                {
                    "variant": "D",
                    "name": "Hoogste opbrengst",
                    "permit_note": "Ruimtelijke opbrengst.",
                },
                {
                    "variant": "E",
                    "name": "Beste ruimtelijke kwaliteit",
                    "permit_note": "Ruimtelijke kwaliteit.",
                },
            ],
        },
        qa_qc_result={"status": "OK", "qa_score": "concept"},
        zip_result={"status": "OPGESLAGEN"},
        storage_result={"status": "AANWEZIG"},
        audit_result={"status": "AANWEZIG"},
        checksum_result={"status": "AANWEZIG"},
        git_evidence_result={"status": "AANWEZIG"},
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()