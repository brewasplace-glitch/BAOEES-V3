from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parents[3]


PROJECT_ROOT = find_project_root()


class PhoenixAutomatedTaskBuilderEngine:
    ENGINE_NAME = "Project Phoenix Automated Task Builder"
    ENGINE_VERSION = "v7.8"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "automated_task_builder"
        self.roadmap_path = self.outputs / "phoenix_task_roadmap_v7_6.json"
        self.selected_task_path = self.outputs / "phoenix_selected_task_v7_7.json"
        self.task_package_path = self.outputs / "phoenix_generated_task_package_v7_7.json"
        self.plan_path = self.outputs / "phoenix_automated_task_builder_plan_v7_8.json"
        self.scaffold_log_path = self.outputs / "phoenix_automated_task_scaffold_log_v7_8.json"
        self.dashboard_path = self.outputs / "phoenix_automated_task_builder_dashboard_v7_8.html"
        self.doc_path = self.docs / "phoenix_automated_task_builder_v7_8.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now().isoformat(timespec="seconds")

        roadmap = self.read_json(self.roadmap_path)
        selected_task = self.read_json(self.selected_task_path)
        task_package = self.read_json(self.task_package_path)

        if not selected_task:
            selected_task = self.select_first_open_task(roadmap)

        scaffold_results = self.scaffold_task_files(selected_task)
        plan = self.build_plan(selected_task, scaffold_results)

        self.write_json(self.plan_path, plan)
        self.write_json(self.scaffold_log_path, {"status": "OPGESLAGEN", "results": scaffold_results})
        self.write_text(self.dashboard_path, self.build_dashboard(plan))
        self.write_text(self.doc_path, self.build_documentation(plan))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "selected_task_id": selected_task.get("task_id", ""),
            "selected_task_title": selected_task.get("title", ""),
            "created_count": len([item for item in scaffold_results if item.get("action") == "created"]),
            "skipped_count": len([item for item in scaffold_results if item.get("action") == "skipped_existing"]),
            "plan_path": str(self.plan_path),
            "scaffold_log_path": str(self.scaffold_log_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
        }
        return result

    def select_first_open_task(self, roadmap: Dict[str, Any]) -> Dict[str, Any]:
        tasks = roadmap.get("tasks", []) if isinstance(roadmap, dict) else []
        open_tasks = [task for task in tasks if isinstance(task, dict) and task.get("status", "open") == "open"]
        if open_tasks:
            return sorted(open_tasks, key=lambda item: item.get("priority", 999999))[0]

        return {
            "task_id": "S01-002",
            "track": "Stabilisatie & automatisering",
            "track_id": "S01",
            "priority": 102,
            "title": "Automated cleanup helper",
            "objective": "Bouw een gecontroleerde Phoenix cleanup helper.",
            "files_to_create_or_modify": [
                "apps/brewster_engineering_wizard/project_analyzer/automated_cleanup_helper.py",
                "DOCS/project_phoenix/s01/automated_cleanup_helper.md",
                "outputs/projects/automated_cleanup_helper_log.json",
                "outputs/projects/automated_cleanup_helper_dashboard.html",
            ],
            "test_command": "python -m py_compile apps/brewster_engineering_wizard/project_analyzer/automated_cleanup_helper.py",
            "commit_message": "feat: add automated cleanup helper (S01-002)",
            "risk_level": "laag",
            "requires_go": False,
            "status": "open",
        }

    def scaffold_task_files(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        files = task.get("files_to_create_or_modify", [])
        if not isinstance(files, list):
            files = []

        results: List[Dict[str, Any]] = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for relative in files:
            rel = str(relative).replace("\\", "/").strip()
            if not rel:
                continue

            target = PROJECT_ROOT / rel

            if target.exists():
                backup = target.with_name(target.name + f".backup_v7_8_{timestamp}")
                try:
                    backup.write_bytes(target.read_bytes())
                    results.append({"path": str(target), "action": "skipped_existing", "backup": str(backup), "reason": "Bestand bestond al; niet overschreven."})
                except Exception as exc:
                    results.append({"path": str(target), "action": "error", "error": str(exc)})
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self.content_for_path(target, task), encoding="utf-8")
            results.append({"path": str(target), "action": "created", "reason": "Scaffoldbestand aangemaakt."})

        return results

    def content_for_path(self, target: Path, task: Dict[str, Any]) -> str:
        suffix = target.suffix.lower()
        if suffix == ".py":
            return self.python_module_content(task)
        if suffix == ".md":
            return self.markdown_content(task)
        if suffix == ".html":
            return self.html_content(task)
        if suffix == ".json":
            return self.json_content(task)
        return "Scaffoldbestand aangemaakt door Project Phoenix v7.8.\n"

    def python_module_content(self, task: Dict[str, Any]) -> str:
        title = str(task.get("title", "Generated Phoenix Task"))
        task_id = str(task.get("task_id", "TASK"))
        class_name = self.class_name(title)
        slug = self.safe_slug(title)

        return f'''from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parents[3]


PROJECT_ROOT = find_project_root()


class {class_name}:
    ENGINE_NAME = "{title}"
    TASK_ID = "{task_id}"
    ENGINE_VERSION = "scaffold_v7_8"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.log_path = self.outputs / "{slug}_log.json"
        self.dashboard_path = self.outputs / "{slug}_dashboard.html"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        result = {{
            "status": "SCAFFOLD_READY",
            "task_id": self.TASK_ID,
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "next_step": "Vul deze scaffold met echte taaklogica in een volgende GO-stap.",
        }}
        self.log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8-sig")
        html_text = "<!doctype html><html><head><meta charset='utf-8'><title>" + self.ENGINE_NAME + "</title></head><body><h1>" + self.ENGINE_NAME + "</h1><p>Status: SCAFFOLD_READY</p></body></html>"
        self.dashboard_path.write_text(html_text, encoding="utf-8")
        return result


def main() -> None:
    engine = {class_name}()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'''

    def markdown_content(self, task: Dict[str, Any]) -> str:
        return f'''# {task.get("title", "Generated Phoenix Task")}

Taak: `{task.get("task_id", "")}`  
Spoor: {task.get("track", "")}  
Risico: {task.get("risk_level", "")}

## Doel

{task.get("objective", "")}

## Verwacht resultaat

{task.get("expected_result", "")}

## Test

```powershell
{task.get("test_command", "git status")}
```

## Commit

```powershell
git commit -m "{task.get("commit_message", "chore: generated task")}"
```

## Status

Scaffold aangemaakt door Project Phoenix Automated Task Builder v7.8.
'''

    def html_content(self, task: Dict[str, Any]) -> str:
        title = html.escape(str(task.get("title", "")))
        task_id = html.escape(str(task.get("task_id", "")))
        return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1000px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; }}
