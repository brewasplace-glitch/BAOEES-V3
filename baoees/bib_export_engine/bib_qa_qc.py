from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BibQaQcEngine:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB QA/QC Engine v3.3

    Doel:
    - Controleert of de BIB compleet is.
    - Controleert verplichte hoofdonderdelen.
    - Controleert verplichte exportbestanden.
    - Maakt JSON- en HTML-rapport.
    """

    ENGINE_NAME = "Project Phoenix BIB QA/QC Engine"
    ENGINE_VERSION = "v3.3"

    def __init__(
        self,
        bib_root: Optional[str | Path] = None,
        output_root: Optional[str | Path] = None,
    ) -> None:
        self.bib_root = Path(bib_root) if bib_root else Path("bib")
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        checks = []
        checks.extend(self.check_required_bib_files())
        checks.extend(self.check_required_bib_directories())
        checks.extend(self.check_required_exports())
        checks.extend(self.check_minimum_content())

        passed = sum(1 for check in checks if check["status"] == "OK")
        warnings = sum(1 for check in checks if check["status"] == "WARNING")
        failed = sum(1 for check in checks if check["status"] == "FAILED")

        overall_status = "OK"
        if failed > 0:
            overall_status = "FAILED"
        elif warnings > 0:
            overall_status = "WARNING"

        report = {
            "status": overall_status,
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "bib_root": str(self.bib_root),
            "output_root": str(self.output_root),
            "summary": {
                "total_checks": len(checks),
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
            },
            "checks": checks,
            "extra_results": extra_results,
            "recommendation": self.build_recommendation(overall_status, failed, warnings),
        }

        json_path = self.output_root / "bib_qa_qc_report.json"
        html_path = self.output_root / "bib_qa_qc_report.html"

        self.write_json(json_path, report)
        html_path.write_text(self.build_html_report(report), encoding="utf-8")

        report["json_path"] = str(json_path)
        report["html_path"] = str(html_path)

        return report

    def check_required_bib_directories(self) -> List[Dict[str, Any]]:
        required_dirs = [
            "01_MASTER_KNOWLEDGE",
            "02_PROJECTS",
            "03_ENGINES",
            "04_STANDARDS_AND_RULES",
            "05_TEMPLATES",
            "06_WORKFLOWS",
            "07_LESSONS_LEARNED",
            "08_SOURCE_EVIDENCE",
            "09_ASSUMPTIONS",
            "10_EXPORTS",
        ]

        checks = []

        for directory in required_dirs:
            path = self.bib_root / directory
            checks.append(
                self.make_check(
                    name=f"Directory bestaat: {directory}",
                    path=path,
                    required=True,
                    ok=path.exists() and path.is_dir(),
                )
            )

        return checks

    def check_required_bib_files(self) -> List[Dict[str, Any]]:
        required_files = [
            "00_BIB_INDEX.md",
            "01_MASTER_KNOWLEDGE/PROJECT_PHOENIX_CORE_KNOWLEDGE.md",
            "01_MASTER_KNOWLEDGE/BREWSTER_ENGINEERING_WIZARD_LIFEVISION.md",
            "01_MASTER_KNOWLEDGE/PROJECT_PHOENIX_SYSTEM_ARCHITECTURE.md",
            "02_PROJECTS/PLUTOSTRAAT_PROJECT_KNOWLEDGE.md",
            "02_PROJECTS/MOSKEE_BUNSCHOTEN_PROJECT_KNOWLEDGE.md",
            "02_PROJECTS/BRUYNZEEL_WATERFRONT_PROJECT_KNOWLEDGE.md",
            "03_ENGINES/BAOEES_V3_ENGINE_REGISTER.md",
            "03_ENGINES/AUTOMATIC_GROUNDWATER_FOUNDATION_ENGINE.md",
            "03_ENGINES/AAIE_ENGINE_KNOWLEDGE.md",
            "03_ENGINES/STEE_ENGINE_KNOWLEDGE.md",
            "03_ENGINES/BIB_EXPORT_ENGINE_KNOWLEDGE.md",
            "04_STANDARDS_AND_RULES/PROJECT_PHOENIX_STANDARDS.md",
            "05_TEMPLATES/PROJECT_INPUT_TEMPLATE.md",
            "05_TEMPLATES/REPORT_OUTPUT_TEMPLATE.md",
            "06_WORKFLOWS/AUTONOMOUS_PROJECT_WORKFLOW.md",
            "06_WORKFLOWS/GITKRAKEN_WORKFLOW.md",
            "07_LESSONS_LEARNED/DASHBOARD_ENGINE_FIXES.md",
            "08_SOURCE_EVIDENCE/GIT_EVIDENCE_BASELINE.md",
            "08_SOURCE_EVIDENCE/SOURCE_EVIDENCE_RULES.md",
            "09_ASSUMPTIONS/PROJECT_PHOENIX_ASSUMPTIONS.md",
            "10_EXPORTS/BIB_EXPORT_PLAN.md",
            "10_EXPORTS/BIB_EXPORT_ENGINE_DESIGN.md",
        ]

        checks = []

        for file_path in required_files:
            path = self.bib_root / file_path
            checks.append(
                self.make_check(
                    name=f"Bestand bestaat: {file_path}",
                    path=path,
                    required=True,
                    ok=path.exists() and path.is_file(),
                )
            )

        return checks

    def check_required_exports(self) -> List[Dict[str, Any]]:
        export_files = [
            "bib_dashboard.html",
            "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx",
            "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf",
            "PROJECT_PHOENIX_BIB_EXPORT.zip",
            "PROJECT_PHOENIX_BIB_FULL_EXPORT.zip",
            "bib_manifest.json",
            "bib_export_log.json",
            "bib_pdf_export_log.json",
            "bib_full_export_log.json",
        ]

        checks = []

        for file_path in export_files:
            path = self.output_root / file_path
            checks.append(
                self.make_check(
                    name=f"Export bestaat: {file_path}",
                    path=path,
                    required=False,
                    ok=path.exists() and path.is_file(),
                    warning_if_missing=True,
                )
            )

        return checks

    def check_minimum_content(self) -> List[Dict[str, Any]]:
        checks = []

        markdown_files = list(self.bib_root.rglob("*.md")) if self.bib_root.exists() else []

        checks.append(
            {
                "name": "Minimum aantal Markdown-bestanden",
                "status": "OK" if len(markdown_files) >= 20 else "WARNING",
                "required": False,
                "path": str(self.bib_root),
                "message": f"{len(markdown_files)} Markdown-bestanden gevonden. Streefwaarde: minimaal 20.",
            }
        )

        for path in markdown_files:
            try:
                text = path.read_text(encoding="utf-8")
                word_count = len(text.split())
                status = "OK" if word_count >= 5 else "WARNING"
                checks.append(
                    {
                        "name": f"Inhoud aanwezig: {path.name}",
                        "status": status,
                        "required": False,
                        "path": str(path),
                        "message": f"{word_count} woorden gevonden.",
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "name": f"Inhoud lezen: {path.name}",
                        "status": "FAILED",
                        "required": False,
                        "path": str(path),
                        "message": f"Kon bestand niet lezen: {exc}",
                    }
                )

        return checks

    def make_check(
        self,
        name: str,
        path: Path,
        required: bool,
        ok: bool,
        warning_if_missing: bool = False,
    ) -> Dict[str, Any]:
        if ok:
            status = "OK"
            message = "Aanwezig."
        else:
            status = "WARNING" if warning_if_missing and not required else "FAILED"
            message = "Ontbreekt."

        return {
            "name": name,
            "status": status,
            "required": required,
            "path": str(path),
            "message": message,
        }

    def build_recommendation(self, overall_status: str, failed: int, warnings: int) -> Dict[str, Any]:
        advice = []

        if overall_status == "OK":
            advice.append("BIB QA/QC is akkoord.")
            advice.append("BIB kan worden gebruikt als kennisbron en exportbasis.")
        else:
            advice.append("Controleer ontbrekende of waarschuwinggevende BIB-onderdelen.")
            advice.append("Vul ontbrekende kennisbestanden aan voordat BIB als volledige kennisbron wordt gebruikt.")

        if failed > 0:
            advice.append(f"{failed} verplichte controles zijn mislukt.")

        if warnings > 0:
            advice.append(f"{warnings} waarschuwingen gevonden.")

        advice.append("Koppel deze QA/QC-check in v3.4 aan de Full Export Runner.")

        return {
            "status": "BIB_QA_QC_ADVIES",
            "advice": advice,
        }

    def build_html_report(self, report: Dict[str, Any]) -> str:
        rows = []

        for check in report.get("checks", []):
            status = check.get("status", "")
            css = "ok" if status == "OK" else "warn"
            if status == "FAILED":
                css = "bad"

            rows.append(
                "<tr>"
                f"<td>{self.esc(check.get('name', ''))}</td>"
                f"<td><span class='badge {css}'>{self.esc(status)}</span></td>"
                f"<td>{self.esc(check.get('message', ''))}</td>"
                f"<td><code>{self.esc(check.get('path', ''))}</code></td>"
                "</tr>"
            )

        summary = report.get("summary", {})

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB QA/QC Report</title>
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
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
      border-bottom: 1px solid #334155;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      font-weight: bold;
      font-size: 12px;
      border: 1px solid #334155;
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
    code {{
      color: #cbd5e1;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX BIB QA/QC</h1>
    <p>Brewster Integrated Bibliotheek — kwaliteitscontrole</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p><span class="badge {'ok' if report.get('status') == 'OK' else 'warn'}">{self.esc(report.get('status'))}</span></p>
      </div>
      <div class="card">
        <h3>Checks</h3>
        <p>{self.esc(summary.get('total_checks', 0))} totaal</p>
      </div>
      <div class="card">
        <h3>OK</h3>
        <p>{self.esc(summary.get('passed', 0))}</p>
      </div>
      <div class="card">
        <h3>Warnings / Failed</h3>
        <p>{self.esc(summary.get('warnings', 0))} waarschuwingen / {self.esc(summary.get('failed', 0))} failed</p>
      </div>
    </section>

    <h2>Controlelijst</h2>
    <table>
      <thead>
        <tr>
          <th>Controle</th>
          <th>Status</th>
          <th>Bericht</th>
          <th>Pad</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = BibQaQcEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()