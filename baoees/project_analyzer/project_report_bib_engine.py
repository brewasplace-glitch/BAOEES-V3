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

from baoees.project_analyzer.geo_foundation_bib_engine import GeoFoundationBibEngine


class ProjectReportBibEngine:
    """
    PROJECT PHOENIX / BAOEES V3-V4
    Project Report BIB Engine v4.1

    Doel:
    - Leest Geo/Foundation BIB analyse.
    - Leest indirect BIB, AAIE en STEE basisregels.
    - Genereert een projectrapport-startpakket.
    - Maakt JSON, Markdown en HTML-output.
    """

    ENGINE_NAME = "Project Phoenix Project Report BIB Engine"
    ENGINE_VERSION = "v4.1"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        geo_analysis_path: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.geo_analysis_path = (
            Path(geo_analysis_path)
            if geo_analysis_path
            else self.project_output_root / "geo_foundation_bib_analysis.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh_geo: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or self.default_project_context()

        geo_status = self.ensure_geo_analysis(
            project_context=project_context,
            force_refresh_geo=force_refresh_geo,
        )

        geo_data = self.read_json(self.geo_analysis_path)

        report_sections = self.build_report_sections(
            project_context=project_context,
            geo_data=geo_data,
        )

        report_markdown = self.build_markdown_report(report_sections)
        report_html = self.build_html_report(report_sections)

        output_json_path = self.project_output_root / "project_report_bib_package.json"
        output_md_path = self.project_output_root / "project_report_bib_report.md"
        output_html_path = self.project_output_root / "project_report_bib_report.html"

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Projectrapportage-startpakket genereren vanuit BIB, AAIE en Geo/Foundation.",
            "project_context": project_context,
            "geo_status": geo_status,
            "geo_analysis_path": str(self.geo_analysis_path),
            "report_sections": report_sections,
            "report_outputs": {
                "json_path": str(output_json_path),
                "markdown_path": str(output_md_path),
                "html_path": str(output_html_path),
            },
            "warnings": self.build_warnings(geo_data, report_sections),
            "next_steps": [
                "Koppel deze rapportage-engine in v4.2 aan DOCX/PDF-generatie.",
                "Laat rapporten voortaan BIB-templatehoofdstukken gebruiken.",
                "Laat AAIE-aannames zichtbaar terugkomen in ieder rapport.",
                "Laat STEE-bronnen en fallbacks automatisch als bronregister opnemen.",
                "Gebruik Geo/Foundation analyse als basis voor funderingshoofdstuk.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(output_json_path, result)
        output_md_path.write_text(report_markdown, encoding="utf-8")
        output_html_path.write_text(report_html, encoding="utf-8")

        return result

    def ensure_geo_analysis(
        self,
        project_context: Dict[str, Any],
        force_refresh_geo: bool,
    ) -> Dict[str, Any]:
        if self.geo_analysis_path.exists() and not force_refresh_geo:
            return {
                "status": "AANWEZIG",
                "message": "Geo/Foundation BIB analyse bestond al.",
                "path": str(self.geo_analysis_path),
            }

        engine = GeoFoundationBibEngine(project_output_root=self.project_output_root)
        result = engine.run(project_context=project_context, force_refresh_assumptions=force_refresh_geo)

        return {
            "status": "GEGENEREERD",
            "message": "Geo/Foundation BIB analyse is gegenereerd of vernieuwd.",
            "path": str(self.geo_analysis_path),
            "engine_result_status": result.get("status"),
        }

    def build_report_sections(
        self,
        project_context: Dict[str, Any],
        geo_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        geo_defaults = geo_data.get("geo_defaults", {})
        foundation_variants = geo_data.get("foundation_variants", [])
        comparison = geo_data.get("foundation_comparison", [])
        recommendation = geo_data.get("foundation_recommendation", {})
        aaie_links = geo_data.get("aaie_assumption_links", [])

        return [
            {
                "order": 1,
                "title": "Managementsamenvatting",
                "type": "summary",
                "content": [
                    "Dit rapport is automatisch voorbereid vanuit Project Phoenix / BAOEES.",
                    "De rapportage gebruikt BIB-kennis, AAIE-aannames en de Geo/Foundation BIB Engine.",
                    "De fundering wordt voorlopig beoordeeld met minimaal F1 strokenfundering en F2 paalfundering.",
                    "Definitieve engineering vereist projectlasten, bodemonderzoek, berekening en QA/QC.",
                ],
            },
            {
                "order": 2,
                "title": "Projectgegevens",
                "type": "project_context",
                "content": self.dict_to_lines(project_context),
            },
            {
                "order": 3,
                "title": "BIB, AAIE en STEE uitgangspunten",
                "type": "system_rules",
                "content": [
                    "Digital Twin First: alle projectoutputs moeten uit dezelfde centrale projectdata komen.",
                    "AAIE: ontbrekende gegevens worden automatisch aangevuld en geregistreerd als aanname.",
                    "STEE: bronnen, fallbacks en aannames moeten herleidbaar worden vastgelegd.",
                    "QA/QC: geen volledige projectexport zonder controle.",
                    "Groundwater fallback: P = -0,50 m als projectgegevens ontbreken.",
                ],
            },
            {
                "order": 4,
                "title": "Geo-profiel startwaarden",
                "type": "geo",
                "content": self.geo_profile_lines(geo_defaults),
            },
            {
                "order": 5,
                "title": "Funderingsvarianten",
                "type": "foundation_variants",
                "content": self.foundation_variant_lines(foundation_variants),
            },
            {
                "order": 6,
                "title": "Funderingsvergelijking",
                "type": "foundation_comparison",
                "content": self.foundation_comparison_lines(comparison),
            },
            {
                "order": 7,
                "title": "Voorlopige funderingsaanbeveling",
                "type": "foundation_recommendation",
                "content": self.recommendation_lines(recommendation),
            },
            {
                "order": 8,
                "title": "AAIE-aannames gekoppeld aan rapport",
                "type": "aaie",
                "content": self.aaie_lines(aaie_links),
            },
            {
                "order": 9,
                "title": "Benodigd voor definitieve rapportage",
                "type": "required_before_final",
                "content": recommendation.get(
                    "required_before_final_design",
                    [
                        "Projectlocatie bevestigen.",
                        "Maaiveldpeil bepalen.",
                        "Grondwaterstand verifiëren.",
                        "Bodemonderzoek of sondering toevoegen.",
                        "Belastingen bepalen.",
                        "Constructieve berekening uitvoeren.",
                        "QA/QC uitvoeren.",
                    ],
                ),
            },
            {
                "order": 10,
                "title": "Standaard outputpakket",
                "type": "outputs",
                "content": [
                    "Projectrapport PDF.",
                    "Projectrapport DOCX.",
                    "HTML dashboard.",
                    "Digital Twin JSON.",
                    "AAIE aannameslog.",
                    "STEE bronregister.",
                    "Geo/Foundation analyse.",
                    "Funderingsvarianten F1/F2.",
                    "QA/QC rapport.",
                    "Project-ZIP.",
                    "Git Evidence.",
                ],
            },
        ]

    def geo_profile_lines(self, geo_defaults: Dict[str, Any]) -> List[str]:
        lines = [
            f"Status: {geo_defaults.get('status', 'onbekend')}",
            f"Grondwaterstand: {geo_defaults.get('groundwater_level', 'onbekend')}",
            f"Bron grondwaterstand: {geo_defaults.get('groundwater_source', 'onbekend')}",
            f"Fallback grondwaterstand: {geo_defaults.get('fallback_groundwater_level', 'P = -0,50 m')}",
            f"Automatische grondwaterdetectie: {geo_defaults.get('automatic_groundwater_detection', True)}",
            f"Automatisch geo-profiel: {geo_defaults.get('automatic_geo_profile', True)}",
        ]

        for item in geo_defaults.get("minimum_geo_profile", []):
            lines.append(
                f"{item.get('field', '')}: {item.get('default', '')} — bron: {item.get('source', '')}"
            )

        return lines

    def foundation_variant_lines(self, variants: List[Dict[str, Any]]) -> List[str]:
        lines = []

        for variant in variants:
            lines.append(f"{variant.get('code', '')} — {variant.get('name', '')}")
            lines.append(f"Type: {variant.get('type', '')}")
            lines.append(f"Omschrijving: {variant.get('description', '')}")

            dimensions = variant.get("default_dimensions", {})
            if dimensions:
                lines.append(f"Standaard dimensies: {json.dumps(dimensions, ensure_ascii=False, default=str)}")

            checks = variant.get("checks", [])
            if checks:
                lines.append(f"Checks: {', '.join(checks)}")

            lines.append("")

        return lines

    def foundation_comparison_lines(self, comparison: List[Dict[str, Any]]) -> List[str]:
        lines = []

        for row in comparison:
            lines.append(
                f"{row.get('code', '')} — {row.get('name', '')}: totaalscore {row.get('total_score', '')}"
            )

            scores = row.get("scores", {})
            for aspect, score_data in scores.items():
                lines.append(
                    f"- {aspect}: {score_data.get('score', '')}/5 — {score_data.get('note', '')}"
                )

            remarks = row.get("remarks", [])
            for remark in remarks:
                lines.append(f"Opmerking: {remark}")

            lines.append("")

        return lines

    def recommendation_lines(self, recommendation: Dict[str, Any]) -> List[str]:
        preferred = recommendation.get("preferred_variant_by_score", {})

        lines = [
            f"Status: {recommendation.get('status', 'VOORLOPIG')}",
            f"Voorlopige voorkeursvariant: {preferred.get('code', '')} — {preferred.get('name', '')}",
            f"Totaalscore: {preferred.get('total_score', '')}",
            recommendation.get(
                "important_note",
                "Definitieve funderingskeuze vereist projectlasten, bodemonderzoek en constructieve berekening.",
            ),
        ]

        return lines

    def aaie_lines(self, aaie_links: List[Dict[str, Any]]) -> List[str]:
        if not aaie_links:
            return ["Geen AAIE-links gevonden."]

        lines = []

        for item in aaie_links:
            lines.append(
                f"{item.get('code', '')} — {item.get('name', '')} — discipline: {item.get('discipline', '')}"
            )

        return lines

    def dict_to_lines(self, data: Dict[str, Any]) -> List[str]:
        if not data:
            return ["Geen projectcontext opgegeven."]

        lines = []

        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, ensure_ascii=False, default=str)
            else:
                value_text = str(value)

            lines.append(f"{key}: {value_text}")

        return lines

    def build_markdown_report(self, sections: List[Dict[str, Any]]) -> str:
        lines = [
            "# PROJECT PHOENIX / BAOEES PROJECTRAPPORT",
            "",
            f"Automatisch gegenereerd: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "> Concept startpakket. Definitieve engineering vereist projectdata, controle en goedkeuring.",
            "",
        ]

        for section in sections:
            lines.append(f"## {section.get('order')}. {section.get('title')}")
            lines.append("")

            for item in section.get("content", []):
                lines.append(f"- {item}")

            lines.append("")

        return "\n".join(lines)

    def build_html_report(self, sections: List[Dict[str, Any]]) -> str:
        section_html = []

        for section in sections:
            items = []
            for item in section.get("content", []):
                items.append(f"<li>{self.esc(item)}</li>")

            section_html.append(
                f"""
                <section class="card">
                  <h2>{self.esc(section.get("order", ""))}. {self.esc(section.get("title", ""))}</h2>
                  <ul>
                    {''.join(items)}
                  </ul>
                </section>
                """
            )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix Projectrapport BIB</title>
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
      display: grid;
      gap: 18px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 20px;
    }}
    h2 {{
      color: #bfdbfe;
    }}
    li {{
      margin-bottom: 8px;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX / BAOEES PROJECTRAPPORT</h1>
    <p>Automatisch rapport-startpakket vanuit BIB, AAIE en Geo/Foundation.</p>
  </header>
  <main>
    {''.join(section_html)}
  </main>
</body>
</html>
"""

    def build_warnings(
        self,
        geo_data: Dict[str, Any],
        report_sections: List[Dict[str, Any]],
    ) -> List[str]:
        warnings = []

        if not geo_data:
            warnings.append("Geo/Foundation analyse ontbreekt of kon niet worden gelezen.")

        if not report_sections:
            warnings.append("Geen rapportsecties opgebouwd.")

        section_titles = [section.get("title") for section in report_sections]

        required = [
            "Managementsamenvatting",
            "Projectgegevens",
            "Geo-profiel startwaarden",
            "Funderingsvarianten",
            "Funderingsvergelijking",
            "AAIE-aannames gekoppeld aan rapport",
        ]

        for title in required:
            if title not in section_titles:
                warnings.append(f"Verplicht rapporthoofdstuk ontbreekt: {title}")

        if not warnings:
            warnings.append("Geen kritieke Project Report BIB-waarschuwingen.")

        return warnings

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default Project Phoenix Report",
            "project_type": "bouw",
            "purpose": "Automatisch projectrapport-startpakket vanuit BIB.",
            "location": "nog niet opgegeven",
            "phase": "concept",
        }

    def read_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = ProjectReportBibEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()