code {{ color:#bfdbfe; }}
</style>
</head>
<body>
<main>
<section>
<h1>{title}</h1>
<p>Taak: <code>{task_id}</code></p>
<p>Status: scaffold aangemaakt door v7.8.</p>
</section>
</main>
</body>
</html>
'''

    def json_content(self, task: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "status": "SCAFFOLD_READY",
                "task_id": task.get("task_id", ""),
                "title": task.get("title", ""),
                "track": task.get("track", ""),
                "generated_by": self.ENGINE_NAME,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        )

    def build_plan(self, task: Dict[str, Any], scaffold_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "selected_task": task,
            "scaffold_results": scaffold_results,
            "test_command": task.get("test_command", "git status"),
            "commit_message": task.get("commit_message", "chore: generated scaffold"),
            "next_steps": [
                "Controleer aangemaakte scaffoldbestanden.",
                "Run testcommando.",
                "Commit en push na review.",
                "Ga daarna door met echte inhoudelijke taaklogica na GO.",
            ],
        }

    def build_dashboard(self, plan: Dict[str, Any]) -> str:
        task = plan["selected_task"]
        rows = "".join(
            "<tr><td><code>" + self.esc(item.get("path", "")) + "</code></td><td>" + self.esc(item.get("action", "")) + "</td><td>" + self.esc(item.get("reason", item.get("error", ""))) + "</td></tr>"
            for item in plan["scaffold_results"]
        )
        return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Automated Task Builder v7.8</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1280px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Automated Task Builder v7.8</h1>
<p>Status: <strong>{self.esc(plan.get("status", ""))}</strong></p>
<p>Geselecteerde taak: <code>{self.esc(task.get("task_id", ""))}</code> — {self.esc(task.get("title", ""))}</p>
</section>
<section>
<h2>Scaffoldresultaten</h2>
<table>
<tr><th>Bestand</th><th>Actie</th><th>Toelichting</th></tr>
{rows}
</table>
</section>
<section>
<h2>Test en commit</h2>
<p>Test: <code>{self.esc(plan.get("test_command", ""))}</code></p>
<p>Commit: <code>{self.esc(plan.get("commit_message", ""))}</code></p>
</section>
</main>
</body>
</html>
'''

    def build_documentation(self, plan: Dict[str, Any]) -> str:
        task = plan["selected_task"]
        lines = [
            "# Project Phoenix Automated Task Builder v7.8",
            "",
            "Deze engine maakt de eerste echte scaffoldbestanden voor de geselecteerde roadmaptaak.",
            "",
            f"- Taak: {task.get('task_id', '')}",
            f"- Titel: {task.get('title', '')}",
            f"- Spoor: {task.get('track', '')}",
            f"- Test: `{plan.get('test_command', '')}`",
            f"- Commit: `{plan.get('commit_message', '')}`",
            "",
            "## Scaffoldresultaten",
            "",
        ]
        for item in plan["scaffold_results"]:
            lines.append(f"- {item.get('action', '')}: `{item.get('path', '')}`")
        lines.append("")
        return "\n".join(lines)

    def class_name(self, value: Any) -> str:
        words = re.findall(r"[A-Za-z0-9]+", str(value))
        name = "".join(word.capitalize() for word in words) or "GeneratedTask"
        if name[0].isdigit():
            name = "Task" + name
        return name + "Engine"

    def safe_slug(self, value: Any) -> str:
        text = str(value).strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "task"

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
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


AutomatedTaskBuilderEngine = PhoenixAutomatedTaskBuilderEngine
PhoenixScaffoldBuilder = PhoenixAutomatedTaskBuilderEngine


def main() -> None:
    engine = PhoenixAutomatedTaskBuilderEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
