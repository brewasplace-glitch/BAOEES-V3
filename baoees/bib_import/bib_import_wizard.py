from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class BibImportWizard:
    """
    PROJECT PHOENIX / BAOEES
    BIB Import Wizard v5.6

    Doel:
    - Lokale importstructuur voor de Brewster Intelligence Bibliotheek.
    - Nieuwe chatkennis, handmatige kennis, uploads en levenswerk-mappen voorbereiden.
    - BIB intake, processed, index, evidence en logs structureren.
    - Intakebestanden tellen en registreren.
    - Markdown-intakebestanden inhoudelijk herkennen.
    - Projectnaam, samenvatting, besluiten, kennisitems, acties en BIB-categorieën uitlezen.
    - Basis-index genereren.
    - Evidence-log genereren.
    - HTML-dashboard genereren.
    """

    ENGINE_NAME = "Project Phoenix BIB Import Wizard"
    ENGINE_VERSION = "v5.6"

    TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv"}

    def __init__(self, bib_root: Optional[str | Path] = None) -> None:
        self.bib_root = Path(bib_root) if bib_root else Path("outputs") / "bib"

        self.intake_root = self.bib_root / "intake"
        self.chat_intake_root = self.intake_root / "chats"
        self.upload_intake_root = self.intake_root / "uploads"
        self.manual_intake_root = self.intake_root / "manual"
        self.lifework_intake_root = self.intake_root / "lifework"

        self.processed_root = self.bib_root / "processed"
        self.index_root = self.bib_root / "index"
        self.evidence_root = self.bib_root / "evidence"
        self.logs_root = self.bib_root / "logs"

    def run(self, source_note: str = "BIB Import Wizard inhoudelijke intake reader run") -> Dict[str, Any]:
        self.ensure_directories()

        imported_items = self.collect_intake_items()
        knowledge_summary = self.build_knowledge_summary(imported_items)
        index_data = self.build_index(imported_items, knowledge_summary)
        evidence_data = self.build_evidence(imported_items, source_note)

        index_path = self.index_root / "bib_import_index.json"
        knowledge_index_path = self.index_root / "bib_knowledge_content_index.json"
        evidence_path = self.evidence_root / "bib_import_evidence_log.json"
        dashboard_path = self.bib_root / "bib_import_dashboard.html"
        run_log_path = self.logs_root / "bib_import_wizard_log.json"

        self.write_json(index_path, index_data)
        self.write_json(knowledge_index_path, knowledge_summary)
        self.write_json(evidence_path, evidence_data)
        self.write_html(dashboard_path, self.build_dashboard(index_data, evidence_data, knowledge_summary))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "BIB Import Wizard met inhoudelijke herkenning van intakebestanden.",
            "bib_root": str(self.bib_root),
            "intake_root": str(self.intake_root),
            "chat_intake_root": str(self.chat_intake_root),
            "upload_intake_root": str(self.upload_intake_root),
            "manual_intake_root": str(self.manual_intake_root),
            "lifework_intake_root": str(self.lifework_intake_root),
            "processed_root": str(self.processed_root),
            "index_root": str(self.index_root),
            "evidence_root": str(self.evidence_root),
            "logs_root": str(self.logs_root),
            "imported_items_count": len(imported_items),
            "recognized_text_items_count": knowledge_summary.get("recognized_text_items_count", 0),
            "recognized_projects": knowledge_summary.get("projects", []),
            "recognized_categories": knowledge_summary.get("categories", {}),
            "index_path": str(index_path),
            "knowledge_index_path": str(knowledge_index_path),
            "evidence_path": str(evidence_path),
            "dashboard_path": str(dashboard_path),
            "run_log_path": str(run_log_path),
            "next_steps": [
                "Controleer outputs/bib/bib_import_dashboard.html.",
                "Controleer outputs/bib/index/bib_knowledge_content_index.json.",
                "Gebruik nieuwe intakebestanden in outputs/bib/intake/chats.",
                "Daarna BIB Import Wizard opnieuw draaien.",
                "Later koppelen aan START PROJECTANALYSE.",
            ],
        }

        self.write_json(run_log_path, result)
        return result

    def ensure_directories(self) -> None:
        directories = [
            self.bib_root,
            self.intake_root,
            self.chat_intake_root,
            self.upload_intake_root,
            self.manual_intake_root,
            self.lifework_intake_root,
            self.processed_root,
            self.index_root,
            self.evidence_root,
            self.logs_root,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def collect_intake_items(self) -> List[Dict[str, Any]]:
        intake_folders = [
            ("chats", self.chat_intake_root),
            ("uploads", self.upload_intake_root),
            ("manual", self.manual_intake_root),
            ("lifework", self.lifework_intake_root),
        ]

        items: List[Dict[str, Any]] = []

        for category, folder in intake_folders:
            if not folder.exists():
                continue

            for path in sorted(folder.rglob("*")):
                if not path.is_file():
                    continue

                analysis = self.analyze_file_content(path)

                items.append(
                    {
                        "category": category,
                        "filename": path.name,
                        "path": str(path),
                        "relative_path": self.safe_relative(path),
                        "suffix": path.suffix.lower(),
                        "size_bytes": path.stat().st_size,
                        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                        "content_analysis": analysis,
                    }
                )

        return items

    def analyze_file_content(self, path: Path) -> Dict[str, Any]:
        suffix = path.suffix.lower()

        if suffix not in self.TEXT_SUFFIXES:
            return {
                "recognized": False,
                "reason": "Geen tekstbestand voor inhoudelijke intake-herkenning.",
            }

        text = self.read_text_file(path)

        if not text.strip():
            return {
                "recognized": False,
                "reason": "Tekstbestand is leeg.",
            }

        sections = self.parse_markdown_sections(text)
        metadata = self.extract_metadata(text)
        decisions = self.extract_numbered_values(text, "Besluit")
        knowledge_items = self.extract_numbered_values(text, "Kennisitem")
        actions = self.extract_numbered_values(text, "Actie")
        bib_categories = self.extract_bib_categories(text)
        technical_topics = self.extract_technical_topics(text)

        project_name = (
            metadata.get("Project")
            or metadata.get("Projectnaam")
            or self.find_line_value(text, "Projectnaam")
            or self.find_line_value(text, "Project")
            or ""
        )

        source = (
            metadata.get("Bron")
            or self.find_line_value(text, "Bron")
            or ""
        )

        reliability = (
            metadata.get("Betrouwbaarheid")
            or self.find_line_value(text, "Betrouwbaarheid")
            or ""
        )

        summary_text = self.extract_section_text(
            sections,
            [
                "2. Korte samenvatting van deze chat",
                "Korte samenvatting van deze chat",
                "Samenvatting",
            ],
        )

        return {
            "recognized": True,
            "reader_version": self.ENGINE_VERSION,
            "title": self.extract_title(text),
            "project_name": project_name,
            "source": source,
            "reliability": reliability,
            "summary_preview": self.compact_text(summary_text, 700),
            "metadata": metadata,
            "headings": list(sections.keys()),
            "decisions": decisions,
            "knowledge_items": knowledge_items,
            "actions": actions,
            "bib_categories": bib_categories,
            "technical_topics": technical_topics,
            "word_count": len(text.split()),
            "character_count": len(text),
        }

    def parse_markdown_sections(self, text: str) -> Dict[str, str]:
        sections: Dict[str, List[str]] = {}
        current_heading = "document"
        sections[current_heading] = []

        for line in text.splitlines():
            heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*$", line)

            if heading_match:
                current_heading = heading_match.group(1).strip()
                sections[current_heading] = []
                continue

            sections.setdefault(current_heading, []).append(line)

        return {
            heading: "\n".join(lines).strip()
            for heading, lines in sections.items()
        }

    def extract_metadata(self, text: str) -> Dict[str, str]:
        wanted_keys = [
            "Datum",
            "Tijd",
            "Chatnaam",
            "Project",
            "Versie",
            "Opsteller",
            "Bron",
            "Status",
            "Projectnaam",
            "Locatie",
            "Opdrachtgever",
            "Onderwerp",
            "Discipline",
            "Betrouwbaarheid",
            "Bronsoort",
            "Datum bron",
        ]

        metadata: Dict[str, str] = {}

        for key in wanted_keys:
            value = self.find_line_value(text, key)

            if value:
                metadata[key] = value

        return metadata

    def extract_numbered_values(self, text: str, prefix: str) -> List[str]:
        values: List[str] = []
        pattern = re.compile(rf"^\s*{re.escape(prefix)}\s+\d+\s*:\s*(.*)$", re.IGNORECASE)

        current_value = ""

        for line in text.splitlines():
            match = pattern.match(line)

            if match:
                if current_value.strip():
                    values.append(self.compact_text(current_value, 600))

                current_value = match.group(1).strip()
                continue

            if current_value and line.strip() and not re.match(r"^\s*#{1,6}\s+", line):
                if re.match(r"^\s*[A-Za-zÀ-ÿ /]+:\s*$", line):
                    continue

                current_value += " " + line.strip()

        if current_value.strip():
            values.append(self.compact_text(current_value, 600))

        return [value for value in values if value.strip()]

    def extract_bib_categories(self, text: str) -> Dict[str, str]:
        category_names = [
            "Projecten",
            "Normen",
            "Geotechniek",
            "Funderingen",
            "Constructies",
            "Bouwkunde",
            "Installaties",
            "Riolering",
            "Verkeer en parkeren",
            "Vergunningen",
            "AERIUS",
            "Kosten",
            "Planning",
            "Digital Twin",
            "AAIE",
            "STEE",
            "Rapporttemplates",
            "Tekenregels",
            "Workflowregels",
            "Software / engines",
            "Overig",
        ]

        categories: Dict[str, str] = {}

        lines = text.splitlines()

        for index, line in enumerate(lines):
            stripped = line.strip()

            for category in category_names:
                if stripped.lower() == f"{category.lower()}:":
                    collected: List[str] = []

                    for follow_line in lines[index + 1:]:
                        follow_stripped = follow_line.strip()

                        if not follow_stripped:
                            if collected:
                                break
                            continue

                        if any(follow_stripped.lower() == f"{name.lower()}:" for name in category_names):
                            break

                        if re.match(r"^\s*#{1,6}\s+", follow_line):
                            break

                        collected.append(follow_stripped)

                    if collected:
                        categories[category] = "; ".join(collected)

        return categories

    def extract_technical_topics(self, text: str) -> List[str]:
        topic_keywords = [
            "BAOEES",
            "BEOS",
            "BREWAS",
            "Digital Twin",
            "AAIE",
            "STEE",
            "BIB",
            "START PROJECTANALYSE",
            "FreeCAD",
            "OpenSees",
            "CalculiX",
            "Geotechniek",
            "Fundering",
            "Strokenfundering",
            "Paalfundering",
            "AERIUS",
            "Omgevingswet",
            "CROW",
            "Parkeren",
            "Riolering",
            "Afwatering",
            "Vergunning",
            "BOPA",
            "DOCX",
            "PDF",
            "DWG",
            "DXF",
            "SKP",
            "IFC",
        ]

        found = []

        for keyword in topic_keywords:
            if keyword.lower() in text.lower():
                found.append(keyword)

        return found

    def build_knowledge_summary(self, imported_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        recognized_items = [
            item for item in imported_items
            if item.get("content_analysis", {}).get("recognized")
        ]

        projects: List[str] = []
        categories: Dict[str, int] = {}
        topics: Dict[str, int] = {}
        decisions_count = 0
        knowledge_items_count = 0
        actions_count = 0

        for item in recognized_items:
            analysis = item.get("content_analysis", {})
            project_name = str(analysis.get("project_name", "")).strip()

            if project_name and project_name not in projects:
                projects.append(project_name)

            for category in analysis.get("bib_categories", {}).keys():
                categories[category] = categories.get(category, 0) + 1

            for topic in analysis.get("technical_topics", []):
                topics[topic] = topics.get(topic, 0) + 1

            decisions_count += len(analysis.get("decisions", []))
            knowledge_items_count += len(analysis.get("knowledge_items", []))
            actions_count += len(analysis.get("actions", []))

        return {
            "status": "GEREED",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "recognized_text_items_count": len(recognized_items),
            "projects": projects,
            "categories": categories,
            "technical_topics": topics,
            "decisions_count": decisions_count,
            "knowledge_items_count": knowledge_items_count,
            "actions_count": actions_count,
            "recognized_items": recognized_items,
        }

    def build_index(
        self,
        imported_items: List[Dict[str, Any]],
        knowledge_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        categories: Dict[str, int] = {}

        for item in imported_items:
            category = str(item.get("category", "unknown"))
            categories[category] = categories.get(category, 0) + 1

        return {
            "status": "GEREED",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "bib_root": str(self.bib_root),
            "total_items": len(imported_items),
            "recognized_text_items_count": knowledge_summary.get("recognized_text_items_count", 0),
            "categories": categories,
            "knowledge_categories": knowledge_summary.get("categories", {}),
            "technical_topics": knowledge_summary.get("technical_topics", {}),
            "projects": knowledge_summary.get("projects", []),
            "items": imported_items,
            "known_intake_routes": {
                "chats": str(self.chat_intake_root),
                "uploads": str(self.upload_intake_root),
                "manual": str(self.manual_intake_root),
                "lifework": str(self.lifework_intake_root),
            },
            "future_extensions": [
                "Automatische samenvatting per chatbestand uitbreiden.",
                "Projectherkenning verder verfijnen.",
                "Koppeling met STEE-bronregistratie uitbreiden.",
                "Koppeling met START PROJECTANALYSE.",
                "Zoekindex voor BAOEES modules.",
                "Automatische projectdossiers per project.",
            ],
        }

    def build_evidence(
        self,
        imported_items: List[Dict[str, Any]],
        source_note: str,
    ) -> Dict[str, Any]:
        return {
            "status": "GEREGISTREERD",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_note": source_note,
            "evidence_type": "BIB intake evidence",
            "items_count": len(imported_items),
            "items": imported_items,
            "limitations": [
                "Nieuwe ChatGPT-chats worden nog niet automatisch naar deze lokale BIB geschreven.",
                "Kennis moet in deze fase nog handmatig in intake-mappen worden geplaatst.",
                "Automatische verwerking van uploads en levenswerk-mappen volgt in latere versies.",
                "De inhoudelijke herkenning is nu regel- en template-gebaseerd en wordt later uitgebreid.",
            ],
        }

    def build_dashboard(
        self,
        index_data: Dict[str, Any],
        evidence_data: Dict[str, Any],
        knowledge_summary: Dict[str, Any],
    ) -> str:
        items = index_data.get("items", [])
        rows = ""

        for item in items:
            analysis = item.get("content_analysis", {})
            recognized = "JA" if analysis.get("recognized") else "NEE"
            project_name = analysis.get("project_name", "")
            topics = ", ".join(analysis.get("technical_topics", []))

            rows += f"""
            <tr>
              <td>{self.esc(item.get("category", ""))}</td>
              <td>{self.esc(item.get("filename", ""))}</td>
              <td><code>{self.esc(item.get("relative_path", ""))}</code></td>
              <td>{self.esc(recognized)}</td>
              <td>{self.esc(project_name)}</td>
              <td>{self.esc(topics)}</td>
              <td>{self.esc(item.get("size_bytes", 0))}</td>
              <td>{self.esc(item.get("modified_at", ""))}</td>
            </tr>
            """

        if not rows:
            rows = """
            <tr>
              <td colspan="8">Nog geen intake-bestanden gevonden. Plaats eerst kennisbestanden in outputs/bib/intake.</td>
            </tr>
            """

        category_cards = self.build_dashboard_cards(index_data.get("categories", {}), "Intakecategorieën")
        knowledge_category_cards = self.build_dashboard_cards(knowledge_summary.get("categories", {}), "BIB-kennis")
        topic_cards = self.build_dashboard_cards(knowledge_summary.get("technical_topics", {}), "Technische onderwerpen")

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB Import Wizard v5.6</title>
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
      padding: 28px;
      border-radius: 18px;
      background: linear-gradient(135deg, #1e3a8a, #0f172a);
      border: 1px solid #38bdf8;
      margin-bottom: 24px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin: 18px 0;
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
    code {{
      color: #bfdbfe;
    }}
    .muted {{
      color: #94a3b8;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: #14532d;
      color: #bbf7d0;
      font-weight: bold;
    }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <p class="muted">PROJECT PHOENIX / BAOEES</p>
    <h1>BIB Import Wizard v5.6</h1>
    <p>Lokale BIB Import Wizard met inhoudelijke herkenning van markdown-intakebestanden.</p>
    <p><span class="badge">{self.esc(index_data.get("status", ""))}</span></p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <div class="grid">
      <div class="card">
        <h3>Totaal intakebestanden</h3>
        <p>{self.esc(index_data.get("total_items", 0))}</p>
      </div>
      <div class="card">
        <h3>Inhoudelijk herkend</h3>
        <p>{self.esc(knowledge_summary.get("recognized_text_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Besluiten</h3>
        <p>{self.esc(knowledge_summary.get("decisions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Kennisitems</h3>
        <p>{self.esc(knowledge_summary.get("knowledge_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Acties</h3>
        <p>{self.esc(knowledge_summary.get("actions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Evidence</h3>
        <p>{self.esc(evidence_data.get("status", ""))}</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Projecten</h2>
    <div class="card">
      <p>{self.esc(', '.join(knowledge_summary.get("projects", [])) or "Nog geen projectnamen herkend.")}</p>
    </div>
  </section>

  <section>
    <h2>Intakecategorieën</h2>
    <div class="grid">
      {category_cards}
    </div>
  </section>

  <section>
    <h2>BIB-kenniscategorieën</h2>
    <div class="grid">
      {knowledge_category_cards}
    </div>
  </section>

  <section>
    <h2>Technische onderwerpen</h2>
    <div class="grid">
      {topic_cards}
    </div>
  </section>

  <section>
    <h2>Intake-bestanden</h2>
    <table>
      <thead>
        <tr>
          <th>Categorie</th>
          <th>Bestand</th>
          <th>Pad</th>
          <th>Herkend</th>
          <th>Project</th>
          <th>Onderwerpen</th>
          <th>Bytes</th>
          <th>Gewijzigd</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Belangrijke beperking</h2>
    <div class="card">
      <p>Nieuwe chats worden nog niet vanzelf in de lokale BIB opgeslagen.</p>
      <p>In deze fase plaatsen we kennis nog bewust in de intake-mappen.</p>
      <p>De automatische koppeling met START PROJECTANALYSE volgt in een volgende versie.</p>
    </div>
  </section>
</main>
</body>
</html>
"""

    def build_dashboard_cards(self, data: Dict[str, Any], empty_title: str) -> str:
        cards = ""

        for key, value in data.items():
            cards += f"""
            <div class="card">
              <h3>{self.esc(key)}</h3>
              <p>{self.esc(value)} item(s)</p>
            </div>
            """

        if not cards:
            cards = f"""
            <div class="card">
              <h3>{self.esc(empty_title)}</h3>
              <p>Nog geen items herkend.</p>
            </div>
            """

        return cards

    def extract_title(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()

            if stripped.startswith("# "):
                return stripped[2:].strip()

        return ""

    def extract_section_text(self, sections: Dict[str, str], candidate_headings: List[str]) -> str:
        normalized = {
            self.normalize_heading(heading): content
            for heading, content in sections.items()
        }

        for heading in candidate_headings:
            value = normalized.get(self.normalize_heading(heading))

            if value:
                return value

        return ""

    def normalize_heading(self, heading: str) -> str:
        return re.sub(r"\s+", " ", heading.strip().lower())

    def find_line_value(self, text: str, key: str) -> str:
        pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*?)\s*$", re.IGNORECASE)

        for line in text.splitlines():
            match = pattern.match(line)

            if match and match.group(1).strip():
                return match.group(1).strip()

        return ""

    def compact_text(self, text: str, max_length: int) -> str:
        compact = re.sub(r"\s+", " ", text).strip()

        if len(compact) <= max_length:
            return compact

        return compact[: max_length - 3].rstrip() + "..."

    def read_text_file(self, path: Path) -> str:
        encodings = ["utf-8-sig", "utf-8", "cp1252"]

        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except Exception:
                return ""

        return ""

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_html(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def safe_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except Exception:
            return path.as_posix()

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    wizard = BibImportWizard()
    result = wizard.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()