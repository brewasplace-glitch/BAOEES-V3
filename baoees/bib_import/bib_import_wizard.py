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


class BibImportWizard:
    """
    PROJECT PHOENIX / BAOEES
    BIB Import Wizard v5.4

    Doel:
    - Eerste lokale importstructuur voor de Brewster Intelligence Bibliotheek.
    - Nieuwe chatkennis, handmatige kennis, uploads en levenswerk-mappen voorbereiden.
    - BIB intake, processed, index, evidence en logs structureren.
    - Basis-index genereren.
    - Evidence-log genereren.
    - HTML-dashboard genereren.
    """

    ENGINE_NAME = "Project Phoenix BIB Import Wizard"
    ENGINE_VERSION = "v5.4"

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

    def run(self, source_note: str = "Eerste lokale BIB Import Wizard run") -> Dict[str, Any]:
        self.ensure_directories()

        imported_items = self.collect_intake_items()
        index_data = self.build_index(imported_items)
        evidence_data = self.build_evidence(imported_items, source_note)

        index_path = self.index_root / "bib_import_index.json"
        evidence_path = self.evidence_root / "bib_import_evidence_log.json"
        dashboard_path = self.bib_root / "bib_import_dashboard.html"
        run_log_path = self.logs_root / "bib_import_wizard_log.json"

        self.write_json(index_path, index_data)
        self.write_json(evidence_path, evidence_data)
        self.write_html(dashboard_path, self.build_dashboard(index_data, evidence_data))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Eerste lokale BIB Import Wizard / Chat Knowledge Intake structuur.",
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
            "index_path": str(index_path),
            "evidence_path": str(evidence_path),
            "dashboard_path": str(dashboard_path),
            "run_log_path": str(run_log_path),
            "next_steps": [
                "Nieuwe chatkennis handmatig opslaan in outputs/bib/intake/chats.",
                "Handmatige kennis opslaan in outputs/bib/intake/manual.",
                "Uploads registreren in outputs/bib/intake/uploads.",
                "Levenswerk-bestanden voorbereiden in outputs/bib/intake/lifework.",
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

                items.append(
                    {
                        "category": category,
                        "filename": path.name,
                        "path": str(path),
                        "relative_path": self.safe_relative(path),
                        "suffix": path.suffix.lower(),
                        "size_bytes": path.stat().st_size,
                        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                    }
                )

        return items

    def build_index(self, imported_items: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            "categories": categories,
            "items": imported_items,
            "known_intake_routes": {
                "chats": str(self.chat_intake_root),
                "uploads": str(self.upload_intake_root),
                "manual": str(self.manual_intake_root),
                "lifework": str(self.lifework_intake_root),
            },
            "future_extensions": [
                "Automatische samenvatting per chatbestand.",
                "Projectherkenning per kennisitem.",
                "Koppeling met STEE-bronregistratie.",
                "Koppeling met START PROJECTANALYSE.",
                "Zoekindex voor BAOEES modules.",
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
            ],
        }

    def build_dashboard(
        self,
        index_data: Dict[str, Any],
        evidence_data: Dict[str, Any],
    ) -> str:
        items = index_data.get("items", [])
        rows = ""

        for item in items:
            rows += f"""
            <tr>
              <td>{self.esc(item.get("category", ""))}</td>
              <td>{self.esc(item.get("filename", ""))}</td>
              <td><code>{self.esc(item.get("relative_path", ""))}</code></td>
              <td>{self.esc(item.get("size_bytes", 0))}</td>
              <td>{self.esc(item.get("modified_at", ""))}</td>
            </tr>
            """

        if not rows:
            rows = """
            <tr>
              <td colspan="5">Nog geen intake-bestanden gevonden. Plaats eerst kennisbestanden in outputs/bib/intake.</td>
            </tr>
            """

        categories = index_data.get("categories", {})
        category_cards = ""

        for category, count in categories.items():
            category_cards += f"""
            <div class="card">
              <h3>{self.esc(category)}</h3>
              <p>{self.esc(count)} item(s)</p>
            </div>
            """

        if not category_cards:
            category_cards = """
            <div class="card">
              <h3>Geen intake-items</h3>
              <p>De structuur is klaar, maar er zijn nog geen kennisbestanden geïmporteerd.</p>
            </div>
            """

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB Import Wizard v5.4</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f172a;
      color: #e5e7eb;
    }}
    main {{
      max-width: 1200px;
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
    <h1>BIB Import Wizard v5.4</h1>
    <p>Lokale basis voor Chat Knowledge Intake, uploads, handmatige kennis en levenswerk-import.</p>
    <p><span class="badge">{self.esc(index_data.get("status", ""))}</span></p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <div class="grid">
      <div class="card">
        <h3>Totaal items</h3>
        <p>{self.esc(index_data.get("total_items", 0))}</p>
      </div>
      <div class="card">
        <h3>BIB root</h3>
        <p><code>{self.esc(index_data.get("bib_root", ""))}</code></p>
      </div>
      <div class="card">
        <h3>Evidence</h3>
        <p>{self.esc(evidence_data.get("status", ""))}</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Categorieën</h2>
    <div class="grid">
      {category_cards}
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