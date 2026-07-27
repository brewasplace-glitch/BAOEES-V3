"""Local-only HTTP runtime for Project Phoenix."""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import signal
import sys
import subprocess
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .dashboard_adapter import DashboardAdapter
from .workflow_registry import WorkflowRegistry


class PhoenixLocalApplication:
    VERSION = "1.2.0"

    def __init__(self, repository: Path, config: dict[str, Any]):
        self.repository = repository.resolve()
        self.config = config
        self.token = secrets.token_urlsafe(24)
        self.dashboard = DashboardAdapter(self.repository, config)
        self.workflows = WorkflowRegistry(self.repository, config)
        self.server: ThreadingHTTPServer | None = None
        self.dashboard_info: dict[str, Any] = {}

    def status(self) -> dict[str, Any]:
        latest = self.workflows.latest()
        return {
            "application_name": self.config["application_name"],
            "version": self.VERSION,
            "repository": str(self.repository),
            "dashboard": self.dashboard_info,
            "git": self._git_status(),
            "projects": self._projects(),
            "workflows": self.workflows.describe(),
            "open_targets": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "available": (self.repository / item["relative_path"]).exists(),
                }
                for item in self.config["open_targets"]
            ],
            "latest_job": latest.to_dict() if latest else None,
        }

    def render_dashboard(self) -> str:
        rendered, info = self.dashboard.render(token=self.token)
        self.dashboard_info = info
        return rendered

    def open_target(self, target_id: str) -> dict[str, Any]:
        target = next(
            (item for item in self.config["open_targets"] if item["id"] == target_id),
            None,
        )
        if target is None:
            raise KeyError(f"Onbekend doel: {target_id}")
        path = (self.repository / target["relative_path"]).resolve()
        if self.repository not in path.parents and path != self.repository:
            raise RuntimeError("Doel ligt buiten de repository.")
        if not path.exists():
            raise FileNotFoundError(path)
        self._open_path(path)
        return {"opened": str(path), "target_id": target_id}

    def serve(self, host: str, port: int) -> None:
        application = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ProjectPhoenixLocal/1.2"

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path in {"/", "/index.html"}:
                    self._text(
                        application.render_dashboard(),
                        "text/html; charset=utf-8",
                    )
                elif parsed.path == "/api/health":
                    self._json({"status": "ok", "version": application.VERSION})
                elif parsed.path == "/api/status":
                    self._json(application.status())
                elif parsed.path.startswith("/api/jobs/"):
                    job_id = parsed.path.rsplit("/", 1)[-1]
                    job = application.workflows.get(job_id)
                    if job is None:
                        self._json({"error": "Job niet gevonden."}, HTTPStatus.NOT_FOUND)
                    else:
                        self._json(job.to_dict())
                else:
                    self._json({"error": "Route niet gevonden."}, HTTPStatus.NOT_FOUND)

            def do_POST(self):
                if self.headers.get("X-Phoenix-Token") != application.token:
                    self._json({"error": "Ongeldig lokaal sessietoken."}, HTTPStatus.FORBIDDEN)
                    return
                parsed = urllib.parse.urlparse(self.path)
                try:
                    body = self._body()
                    if parsed.path.startswith("/api/workflows/") and parsed.path.endswith("/run"):
                        workflow_id = parsed.path.split("/")[3]
                        job = application.workflows.start(workflow_id)
                        self._json(job.to_dict(), HTTPStatus.ACCEPTED)
                    elif parsed.path == "/api/open":
                        self._json(application.open_target(str(body.get("target_id", ""))))
                    elif parsed.path == "/api/shutdown":
                        self._json({"status": "shutting_down"})
                        threading.Thread(target=application.server.shutdown, daemon=True).start()
                    else:
                        self._json({"error": "Route niet gevonden."}, HTTPStatus.NOT_FOUND)
                except KeyError as error:
                    self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
                except (RuntimeError, FileNotFoundError, ValueError) as error:
                    self._json({"error": str(error)}, HTTPStatus.CONFLICT)

            def log_message(self, fmt, *args):
                return

            def _body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 64_000:
                    raise ValueError("Aanvraag is te groot.")
                raw = self.rfile.read(length) if length else b"{}"
                return json.loads(raw.decode("utf-8"))

            def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK):
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

            def _text(self, value: str, content_type: str):
                payload = value.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.daemon_threads = True
        self.server.serve_forever(poll_interval=0.25)

    def _git_status(self) -> dict[str, Any]:
        def run(*args: str) -> str:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repository,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.strip()
        branch = run("branch", "--show-current")
        porcelain = run("status", "--porcelain=v1", "--untracked-files=all")
        return {
            "branch": branch,
            "clean": not bool(porcelain),
            "status_lines": porcelain.splitlines() if porcelain else [],
        }

    def _projects(self) -> list[dict[str, Any]]:
        root = self.repository / "configs" / "projects"
        if not root.is_dir():
            return []
        result = []
        for path in sorted(root.glob("*.json"))[:200]:
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            result.append({
                "file": path.relative_to(self.repository).as_posix(),
                "project_id": value.get("project_id") or value.get("id") or path.stem,
                "name": value.get("project_name") or value.get("name") or path.stem,
            })
        return result

    @staticmethod
    def _open_path(path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":  # pragma: no cover
            subprocess.Popen(["open", str(path)])
        else:  # pragma: no cover
            subprocess.Popen(["xdg-open", str(path)])
