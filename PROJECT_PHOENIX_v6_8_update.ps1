# PROJECT PHOENIX v6.8 UPDATE
# Doel: Deep Knowledge Harvest Engine toevoegen.
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.8 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\deep_knowledge_harvest_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_8.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_8.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v6_8_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v6_8_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class DeepKnowledgeHarvestEngine:
    ENGINE_NAME = "Project Phoenix Deep Knowledge Harvest Engine"
    ENGINE_VERSION = "v6.8"

    TEXT_SUFFIXES = {
        ".txt",
        ".md",
        ".json",
        ".py",
        ".ps1",
        ".bat",
        ".html",
        ".htm",
        ".csv",
        ".xml",
        ".yaml",
        ".yml",
    }

    SKIP_PARTS = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
    }

    KEYWORDS = {
        "moskee_bunschoten": [
            "moskee",
            "bikkersweg",
            "bunschoten",
            "aerius",
            "parkeer",
            "participatie",
        ],
        "plutostraat_paramaribo": [
            "plutostraat",
            "paramaribo",
            "grondwater",
            "strokenfundering",
            "sondering",
            "fundering",
        ],
        "bruynzeel_waterfront": [
            "bruynzeel",
            "waterfront",
            "glis",
            "masterplan",
            "grex",
            "investeerders",
        ],
        "baoees_core": [
            "baoees",
            "beos",
            "brewas",
            "digital twin",
            "aaie",
            "stee",
            "knowledge graph",
        ],
        "engineering_modules": [
            "freecad",
            "opensees",
            "calculix",
            "geotechniek",
            "constructie",
            "riolering",
            "vergunning",
            "parking",
            "parkeren",
        ],
        "workflow_automation": [
            "start_projectanalyse",
            "health check",
            "auto repair",
            "diagnostics",
            "project phoenix",
        ],
    }

    def __init__(self) -> None:
        self.project_output_root = PROJECT_ROOT / "outputs" / "projects"
        self.bib_root = PROJECT_ROOT / "outputs" / "bib"
        self.harvest_root = self.bib_root / "harvest"
        self.dashboard_root = self.bib_root / "dashboards"
        self.index_root = self.bib_root / "index"

        self.harvest_index_path = (
            self.harvest_root
            / "deep_knowledge_harvest_index_v6_8.json"
        )
        self.harvest_summary_path = (
            self.harvest_root
            / "deep_knowledge_harvest_summary_v6_8.md"
        )
        self.harvest_log_path = (
            self.harvest_root
            / "deep_knowledge_harvest_log_v6_8.json"
        )
        self.harvest_dashboard_path = (
            self.dashboard_root
            / "deep_knowledge_harvest_dashboard_v6_8.html"
        )
        self.bib_index_path = (
            self.index_root
            / "bib_knowledge_content_index.json"
        )
        self.project_summary_path = (
            self.project_output_root
            / "deep_knowledge_harvest_summary_v6_8.json"
        )

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)
        self.bib_root.mkdir(parents=True, exist_ok=True)
        self.harvest_root.mkdir(parents=True, exist_ok=True)
        self.dashboard_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        harvest_files = self.scan_repository()
        knowledge_records = self.build_knowledge_records(harvest_files)
        project_map = self.build_project_map(knowledge_records)
        topic_map = self.build_topic_map(knowledge_records)
        gaps = self.detect_gaps(project_map, topic_map)

        harvest_index = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "file_count": len(harvest_files),
            "knowledge_record_count": len(knowledge_records),
            "project_map": project_map,
            "topic_map": topic_map,
            "gaps": gaps,
            "files": harvest_files,
            "knowledge_records": knowledge_records,
        }

        self.write_json(self.harvest_index_path, harvest_index)
        self.write_text(
            self.harvest_summary_path,
            self.build_markdown_summary(harvest_index),
        )

        existing_bib_index = self.read_json(self.bib_index_path)
        merged_bib_index = self.merge_into_bib_index(existing_bib_index, harvest_index)
        self.write_json(self.bib_index_path, merged_bib_index)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "bib_root": str(self.bib_root),
            "harvest_index_path": str(self.harvest_index_path),
            "harvest_summary_path": str(self.harvest_summary_path),
            "harvest_log_path": str(self.harvest_log_path),
            "harvest_dashboard_path": str(self.harvest_dashboard_path),
            "bib_index_path": str(self.bib_index_path),
            "project_summary_path": str(self.project_summary_path),
            "file_count": len(harvest_files),
            "knowledge_record_count": len(knowledge_records),
            "project_count": len(project_map),
            "topic_count": len(topic_map),
            "gap_count": len(gaps),
            "next_steps": [
                "Controleer deep_knowledge_harvest_dashboard_v6_8.html.",
                "Controleer deep_knowledge_harvest_index_v6_8.json.",
                "Controleer welke kennisgaten nog openstaan.",
                "Leg v6.8 vast met git add, commit en push.",
                "Ga daarna door naar Module Registry & Engine Dashboard.",
            ],
        }

        self.write_json(self.harvest_log_path, result)
        self.write_json(self.project_summary_path, result)
        self.write_text(self.harvest_dashboard_path, self.build_dashboard(result, harvest_index))

        return result

    def scan_repository(self) -> List[Dict[str, Any]]:
        scan_roots = [
            PROJECT_ROOT / "outputs",
            PROJECT_ROOT / "baoees",
            PROJECT_ROOT / "START_PROJECTANALYSE.bat",
            PROJECT_ROOT / "START_PROJECTANALYSE.ps1",
        ]

        for path in PROJECT_ROOT.glob("PROJECT_PHOENIX_v*_update.ps1"):
            scan_roots.append(path)

        all_paths: List[Path] = []

        for root in scan_roots:
            if not root.exists():
                continue

            if root.is_file():
                all_paths.append(root)
                continue

            for path in root.rglob("*"):
                if not path.is_file():
                    continue

                if self.should_skip(path):
                    continue

                all_paths.append(path)

        unique_paths = []
        seen = set()

        for path in all_paths:
            key = str(path.resolve()).lower()

            if key in seen:
                continue

            seen.add(key)
            unique_paths.append(path)

        harvested: List[Dict[str, Any]] = []

        for path in sorted(unique_paths, key=lambda item: str(item).lower()):
            harvested.append(self.describe_file(path))

        return harvested

    def should_skip(self, path: Path) -> bool:
        for part in path.parts:
            if part in self.SKIP_PARTS:
                return True

        if path.suffix.lower() not in self.TEXT_SUFFIXES:
            return True

        try:
            if path.stat().st_size > 2_000_000:
                return True
        except Exception:
            return True

        return False

    def describe_file(self, path: Path) -> Dict[str, Any]:
        text = self.read_text(path)
        lower_text = text.lower()
        topics = self.detect_topics(lower_text)
        projects = self.detect_projects(lower_text)
        decisions = self.extract_decisions(text)
        actions = self.extract_actions(text)

        stat = path.stat()

        return {
            "name": path.name,
            "path": str(path),
            "relative_path": self.safe_relative_path(path),
            "suffix": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "sha256": self.sha256_text(text),
            "topics": topics,
            "projects": projects,
            "decision_count": len(decisions),
            "action_count": len(actions),
            "decisions": decisions[:20],
            "actions": actions[:20],
            "snippet": self.make_snippet(text),
        }

    def build_knowledge_records(
        self,
        files: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        for index, file_item in enumerate(files, start=1):
            if not file_item.get("topics") and not file_item.get("projects"):
                continue

            records.append(
                {
                    "record_id": f"KH-{index:04d}",
                    "source_file": file_item.get("relative_path", ""),
                    "name": file_item.get("name", ""),
                    "topics": file_item.get("topics", []),
                    "projects": file_item.get("projects", []),
                    "decision_count": file_item.get("decision_count", 0),
                    "action_count": file_item.get("action_count", 0),
                    "snippet": file_item.get("snippet", ""),
                    "modified_at": file_item.get("modified_at", ""),
                    "source_hash": file_item.get("sha256", ""),
                }
            )

        return records

    def build_project_map(
        self,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        project_map: Dict[str, Any] = {}

        for record in records:
            for project in record.get("projects", []):
                if project not in project_map:
                    project_map[project] = {
                        "record_count": 0,
                        "sources": [],
                        "topics": {},
                    }

                project_map[project]["record_count"] += 1
                project_map[project]["sources"].append(record["source_file"])

                for topic in record.get("topics", []):
                    project_map[project]["topics"][topic] = (
                        project_map[project]["topics"].get(topic, 0) + 1
                    )

        return project_map

    def build_topic_map(
        self,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        topic_map: Dict[str, Any] = {}

        for record in records:
            for topic in record.get("topics", []):
                if topic not in topic_map:
                    topic_map[topic] = {
                        "record_count": 0,
                        "sources": [],
                        "projects": {},
                    }

                topic_map[topic]["record_count"] += 1
                topic_map[topic]["sources"].append(record["source_file"])

                for project in record.get("projects", []):
                    topic_map[topic]["projects"][project] = (
                        topic_map[topic]["projects"].get(project, 0) + 1
                    )

        return topic_map

    def detect_gaps(
        self,
        project_map: Dict[str, Any],
        topic_map: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        expected_projects = [
            "moskee_bunschoten",
            "plutostraat_paramaribo",
            "bruynzeel_waterfront",
        ]

        expected_topics = [
            "baoees_core",
            "engineering_modules",
            "workflow_automation",
        ]

        gaps: List[Dict[str, Any]] = []

        for project in expected_projects:
            if project not in project_map:
                gaps.append(
                    {
                        "type": "project",
                        "name": project,
                        "message": "Projectkennis is nog niet of onvoldoende lokaal geoogst.",
                    }
                )

        for topic in expected_topics:
            if topic not in topic_map:
                gaps.append(
                    {
                        "type": "topic",
                        "name": topic,
                        "message": "Topic is nog niet of onvoldoende lokaal geoogst.",
                    }
                )

        return gaps

    def detect_topics(self, lower_text: str) -> List[str]:
        topics: List[str] = []

        for topic, keywords in self.KEYWORDS.items():
            if any(keyword in lower_text for keyword in keywords):
                topics.append(topic)

        return topics

    def detect_projects(self, lower_text: str) -> List[str]:
        projects: List[str] = []

        if any(keyword in lower_text for keyword in ["moskee", "bikkersweg", "bunschoten"]):
            projects.append("moskee_bunschoten")

        if any(keyword in lower_text for keyword in ["plutostraat", "paramaribo", "sondering"]):
            projects.append("plutostraat_paramaribo")

        if any(keyword in lower_text for keyword in ["bruynzeel", "waterfront", "glis"]):
            projects.append("bruynzeel_waterfront")

        return projects

    def extract_decisions(self, text: str) -> List[str]:
        patterns = [
            r"(?i)(besluit|keuze|default|standaard|afgesproken|voortaan|vanaf nu).{0,180}",
            r"(?i)(gekozen|vastgelegd|geïntegreerd|geintegreerd).{0,180}",
        ]

        return self.extract_matches(text, patterns)

    def extract_actions(self, text: str) -> List[str]:
        patterns = [
            r"(?i)(actie|todo|next step|volgende stap|nog te bouwen|moet).{0,180}",
            r"(?i)(run|voer uit|download|commit|push).{0,180}",
        ]

        return self.extract_matches(text, patterns)

    def extract_matches(
        self,
        text: str,
        patterns: List[str],
    ) -> List[str]:
        matches: List[str] = []

        for pattern in patterns:
            for match in re.findall(pattern, text):
                if isinstance(match, tuple):
                    continue

            for found in re.finditer(pattern, text):
                cleaned = " ".join(found.group(0).split())

                if cleaned not in matches:
                    matches.append(cleaned)

                if len(matches) >= 50:
                    return matches

        return matches

    def merge_into_bib_index(
        self,
        existing_index: Dict[str, Any],
        harvest_index: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not existing_index:
            existing_index = {}

        existing_index["status"] = "BIJGEWERKT"
        existing_index["last_updated_by"] = self.ENGINE_NAME
        existing_index["last_updated_version"] = self.ENGINE_VERSION
        existing_index["last_updated_at"] = datetime.now().isoformat(timespec="seconds")
        existing_index["deep_knowledge_harvest"] = {
            "path": str(self.harvest_index_path),
            "summary_path": str(self.harvest_summary_path),
            "file_count": harvest_index.get("file_count", 0),
            "knowledge_record_count": harvest_index.get("knowledge_record_count", 0),
            "project_count": len(harvest_index.get("project_map", {})),
            "topic_count": len(harvest_index.get("topic_map", {})),
            "gap_count": len(harvest_index.get("gaps", [])),
        }

        records = existing_index.get("recognized_text_items", [])

        if not isinstance(records, list):
            records = []

        records.append(
            {
                "source": "deep_knowledge_harvest_v6_8",
                "type": "deep_harvest",
                "title": "Deep Knowledge Harvest v6.8",
                "summary": "Lokale Phoenix/BIB/outputs/code kennis geoogst en geïndexeerd.",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "harvest_index_path": str(self.harvest_index_path),
            }
        )

        existing_index["recognized_text_items"] = records

        return existing_index

    def build_markdown_summary(
        self,
        harvest_index: Dict[str, Any],
    ) -> str:
        lines: List[str] = []

        lines.append("# Deep Knowledge Harvest v6.8")
        lines.append("")
        lines.append(f"Bestanden gescand: {harvest_index.get('file_count', 0)}")
        lines.append(f"Kennisrecords: {harvest_index.get('knowledge_record_count', 0)}")
        lines.append("")

        lines.append("## Projecten")
        lines.append("")

        for project, data in harvest_index.get("project_map", {}).items():
            lines.append(f"### {project}")
            lines.append(f"Records: {data.get('record_count', 0)}")
            lines.append("Topics:")
            for topic, count in data.get("topics", {}).items():
                lines.append(f"- {topic}: {count}")
            lines.append("")

        lines.append("## Topics")
        lines.append("")

        for topic, data in harvest_index.get("topic_map", {}).items():
            lines.append(f"### {topic}")
            lines.append(f"Records: {data.get('record_count', 0)}")
            lines.append("")

        lines.append("## Kennisgaten")
        lines.append("")

        gaps = harvest_index.get("gaps", [])

        if not gaps:
            lines.append("Geen hoofdgaten gevonden.")
        else:
            for gap in gaps:
                lines.append(f"- {gap.get('type', '')}: {gap.get('name', '')} — {gap.get('message', '')}")

        lines.append("")

        return "\n".join(lines)

    def build_dashboard(
        self,
        result: Dict[str, Any],
        harvest_index: Dict[str, Any],
    ) -> str:
        project_rows = "".join(
            "<tr>"
            f"<td>{self.esc(project)}</td>"
            f"<td>{self.esc(data.get('record_count', 0))}</td>"
            f"<td>{self.esc(', '.join(data.get('topics', {}).keys()))}</td>"
            "</tr>"
            for project, data in harvest_index.get("project_map", {}).items()
        )

        topic_rows = "".join(
            "<tr>"
            f"<td>{self.esc(topic)}</td>"
            f"<td>{self.esc(data.get('record_count', 0))}</td>"
            f"<td>{self.esc(', '.join(data.get('projects', {}).keys()))}</td>"
            "</tr>"
            for topic, data in harvest_index.get("topic_map", {}).items()
        )

        gap_rows = "".join(
            "<tr>"
            f"<td>{self.esc(gap.get('type', ''))}</td>"
            f"<td>{self.esc(gap.get('name', ''))}</td>"
            f"<td>{self.esc(gap.get('message', ''))}</td>"
            "</tr>"
            for gap in harvest_index.get("gaps", [])
        )

        if not gap_rows:
            gap_rows = "<tr><td>OK</td><td>Geen hoofdgaten</td><td>Geen actie nodig</td></tr>"

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Deep Knowledge Harvest v6.8</title>
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
    <h1>Project Phoenix Deep Knowledge Harvest v6.8</h1>
    <p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
    <p>Lokale Phoenix-, BIB-, output- en codebestanden zijn gescand en als kennisindex gekoppeld aan de BIB.</p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <p>Bestanden gescand: {self.esc(result.get("file_count", 0))}</p>
    <p>Kennisrecords: {self.esc(result.get("knowledge_record_count", 0))}</p>
    <p>Projecten: {self.esc(result.get("project_count", 0))}</p>
    <p>Topics: {self.esc(result.get("topic_count", 0))}</p>
    <p>Kennisgaten: {self.esc(result.get("gap_count", 0))}</p>
  </section>

  <section>
    <h2>Projectkaart</h2>
    <table>
      <tr><th>Project</th><th>Records</th><th>Topics</th></tr>
      {project_rows}
    </table>
  </section>

  <section>
    <h2>Topickaart</h2>
    <table>
      <tr><th>Topic</th><th>Records</th><th>Projecten</th></tr>
      {topic_rows}
    </table>
  </section>

  <section>
    <h2>Kennisgaten</h2>
    <table>
      <tr><th>Type</th><th>Naam</th><th>Bericht</th></tr>
      {gap_rows}
    </table>
  </section>

  <section>
    <h2>Bestanden</h2>
    <p><code>{self.esc(result.get("harvest_index_path", ""))}</code></p>
    <p><code>{self.esc(result.get("harvest_summary_path", ""))}</code></p>
    <p><code>{self.esc(result.get("bib_index_path", ""))}</code></p>
  </section>
</main>
</body>
</html>
"""

    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                try:
                    return path.read_text(encoding="latin-1")
                except Exception:
                    return ""

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

    def make_snippet(self, text: str) -> str:
        cleaned = " ".join(text.split())
        return cleaned[:600]

    def sha256_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def safe_relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except Exception:
            return str(path)

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


KnowledgeHarvestEngine = DeepKnowledgeHarvestEngine
DeepHarvestEngine = DeepKnowledgeHarvestEngine
BIBHarvestEngine = DeepKnowledgeHarvestEngine


def main() -> None:
    engine = DeepKnowledgeHarvestEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.8
echo ============================================================
echo.

echo [1/13] Brewster kennis migreren...
python baoees\project_analyzer\brewster_knowledge_migration_engine.py
if errorlevel 1 goto error

echo [2/13] Deep Knowledge Harvest uitvoeren...
python baoees\project_analyzer\deep_knowledge_harvest_engine.py
if errorlevel 1 goto error

echo [3/13] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [4/13] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [5/13] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [6/13] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [7/13] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [8/13] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [9/13] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [10/13] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo [11/13] Error diagnostics uitvoeren...
python baoees\project_analyzer\project_error_diagnostics_engine.py
if errorlevel 1 goto error

echo [12/13] Auto repair uitvoeren...
python baoees\project_analyzer\project_auto_repair_engine.py
if errorlevel 1 goto error

echo [13/13] Health check na reparatie uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.8 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\bib\dashboards\deep_knowledge_harvest_dashboard_v6_8.html" (
    start "" "outputs\bib\dashboards\deep_knowledge_harvest_dashboard_v6_8.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.8 is gestopt.
echo Controleer de foutmelding hierboven.
echo.
git status
pause
exit /b 1
'@

$Ps1RunnerContent = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.8" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Steps = @(
    @{ Name = "Brewster kennis migreren"; Command = "baoees\project_analyzer\brewster_knowledge_migration_engine.py" },
    @{ Name = "Deep Knowledge Harvest"; Command = "baoees\project_analyzer\deep_knowledge_harvest_engine.py" },
    @{ Name = "Startanalyse"; Command = "baoees\project_analyzer\project_start_analysis_engine.py" },
    @{ Name = "Workflow"; Command = "baoees\project_analyzer\project_analyzer_workflow_engine.py" },
    @{ Name = "AAIE/BIB aannames"; Command = "baoees\project_analyzer\aaie_bib_assumption_loader.py" },
    @{ Name = "Projectrapportagepackage"; Command = "baoees\project_analyzer\project_report_bib_engine.py" },
    @{ Name = "DOCX/PDF export"; Command = "baoees\project_analyzer\project_report_export_engine.py" },
    @{ Name = "Evidence en projectpakket"; Command = "baoees\project_analyzer\project_package_evidence_engine.py" },
    @{ Name = "Launcher bridge en startdashboard"; Command = "baoees\project_analyzer\project_analyzer_launcher_bridge.py" },
    @{ Name = "Health check"; Command = "baoees\project_analyzer\project_analysis_health_check_engine.py" },
    @{ Name = "Error diagnostics"; Command = "baoees\project_analyzer\project_error_diagnostics_engine.py" },
    @{ Name = "Auto repair"; Command = "baoees\project_analyzer\project_auto_repair_engine.py" },
    @{ Name = "Health check na reparatie"; Command = "baoees\project_analyzer\project_analysis_health_check_engine.py" }
)

$Index = 1

foreach ($Step in $Steps) {
    Write-Host ""
    Write-Host "[$Index/$($Steps.Count)] $($Step.Name) uitvoeren..." -ForegroundColor Yellow
    python $Step.Command
    if ($LASTEXITCODE -ne 0) {
        throw "Stap mislukt: $($Step.Name)"
    }
    $Index++
}

Write-Host ""
Write-Host "PROJECT PHOENIX v6.8 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$HarvestDashboard = Join-Path $PSScriptRoot "outputs\bib\dashboards\deep_knowledge_harvest_dashboard_v6_8.html"

if (Test-Path $HarvestDashboard) {
    Start-Process $HarvestDashboard
}

git status
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1RunnerContent -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1RunnerContent -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Deep Knowledge Harvest Connector"
    engine_version = "v6.8"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    harvest_engine = "$EnginePath"
    start_projectanalyse_bat = "$BatPath"
    start_projectanalyse_ps1 = "$Ps1Path"
    versioned_bat = "$VersionedBatPath"
    versioned_ps1 = "$VersionedPs1Path"
    purpose = "Scant lokale Phoenix/BIB/output/codebestanden, oogst kennis en koppelt die aan de BIB."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven:" -ForegroundColor Green
Write-Host " - baoees\project_analyzer\deep_knowledge_harvest_engine.py"
Write-Host " - START_PROJECTANALYSE.bat"
Write-Host " - START_PROJECTANALYSE.ps1"
Write-Host " - START_PROJECTANALYSE_v6_8.bat"
Write-Host " - START_PROJECTANALYSE_v6_8.ps1"
Write-Host " - outputs\projects\start_projectanalyse_v6_8_update_log.json"

Write-Host ""
Write-Host "Syntaxcontrole deep knowledge harvest engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\deep_knowledge_harvest_engine.py

Write-Host ""
Write-Host "Test START_PROJECTANALYSE_v6_8.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v6_8.ps1

Write-Host ""
Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "PROJECT PHOENIX v6.8 UPDATE KLAAR" -ForegroundColor Green
