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

from baoees.project_analyzer.bib_context_loader import ProjectAnalyzerBibContextLoader


class AaieBibAssumptionLoader:
    """
    PROJECT PHOENIX / BAOEES V3
    AAIE BIB Assumption Loader v3.9

    Doel:
    - Leest de Project Analyzer BIB-context.
    - Zet BIB-regels om naar AAIE-aannames.
    - Legt standaardwaarden vast voor grondwater, geo, fundering, QA/QC, STEE en outputs.
    - Maakt JSON- en HTML-output voor controle.
    """

    ENGINE_NAME = "Project Phoenix AAIE BIB Assumption Loader"
    ENGINE_VERSION = "v3.9"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        context_path: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.context_path = (
            Path(context_path)
            if context_path
            else self.project_output_root / "project_analyzer_bib_context.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh_context: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        context_status = self.ensure_project_analyzer_context(
            project_context=project_context,
            force_refresh_context=force_refresh_context,
        )

        context_data = self.read_json(self.context_path)
        defaults = context_data.get("project_input_defaults", {})
        analyzer_context = context_data.get("project_analyzer_context", {})

        assumptions = self.build_assumptions(
            defaults=defaults,
            analyzer_context=analyzer_context,
            project_context=project_context or {},
        )

        output_json_path = self.project_output_root / "aaie_bib_assumptions.json"
        output_html_path = self.project_output_root / "aaie_bib_assumptions.html"

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "AAIE automatisch voeden met aannames uit de BIB-context.",
            "context_status": context_status,
            "context_path": str(self.context_path),
            "project_output_root": str(self.project_output_root),
            "assumption_count": len(assumptions),
            "assumptions": assumptions,
            "assumption_register": self.build_assumption_register(assumptions),
            "warnings": self.build_warnings(assumptions, defaults),
            "recommendation": self.build_recommendation(),
            "outputs": {
                "json_path": str(output_json_path),
                "html_path": str(output_html_path),
            },
            "extra_results": extra_results,
        }

        self.write_json(output_json_path, result)
        output_html_path.write_text(
            self.build_html_report(result),
            encoding="utf-8",
        )

        return result

    def ensure_project_analyzer_context(
        self,
        project_context: Optional[Dict[str, Any]],
        force_refresh_context: bool,
    ) -> Dict[str, Any]:
        if self.context_path.exists() and not force_refresh_context and not project_context:
            return {
                "status": "AANWEZIG",
                "message": "Project Analyzer BIB-context bestond al.",
                "path": str(self.context_path),
            }

        loader = ProjectAnalyzerBibContextLoader(project_output_root=self.project_output_root)
        loader_result = loader.run(
            project_context=project_context or self.default_project_context(),
            force_refresh_bridge=force_refresh_context,
        )

        return {
            "status": "GEGENEREERD",
            "message": "Project Analyzer BIB-context is gegenereerd of vernieuwd.",
            "path": str(self.context_path),
            "loader_result_status": loader_result.get("status"),
        }

    def build_assumptions(
        self,
        defaults: Dict[str, Any],
        analyzer_context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        assumptions: List[Dict[str, Any]] = []

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-001",
                name="Digital Twin First",
                value=defaults.get("digital_twin_first", True),
                discipline="system",
                reason="BIB-regel: alle projectoutputs moeten uit dezelfde centrale projectdata komen.",
                confidence="hoog",
                source_field="project_input_defaults.digital_twin_first",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-002",
                name="AAIE actief",
                value=defaults.get("aaie_enabled", True),
                discipline="system",
                reason="Ontbrekende projectgegevens moeten automatisch worden aangevuld met aannameslog.",
                confidence="hoog",
                source_field="project_input_defaults.aaie_enabled",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-003",
                name="STEE actief",
                value=defaults.get("stee_enabled", True),
                discipline="source_evidence",
                reason="Bronnen, fallbacks en aannames moeten traceerbaar zijn.",
                confidence="hoog",
                source_field="project_input_defaults.stee_enabled",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-004",
                name="QA/QC verplicht",
                value=defaults.get("qa_qc_required", True),
                discipline="quality",
                reason="Geen volledige projectexport zonder QA/QC-controle.",
                confidence="hoog",
                source_field="project_input_defaults.qa_qc_required",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-005",
                name="Automatische grondwaterdetectie",
                value=defaults.get("automatic_groundwater_detection", True),
                discipline="geotechniek",
                reason="BAOEES moet grondwaterstand automatisch proberen te bepalen uit locatie, kaart, bodemdata en projectcontext.",
                confidence="middel",
                source_field="project_input_defaults.automatic_groundwater_detection",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-006",
                name="Fallback grondwaterstand",
                value=defaults.get("groundwater_fallback", "P = -0,50 m"),
                discipline="geotechniek",
                reason="Wanneer projectdata ontbreken, gebruikt AAIE de BIB fallback grondwaterstand.",
                confidence="middel",
                source_field="project_input_defaults.groundwater_fallback",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-007",
                name="Status fallback grondwaterstand",
                value=defaults.get("groundwater_fallback_status", "AAIE fallback assumption"),
                discipline="geotechniek",
                reason="Fallbackwaarde moet zichtbaar als AAIE-aanname worden gemarkeerd.",
                confidence="hoog",
                source_field="project_input_defaults.groundwater_fallback_status",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-008",
                name="Automatisch geo-profiel",
                value=defaults.get("automatic_geo_profile", True),
                discipline="geotechniek",
                reason="BAOEES moet een voorlopig geo-profiel kunnen maken op basis van beschikbare locatie- en bodemgegevens.",
                confidence="middel",
                source_field="project_input_defaults.automatic_geo_profile",
            )
        )

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-009",
                name="Funderingsvarianten verplicht",
                value=defaults.get("foundation_variants_required", True),
                discipline="fundering",
                reason="Voor bouwprojecten moeten minimaal F1 strokenfundering en F2 paalfundering worden vergeleken.",
                confidence="hoog",
                source_field="project_input_defaults.foundation_variants_required",
            )
        )

        foundation_variants = defaults.get("foundation_variants", [])

        for index, variant in enumerate(foundation_variants, start=1):
            assumptions.append(
                self.make_assumption(
                    code=f"AAIE-BIB-F{index:02d}",
                    name=f"Funderingsvariant {variant.get('code', index)} - {variant.get('name', '')}",
                    value=variant,
                    discipline="fundering",
                    reason="Funderingsvariant overgenomen uit BIB Project Analyzer Context.",
                    confidence="hoog",
                    source_field="project_input_defaults.foundation_variants",
                )
            )

        default_outputs = defaults.get("default_outputs", [])

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-010",
                name="Standaard projectoutputs",
                value=default_outputs,
                discipline="output",
                reason="BAOEES moet standaard projectanalyse, rapporten, tekeningen, QA/QC, dashboard, ZIP en Git Evidence voorbereiden.",
                confidence="hoog",
                source_field="project_input_defaults.default_outputs",
            )
        )

        mandatory_rules = analyzer_context.get("mandatory_project_analyzer_rules", [])

        assumptions.append(
            self.make_assumption(
                code="AAIE-BIB-011",
                name="Verplichte Project Analyzer regels",
                value=mandatory_rules,
                discipline="system",
                reason="Project Analyzer moet de verplichte BIB-regels gebruiken als basiscontrole.",
                confidence="hoog",
                source_field="project_analyzer_context.mandatory_project_analyzer_rules",
            )
        )

        if project_context:
            assumptions.append(
                self.make_assumption(
                    code="AAIE-BIB-012",
                    name="Projectcontext ontvangen",
                    value=project_context,
                    discipline="project",
                    reason="Specifieke projectcontext is meegegeven en wordt opgenomen in het aannamesregister.",
                    confidence="hoog",
                    source_field="runtime.project_context",
                )
            )

        return assumptions

    def make_assumption(
        self,
        code: str,
        name: str,
        value: Any,
        discipline: str,
        reason: str,
        confidence: str,
        source_field: str,
    ) -> Dict[str, Any]:
        return {
            "code": code,
            "name": name,
            "value": value,
            "discipline": discipline,
            "reason": reason,
            "source": {
                "type": "BIB Project Analyzer Context",
                "path": str(self.context_path),
                "field": source_field,
            },
            "method": "automatic_from_bib_context",
            "confidence": confidence,
            "status": "ACTIVE",
            "editable_by_user": True,
            "registered_at": datetime.now().isoformat(timespec="seconds"),
        }

    def build_assumption_register(self, assumptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_discipline: Dict[str, int] = {}

        for assumption in assumptions:
            discipline = assumption.get("discipline", "unknown")
            by_discipline[discipline] = by_discipline.get(discipline, 0) + 1

        return {
            "status": "GEREED",
            "total": len(assumptions),
            "by_discipline": by_discipline,
            "must_be_written_to_project": True,
            "must_be_visible_in_reports": True,
            "must_be_linked_to_stee": True,
        }

    def build_warnings(
        self,
        assumptions: List[Dict[str, Any]],
        defaults: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not assumptions:
            warnings.append("Geen AAIE BIB-aannames opgebouwd.")

        if not defaults:
            warnings.append("Project input defaults ontbreken.")

        required_names = [
            "Fallback grondwaterstand",
            "Funderingsvarianten verplicht",
            "AAIE actief",
            "STEE actief",
            "QA/QC verplicht",
        ]

        assumption_names = [item.get("name") for item in assumptions]

        for name in required_names:
            if name not in assumption_names:
                warnings.append(f"Verplichte AAIE-aanname ontbreekt: {name}")

        if not warnings:
            warnings.append("Geen kritieke AAIE BIB assumption-waarschuwingen.")

        return warnings

    def build_recommendation(self) -> Dict[str, Any]:
        return {
            "status": "AAIE_BIB_ASSUMPTION_ADVIES",
            "advice": [
                "Open aaie_bib_assumptions.html en controleer de aannames.",
                "Gebruik aaie_bib_assumptions.json in v4.0 voor Geo/Fundering integratie.",
                "Laat ieder project deze aannames als start-aannames laden.",
                "Zorg dat iedere aanname later zichtbaar is in rapport, dashboard en STEE-register.",
            ],
        }

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default AAIE BIB Assumption Context",
            "project_type": "generic",
            "purpose": "Testen van automatische AAIE-aannames vanuit BIB.",
        }

    def build_html_report(self, result: Dict[str, Any]) -> str:
        assumptions = result.get("assumptions", [])
        register = result.get("assumption_register", {})

        rows = []

        for assumption in assumptions:
            value = assumption.get("value")

            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
            else:
                value_text = str(value)

            rows.append(
                "<tr>"
                f"<td>{self.esc(assumption.get('code', ''))}</td>"
                f"<td>{self.esc(assumption.get('name', ''))}</td>"
                f"<td>{self.esc(assumption.get('discipline', ''))}</td>"
                f"<td>{self.esc(value_text[:500])}</td>"
                f"<td>{self.esc(assumption.get('confidence', ''))}</td>"
                f"<td>{self.esc(assumption.get('reason', ''))}</td>"
                "</tr>"
            )

        discipline_rows = []

        for discipline, count in register.get("by_discipline", {}).items():
            discipline_rows.append(
                "<tr>"
                f"<td>{self.esc(discipline)}</td>"
                f"<td>{self.esc(count)}</td>"
                "</tr>"
            )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>AAIE BIB Assumptions</title>
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
    code {{
      color: #cbd5e1;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <header>
    <h1>AAIE BIB ASSUMPTIONS</h1>
    <p>Autonomous Assumption & Inference Engine gevoed vanuit de Brewster Integrated Bibliotheek.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Aannames</h3>
        <p>{self.esc(result.get("assumption_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Context</h3>
        <p class="muted">{self.esc(result.get("context_path", ""))}</p>
      </div>
    </section>

    <h2>Aannames per discipline</h2>
    <table>
      <thead>
        <tr>
          <th>Discipline</th>
          <th>Aantal</th>
        </tr>
      </thead>
      <tbody>
        {''.join(discipline_rows)}
      </tbody>
    </table>

    <h2>AAIE-aannames uit BIB</h2>
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Naam</th>
          <th>Discipline</th>
          <th>Waarde</th>
          <th>Betrouwbaarheid</th>
          <th>Reden</th>
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
    loader = AaieBibAssumptionLoader()
    result = loader.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()