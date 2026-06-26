from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Veilig maken voor direct starten én module-start.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.bib_export_engine.bib_knowledge_source import BibKnowledgeSourceEngine


class BibProjectAnalyzerBridge:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Project Analyzer Bridge v3.7

    Doel:
    - Leest de BIB Knowledge Source.
    - Zet BIB-kennis om naar bruikbare context voor BAOEES Project Analyzer.
    - Maakt een JSON-bridgebestand.
    - Maakt een HTML-controlepagina.
    - Wijzigt de bestaande Project Analyzer nog niet.
    """

    ENGINE_NAME = "Project Phoenix BIB Project Analyzer Bridge"
    ENGINE_VERSION = "v3.7"

    def __init__(
        self,
        output_root: Optional[str | Path] = None,
        bib_context_path: Optional[str | Path] = None,
    ) -> None:
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"
        self.bib_context_path = (
            Path(bib_context_path)
            if bib_context_path
            else self.output_root / "bib_project_analysis_context.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or self.default_project_context()

        knowledge_source_result = self.ensure_bib_context(project_context=project_context)
        bib_context = self.read_json(self.bib_context_path)

        analyzer_context = self.build_project_analyzer_context(
            bib_context=bib_context,
            project_context=project_context,
        )

        bridge_path = self.output_root / "bib_project_analyzer_bridge.json"
        html_path = self.output_root / "bib_project_analyzer_context.html"

        bridge_result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "BIB-context geschikt maken voor BAOEES Project Analyzer.",
            "project_context": project_context,
            "knowledge_source_result": knowledge_source_result,
            "bib_context_path": str(self.bib_context_path),
            "project_analyzer_context": analyzer_context,
            "outputs": {
                "bridge_path": str(bridge_path),
                "html_path": str(html_path),
            },
            "warnings": self.build_warnings(bib_context, analyzer_context),
            "recommendation": self.build_recommendation(),
            "extra_results": extra_results,
        }

        self.write_json(bridge_path, bridge_result)
        html_path.write_text(
            self.build_html_report(bridge_result),
            encoding="utf-8",
        )

        return bridge_result

    def ensure_bib_context(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zorgt dat bib_project_analysis_context.json bestaat.
        Als het ontbreekt, wordt de BibKnowledgeSourceEngine gedraaid.
        """

        if self.bib_context_path.exists():
            return {
                "status": "AANWEZIG",
                "message": "BIB project analysis context bestond al.",
                "path": str(self.bib_context_path),
            }

        engine = BibKnowledgeSourceEngine(output_root=self.output_root)
        result = engine.run(project_context=project_context)

        return {
            "status": "GEGENEREERD",
            "message": "BIB project analysis context is opnieuw gegenereerd.",
            "path": str(self.bib_context_path),
            "source_engine_result": result,
        }

    def build_project_analyzer_context(
        self,
        bib_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        relevant_by_topic = bib_context.get("relevant_by_topic", {})
        core_sections = bib_context.get("core_sections", [])

        context = {
            "status": "GEREED",
            "for_engine": "BAOEES Project Analyzer",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_context": project_context,
            "core_bib_sections": core_sections,
            "topic_context": relevant_by_topic,
            "mandatory_project_analyzer_rules": self.mandatory_rules(),
            "automatic_geo_foundation_rules": self.automatic_geo_foundation_rules(),
            "aaie_rules": self.aaie_rules(),
            "stee_rules": self.stee_rules(),
            "default_outputs": self.default_outputs(),
            "project_type_hints": self.project_type_hints(project_context),
            "recommended_project_analyzer_steps": self.recommended_project_analyzer_steps(),
        }

        return context

    def mandatory_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "rule": "Digital Twin First",
                "description": "Alle rapporten, tekeningen, berekeningen, vergunningstukken, kosten en exports moeten voortkomen uit dezelfde centrale projectdata.",
                "required": True,
            },
            {
                "rule": "AAIE assumptions visible",
                "description": "Alle automatisch gegenereerde waarden moeten zichtbaar in het aannameslog komen.",
                "required": True,
            },
            {
                "rule": "STEE source evidence required",
                "description": "Elke bron of fallback moet herleidbaar zijn via STEE of als AAIE fallback assumption worden gemarkeerd.",
                "required": True,
            },
            {
                "rule": "Foundation variants required",
                "description": "Voor bouwprojecten standaard F1 strokenfundering en F2 paalfundering genereren en vergelijken.",
                "required": True,
            },
            {
                "rule": "No final export without QA/QC",
                "description": "Een projectexport is pas volledig als QA/QC is uitgevoerd.",
                "required": True,
            },
        ]

    def automatic_geo_foundation_rules(self) -> Dict[str, Any]:
        return {
            "status": "ACTIEF",
            "groundwater": {
                "automatic_detection": True,
                "fallback_value": "P = -0,50 m",
                "fallback_status": "AAIE fallback assumption",
                "sources_to_check": [
                    "projectlocatie",
                    "kaartuitsnede",
                    "Google Maps of satellietbeeld",
                    "maaiveldinformatie",
                    "bodemdata",
                    "nabijheid oppervlaktewater",
                    "eerdere projectdata",
                    "handmatige gebruikersinput",
                ],
            },
            "geo_profile": {
                "automatic_generation": True,
                "minimum_output": [
                    "maaiveldniveau",
                    "grondwaterstand",
                    "globale bodemopbouw",
                    "grondsoort per laag",
                    "draagkrachtindicatie",
                    "zettingsgevoeligheid",
                    "risico-indicatie",
                    "advies vervolgonderzoek",
                ],
            },
            "foundation_variants": [
                {
                    "code": "F1",
                    "name": "Strokenfundering",
                    "description": "Fundering op staal met stroken onder dragende wanden en kolommen.",
                    "default_dimensions": {
                        "strookbreedte": "150 cm tot 200 cm",
                        "strookhoogte": "40 cm",
                        "funderingsbalk": "50 cm x 60 cm",
                        "ligging_balk": "hart van strook",
                    },
                    "checks": [
                        "draagkracht",
                        "zetting",
                        "grondwaterinvloed",
                        "uitvoerbaarheid",
                        "kosten",
                        "bouwrisico",
                    ],
                },
                {
                    "code": "F2",
                    "name": "Paalfundering",
                    "description": "Diepe fundering op palen bij slappe bodem, onvoldoende draagkracht of verhoogd zettingsrisico.",
                    "checks": [
                        "paallengte",
                        "paaltype",
                        "draagkracht per paal",
                        "paalbelasting",
                        "paalafstand",
                        "kosten",
                        "uitvoerbaarheid",
                    ],
                },
            ],
            "comparison_required": True,
            "comparison_aspects": [
                "draagkracht",
                "zetting",
                "kosten",
                "bouwtijd",
                "risico",
                "bodemgeschiktheid",
                "grondwaterinvloed",
                "constructieve haalbaarheid",
                "vergunning / acceptatie",
            ],
        }

    def aaie_rules(self) -> Dict[str, Any]:
        return {
            "engine": "AAIE",
            "meaning": "Autonomous Assumption and Inference Engine",
            "must_register": [
                "naam",
                "waarde",
                "discipline",
                "reden",
                "bron",
                "methode",
                "betrouwbaarheid",
                "datum/tijd",
                "status",
                "gebruiker kan aanpassen",
            ],
            "confidence_levels": [
                "hoog",
                "middel",
                "laag",
                "onbekend",
            ],
            "important_fallbacks": {
                "grondwaterstand": "P = -0,50 m",
                "fundering": "altijd F1 strokenfundering en F2 paalfundering genereren",
            },
        }

    def stee_rules(self) -> Dict[str, Any]:
        return {
            "engine": "STEE",
            "meaning": "Source Traceability and Evidence Engine",
            "must_register": [
                "bronnaam",
                "bronbestand of URL",
                "type bron",
                "discipline",
                "projectonderdeel",
                "datum/tijd",
                "betrouwbaarheid",
                "gebruikte waarde",
                "relatie met rapport",
                "relatie met tekening",
                "relatie met berekening",
                "relatie met aanname",
            ],
            "fallback_without_source": "AAIE fallback assumption",
            "principle": "Geen eindrapport zonder bronvermelding.",
        }

    def default_outputs(self) -> List[str]:
        return [
            "projectanalyse",
            "Digital Twin JSON",
            "aannameslog",
            "bronregister",
            "5 ontwerpvarianten A t/m E",
            "funderingsvarianten F1 en F2",
            "projectrapport PDF",
            "projectrapport DOCX",
            "tekeningen",
            "CAD/DXF",
            "QA/QC rapport",
            "HTML dashboard",
            "project-ZIP",
            "Git Evidence",
        ]

    def project_type_hints(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        text = json.dumps(project_context, ensure_ascii=False, default=str).lower()

        hints = {
            "bouw": any(term in text for term in ["woning", "gebouw", "uitbreiding", "moskee", "kantoor"]),
            "vergunning": any(term in text for term in ["vergunning", "bopa", "omgevingsvergunning", "aerius"]),
            "gebiedsontwikkeling": any(term in text for term in ["masterplan", "gebied", "waterfront", "kavel"]),
            "infra": any(term in text for term in ["parkeren", "verkeer", "weg", "riolering", "afwatering"]),
            "geotechniek": any(term in text for term in ["fundering", "grondwater", "bodem", "sondering"]),
        }

        return {
            "detected_hints": hints,
            "recommendation": "Gebruik deze hints als eerste classificatie, daarna project_analyzer laten bevestigen.",
        }

    def recommended_project_analyzer_steps(self) -> List[str]:
        return [
            "Laad BIB project analyzer context.",
            "Classificeer projecttype.",
            "Bepaal benodigde disciplines.",
            "Laad relevante BIB-topicsecties.",
            "Voer AAIE-aanvulling uit voor ontbrekende gegevens.",
            "Registreer bronnen en fallbacks via STEE.",
            "Maak Digital Twin basisobjecten.",
            "Genereer ontwerpvarianten A t/m E.",
            "Genereer funderingsvarianten F1 en F2.",
            "Maak outputlijst.",
            "Voer QA/QC uit.",
            "Maak dashboard, ZIP en Git Evidence.",
        ]

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default Project Phoenix Analysis Context",
            "purpose": "Standaard context voor het testen van de BIB Project Analyzer Bridge.",
            "project_type": "generic",
            "requires": [
                "projectanalyse",
                "AAIE",
                "STEE",
                "Digital Twin",
                "grondwaterstand",
                "funderingsvarianten",
                "QA/QC",
            ],
        }

    def build_warnings(
        self,
        bib_context: Dict[str, Any],
        analyzer_context: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not bib_context:
            warnings.append("BIB-context ontbreekt of kon niet worden gelezen.")

        topic_context = analyzer_context.get("topic_context", {})

        required_topics = [
            "core_system",
            "geotechniek_fundering",
            "aannames_aaie",
            "bronnen_stee",
            "exports",
        ]

        for topic in required_topics:
            if not topic_context.get(topic):
                warnings.append(f"Geen topic-context gevonden voor: {topic}")

        if not analyzer_context.get("automatic_geo_foundation_rules"):
            warnings.append("Automatic geo/foundation rules ontbreken.")

        if not warnings:
            warnings.append("Geen kritieke BIB Project Analyzer Bridge-waarschuwingen.")

        return warnings

    def build_recommendation(self) -> Dict[str, Any]:
        return {
            "status": "BIB_PROJECT_ANALYZER_BRIDGE_ADVIES",
            "advice": [
                "Controleer bib_project_analyzer_bridge.json.",
                "Open bib_project_analyzer_context.html.",
                "Gebruik deze bridge in v3.8 om project_analyzer/main.py veilig te koppelen.",
                "Laat project_analyzer voortaan eerst BIB-context laden voordat analyse begint.",
                "Gebruik automatic_geo_foundation_rules voor grondwater en funderingsvarianten.",
            ],
        }

    def build_html_report(self, bridge_result: Dict[str, Any]) -> str:
        analyzer_context = bridge_result.get("project_analyzer_context", {})
        rules = analyzer_context.get("mandatory_project_analyzer_rules", [])
        outputs = analyzer_context.get("default_outputs", [])
        foundation = analyzer_context.get("automatic_geo_foundation_rules", {})
        topic_context = analyzer_context.get("topic_context", {})

        rule_rows = []
        for rule in rules:
            rule_rows.append(
                "<tr>"
                f"<td>{self.esc(rule.get('rule', ''))}</td>"
                f"<td>{self.esc(rule.get('description', ''))}</td>"
                f"<td>{self.esc(rule.get('required', ''))}</td>"
                "</tr>"
            )

        output_rows = []
        for output in outputs:
            output_rows.append(f"<tr><td>{self.esc(output)}</td></tr>")

        topic_rows = []
        for topic, sections in topic_context.items():
            topic_rows.append(
                "<tr>"
                f"<td>{self.esc(topic)}</td>"
                f"<td>{self.esc(len(sections))}</td>"
                f"<td>{self.esc(', '.join([item.get('heading', '') for item in sections[:5]]))}</td>"
                "</tr>"
            )

        foundation_variants = foundation.get("foundation_variants", [])
        foundation_rows = []
        for variant in foundation_variants:
            foundation_rows.append(
                "<tr>"
                f"<td>{self.esc(variant.get('code', ''))}</td>"
                f"<td>{self.esc(variant.get('name', ''))}</td>"
                f"<td>{self.esc(variant.get('description', ''))}</td>"
                f"<td>{self.esc(', '.join(variant.get('checks', [])))}</td>"
                "</tr>"
            )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB Project Analyzer Bridge</title>
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
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX BIB PROJECT ANALYZER BRIDGE</h1>
    <p>BIB-context voorbereid voor BAOEES Project Analyzer</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(bridge_result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Engine</h3>
        <p>{self.esc(self.ENGINE_NAME)} {self.esc(self.ENGINE_VERSION)}</p>
      </div>
      <div class="card">
        <h3>BIB-context</h3>
        <p>{self.esc(bridge_result.get("bib_context_path", ""))}</p>
      </div>
    </section>

    <h2>Verplichte Project Analyzer regels</h2>
    <table>
      <thead>
        <tr>
          <th>Regel</th>
          <th>Omschrijving</th>
          <th>Verplicht</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rule_rows)}
      </tbody>
    </table>

    <h2>Funderingsvarianten</h2>
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Naam</th>
          <th>Omschrijving</th>
          <th>Checks</th>
        </tr>
      </thead>
      <tbody>
        {''.join(foundation_rows)}
      </tbody>
    </table>

    <h2>Topic-context uit BIB</h2>
    <table>
      <thead>
        <tr>
          <th>Topic</th>
          <th>Aantal secties</th>
          <th>Topsecties</th>
        </tr>
      </thead>
      <tbody>
        {''.join(topic_rows)}
      </tbody>
    </table>

    <h2>Default outputs</h2>
    <table>
      <tbody>
        {''.join(output_rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""

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
    bridge = BibProjectAnalyzerBridge()
    result = bridge.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()