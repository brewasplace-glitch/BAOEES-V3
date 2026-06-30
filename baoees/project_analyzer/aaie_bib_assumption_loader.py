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


class AAIEBibAssumptionLoader:
    """
    PROJECT PHOENIX / BAOEES
    AAIE BIB Assumption Loader v5.8

    Doel:
    - AAIE laat eerst de lokale BIB-kennisindex zoeken.
    - Bestaande BIB-kennis krijgt voorrang boven nieuwe aannames.
    - Nieuwe aannames worden alleen aanvullend gemaakt.
    - Elke aanname krijgt bronstatus, betrouwbaarheid en herkomst.
    - Output wordt geschreven naar:
      outputs/projects/aaie_bib_assumptions.json
      outputs/projects/aaie_bib_assumptions.html
    """

    ENGINE_NAME = "Project Phoenix AAIE BIB Assumption Loader"
    ENGINE_VERSION = "v5.8"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        bib_root: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else PROJECT_ROOT / "outputs" / "projects"
        )

        self.bib_root = (
            Path(bib_root)
            if bib_root
            else PROJECT_ROOT / "outputs" / "bib"
        )

        self.bib_knowledge_index_path = self.bib_root / "index" / "bib_knowledge_content_index.json"
        self.output_json_path = self.project_output_root / "aaie_bib_assumptions.json"
        self.output_html_path = self.project_output_root / "aaie_bib_assumptions.html"

    def run(self, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or {}
        bib_data = self.load_bib_knowledge_index()
        bib_lookup = self.build_bib_lookup(bib_data)
        assumptions = self.build_assumptions(project_context, bib_lookup)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "AAIE zoekt eerst in de lokale BIB voordat nieuwe aannames worden gemaakt.",
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "bib_root": str(self.bib_root),
            "bib_knowledge_index_path": str(self.bib_knowledge_index_path),
            "bib_status": bib_lookup.get("status", "ONBEKEND"),
            "bib_lookup": bib_lookup,
            "assumptions": assumptions,
            "assumption_count": len(assumptions),
            "source_priority": [
                "1. Lokale BIB-kennisindex",
                "2. Eerder bevestigde Project Phoenix / BAOEES kennis",
                "3. Standaard engineeringregels",
                "4. AAIE-aanvullende aannames",
            ],
            "next_steps": [
                "Controleer outputs/projects/aaie_bib_assumptions.html.",
                "Controleer of BIB-kennis als bron wordt weergegeven.",
                "Koppel deze AAIE-output verder aan Project Analyzer en rapportage.",
                "Laat toekomstige modules eerst BIB-kennis raadplegen voordat nieuwe aannames worden gemaakt.",
            ],
        }

        self.write_json(self.output_json_path, result)
        self.write_html(self.output_html_path, self.build_dashboard(result))

        return result

    def load_bib_knowledge_index(self) -> Dict[str, Any]:
        if not self.bib_knowledge_index_path.exists():
            return {
                "status": "ONTBREEKT",
                "message": "BIB-kennisindex is nog niet aanwezig.",
                "path": str(self.bib_knowledge_index_path),
                "recognized_text_items_count": 0,
                "projects": [],
                "categories": {},
                "technical_topics": {},
                "decisions_count": 0,
                "knowledge_items_count": 0,
                "actions_count": 0,
                "recognized_items": [],
            }

        try:
            return json.loads(self.bib_knowledge_index_path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(self.bib_knowledge_index_path.read_text(encoding="utf-8"))
            except Exception as error:
                return {
                    "status": "FOUT",
                    "message": f"BIB-kennisindex kon niet worden gelezen: {error}",
                    "path": str(self.bib_knowledge_index_path),
                    "recognized_text_items_count": 0,
                    "projects": [],
                    "categories": {},
                    "technical_topics": {},
                    "decisions_count": 0,
                    "knowledge_items_count": 0,
                    "actions_count": 0,
                    "recognized_items": [],
                }

    def build_bib_lookup(self, bib_data: Dict[str, Any]) -> Dict[str, Any]:
        recognized_items = bib_data.get("recognized_items", [])
        projects = bib_data.get("projects", [])
        categories = bib_data.get("categories", {})
        technical_topics = bib_data.get("technical_topics", {})

        decisions: List[str] = []
        knowledge_items: List[str] = []
        actions: List[str] = []

        for item in recognized_items:
            analysis = item.get("content_analysis", {})
            decisions.extend(analysis.get("decisions", []))
            knowledge_items.extend(analysis.get("knowledge_items", []))
            actions.extend(analysis.get("actions", []))

        if bib_data.get("status") in ["GEREED", "GELEZEN"]:
            status = "BIB_GEVONDEN"
        elif bib_data.get("status") == "ONTBREEKT":
            status = "BIB_ONTBREEKT"
        elif bib_data.get("status") == "FOUT":
            status = "BIB_FOUT"
        else:
            status = "BIB_ONBEKEND"

        return {
            "status": status,
            "source": str(self.bib_knowledge_index_path),
            "raw_status": bib_data.get("status", ""),
            "generated_at": bib_data.get("generated_at", ""),
            "recognized_text_items_count": bib_data.get("recognized_text_items_count", 0),
            "projects": projects,
            "categories": categories,
            "technical_topics": technical_topics,
            "decisions_count": len(decisions),
            "knowledge_items_count": len(knowledge_items),
            "actions_count": len(actions),
            "decisions": decisions,
            "knowledge_items": knowledge_items,
            "actions": actions,
        }

    def build_assumptions(
        self,
        project_context: Dict[str, Any],
        bib_lookup: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        assumptions: List[Dict[str, Any]] = []

        if bib_lookup.get("status") == "BIB_GEVONDEN":
            assumptions.extend(self.build_bib_based_assumptions(bib_lookup))
        else:
            assumptions.append(
                self.make_assumption(
                    key="bib_status",
                    value="Geen bruikbare BIB-kennisindex gevonden.",
                    source="AAIE v5.8 controle",
                    source_type="system_check",
                    reliability="laag",
                    method="fallback",
                    note="AAIE kan nog niet eerst uit BIB putten omdat de BIB-kennisindex ontbreekt of niet leesbaar is.",
                )
            )

        assumptions.extend(self.build_standard_project_assumptions(bib_lookup))
        assumptions.extend(self.build_context_assumptions(project_context))

        return assumptions

    def build_bib_based_assumptions(self, bib_lookup: Dict[str, Any]) -> List[Dict[str, Any]]:
        assumptions: List[Dict[str, Any]] = []

        projects = bib_lookup.get("projects", [])
        categories = bib_lookup.get("categories", {})
        technical_topics = bib_lookup.get("technical_topics", {})
        decisions = bib_lookup.get("decisions", [])
        knowledge_items = bib_lookup.get("knowledge_items", [])
        actions = bib_lookup.get("actions", [])

        assumptions.append(
            self.make_assumption(
                key="bib_first_policy",
                value="AAIE gebruikt eerst lokale BIB-kennis voordat nieuwe aannames worden gemaakt.",
                source=bib_lookup.get("source", ""),
                source_type="bib_knowledge_index",
                reliability="hoog",
                method="bib_lookup_first",
                note="Dit is de centrale wijziging van v5.8.",
            )
        )

        if projects:
            assumptions.append(
                self.make_assumption(
                    key="recognized_projects",
                    value=", ".join(projects),
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="hoog",
                    method="bib_project_recognition",
                    note="Projectnamen zijn uit de BIB-kennisindex gehaald.",
                )
            )

        if categories:
            assumptions.append(
                self.make_assumption(
                    key="recognized_bib_categories",
                    value=", ".join(categories.keys()),
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="hoog",
                    method="bib_category_recognition",
                    note="BIB-categorieën zijn uit intakebestanden herkend.",
                )
            )

        if technical_topics:
            assumptions.append(
                self.make_assumption(
                    key="recognized_technical_topics",
                    value=", ".join(technical_topics.keys()),
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="hoog",
                    method="bib_topic_recognition",
                    note="Technische onderwerpen zijn uit de BIB gehaald.",
                )
            )

        if decisions:
            assumptions.append(
                self.make_assumption(
                    key="bib_decisions_available",
                    value=f"{len(decisions)} besluit(en) gevonden in de BIB.",
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="hoog",
                    method="bib_decision_reuse",
                    note="Deze besluiten moeten voorrang krijgen boven nieuwe aannames.",
                )
            )

        if knowledge_items:
            assumptions.append(
                self.make_assumption(
                    key="bib_knowledge_items_available",
                    value=f"{len(knowledge_items)} kennisitem(s) gevonden in de BIB.",
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="hoog",
                    method="bib_knowledge_reuse",
                    note="Deze kennisitems kunnen gebruikt worden door Project Analyzer, AAIE en rapportage.",
                )
            )

        if actions:
            assumptions.append(
                self.make_assumption(
                    key="bib_actions_available",
                    value=f"{len(actions)} actiepunt(en) gevonden in de BIB.",
                    source=bib_lookup.get("source", ""),
                    source_type="bib_knowledge_index",
                    reliability="middel",
                    method="bib_action_reuse",
                    note="Acties zijn bruikbaar voor planning en vervolgstappen.",
                )
            )

        return assumptions

    def build_standard_project_assumptions(self, bib_lookup: Dict[str, Any]) -> List[Dict[str, Any]]:
        source = (
            bib_lookup.get("source", "")
            if bib_lookup.get("status") == "BIB_GEVONDEN"
            else "Project Phoenix standaardkennis"
        )

        return [
            self.make_assumption(
                key="default_groundwater_level",
                value="P = -0,50 m, tenzij projectspecifieke gegevens anders aangeven.",
                source=source,
                source_type="project_standard",
                reliability="middel",
                method="standard_engineering_rule",
                note="Bekende Brewster Engineering standaard voor geotechniek.",
            ),
            self.make_assumption(
                key="default_foundation_concept",
                value="Strokenfundering 150 cm breed en 40 cm hoog met funderingsbalk 50 x 60 cm in het hart van de strook.",
                source=source,
                source_type="project_standard",
                reliability="middel",
                method="standard_engineering_rule",
                note="Bekend standaard concept-funderingsplan voor BEOS/Brewster Engineering.",
            ),
            self.make_assumption(
                key="default_output_formats",
                value="Rapporten standaard PDF/DOCX; tekeningen standaard SKP/DWG/DXF; waar relevant IFC, STEP, FreeCAD, OpenSees, CalculiX, Excel/CSV.",
                source=source,
                source_type="project_standard",
                reliability="hoog",
                method="confirmed_project_preference",
                note="Door gebruiker herhaald als vaste outputwens.",
            ),
            self.make_assumption(
                key="autonomous_project_mode",
                value="Volledig autonoom als standaardmodus, met controleerbare output en evidence.",
                source=source,
                source_type="project_standard",
                reliability="hoog",
                method="confirmed_project_preference",
                note="Vaste wens voor BAOEES / Project Phoenix.",
            ),
            self.make_assumption(
                key="five_design_variants",
                value="Automatisch 5 ontwerpvarianten: laagste kosten, hoogste vergunningkans, duurzaamste, hoogste opbrengst, beste ruimtelijke kwaliteit.",
                source=source,
                source_type="project_standard",
                reliability="hoog",
                method="confirmed_project_preference",
                note="Vaste eis voor BAOEES variantenmodule.",
            ),
        ]

    def build_context_assumptions(self, project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        assumptions: List[Dict[str, Any]] = []

        for key, value in project_context.items():
            if value is None or value == "":
                continue

            assumptions.append(
                self.make_assumption(
                    key=f"context_{key}",
                    value=value,
                    source="project_context",
                    source_type="runtime_context",
                    reliability="hoog",
                    method="provided_context",
                    note="Waarde is meegegeven aan AAIE vanuit de projectcontext.",
                )
            )

        return assumptions

    def make_assumption(
        self,
        key: str,
        value: Any,
        source: str,
        source_type: str,
        reliability: str,
        method: str,
        note: str,
    ) -> Dict[str, Any]:
        return {
            "key": key,
            "value": value,
            "source": source,
            "source_type": source_type,
            "reliability": reliability,
            "method": method,
            "note": note,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "aaie_version": self.ENGINE_VERSION,
        }

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        bib_lookup = result.get("bib_lookup", {})
        assumptions = result.get("assumptions", [])

        rows = ""

        for assumption in assumptions:
            rows += f"""
            <tr>
              <td>{self.esc(assumption.get("key", ""))}</td>
              <td>{self.esc(assumption.get("value", ""))}</td>
              <td>{self.esc(assumption.get("source_type", ""))}</td>
              <td>{self.esc(assumption.get("reliability", ""))}</td>
              <td>{self.esc(assumption.get("method", ""))}</td>
              <td>{self.esc(assumption.get("note", ""))}</td>
            </tr>
            """

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix AAIE BIB Assumptions v5.8</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f172a;
      color: #e5e7eb;
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 32px;
    }}
    h1, h2, h3 {{
      color: #f8fafc;
    }}
    .hero {{
      padding: 30px;
      border-radius: 20px;
      background: linear-gradient(135deg, #0f172a, #1e3a8a);
      border: 1px solid #38bdf8;
      margin-bottom: 26px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin: 18px 0;
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
      background: #14532d;
      color: #bbf7d0;
      font-weight: bold;
    }}
    .muted {{
      color: #94a3b8;
    }}
    code {{
      color: #bfdbfe;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 18px;
      background: #111827;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid #334155;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #1e293b;
    }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <p class="muted">PROJECT PHOENIX / BAOEES</p>
    <h1>AAIE BIB Assumption Loader v5.8</h1>
    <p>AAIE zoekt eerst in de lokale BIB voordat nieuwe aannames worden gemaakt.</p>
    <p><span class="badge">{self.esc(result.get("status", ""))}</span></p>
  </section>

  <section>
    <h2>BIB-status</h2>
    <div class="grid">
      <div class="card">
        <h3>BIB lookup</h3>
        <p><span class="badge">{self.esc(bib_lookup.get("status", ""))}</span></p>
      </div>
      <div class="card">
        <h3>Inhoudelijk herkend</h3>
        <p>{self.esc(bib_lookup.get("recognized_text_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Besluiten</h3>
        <p>{self.esc(bib_lookup.get("decisions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Kennisitems</h3>
        <p>{self.esc(bib_lookup.get("knowledge_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Acties</h3>
        <p>{self.esc(bib_lookup.get("actions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Aannames</h3>
        <p>{self.esc(result.get("assumption_count", 0))}</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Bronvolgorde</h2>
    <div class="card">
      <p>1. Lokale BIB-kennisindex</p>
      <p>2. Eerder bevestigde Project Phoenix / BAOEES kennis</p>
      <p>3. Standaard engineeringregels</p>
      <p>4. AAIE-aanvullende aannames</p>
    </div>
  </section>

  <section>
    <h2>AAIE-aannames</h2>
    <table>
      <thead>
        <tr>
          <th>Sleutel</th>
          <th>Waarde</th>
          <th>Bronsoort</th>
          <th>Betrouwbaarheid</th>
          <th>Methode</th>
          <th>Toelichting</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </section>
</main>
</body>
</html>
"""

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_html(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


AaieBibAssumptionLoader = AAIEBibAssumptionLoader
AAIEBibAssumptionEngine = AAIEBibAssumptionLoader
AaieBibAssumptionEngine = AAIEBibAssumptionLoader


def main() -> None:
    loader = AAIEBibAssumptionLoader()
    result = loader.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()