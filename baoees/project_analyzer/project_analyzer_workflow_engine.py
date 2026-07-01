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


class ProjectAnalyzerWorkflowEngine:
    ENGINE_NAME = "Project Phoenix Project Analyzer Workflow Engine"
    ENGINE_VERSION = "v5.9"

    def __init__(self, project_output_root: Optional[str | Path] = None) -> None:
        if project_output_root:
            self.project_output_root = Path(project_output_root)
        else:
            self.project_output_root = PROJECT_ROOT / "outputs" / "projects"

        self.bib_index_path = (
            PROJECT_ROOT
            / "outputs"
            / "bib"
            / "index"
            / "bib_knowledge_content_index.json"
        )

        self.aaie_path = (
            self.project_output_root
            / "aaie_bib_assumptions.json"
        )

        self.workflow_log_path = (
            self.project_output_root
            / "project_analyzer_workflow_log.json"
        )

        self.workflow_dashboard_path = (
            self.project_output_root
            / "project_analyzer_workflow_dashboard.html"
        )

    def run(self, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        bib_index = self.read_json(self.bib_index_path)
        aaie_output = self.read_json(self.aaie_path)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "bib_index_path": str(self.bib_index_path),
            "aaie_bib_assumptions_path": str(self.aaie_path),
            "workflow_log_path": str(self.workflow_log_path),
            "workflow_dashboard_path": str(self.workflow_dashboard_path),
            "bib_summary": self.build_bib_summary(bib_index),
            "aaie_summary": self.build_aaie_summary(aaie_output),
            "workflow_steps": [
                {
                    "step": "BIB-kennisindex uitlezen",
                    "status": "GELEZEN" if bib_index else "ONTBREEKT",
                },
                {
                    "step": "AAIE/BIB-output koppelen",
                    "status": "GEKOPPELD" if aaie_output else "ONTBREEKT",
                },
                {
                    "step": "Workflow-log schrijven",
                    "status": "OPGESLAGEN",
                },
                {
                    "step": "Workflow-dashboard schrijven",
                    "status": "OPGESLAGEN",
                },
            ],
        }

        self.write_json(self.workflow_log_path, result)
        self.write_text(self.workflow_dashboard_path, self.build_dashboard(result))

        return result

    def build_bib_summary(self, bib_index: Dict[str, Any]) -> Dict[str, Any]:
        if not bib_index:
            return {
                "status": "ONTBREEKT",
                "engine_version": "",
                "recognized_text_items_count": 0,
                "decisions_count": 0,
                "knowledge_items_count": 0,
                "actions_count": 0,
            }

        return {
            "status": bib_index.get("status", "GELEZEN"),
            "engine_version": bib_index.get("engine_version", ""),
            "recognized_text_items_count": bib_index.get(
                "recognized_text_items_count",
                0,
            ),
            "decisions_count": bib_index.get("decisions_count", 0),
            "knowledge_items_count": bib_index.get("knowledge_items_count", 0),
            "actions_count": bib_index.get("actions_count", 0),
        }

    def build_aaie_summary(self, aaie_output: Dict[str, Any]) -> Dict[str, Any]:
        if not aaie_output:
            return {
                "status": "ONTBREEKT",
                "engine_version": "",
                "assumption_count": 0,
                "source_priority": [],
            }

        assumptions = aaie_output.get("assumptions", [])

        return {
            "status": aaie_output.get("status", "GELEZEN"),
            "engine_version": aaie_output.get("engine_version", ""),
            "assumption_count": aaie_output.get(
                "assumption_count",
                len(assumptions),
            ),
            "source_priority": aaie_output.get("source_priority", []),
        }

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        bib = result["bib_summary"]
        aaie = result["aaie_summary"]

        row_parts: List[str] = []

        for step in result["workflow_steps"]:
            row_parts.append(
                "<tr>"
                f"<td>{self.esc(step.get('step', ''))}</td>"
                f"<td>{self.esc(step.get('status', ''))}</td>"
                "</tr>"
            )

        rows = "\n".join(row_parts)

        status_text = self.esc(result.get("status", ""))
        bib_status = self.esc(bib.get("status", ""))
        bib_decisions = self.esc(bib.get("decisions_count", 0))
        bib_knowledge = self.esc(bib.get("knowledge_items_count", 0))
        bib_actions = self.esc(bib.get("actions_count", 0))
        aaie_status = self.esc(aaie.get("status", ""))
        aaie_count = self.esc(aaie.get("assumption_count", 0))

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix Workflow v5.9</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f172a;
      color: #e5e7eb;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px;
    }}
    section {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 18px;
    }}
    h1, h2 {{
      color: #f8fafc;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    td, th {{
      border: 1px solid #334155;
      padding: 10px;
      text-align: left;
    }}
    th {{
      background: #1e293b;
    }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Project Phoenix Workflow v5.9</h1>
    <p>Status: {status_text}</p>
    <p>AAIE/BIB-output is gekoppeld aan de Project Analyzer Workflow.</p>
  </section>

  <section>
    <h2>BIB samenvatting</h2>
    <p>Status: {bib_status}</p>
    <p>Besluiten: {bib_decisions}</p>
    <p>Kennisitems: {bib_knowledge}</p>
    <p>Acties: {bib_actions}</p>
  </section>

  <section>
    <h2>AAIE samenvatting</h2>
    <p>Status: {aaie_status}</p>
    <p>Aannames: {aaie_count}</p>
  </section>

  <section>
    <h2>Workflowstappen</h2>
    <table>
      <tr>
        <th>Stap</th>
        <th>Status</th>
      </tr>
      {rows}
    </table>
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


ProjectAnalyzerWorkflow = ProjectAnalyzerWorkflowEngine
ProjectAnalyzerCentralWorkflowEngine = ProjectAnalyzerWorkflowEngine


def main() -> None:
    engine = ProjectAnalyzerWorkflowEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()