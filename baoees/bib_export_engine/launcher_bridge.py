from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BibLauncherBridge:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Launcher Bridge v3.2

    Doel:
    - Koppelt de Brewster Integrated Bibliotheek aan de centrale Project Phoenix launcher.
    - Voegt een BIB-sectie toe aan outputs/projects/index.html.
    - Werkt veilig met HTML-markers, zodat de sectie later opnieuw kan worden bijgewerkt.
    """

    ENGINE_NAME = "Project Phoenix BIB Launcher Bridge"
    ENGINE_VERSION = "v3.2"

    START_MARKER = "<!-- PROJECT_PHOENIX_BIB_LAUNCHER_START -->"
    END_MARKER = "<!-- PROJECT_PHOENIX_BIB_LAUNCHER_END -->"

    def __init__(
        self,
        project_index_path: Optional[str | Path] = None,
        bib_output_root: Optional[str | Path] = None,
    ) -> None:
        self.project_index_path = Path(project_index_path) if project_index_path else Path("outputs") / "projects" / "index.html"
        self.bib_output_root = Path(bib_output_root) if bib_output_root else Path("outputs") / "bib"

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.bib_output_root.mkdir(parents=True, exist_ok=True)

        result = {
            "status": "GESTART",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "project_index_path": str(self.project_index_path),
            "bib_output_root": str(self.bib_output_root),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "extra_results": extra_results,
        }

        if not self.project_index_path.exists():
            result["status"] = "FOUT"
            result["warnings"] = [
                f"Project index bestaat niet: {self.project_index_path}",
                "Open of genereer eerst outputs/projects/index.html.",
            ]
            self.write_log(result)
            return result

        html_text = self.project_index_path.read_text(encoding="utf-8")
        bib_section = self.build_bib_section()

        updated_html = self.insert_or_replace_section(html_text, bib_section)

        self.project_index_path.write_text(updated_html, encoding="utf-8")

        output_links = self.collect_bib_outputs()

        result.update(
            {
                "status": "OPGESLAGEN",
                "bib_links_count": len(output_links),
                "bib_outputs": output_links,
                "warnings": self.build_warnings(output_links),
                "recommendation": {
                    "status": "BIB_LAUNCHER_BRIDGE_ADVIES",
                    "advice": [
                        "Open outputs/projects/index.html en controleer de BIB-sectie.",
                        "Controleer of BIB Dashboard, DOCX, PDF en ZIP openen.",
                        "Draai bij nieuwe BIB-exports opnieuw deze bridge.",
                        "Koppel deze bridge later aan de Project Phoenix hoofdworkflow.",
                    ],
                },
            }
        )

        self.write_log(result)
        return result

    def insert_or_replace_section(self, html_text: str, section: str) -> str:
        if self.START_MARKER in html_text and self.END_MARKER in html_text:
            before = html_text.split(self.START_MARKER)[0]
            after = html_text.split(self.END_MARKER, 1)[1]
            return before + section + after

        if "</main>" in html_text:
            return html_text.replace("</main>", section + "\n</main>", 1)

        if "</body>" in html_text:
            return html_text.replace("</body>", section + "\n</body>", 1)

        return html_text + "\n" + section

    def build_bib_section(self) -> str:
        outputs = self.collect_bib_outputs()

        cards = []
        for item in outputs:
            status_class = "ok" if item["exists"] else "warn"
            status_text = "AANWEZIG" if item["exists"] else "ONTBREEKT"

            if item["exists"]:
                link = f'<a href="{self.esc(item["href"])}">{self.esc(item["label"])}</a>'
            else:
                link = f'<span class="muted">{self.esc(item["label"])}</span>'

            cards.append(
                f"""
                <div class="card">
                  <h3>{link}</h3>
                  <p><span class="badge {status_class}">{status_text}</span></p>
                  <p class="muted">{self.esc(item["description"])}</p>
                  <p class="muted"><code>{self.esc(item["path"])}</code></p>
                </div>
                """
            )

        return f"""
{self.START_MARKER}
<section style="margin-top:34px;">
  <h2>PROJECT PHOENIX BIB / Kennisbibliotheek</h2>
  <p class="muted">
    Centrale Brewster Integrated Bibliotheek met masterkennis, projectkennis,
    enginekennis, standaarden, aannames, workflows, templates, lessons learned en source evidence.
  </p>

  <div class="grid">
    {''.join(cards)}
  </div>
</section>
{self.END_MARKER}
"""

    def collect_bib_outputs(self) -> List[Dict[str, Any]]:
        files = [
            {
                "label": "Open BIB Dashboard",
                "path": self.bib_output_root / "bib_dashboard.html",
                "href": "../bib/bib_dashboard.html",
                "description": "HTML knowledge dashboard van de BIB.",
            },
            {
                "label": "Open BIB DOCX",
                "path": self.bib_output_root / "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx",
                "href": "../bib/PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx",
                "description": "Word-export van de volledige BIB.",
            },
            {
                "label": "Open BIB PDF",
                "path": self.bib_output_root / "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf",
                "href": "../bib/PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf",
                "description": "PDF-export van de volledige BIB.",
            },
            {
                "label": "Open BIB ZIP",
                "path": self.bib_output_root / "PROJECT_PHOENIX_BIB_EXPORT.zip",
                "href": "../bib/PROJECT_PHOENIX_BIB_EXPORT.zip",
                "description": "Basis ZIP-export met BIB-bestanden en exports.",
            },
            {
                "label": "Open BIB Full ZIP",
                "path": self.bib_output_root / "PROJECT_PHOENIX_BIB_FULL_EXPORT.zip",
                "href": "../bib/PROJECT_PHOENIX_BIB_FULL_EXPORT.zip",
                "description": "Volledige ZIP-export met BIB en exportbestanden.",
            },
            {
                "label": "Open BIB Manifest",
                "path": self.bib_output_root / "bib_manifest.json",
                "href": "../bib/bib_manifest.json",
                "description": "Manifest met alle BIB-bestanden, categorieën en checksums.",
            },
            {
                "label": "Open BIB Full Export Log",
                "path": self.bib_output_root / "bib_full_export_log.json",
                "href": "../bib/bib_full_export_log.json",
                "description": "Logbestand van de volledige BIB-export.",
            },
        ]

        result = []
        for item in files:
            path = Path(item["path"])
            item["exists"] = path.exists()
            item["size_bytes"] = path.stat().st_size if path.exists() else 0
            item["path"] = str(path)
            result.append(item)

        return result

    def build_warnings(self, outputs: List[Dict[str, Any]]) -> List[str]:
        warnings = []

        for item in outputs:
            if not item.get("exists"):
                warnings.append(f"BIB-output ontbreekt: {item.get('path')}")

        if not warnings:
            warnings.append("Geen kritieke BIB launcher bridge-waarschuwingen.")

        return warnings

    def write_log(self, result: Dict[str, Any]) -> None:
        log_path = self.bib_output_root / "bib_launcher_bridge_log.json"
        log_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    bridge = BibLauncherBridge()
    result = bridge.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()