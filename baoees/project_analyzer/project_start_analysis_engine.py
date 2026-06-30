from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectStartAnalysisEngine:
    """
    PROJECT PHOENIX / BAOEES
    START PROJECTANALYSE Engine v5.7

    Doel:
    - Centrale lokale startknop voor Project Phoenix / BAOEES.
    - Draait de centrale Project Analyzer workflow waar mogelijk.
    - Draait de Project Package Evidence Engine waar mogelijk.
    - Draait de Launcher Bridge waar mogelijk.
    - Leest de BIB-kennisindex uit:
      outputs/bib/index/bib_knowledge_content_index.json
    - Toont BIB-status in het START PROJECTANALYSE dashboard.
    - Schrijft een JSON-log en HTML-dashboard.
    - Blijft robuust werken als een onderliggende module nog ontbreekt.
    """

    ENGINE_NAME = "Project Phoenix START PROJECTANALYSE Engine"
    ENGINE_VERSION = "v5.7"

    def __init__(self, project_output_root: Optional[str | Path] = None) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.bib_root = Path("outputs") / "bib"
        self.bib_index_path = self.bib_root / "index" / "bib_knowledge_content_index.json"

        self.dashboard_path = self.project_output_root / "project_start_analysis_dashboard.html"
        self.log_path = self.project_output_root / "project_start_analysis_log.json"

    def run(self) -> Dict[str, Any]:
        started_at = datetime.now().isoformat(timespec="seconds")
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        run_results: Dict[str, Any] = {
            "central_workflow": self.run_optional_engine(
                candidates=[
                    {
                        "module": "baoees.project_analyzer.project_analyzer_workflow_engine",
                        "class": "ProjectAnalyzerWorkflowEngine",
                    },
                    {
                        "module": "baoees.project_analyzer.project_analyzer_workflow",
                        "class": "ProjectAnalyzerWorkflow",
                    },
                ],
                label="Centrale Project Analyzer workflow",
            ),
            "project_package_evidence": self.run_optional_engine(
                candidates=[
                    {
                        "module": "baoees.project_analyzer.project_package_evidence_engine",
                        "class": "ProjectPackageEvidenceEngine",
                    },
                    {
                        "module": "baoees.project_analyzer.project_analyzer_package_evidence_engine",
                        "class": "ProjectAnalyzerPackageEvidenceEngine",
                    },
                ],
                label="Project Package Evidence Engine",
            ),
            "launcher_bridge": self.run_optional_engine(
                candidates=[
                    {
                        "module": "baoees.project_analyzer.project_analyzer_launcher_bridge",
                        "class": "ProjectAnalyzerLauncherBridge",
                    },
                ],
                label="Project Analyzer Launcher Bridge",
            ),
        }

        bib_summary = self.load_bib_knowledge_summary()
        finished_at = datetime.now().isoformat(timespec="seconds")

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "purpose": "START PROJECTANALYSE met BIB-kennisindexkoppeling.",
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "dashboard_path": str(self.dashboard_path),
            "log_path": str(self.log_path),
            "bib": bib_summary,
            "run_results": run_results,
            "next_steps": [
                "Open outputs/projects/project_start_analysis_dashboard.html.",
                "Controleer BIB-status in het START PROJECTANALYSE dashboard.",
                "Controleer outputs/bib/index/bib_knowledge_content_index.json.",
                "Controleer outputs/projects/index.html.",
                "Daarna BIB-koppeling verder doorzetten naar AAIE en Project Analyzer modules.",
            ],
        }

        self.write_json(self.log_path, result)
        self.write_html(self.dashboard_path, self.build_dashboard(result))

        return result

    def run_optional_engine(
        self,
        candidates: List[Dict[str, str]],
        label: str,
    ) -> Dict[str, Any]:
        errors: List[str] = []

        for candidate in candidates:
            module_name = candidate["module"]
            class_name = candidate["class"]

            try:
                module = importlib.import_module(module_name)
                engine_class = getattr(module, class_name)
                engine = engine_class()

                if not hasattr(engine, "run"):
                    errors.append(f"{module_name}.{class_name} heeft geen run() methode.")
                    continue

                output = engine.run()

                return {
                    "status": "UITGEVOERD",
                    "label": label,
                    "module": module_name,
                    "class": class_name,
                    "output": output,
                }

            except ModuleNotFoundError as error:
                errors.append(f"Module niet gevonden: {module_name} — {error}")
            except AttributeError as error:
                errors.append(f"Class niet gevonden: {module_name}.{class_name} — {error}")
            except Exception as error:
                errors.append(
                    f"Fout bij uitvoeren {module_name}.{class_name}: {error}\n"
                    f"{traceback.format_exc()}"
                )

        return {
            "status": "OVERGESLAGEN",
            "label": label,
            "message": "Geen werkende engine-kandidaat gevonden of engine kon niet worden uitgevoerd.",
            "errors": errors,
        }

    def load_bib_knowledge_summary(self) -> Dict[str, Any]:
        if not self.bib_index_path.exists():
            return {
                "status": "ONTBREEKT",
                "message": "BIB-kennisindex bestaat nog niet.",
                "bib_index_path": str(self.bib_index_path),
                "recognized_text_items_count": 0,
                "projects": [],
                "categories": {},
                "technical_topics": {},
                "decisions_count": 0,
                "knowledge_items_count": 0,
                "actions_count": 0,
            }

        data = self.read_json(self.bib_index_path)

        return {
            "status": data.get("status", "GELEZEN"),
            "engine": data.get("engine", ""),
            "engine_version": data.get("engine_version", ""),
            "generated_at": data.get("generated_at", ""),
            "bib_index_path": str(self.bib_index_path),
            "recognized_text_items_count": data.get("recognized_text_items_count", 0),
            "projects": data.get("projects", []),
            "categories": data.get("categories", {}),
            "technical_topics": data.get("technical_topics", {}),
            "decisions_count": data.get("decisions_count", 0),
            "knowledge_items_count": data.get("knowledge_items_count", 0),
            "actions_count": data.get("actions_count", 0),
            "recognized_items_count": len(data.get("recognized_items", [])),
        }

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        bib = result.get("bib", {})
        run_results = result.get("run_results", {})

        engine_cards = ""

        for key, item in run_results.items():
            status = item.get("status", "ONBEKEND")
            label = item.get("label", key)
            message = item.get("message", "")
            module = item.get("module", "")

            engine_cards += f"""
            <div class="card">
              <h3>{self.esc(label)}</h3>
              <p><span class="badge">{self.esc(status)}</span></p>
              <p class="muted">{self.esc(message)}</p>
              <p class="muted"><code>{self.esc(module)}</code></p>
            </div>
            """

        bib_category_cards = self.build_cards_from_dict(
            bib.get("categories", {}),
            "Nog geen BIB-categorieën herkend.",
        )

        topic_cards = self.build_cards_from_dict(
            bib.get("technical_topics", {}),
            "Nog geen technische onderwerpen herkend.",
        )

        projects_text = ", ".join(bib.get("projects", [])) or "Nog geen projecten herkend."

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix START PROJECTANALYSE v5.7</title>
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
    a {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <p class="muted">PROJECT PHOENIX / BAOEES</p>
    <h1>START PROJECTANALYSE v5.7</h1>
    <p>Centrale projectstart met koppeling naar de lokale BIB-kennisindex.</p>
    <p><span class="badge">{self.esc(result.get("status", ""))}</span></p>
  </section>

  <section>
    <h2>Startanalyse</h2>
    <div class="grid">
      <div class="card">
        <h3>Engine</h3>
        <p>{self.esc(result.get("engine", ""))}</p>
        <p class="muted">{self.esc(result.get("engine_version", ""))}</p>
      </div>
      <div class="card">
        <h3>Start</h3>
        <p>{self.esc(result.get("started_at", ""))}</p>
      </div>
      <div class="card">
        <h3>Einde</h3>
        <p>{self.esc(result.get("finished_at", ""))}</p>
      </div>
      <div class="card">
        <h3>Projectmap</h3>
        <p><code>{self.esc(result.get("project_root", ""))}</code></p>
      </div>
    </div>
  </section>

  <section>
    <h2>BIB-status</h2>
    <div class="grid">
      <div class="card">
        <h3>BIB-index</h3>
        <p><span class="badge">{self.esc(bib.get("status", ""))}</span></p>
        <p class="muted"><code>{self.esc(bib.get("bib_index_path", ""))}</code></p>
      </div>
      <div class="card">
        <h3>Inhoudelijk herkend</h3>
        <p>{self.esc(bib.get("recognized_text_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Besluiten</h3>
        <p>{self.esc(bib.get("decisions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Kennisitems</h3>
        <p>{self.esc(bib.get("knowledge_items_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Acties</h3>
        <p>{self.esc(bib.get("actions_count", 0))}</p>
      </div>
      <div class="card">
        <h3>Projecten</h3>
        <p>{self.esc(projects_text)}</p>
      </div>
    </div>
  </section>

  <section>
    <h2>BIB-kenniscategorieën</h2>
    <div class="grid">
      {bib_category_cards}
    </div>
  </section>

  <section>
    <h2>Technische onderwerpen uit BIB</h2>
    <div class="grid">
      {topic_cards}
    </div>
  </section>

  <section>
    <h2>Uitgevoerde engines</h2>
    <div class="grid">
      {engine_cards}
    </div>
  </section>

  <section>
    <h2>Belangrijke links</h2>
    <div class="card">
      <p><a href="index.html">Open Home Dashboard / Launcher</a></p>
      <p><a href="../../outputs/bib/bib_import_dashboard.html">Open BIB Import Dashboard</a></p>
      <p><a href="../../outputs/bib/index/bib_knowledge_content_index.json">Open BIB Knowledge Content Index</a></p>
      <p><a href="project_analyzer_workflow_dashboard.html">Open Project Analyzer Workflow Dashboard</a></p>
      <p><a href="project_package_evidence_dashboard.html">Open Project Package Evidence Dashboard</a></p>
    </div>
  </section>

  <section>
    <h2>Volgende stap</h2>
    <div class="card">
      <p>De BIB wordt nu zichtbaar gekoppeld aan START PROJECTANALYSE.</p>
      <p>De volgende stap is om AAIE en Project Analyzer inhoudelijk eerst in de BIB te laten zoeken voordat nieuwe aannames worden gemaakt.</p>
    </div>
  </section>
</main>
</body>
</html>
"""

    def build_cards_from_dict(self, data: Dict[str, Any], empty_text: str) -> str:
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
              <h3>Geen items</h3>
              <p>{self.esc(empty_text)}</p>
            </div>
            """

        return cards

    def read_json(self, path: Path) -> Dict[str, Any]:
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

    def write_html(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def esc(self, value: Any) -> str:
        import html

        return html.escape(str(value), quote=True)


def configure_console_output() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def safe_print_json(data: Dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=True, indent=2, default=str)
    print(text)


def main() -> None:
    configure_console_output()
    engine = ProjectStartAnalysisEngine()
    result = engine.run()
    safe_print_json(result)


if __name__ == "__main__":
    main()