from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Veilig voor module-start én directe start.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.bib_export_engine.bib_project_analyzer_bridge import BibProjectAnalyzerBridge


class ProjectAnalyzerBibContextLoader:
    """
    PROJECT PHOENIX / BAOEES V3
    Project Analyzer BIB Context Loader v3.8

    Doel:
    - Laat BAOEES Project Analyzer automatisch BIB-context lezen.
    - Gebruikt de BIB Project Analyzer Bridge v3.7 als bron.
    - Controleert of de verplichte context aanwezig is.
    - Schrijft een JSON-context en HTML-controlepagina voor de Project Analyzer.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer BIB Context Loader"
    ENGINE_VERSION = "v3.8"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        bib_output_root: Optional[str | Path] = None,
        bridge_path: Optional[str | Path] = None,
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
        self.bridge_path = (
            Path(bridge_path)
            if bridge_path
            else self.bib_output_root / "bib_project_analyzer_bridge.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh_bridge: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)
        self.bib_output_root.mkdir(parents=True, exist_ok=True)

        bridge_status = self.ensure_bridge_context(
            project_context=project_context,
            force_refresh_bridge=force_refresh_bridge,
        )

        bridge_data = self.read_json(self.bridge_path)
        project_analyzer_context = bridge_data.get("project_analyzer_context", {})

        validation = self.validate_context(project_analyzer_context)
        boot_sequence = self.build_boot_sequence(project_analyzer_context)
        project_input_defaults = self.build_project_input_defaults(project_analyzer_context)

        output_json_path = self.project_output_root / "project_analyzer_bib_context.json"
        output_html_path = self.project_output_root / "project_analyzer_bib_context.html"

        result = {
            "status": "GEREED" if validation["ready"] else "WARNING",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "BAOEES Project Analyzer automatisch voeden met BIB-context.",
            "bridge_status": bridge_status,
            "bridge_path": str(self.bridge_path),
            "project_output_root": str(self.project_output_root),
            "bib_output_root": str(self.bib_output_root),
            "ready_for_project_analyzer": validation["ready"],
            "validation": validation,
            "project_analyzer_boot_sequence": boot_sequence,
            "project_input_defaults": project_input_defaults,
            "project_analyzer_context": project_analyzer_context,
            "outputs": {
                "json_path": str(output_json_path),
                "html_path": str(output_html_path),
            },
            "warnings": self.build_warnings(validation, project_analyzer_context),
            "recommendation": self.build_recommendation(validation),
            "extra_results": extra_results,
        }

        self.write_json(output_json_path, result)
        output_html_path.write_text(
            self.build_html_report(result),
            encoding="utf-8",
        )

        return result

    def ensure_bridge_context(
        self,
        project_context: Optional[Dict[str, Any]],
        force_refresh_bridge: bool,
    ) -> Dict[str, Any]:
        """
        Zorgt dat de BIB Project Analyzer Bridge bestaat.
        """

        if self.bridge_path.exists() and not force_refresh_bridge and not project_context:
            return {
                "status": "AANWEZIG",
                "message": "BIB Project Analyzer Bridge bestond al.",
                "path": str(self.bridge_path),
            }

        bridge = BibProjectAnalyzerBridge(output_root=self.bib_output_root)
        bridge_result = bridge.run(project_context=project_context or self.default_project_context())

        return {
            "status": "GEGENEREERD",
            "message": "BIB Project Analyzer Bridge is gegenereerd of vernieuwd.",
            "path": str(self.bridge_path),
            "bridge_result_status": bridge_result.get("status"),
        }

    def validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        required_keys = [
            "mandatory_project_analyzer_rules",
            "automatic_geo_foundation_rules",
            "aaie_rules",
            "stee_rules",
            "default_outputs",
            "recommended_project_analyzer_steps",
        ]

        checks = []

        for key in required_keys:
            value = context.get(key)
            ok = bool(value)
            checks.append(
                {
                    "name": f"Context key aanwezig: {key}",
                    "key": key,
                    "status": "OK" if ok else "FAILED",
                    "message": "Aanwezig." if ok else "Ontbreekt of is leeg.",
                }
            )

        geo = context.get("automatic_geo_foundation_rules", {})
        groundwater = geo.get("groundwater", {})
        variants = geo.get("foundation_variants", [])

        checks.append(
            {
                "name": "Grondwater fallback aanwezig",
                "key": "groundwater.fallback_value",
                "status": "OK" if groundwater.get("fallback_value") else "FAILED",
                "message": groundwater.get("fallback_value", "Ontbreekt."),
            }
        )

        variant_codes = [variant.get("code") for variant in variants]

        checks.append(
            {
                "name": "F1 strokenfundering aanwezig",
                "key": "foundation_variants.F1",
                "status": "OK" if "F1" in variant_codes else "FAILED",
                "message": "F1 aanwezig." if "F1" in variant_codes else "F1 ontbreekt.",
            }
        )

        checks.append(
            {
                "name": "F2 paalfundering aanwezig",
                "key": "foundation_variants.F2",
                "status": "OK" if "F2" in variant_codes else "FAILED",
                "message": "F2 aanwezig." if "F2" in variant_codes else "F2 ontbreekt.",
            }
        )

        failed = [check for check in checks if check["status"] == "FAILED"]

        return {
            "ready": len(failed) == 0,
            "total_checks": len(checks),
            "failed_count": len(failed),
            "checks": checks,
        }

    def build_boot_sequence(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps = context.get("recommended_project_analyzer_steps", [])

        if not steps:
            steps = [
                "Laad BIB-context.",
                "Classificeer projecttype.",
                "Laad AAIE, STEE en Digital Twin regels.",
                "Bepaal outputs.",
                "Voer QA/QC uit.",
            ]

        return [
            {
                "step": index + 1,
                "action": step,
                "source": "BIB Project Analyzer Context",
                "required": True,
            }
            for index, step in enumerate(steps)
        ]

    def build_project_input_defaults(self, context: Dict[str, Any]) -> Dict[str, Any]:
        geo = context.get("automatic_geo_foundation_rules", {})
        groundwater = geo.get("groundwater", {})
        foundation_variants = geo.get("foundation_variants", [])

        return {
            "digital_twin_first": True,
            "aaie_enabled": True,
            "stee_enabled": True,
            "qa_qc_required": True,
            "automatic_groundwater_detection": groundwater.get("automatic_detection", True),
            "groundwater_fallback": groundwater.get("fallback_value", "P = -0,50 m"),
            "groundwater_fallback_status": groundwater.get("fallback_status", "AAIE fallback assumption"),
            "automatic_geo_profile": geo.get("geo_profile", {}).get("automatic_generation", True),
            "foundation_variants_required": True,
            "foundation_variants": [
                {
                    "code": variant.get("code"),
                    "name": variant.get("name"),
                    "description": variant.get("description"),
                    "checks": variant.get("checks", []),
                    "default_dimensions": variant.get("default_dimensions", {}),
                }
                for variant in foundation_variants
            ],
            "default_outputs": context.get("default_outputs", []),
        }

    def build_warnings(
        self,
        validation: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not context:
            warnings.append("Project Analyzer context ontbreekt.")

        for check in validation.get("checks", []):
            if check.get("status") == "FAILED":
                warnings.append(check.get("message", "Onbekende validatiefout."))

        if not warnings:
            warnings.append("Geen kritieke Project Analyzer BIB Context-waarschuwingen.")

        return warnings

    def build_recommendation(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        if validation.get("ready"):
            advice = [
                "Project Analyzer BIB Context is gereed.",
                "Koppel in v3.9 deze loader aan de bestaande projectanalyse-start.",
                "Laat ieder nieuw project eerst project_analyzer_bib_context.json laden.",
                "Gebruik project_input_defaults als standaard analyse-instellingen.",
            ]
        else:
            advice = [
                "Los ontbrekende BIB-contextvelden op.",
                "Draai daarna opnieuw: python -m baoees.project_analyzer.bib_context_loader",
                "Koppel pas daarna aan de bestaande projectanalyse-start.",
            ]

        return {
            "status": "PROJECT_ANALYZER_BIB_CONTEXT_ADVIES",
            "ready": validation.get("ready"),
            "advice": advice,
        }

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default BAOEES Project Analyzer Context",
            "project_type": "generic",
            "purpose": "Automatisch laden van BIB-context voor projectanalyse.",
            "requires": [
                "Digital Twin",
                "AAIE",
                "STEE",
                "grondwaterstand",
                "funderingsvarianten",
                "QA/QC",
                "rapporten",
                "tekeningen",
                "project-ZIP",
            ],
        }

    def build_html_report(self, result: Dict[str, Any]) -> str:
        validation = result.get("validation", {})
        defaults = result.get("project_input_defaults", {})
        boot_sequence = result.get("project_analyzer_boot_sequence", [])

        check_rows = []
        for check in validation.get("checks", []):
            status = check.get("status", "")
            css = "ok" if status == "OK" else "bad"
            check_rows.append(
                "<tr>"
                f"<td>{self.esc(check.get('name', ''))}</td>"
                f"<td><span class='{css}'>{self.esc(status)}</span></td>"
                f"<td>{self.esc(check.get('message', ''))}</td>"
                "</tr>"
            )

        boot_rows = []
        for step in boot_sequence:
            boot_rows.append(
                "<tr>"
                f"<td>{self.esc(step.get('step', ''))}</td>"
                f"<td>{self.esc(step.get('action', ''))}</td>"
                f"<td>{self.esc(step.get('source', ''))}</td>"
                "</tr>"
            )

        variant_rows = []
        for variant in defaults.get("foundation_variants", []):
            variant_rows.append(
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
  <title>Project Analyzer BIB Context</title>
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
    .ok {{
      color: #86efac;
      font-weight: bold;
    }}
    .bad {{
      color: #fca5a5;
      font-weight: bold;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT ANALYZER BIB CONTEXT</h1>
    <p>BAOEES Project Analyzer leest automatisch de Brewster Integrated Bibliotheek-context.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Ready</h3>
        <p>{self.esc(result.get("ready_for_project_analyzer", ""))}</p>
      </div>
      <div class="card">
        <h3>Grondwater fallback</h3>
        <p>{self.esc(defaults.get("groundwater_fallback", ""))}</p>
      </div>
      <div class="card">
        <h3>Bron</h3>
        <p class="muted">{self.esc(result.get("bridge_path", ""))}</p>
      </div>
    </section>

    <h2>Validatie</h2>
    <table>
      <thead>
        <tr>
          <th>Controle</th>
          <th>Status</th>
          <th>Bericht</th>
        </tr>
      </thead>
      <tbody>
        {''.join(check_rows)}
      </tbody>
    </table>

    <h2>Project Analyzer Boot Sequence</h2>
    <table>
      <thead>
        <tr>
          <th>Stap</th>
          <th>Actie</th>
          <th>Bron</th>
        </tr>
      </thead>
      <tbody>
        {''.join(boot_rows)}
      </tbody>
    </table>

    <h2>Funderingsvarianten uit BIB</h2>
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
        {''.join(variant_rows)}
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
    loader = ProjectAnalyzerBibContextLoader()
    result = loader.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()