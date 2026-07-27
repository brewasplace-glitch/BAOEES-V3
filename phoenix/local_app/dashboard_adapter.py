"""Discover and adapt the existing Phoenix start dashboard."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .models import DashboardCandidate


class DashboardAdapter:
    def __init__(self, repository: Path, config: dict[str, Any]):
        self.repository = repository.resolve()
        self.config = config
        self.dashboard_config = config["dashboard"]
        self.fallback = (
            Path(__file__).resolve().parent
            / "static"
            / "fallback_dashboard.html"
        )

    def discover(self) -> list[DashboardCandidate]:
        candidates: dict[str, DashboardCandidate] = {}
        max_files = int(self.dashboard_config["max_candidate_files"])
        examined = 0
        for pattern in self.dashboard_config["search_globs"]:
            for path in self.repository.rglob(pattern):
                if examined >= max_files:
                    break
                examined += 1
                if not path.is_file() or self._excluded(path):
                    continue
                candidate = self._score(path)
                if candidate.score <= 0:
                    continue
                previous = candidates.get(candidate.relative_path)
                if previous is None or candidate.score > previous.score:
                    candidates[candidate.relative_path] = candidate
        return sorted(
            candidates.values(),
            key=lambda item: (-item.score, item.relative_path.lower()),
        )

    def select(self) -> DashboardCandidate | None:
        if not self.dashboard_config.get("reuse_existing", True):
            return None
        candidates = self.discover()
        if not candidates:
            return None
        best = candidates[0]
        minimum = int(self.dashboard_config.get("minimum_score", 0))
        return best if best.score >= minimum else None

    def render(self, token: str, api_base: str = "") -> tuple[str, dict[str, Any]]:
        selected = self.select()
        if selected is None:
            source = self.fallback
            source_kind = "FALLBACK_DASHBOARD"
            source_path = source.name
            source_score = 0
        else:
            source = self.repository / selected.relative_path
            source_kind = "REUSED_EXISTING_DASHBOARD"
            source_path = selected.relative_path
            source_score = selected.score

        text = source.read_text(encoding="utf-8-sig", errors="replace")
        bridge = self._bridge(token=token, api_base=api_base)
        if "</body>" in text.lower():
            index = text.lower().rfind("</body>")
            text = text[:index] + bridge + text[index:]
        else:
            text += bridge

        info = {
            "source_kind": source_kind,
            "source_path": source_path,
            "source_score": source_score,
            "candidate_count": len(self.discover()),
        }
        banner = (
            "<script>window.PHOENIX_DASHBOARD_INFO="
            + json.dumps(info, ensure_ascii=False)
            + ";</script>"
        )
        return banner + text, info

    def _excluded(self, path: Path) -> bool:
        relative = path.relative_to(self.repository).as_posix()
        lowered = relative.lower()
        return any(
            part.lower() in lowered
            for part in self.dashboard_config.get("excluded_parts", [])
        )

    def _score(self, path: Path) -> DashboardCandidate:
        relative = path.relative_to(self.repository).as_posix()
        lowered_name = path.name.lower()
        score = 0
        markers: list[str] = []
        if "phoenix" in lowered_name:
            score += 4
        if "start" in lowered_name:
            score += 4
        if "dashboard" in lowered_name:
            score += 3
        if lowered_name.startswith("index"):
            score += 2
        try:
            content = path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )[:1_500_000]
        except OSError:
            content = ""
        for marker, weight in self.dashboard_config["content_markers"].items():
            if marker.lower() in content.lower():
                score += int(weight)
                markers.append(marker)
        return DashboardCandidate(
            relative_path=relative,
            score=score,
            matched_markers=tuple(markers),
        )

    @staticmethod
    def _bridge(token: str, api_base: str) -> str:
        safe_token = html.escape(token, quote=True)
        safe_api = html.escape(api_base, quote=True)
        return f"""
