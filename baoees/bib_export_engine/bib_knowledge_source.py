from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BibKnowledgeSourceEngine:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Knowledge Source Engine v3.6

    Doel:
    - Leest de Brewster Integrated Bibliotheek.
    - Maakt een kennisindex van alle Markdown-bestanden.
    - Maakt een projectanalyse-context voor BAOEES.
    - Maakt een HTML-overzicht van de kennisbron.
    - Bereidt de BIB voor als kennislaag voor projectanalyse.
    """

    ENGINE_NAME = "Project Phoenix BIB Knowledge Source Engine"
    ENGINE_VERSION = "v3.6"

    CATEGORY_ORDER = [
        "00_BIB_INDEX.md",
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

    STOPWORDS = {
        "the", "and", "for", "with", "from", "this", "that", "zijn", "wordt",
        "voor", "naar", "van", "het", "een", "als", "met", "moet", "moeten",
        "project", "phoenix", "bib", "baoees", "brewster", "engine",
        "status", "doel", "output", "input", "deze", "door", "worden",
        "kunnen", "alle", "niet", "wel", "bij", "per", "via", "aan",
    }

    def __init__(
        self,
        bib_root: Optional[str | Path] = None,
        output_root: Optional[str | Path] = None,
    ) -> None:
        self.bib_root = Path(bib_root) if bib_root else Path("bib")
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        search_terms: Optional[List[str]] = None,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        markdown_files = self.scan_markdown_files()
        sections = self.build_sections(markdown_files)
        index = self.build_knowledge_index(markdown_files, sections)
        project_analysis_context = self.build_project_analysis_context(
            sections=sections,
            project_context=project_context or {},
            search_terms=search_terms or [],
        )

        index_path = self.output_root / "bib_knowledge_index.json"
        context_path = self.output_root / "bib_project_analysis_context.json"
        html_path = self.output_root / "bib_knowledge_source.html"

        self.write_json(index_path, index)
        self.write_json(context_path, project_analysis_context)
        html_path.write_text(
            self.build_html_report(index=index, project_analysis_context=project_analysis_context),
            encoding="utf-8",
        )

        warnings = self.build_warnings(markdown_files, sections, project_analysis_context)

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "bib_root": str(self.bib_root),
            "output_root": str(self.output_root),
            "markdown_file_count": len(markdown_files),
            "section_count": len(sections),
            "index_path": str(index_path),
            "project_analysis_context_path": str(context_path),
            "html_path": str(html_path),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "warnings": warnings,
            "recommendation": self.build_recommendation(warnings),
            "extra_results": extra_results,
        }

    def scan_markdown_files(self) -> List[Path]:
        if not self.bib_root.exists():
            return []

        files = [path for path in self.bib_root.rglob("*.md") if path.is_file()]
        return sorted(files, key=self.sort_key)

    def sort_key(self, path: Path) -> tuple:
        rel = self.safe_relative(path, self.bib_root)
        parts = Path(rel).parts
        first = parts[0] if parts else rel

        try:
            index = self.CATEGORY_ORDER.index(first)
        except ValueError:
            index = 999

        return index, rel.lower()

    def build_sections(self, markdown_files: List[Path]) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []

        for file_path in markdown_files:
            rel = self.safe_relative(file_path, self.bib_root)
            category = self.category_for(file_path)
            text = self.read_text_file(file_path)

            current_heading = file_path.stem
            current_level = 1
            current_lines: List[str] = []

            def flush_section() -> None:
                if not current_lines and not current_heading:
                    return

                content = "\n".join(current_lines).strip()
                combined_text = f"{current_heading}\n{content}".strip()

                if not combined_text:
                    return

                keywords = self.extract_keywords(combined_text)

                sections.append(
                    {
                        "section_id": f"bib-section-{len(sections) + 1:04d}",
                        "file_name": file_path.name,
                        "relative_path": rel,
                        "category": category,
                        "heading": current_heading,
                        "heading_level": current_level,
                        "content": content,
                        "keywords": keywords,
                        "word_count": len(combined_text.split()),
                        "char_count": len(combined_text),
                        "priority": self.priority_for(category, current_heading, combined_text),
                    }
                )

            for raw_line in text.splitlines():
                stripped = raw_line.strip()

                heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)

                if heading_match:
                    flush_section()
                    current_level = len(heading_match.group(1))
                    current_heading = heading_match.group(2).strip()
                    current_lines = []
                else:
                    current_lines.append(raw_line)

            flush_section()

        return sections

    def build_knowledge_index(
        self,
        markdown_files: List[Path],
        sections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        categories: Dict[str, Dict[str, Any]] = {}
        keyword_counter: Counter[str] = Counter()

        for section in sections:
            category = section["category"]

            if category not in categories:
                categories[category] = {
                    "category": category,
                    "section_count": 0,
                    "word_count": 0,
                    "top_keywords": [],
                }

            categories[category]["section_count"] += 1
            categories[category]["word_count"] += section["word_count"]

            for keyword in section["keywords"]:
                keyword_counter[keyword] += 1

        for category in categories.values():
            cat_sections = [item for item in sections if item["category"] == category["category"]]
            cat_counter: Counter[str] = Counter()

            for section in cat_sections:
                for keyword in section["keywords"]:
                    cat_counter[keyword] += 1

            category["top_keywords"] = [word for word, _count in cat_counter.most_common(12)]

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "bib_root": str(self.bib_root),
            "markdown_file_count": len(markdown_files),
            "section_count": len(sections),
            "categories": list(categories.values()),
            "top_keywords": [word for word, _count in keyword_counter.most_common(40)],
            "files": [
                {
                    "name": path.name,
                    "relative_path": self.safe_relative(path, self.bib_root),
                    "category": self.category_for(path),
                    "size_bytes": path.stat().st_size if path.exists() else 0,
                }
                for path in markdown_files
            ],
            "sections": sections,
        }

    def build_project_analysis_context(
        self,
        sections: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        search_terms: List[str],
    ) -> Dict[str, Any]:
        topic_queries = {
            "core_system": ["digital", "twin", "project", "phoenix", "workflow"],
            "geotechniek_fundering": ["grondwater", "fundering", "strokenfundering", "paalfundering", "geo", "bodem"],
            "aannames_aaie": ["aaie", "aanname", "aannameslog", "fallback", "automatisch"],
            "bronnen_stee": ["stee", "bron", "evidence", "source", "git", "traceability"],
            "projecten": ["plutostraat", "moskee", "bunschoten", "bruynzeel", "waterfront"],
            "vergunning": ["vergunning", "bopa", "omgevingsvergunning", "aerius", "parkeren"],
            "templates_workflows": ["template", "workflow", "rapport", "input", "output"],
            "exports": ["docx", "pdf", "zip", "dashboard", "manifest", "export"],
        }

        if search_terms:
            topic_queries["custom_search_terms"] = search_terms

        project_text = json.dumps(project_context, ensure_ascii=False, default=str)
        project_keywords = self.extract_keywords(project_text)

        relevant_by_topic = {}

        for topic, terms in topic_queries.items():
            relevant_by_topic[topic] = self.search_sections(
                sections=sections,
                terms=terms,
                limit=10,
            )

        project_relevant_sections = self.search_sections(
            sections=sections,
            terms=project_keywords,
            limit=15,
        )

        core_sections = sorted(
            sections,
            key=lambda item: (-item["priority"], item["relative_path"], item["heading"]),
        )[:20]

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "BIB-contextpakket voor BAOEES projectanalyse.",
            "how_to_use": [
                "Gebruik core_sections als basiskennis voor ieder project.",
                "Gebruik relevant_by_topic voor disciplinegerichte projectanalyse.",
                "Gebruik project_relevant_sections wanneer project_context is meegegeven.",
                "Gebruik AAIE- en STEE-secties om aannames en bronnen te sturen.",
                "Gebruik geotechniek_fundering voor automatische grondwaterstand en funderingsvarianten F1/F2.",
            ],
            "project_context_received": project_context,
            "project_keywords": project_keywords,
            "core_sections": self.compact_sections(core_sections),
            "relevant_by_topic": relevant_by_topic,
            "project_relevant_sections": project_relevant_sections,
            "recommended_next_integration": [
                "Koppel deze engine aan de BAOEES project analyzer.",
                "Laat project_analyzer eerst bib_project_analysis_context.json lezen.",
                "Gebruik BIB-regels voor AAIE defaults, STEE-bronvermelding en funderingsvarianten.",
            ],
        }

    def search_sections(
        self,
        sections: List[Dict[str, Any]],
        terms: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        normalized_terms = [term.lower().strip() for term in terms if term and len(term.strip()) >= 3]

        scored = []

        for section in sections:
            haystack = " ".join(
                [
                    section.get("heading", ""),
                    section.get("content", ""),
                    " ".join(section.get("keywords", [])),
                    section.get("relative_path", ""),
                    section.get("category", ""),
                ]
            ).lower()

            score = 0

            for term in normalized_terms:
                if term in haystack:
                    score += 3

                if term in section.get("keywords", []):
                    score += 5

                if term in section.get("heading", "").lower():
                    score += 6

            score += int(section.get("priority", 0))

            if score > 0:
                scored.append((score, section))

        scored.sort(key=lambda item: (-item[0], item[1]["relative_path"], item[1]["heading"]))

        return [
            self.compact_section(section, score=score)
            for score, section in scored[:limit]
        ]

    def compact_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.compact_section(section) for section in sections]

    def compact_section(self, section: Dict[str, Any], score: Optional[int] = None) -> Dict[str, Any]:
        content = section.get("content", "")
        snippet = content[:600] + ("..." if len(content) > 600 else "")

        result = {
            "section_id": section.get("section_id"),
            "relative_path": section.get("relative_path"),
            "category": section.get("category"),
            "heading": section.get("heading"),
            "keywords": section.get("keywords", [])[:12],
            "word_count": section.get("word_count"),
            "priority": section.get("priority"),
            "snippet": snippet,
        }

        if score is not None:
            result["score"] = score

        return result

    def extract_keywords(self, text: str, limit: int = 20) -> List[str]:
        words = re.findall(r"[A-Za-zÀ-ÿ0-9_\-]{3,}", text.lower())
        filtered = [
            word.strip("_-")
            for word in words
            if word.strip("_-") and word.strip("_-") not in self.STOPWORDS
        ]

        counter = Counter(filtered)
        return [word for word, _count in counter.most_common(limit)]

    def priority_for(self, category: str, heading: str, text: str) -> int:
        score = 0
        category_scores = {
            "01_MASTER_KNOWLEDGE": 10,
            "03_ENGINES": 9,
            "04_STANDARDS_AND_RULES": 9,
            "09_ASSUMPTIONS": 9,
            "08_SOURCE_EVIDENCE": 8,
            "06_WORKFLOWS": 7,
            "05_TEMPLATES": 6,
            "02_PROJECTS": 6,
            "07_LESSONS_LEARNED": 5,
            "10_EXPORTS": 4,
            "00_INDEX": 10,
        }

        score += category_scores.get(category, 3)

        important_terms = [
            "digital twin",
            "aaie",
            "stee",
            "grondwater",
            "fundering",
            "strokenfundering",
            "paalfundering",
            "source evidence",
            "git evidence",
            "workflow",
            "projectanalyse",
        ]

        text_lower = f"{heading} {text}".lower()

        for term in important_terms:
            if term in text_lower:
                score += 2

        return score

    def category_for(self, path: Path) -> str:
        rel = self.safe_relative(path, self.bib_root)
        parts = Path(rel).parts

        if len(parts) == 1:
            return "00_INDEX"

        return parts[0]

    def build_warnings(
        self,
        markdown_files: List[Path],
        sections: List[Dict[str, Any]],
        project_analysis_context: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not self.bib_root.exists():
            warnings.append("BIB-map ontbreekt.")

        if len(markdown_files) == 0:
            warnings.append("Geen Markdown-bestanden gevonden.")

        if len(sections) == 0:
            warnings.append("Geen BIB-secties opgebouwd.")

        required_topics = [
            "core_system",
            "geotechniek_fundering",
            "aannames_aaie",
            "bronnen_stee",
            "exports",
        ]

        relevant_by_topic = project_analysis_context.get("relevant_by_topic", {})

        for topic in required_topics:
            if not relevant_by_topic.get(topic):
                warnings.append(f"Geen relevante BIB-secties gevonden voor topic: {topic}")

        if not warnings:
            warnings.append("Geen kritieke BIB knowledge source-waarschuwingen.")

        return warnings

    def build_recommendation(self, warnings: List[str]) -> Dict[str, Any]:
        return {
            "status": "BIB_KNOWLEDGE_SOURCE_ADVIES",
            "advice": [
                "Open bib_knowledge_source.html en controleer de kennisindex.",
                "Controleer bib_project_analysis_context.json.",
                "Gebruik deze context in v3.7 voor koppeling aan BAOEES Project Analyzer.",
                "Gebruik geotechniek_fundering voor automatische grondwaterstand en funderingsvarianten.",
                "Gebruik aannames_aaie en bronnen_stee voor transparantie en traceability.",
            ],
            "warnings_count": len(warnings),
        }

    def build_html_report(
        self,
        index: Dict[str, Any],
        project_analysis_context: Dict[str, Any],
    ) -> str:
        category_cards = []

        for category in index.get("categories", []):
            category_cards.append(
                f"""
                <div class="card">
                  <h3>{self.esc(category.get("category", ""))}</h3>
                  <p><strong>{self.esc(category.get("section_count", 0))}</strong> secties</p>
                  <p>{self.esc(category.get("word_count", 0))} woorden</p>
                  <p class="muted">{self.esc(", ".join(category.get("top_keywords", [])[:8]))}</p>
                </div>
                """
            )

        topic_rows = []

        for topic, sections in project_analysis_context.get("relevant_by_topic", {}).items():
            topic_rows.append(
                "<tr>"
                f"<td>{self.esc(topic)}</td>"
                f"<td>{self.esc(len(sections))}</td>"
                f"<td>{self.esc(', '.join([item.get('heading', '') for item in sections[:5]]))}</td>"
                "</tr>"
            )

        section_rows = []

        for section in index.get("sections", [])[:200]:
            section_rows.append(
                "<tr>"
                f"<td>{self.esc(section.get('category', ''))}</td>"
                f"<td>{self.esc(section.get('relative_path', ''))}</td>"
                f"<td>{self.esc(section.get('heading', ''))}</td>"
                f"<td>{self.esc(section.get('word_count', ''))}</td>"
                f"<td>{self.esc(', '.join(section.get('keywords', [])[:8]))}</td>"
                "</tr>"
            )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB Knowledge Source</title>
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
    .muted {{
      color: #cbd5e1;
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
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX BIB KNOWLEDGE SOURCE</h1>
    <p>Brewster Integrated Bibliotheek als kennisbron voor BAOEES projectanalyse</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(index.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Markdown-bestanden</h3>
        <p>{self.esc(index.get("markdown_file_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Secties</h3>
        <p>{self.esc(index.get("section_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Top keywords</h3>
        <p class="muted">{self.esc(", ".join(index.get("top_keywords", [])[:14]))}</p>
      </div>
    </section>

    <h2>Categorieën</h2>
    <section class="grid">
      {''.join(category_cards)}
    </section>

    <h2>Projectanalyse Topics</h2>
    <table>
      <thead>
        <tr>
          <th>Topic</th>
          <th>Matches</th>
          <th>Topsecties</th>
        </tr>
      </thead>
      <tbody>
        {''.join(topic_rows)}
      </tbody>
    </table>

    <h2>Kennisindex Secties</h2>
    <table>
      <thead>
        <tr>
          <th>Categorie</th>
          <th>Bestand</th>
          <th>Kop</th>
          <th>Woorden</th>
          <th>Keywords</th>
        </tr>
      </thead>
      <tbody>
        {''.join(section_rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""

    def read_text_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            return f"[Kon bestand niet lezen: {path} — {exc}]"

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def safe_relative(self, path: Path, start: Path) -> str:
        try:
            return path.resolve().relative_to(start.resolve()).as_posix()
        except Exception:
            try:
                return path.relative_to(start).as_posix()
            except Exception:
                return path.as_posix()

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = BibKnowledgeSourceEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()