from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class BrewsterKnowledgeMigrationEngine:
    ENGINE_NAME = "Project Phoenix Brewster Engineering Wizard Knowledge Migration Engine"
    ENGINE_VERSION = "v6.6"

    def __init__(self) -> None:
        self.project_output_root = PROJECT_ROOT / "outputs" / "projects"
        self.bib_root = PROJECT_ROOT / "outputs" / "bib"
        self.knowledge_root = self.bib_root / "knowledge"
        self.index_root = self.bib_root / "index"
        self.dashboard_root = self.bib_root / "dashboards"

        self.knowledge_json_path = (
            self.knowledge_root
            / "brewster_engineering_wizard_knowledge_base_v6_6.json"
        )
        self.knowledge_md_path = (
            self.knowledge_root
            / "brewster_engineering_wizard_knowledge_base_v6_6.md"
        )
        self.migration_log_path = (
            self.knowledge_root
            / "brewster_knowledge_migration_log_v6_6.json"
        )
        self.dashboard_path = (
            self.dashboard_root
            / "brewster_knowledge_migration_dashboard_v6_6.html"
        )
        self.bib_index_path = (
            self.index_root
            / "bib_knowledge_content_index.json"
        )
        self.project_summary_path = (
            self.project_output_root
            / "brewster_knowledge_migration_summary_v6_6.json"
        )

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)
        self.knowledge_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.dashboard_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        knowledge_base = self.build_knowledge_base()
        markdown = self.build_markdown(knowledge_base)

        self.write_json(self.knowledge_json_path, knowledge_base)
        self.write_text(self.knowledge_md_path, markdown)

        existing_index = self.read_json(self.bib_index_path)
        merged_index = self.merge_into_bib_index(existing_index, knowledge_base)
        self.write_json(self.bib_index_path, merged_index)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "bib_root": str(self.bib_root),
            "knowledge_json_path": str(self.knowledge_json_path),
            "knowledge_md_path": str(self.knowledge_md_path),
            "migration_log_path": str(self.migration_log_path),
            "dashboard_path": str(self.dashboard_path),
            "bib_index_path": str(self.bib_index_path),
            "project_summary_path": str(self.project_summary_path),
            "domain_count": len(knowledge_base["domains"]),
            "project_count": len(knowledge_base["projects"]),
            "module_count": len(knowledge_base["modules"]),
            "standard_rule_count": len(knowledge_base["standard_rules"]),
            "output_format_count": len(knowledge_base["output_formats"]),
            "next_steps": [
                "Controleer brewster_knowledge_migration_dashboard_v6_6.html.",
                "Controleer brewster_engineering_wizard_knowledge_base_v6_6.json.",
                "Controleer of bib_knowledge_content_index.json is bijgewerkt.",
                "Leg v6.6 vast met git add, commit en push.",
                "Ga daarna door naar v6.7: modules en engines verder operationaliseren.",
            ],
        }

        self.write_json(self.migration_log_path, result)
        self.write_json(self.project_summary_path, result)
        self.write_text(self.dashboard_path, self.build_dashboard(result, knowledge_base))

        return result

    def build_knowledge_base(self) -> Dict[str, Any]:
        generated_at = datetime.now().isoformat(timespec="seconds")

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": generated_at,
            "purpose": (
                "Systematische migratie van opgebouwde Brewster Engineering Wizard "
                "kennis naar Project Phoenix / BAOEES BIB."
            ),
            "domains": [
                {
                    "name": "BEOS / BREWAS / BAOEES visie",
                    "summary": (
                        "Autonoom engineeringplatform van locatiekeuze tot beheer, "
                        "met Digital Twin, Knowledge Graph en AI Engine als centrale kern."
                    ),
                    "importance": "kern",
                },
                {
                    "name": "Digital Twin centraal",
                    "summary": (
                        "Alle disciplines lezen en schrijven naar dezelfde Digital Twin: "
                        "terrein, BIM, constructie, fundering, riolering, verkeer, "
                        "vergunning, kosten en assetbeheer."
                    ),
                    "importance": "kern",
                },
                {
                    "name": "AAIE",
                    "summary": (
                        "Autonomous Assumption and Inference Engine vult ontbrekende "
                        "gegevens aan met aannameslog, bron, datum, betrouwbaarheid "
                        "en projectcontext."
                    ),
                    "importance": "kern",
                },
                {
                    "name": "STEE",
                    "summary": (
                        "Source Traceability and Evidence Engine maakt per project een "
                        "bronvermelding, evidence-log en projectpakket."
                    ),
                    "importance": "kern",
                },
                {
                    "name": "Open engineering stack",
                    "summary": (
                        "SCIA/Viktor worden vervangen door open engines zoals FreeCAD BIM, "
                        "OpenSees, CalculiX, BREWAS Geo Engine, rapportage-engine en viewers."
                    ),
                    "importance": "hoog",
                },
            ],
            "projects": [
                {
                    "name": "Moskee Bunschoten",
                    "location": "Bikkersweg 88, Bunschoten",
                    "summary": (
                        "Uitbreiding circa 20 m² inclusief vergunning, parkeren, "
                        "AERIUS, constructie, situatietekening, plattegronden, "
                        "gevels, doorsneden en 3D-impressies."
                    ),
                    "known_outputs": [
                        "situatietekening",
                        "plattegronden bestaand en nieuw",
                        "geveltekeningen",
                        "doorsneden",
                        "3D-impressies",
                        "ruimtelijke onderbouwing / BOPA",
                        "parkeeronderzoek",
                        "participatie",
                        "AERIUS",
                    ],
                },
                {
                    "name": "Plutostraat Paramaribo",
                    "location": "Paramaribo, Suriname",
                    "summary": (
                        "Testproject voor geotechniek, fundering, constructie, "
                        "grondwaterstand, strokenfundering en automatische rapportage."
                    ),
                    "known_outputs": [
                        "funderingsplan",
                        "geotechnische uitgangspunten",
                        "constructieschema",
                        "rapportage",
                    ],
                },
                {
                    "name": "Bruynzeel Waterfront District",
                    "location": "Paramaribo, Suriname",
                    "summary": (
                        "Masterplanontwikkeling met GLIS-percelen, waterfront, "
                        "kantoorprogramma, multifunctionele functies, GREX, "
                        "investeerdersmemo en professioneel masterplanrapport."
                    ),
                    "known_outputs": [
                        "masterplan",
                        "GLIS kaarten",
                        "perceelanalyse",
                        "GREX",
                        "SWOT",
                        "ontwikkelscenario's",
                        "investeerdersmemorandum",
                    ],
                },
            ],
            "modules": [
                {
                    "name": "Geotechniek",
                    "summary": (
                        "Automatisch grondwater en geo-informatie genereren op basis van "
                        "kaartuitsnede of Google Maps/satellietfoto, met handmatige optie."
                    ),
                    "default_rules": [
                        "Standaard grondwaterstand P = -0,50 m tenzij projectspecifiek anders.",
                        "Onderzoek strokenfundering en palenfundering als varianten.",
                    ],
                },
                {
                    "name": "Fundering",
                    "summary": (
                        "Standaard funderingsconcepten, waaronder strokenfundering "
                        "met funderingsbalk en variantenonderzoek."
                    ),
                    "default_rules": [
                        "Standaard strook 150 cm breed en 40 cm hoog onder muren en kolommen.",
                        "Funderingsbalk 50 cm breed en 60 cm hoog in hart strook.",
                        "Later projectspecifiek ook strook 200 cm toepasbaar.",
                    ],
                },
                {
                    "name": "Constructie",
                    "summary": (
                        "Constructiemodellen, belastingen, materiaaloptimalisatie, "
                        "FreeCAD/OpenSees/CalculiX en constructierapportage."
                    ),
                    "default_rules": [
                        "Open engines krijgen voorkeur boven gesloten SCIA/Viktor flow.",
                        "Constructie-output moet reproduceerbaar en traceerbaar zijn.",
                    ],
                },
                {
                    "name": "Riolering en afwatering",
                    "summary": (
                        "Ontwerp HWA, DWA, infiltratie, berging, leidingen, kolken, "
                        "putten, hoeveelheden en kosten."
                    ),
                    "default_rules": [
                        "Afwateringsplan koppelen aan Digital Twin.",
                        "Hoeveelheden en kosten automatisch genereren.",
                    ],
                },
                {
                    "name": "Verkeer en parkeren",
                    "summary": (
                        "Verkeersgeneratie, parkeerbalans, parkeerdruk, CROW-toets, "
                        "advies parkeerregime en fysieke parkeerinformatie."
                    ),
                    "default_rules": [
                        "Vink advies parkeerregime opnemen.",
                        "Vink fysieke parkeerinfo opnemen.",
                        "Automatische analyse via kaartgebied of gesproken projectopdracht.",
                    ],
                },
                {
                    "name": "Vergunningen",
                    "summary": (
                        "Ruimtelijke onderbouwing, BOPA, omgevingsvergunning, "
                        "participatieplan, AERIUS en milieukundige paragrafen."
                    ),
                    "default_rules": [
                        "Omgevingswet en Regels op de kaart als bron opnemen.",
                        "AERIUS/stikstof als automatische stap opnemen.",
                    ],
                },
                {
                    "name": "Rapportage en export",
                    "summary": (
                        "PDF, DOCX, dashboards, evidence, bronvermelding, manifest en ZIP-pakket."
                    ),
                    "default_rules": [
                        "PDF en DOCX standaard.",
                        "Project-ZIP standaard.",
                        "Bronvermelding_van_dit_project standaard.",
                    ],
                },
                {
                    "name": "Live Digital Twin Viewer",
                    "summary": (
                        "Interactieve 3D viewer met vogelvlucht, walkthrough, drivethrough "
                        "en videopresentatie."
                    ),
                    "default_rules": [
                        "Project moet rondom en van boven bekeken kunnen worden.",
                    ],
                },
            ],
            "standard_rules": [
                {
                    "name": "Outputstandaard",
                    "rule": "Rapporten standaard PDF en DOCX; tekeningen standaard SKP, DWG en DXF.",
                },
                {
                    "name": "Autonomous Project Mode",
                    "rule": "Volledig autonoom is default, met mogelijkheid tot assistent of semi-autonoom.",
                },
                {
                    "name": "Ontwerpvarianten",
                    "rule": "Automatisch vijf varianten A t/m E genereren: kosten, vergunningkans, duurzaamheid, opbrengst en ruimtelijke kwaliteit.",
                },
                {
                    "name": "Bronvermelding",
                    "rule": "Elke projectanalyse krijgt automatisch map Bronvermelding_van_dit_project.",
                },
                {
                    "name": "Geen handmatig plakken",
                    "rule": "Project Phoenix updates gebeuren voortaan via downloadbare updatebestanden en scripts, niet via handmatig Python knip- en plakwerk.",
                },
            ],
            "output_formats": [
                "PDF",
                "DOCX",
                "SKP",
                "DWG",
                "DXF",
                "IFC",
                "STEP",
                "FreeCAD",
                "OpenSees",
                "CalculiX",
                "Excel",
                "CSV",
                "JSON",
                "HTML dashboard",
                "ZIP projectpakket",
            ],
            "workflow_policy": {
                "preferred_update_method": "downloadbaar PowerShell updatebestand",
                "manual_python_paste": "niet standaard gebruiken",
                "git_policy": [
                    "testen",
                    "git status",
                    "git add",
                    "git commit",
                    "git push",
                    "git status",
                ],
            },
        }

    def merge_into_bib_index(
        self,
        existing_index: Dict[str, Any],
        knowledge_base: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not existing_index:
            existing_index = {}

        existing_index["status"] = "BIJGEWERKT"
        existing_index["last_updated_by"] = self.ENGINE_NAME
        existing_index["last_updated_version"] = self.ENGINE_VERSION
        existing_index["last_updated_at"] = datetime.now().isoformat(timespec="seconds")
        existing_index["brewster_knowledge_base"] = {
            "path": str(self.knowledge_json_path),
            "markdown_path": str(self.knowledge_md_path),
            "domain_count": len(knowledge_base["domains"]),
            "project_count": len(knowledge_base["projects"]),
            "module_count": len(knowledge_base["modules"]),
            "standard_rule_count": len(knowledge_base["standard_rules"]),
            "output_format_count": len(knowledge_base["output_formats"]),
        }

        recognized_items = existing_index.get("recognized_text_items", [])

        if not isinstance(recognized_items, list):
            recognized_items = []

        recognized_items.append(
            {
                "source": "brewster_engineering_wizard_knowledge_base_v6_6",
                "type": "knowledge_migration",
                "title": "Brewster Engineering Wizard kennisbasis v6.6",
                "summary": knowledge_base["purpose"],
                "created_at": knowledge_base["generated_at"],
            }
        )

        existing_index["recognized_text_items"] = recognized_items

        return existing_index

    def build_markdown(self, knowledge_base: Dict[str, Any]) -> str:
        lines: List[str] = []

        lines.append("# Brewster Engineering Wizard Knowledge Base v6.6")
        lines.append("")
        lines.append(knowledge_base["purpose"])
        lines.append("")
        lines.append("## Domeinen")
        lines.append("")

        for item in knowledge_base["domains"]:
            lines.append(f"### {item['name']}")
            lines.append(item["summary"])
            lines.append(f"Belang: {item['importance']}")
            lines.append("")

        lines.append("## Projecten")
        lines.append("")

        for project in knowledge_base["projects"]:
            lines.append(f"### {project['name']}")
            lines.append(f"Locatie: {project['location']}")
            lines.append(project["summary"])
            lines.append("")
            lines.append("Bekende outputs:")
            for output in project["known_outputs"]:
                lines.append(f"- {output}")
            lines.append("")

        lines.append("## Modules")
        lines.append("")

        for module in knowledge_base["modules"]:
            lines.append(f"### {module['name']}")
            lines.append(module["summary"])
            lines.append("")
            lines.append("Default regels:")
            for rule in module["default_rules"]:
                lines.append(f"- {rule}")
            lines.append("")

        lines.append("## Standaardregels")
        lines.append("")

        for rule in knowledge_base["standard_rules"]:
            lines.append(f"- **{rule['name']}**: {rule['rule']}")

        lines.append("")
        lines.append("## Outputformaten")
        lines.append("")

        for output_format in knowledge_base["output_formats"]:
            lines.append(f"- {output_format}")

        lines.append("")

        return "\n".join(lines)

    def build_dashboard(
        self,
        result: Dict[str, Any],
        knowledge_base: Dict[str, Any],
    ) -> str:
        domain_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['name'])}</td>"
            f"<td>{self.esc(item['importance'])}</td>"
            f"<td>{self.esc(item['summary'])}</td>"
            "</tr>"
            for item in knowledge_base["domains"]
        )

        project_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['name'])}</td>"
            f"<td>{self.esc(item['location'])}</td>"
            f"<td>{self.esc(item['summary'])}</td>"
            "</tr>"
            for item in knowledge_base["projects"]
        )

        module_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['name'])}</td>"
            f"<td>{self.esc(item['summary'])}</td>"
            "</tr>"
            for item in knowledge_base["modules"]
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Brewster Knowledge Migration v6.6</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px; }}
    section {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
    h1, h2 {{ color: #f8fafc; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #1e293b; }}
    code {{ color: #bfdbfe; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Brewster Engineering Wizard Knowledge Migration v6.6</h1>
    <p>Status: <strong>{self.esc(result["status"])}</strong></p>
    <p>De opgebouwde Brewster Engineering Wizard kennis is vastgelegd in de lokale Project Phoenix BIB.</p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <p>Domeinen: {self.esc(result["domain_count"])}</p>
    <p>Projecten: {self.esc(result["project_count"])}</p>
    <p>Modules: {self.esc(result["module_count"])}</p>
    <p>Standaardregels: {self.esc(result["standard_rule_count"])}</p>
    <p>Outputformaten: {self.esc(result["output_format_count"])}</p>
  </section>

  <section>
    <h2>Domeinen</h2>
    <table>
      <tr><th>Domein</th><th>Belang</th><th>Samenvatting</th></tr>
      {domain_rows}
    </table>
  </section>

  <section>
    <h2>Projecten</h2>
    <table>
      <tr><th>Project</th><th>Locatie</th><th>Samenvatting</th></tr>
      {project_rows}
    </table>
  </section>

  <section>
    <h2>Modules</h2>
    <table>
      <tr><th>Module</th><th>Samenvatting</th></tr>
      {module_rows}
    </table>
  </section>

  <section>
    <h2>Bestanden</h2>
    <p><code>{self.esc(result["knowledge_json_path"])}</code></p>
    <p><code>{self.esc(result["knowledge_md_path"])}</code></p>
    <p><code>{self.esc(result["bib_index_path"])}</code></p>
  </section>
</main>
</body>
</html>
"""

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

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


BrewsterKnowledgeEngine = BrewsterKnowledgeMigrationEngine
KnowledgeMigrationEngine = BrewsterKnowledgeMigrationEngine
BIBKnowledgeMigrationEngine = BrewsterKnowledgeMigrationEngine


def main() -> None:
    engine = BrewsterKnowledgeMigrationEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