<style id="phoenix-local-bridge-style">
#phoenix-local-bridge{{position:fixed;right:18px;bottom:18px;width:min(420px,calc(100vw - 36px));max-height:80vh;overflow:auto;background:#111827;color:#f9fafb;border:1px solid #4b5563;border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.35);padding:16px;z-index:2147483647;font:14px/1.45 Arial,sans-serif}}
#phoenix-local-bridge h2{{font-size:17px;margin:0 0 8px}}
#phoenix-local-bridge p{{margin:6px 0;color:#d1d5db}}
#phoenix-local-bridge button{{margin:5px 4px 0 0;padding:8px 10px;border:0;border-radius:8px;cursor:pointer;background:#2563eb;color:white}}
#phoenix-local-bridge button.secondary{{background:#374151}}
#phoenix-local-bridge button:disabled{{background:#6b7280;cursor:not-allowed}}
#phoenix-local-bridge pre{{white-space:pre-wrap;background:#030712;border-radius:8px;padding:9px;max-height:170px;overflow:auto}}
#phoenix-local-bridge .ok{{color:#86efac}} #phoenix-local-bridge .warn{{color:#fde68a}}
</style>
<div id="phoenix-local-bridge">
  <h2>Project Phoenix — lokale runtime</h2>
  <p id="phoenix-local-source">Dashboardbron wordt vastgesteld…</p>
  <p id="phoenix-local-status">Runtime wordt geladen…</p>
  <div id="phoenix-local-actions"></div>
  <div id="phoenix-local-workflows"></div>
  <pre id="phoenix-local-log">Geen actieve run.</pre>
</div>
<script id="phoenix-local-bridge-script">
(() => {{
  const TOKEN = "{safe_token}";
  const API = "{safe_api}";
  const headers = {{"Content-Type":"application/json","X-Phoenix-Token":TOKEN}};
  const byId = id => document.getElementById(id);
  const call = async (path, options={{}}) => {{
    const response = await fetch(API + path, options);
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || response.statusText);
    return value;
  }};
  const post = (path, body={{}}) => call(path, {{method:"POST",headers,body:JSON.stringify(body)}});
  const button = (label, click, cls="") => {{
    const element = document.createElement("button");
    element.textContent = label;
    element.className = cls;
    element.onclick = click;
    return element;
  }};
  const refresh = async () => {{
    try {{
      const status = await call("/api/status");
      byId("phoenix-local-source").innerHTML = `<span class="ok">Dashboard:</span> ${{status.dashboard.source_kind}} — ${{status.dashboard.source_path}}`;
      byId("phoenix-local-status").innerHTML = `<span class="ok">Actief:</span> ${{status.application_name}} v${{status.version}} · branch ${{status.git.branch}} · ${{status.git.clean ? "repository schoon" : "repository bevat wijzigingen"}}`;
      const actions = byId("phoenix-local-actions"); actions.replaceChildren();
      status.open_targets.forEach(item => actions.appendChild(button(item.label, async () => {{ try {{ await post("/api/open", {{target_id:item.id}}); }} catch (e) {{ alert(e.message); }} }}, "secondary")));
      const workflows = byId("phoenix-local-workflows"); workflows.replaceChildren();
      status.workflows.forEach(item => {{
        const label = item.available ? `Start: ${{item.label}}` : `${{item.label}} — nog niet beschikbaar`;
        const element = button(label, async () => {{
          try {{ const job = await post(`/api/workflows/${{item.id}}/run`); byId("phoenix-local-log").textContent = `Run gestart: ${{job.job_id}}`; }} catch (e) {{ alert(e.message); }}
        }});
        element.disabled = !item.available;
        workflows.appendChild(element);
      }});
      if (status.latest_job) {{
        byId("phoenix-local-log").textContent = JSON.stringify(status.latest_job, null, 2);
      }}
    }} catch (error) {{
      byId("phoenix-local-status").innerHTML = `<span class="warn">Runtimefout:</span> ${{error.message}}`;
    }}
  }};
  refresh(); setInterval(refresh, 3000);
}})();
</script>
"""
