from __future__ import annotations
from pathlib import Path
from html import escape
import json

def render_dashboard(report:dict,path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    risk=escape(str(report.get("decision",{}).get("risk","UNKNOWN")))
    allowed=escape(str(report.get("decision",{}).get("allowed",False)))
    task=escape(str(report.get("task",{}).get("title","No task")))
    mode=escape(str(report.get("mode","dry-run")))
    payload=escape(json.dumps(report,indent=2,ensure_ascii=False))
    html=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>PROJECT PHOENIX Autonomous Development Foundation</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:28px;max-width:1100px}}
.card{{border:1px solid #bbb;border-radius:10px;padding:16px;margin:12px 0}}
pre{{white-space:pre-wrap;word-break:break-word}}
</style></head><body>
<h1>PROJECT PHOENIX 4.41</h1>
<h2>Autonomous Development Foundation v1.0</h2>
<div class="card"><b>Mode:</b> {mode}<br><b>Task:</b> {task}<br>
<b>Risk:</b> {risk}<br><b>Execute allowed:</b> {allowed}</div>
<div class="card"><h3>Cycle evidence</h3><pre>{payload}</pre></div>
</body></html>"""
    path.write_text(html,encoding="utf-8")
