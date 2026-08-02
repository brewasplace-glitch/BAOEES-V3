"""Local-only HTTP runtime for Project Phoenix.

v1.5.0 adds the Phoenix 3.0.1 functional official start screen while retaining
the existing dashboard, workflow, open-target and status APIs.
"""
from __future__ import annotations

import base64
import binascii
import json
import mimetypes
import os
import re
import secrets
import signal
import sys
import subprocess
import threading
import urllib.parse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .dashboard_adapter import DashboardAdapter
from .workflow_registry import WorkflowRegistry


class PhoenixLocalApplication:
    VERSION = "1.5.0"
    START_SCREEN_VERSION = "3.0.1"

    def __init__(self, repository: Path, config: dict[str, Any]):
        self.repository = repository.resolve()
        self.config = config
        self.token = secrets.token_urlsafe(24)
        self.dashboard = DashboardAdapter(self.repository, config)
        self.workflows = WorkflowRegistry(self.repository, config)
        self.server: ThreadingHTTPServer | None = None
        self.dashboard_info: dict[str, Any] = {}
        self.start_screen_root = (
            self.repository
            / "phoenix"
            / "local_app"
            / "static"
            / "official_start_v3_0"
        ).resolve()

    def status(self) -> dict[str, Any]:
        latest = self.workflows.latest()
        return {
            "application_name": self.config["application_name"],
            "version": self.VERSION,
            "start_screen_version": self.START_SCREEN_VERSION,
            "repository": str(self.repository),
            "dashboard": self.dashboard_info,
            "git": self._git_status(),
            "projects": self._projects(),
            "modules": self.module_catalog(),
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
            "production_orchestrator": self._orchestrator_status(),
            "official_start": {
                "route": "/start-v3/",
                "functional_controls": True,
                "same_origin_api": True,
                "upload_intake": True,
                "speech_input": "browser_capability",
            },
        }

    def render_dashboard(self) -> str:
        rendered, info = self.dashboard.render(token=self.token)
        self.dashboard_info = info
        return rendered

    def render_start_v3(self) -> str:
        path = self.start_screen_root / "index.html"
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8")
        return (
            text.replace("__PHOENIX_SESSION_TOKEN__", self.token)
            .replace("__PHOENIX_RUNTIME_VERSION__", self.VERSION)
            .replace("__PHOENIX_START_SCREEN_VERSION__", self.START_SCREEN_VERSION)
        )

    def module_catalog(self) -> list[dict[str, Any]]:
        preferred = {
            "projects": ["projects", "configs/projects"],
            "digital_twin": [
                "artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/16_model_browser.html",
                "digital_twin",
            ],
            "architectural": ["suites/architectural", "architecture"],
            "structural": ["structural", "configs/phoenix/structural"],
            "civil": ["infrastructure"],
            "infra": ["infrastructure"],
            "permits": ["permit"],
            "cost_planning": ["configs/phoenix/cost_ratebooks", "reports"],
            "qaqc": [
                "artifacts/bb35/pilot_1_moskee_bunschoten/professional_evidence_intake_closure_gate_v2_3_0/09_professional_evidence_intake_dashboard.html",
                "reports",
            ],
            "release_control": [
                "artifacts/bb35/pilot_1_moskee_bunschoten/unified_model_driven_production_orchestrator_v1_0_0/11_orchestrator_dashboard.html",
                "releases",
            ],
            "knowledge": ["bib", "knowledge"],
            "system": ["outputs/runtime"],
        }
        labels = {
            "projects": "Projecten",
            "digital_twin": "Digital Twin",
            "architectural": "Bouwkundig",
            "structural": "Constructief",
            "civil": "Civiel",
            "infra": "Infra",
            "permits": "Vergunningen",
            "cost_planning": "Kosten & Planning",
            "qaqc": "QA/QC",
            "release_control": "Release Control",
            "knowledge": "BIB / Knowledge",
            "system": "System Runtime",
        }
        result = []
        for module_id, candidates in preferred.items():
            selected = None
            for relative in candidates:
                if (self.repository / relative).exists():
                    selected = relative
                    break
            result.append(
                {
                    "id": module_id,
                    "label": labels[module_id],
                    "available": selected is not None,
                    "relative_path": selected,
                }
            )
        return result

    def open_module(self, module_id: str) -> dict[str, Any]:
        item = next((x for x in self.module_catalog() if x["id"] == module_id), None)
        if item is None:
            raise KeyError(f"Onbekende Phoenix-module: {module_id}")
        if not item["available"] or not item["relative_path"]:
            raise FileNotFoundError(f"Modulepad is niet beschikbaar: {module_id}")
        path = self._safe_repo_path(item["relative_path"])
        self._open_path(path)
        return {
            "opened": str(path),
            "module_id": module_id,
            "label": item["label"],
        }

    def open_target(self, target_id: str) -> dict[str, Any]:
        target = next(
            (item for item in self.config["open_targets"] if item["id"] == target_id),
            None,
        )
        if target is None:
            raise KeyError(f"Onbekend doel: {target_id}")
        path = self._safe_repo_path(target["relative_path"])
        if not path.exists():
            raise FileNotFoundError(path)
        self._open_path(path)
        return {"opened": str(path), "target_id": target_id}

    def create_analysis_session(self, body: dict[str, Any]) -> dict[str, Any]:
        project_type = str(body.get("project_type", "BOUW")).strip().upper()
        if project_type not in {"BOUW", "CIVIEL", "INFRA"}:
            raise ValueError("project_type moet BOUW, CIVIEL of INFRA zijn.")
        brief = str(body.get("brief", "")).strip()
        selected_project = str(body.get("selected_project", "")).strip() or None
        upload_batch = str(body.get("upload_batch", "")).strip() or None

        now = datetime.now(timezone.utc)
        session_id = f"PHX-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"
        root = self.repository / "outputs" / "runtime" / "phoenix_start_v3_sessions"
        root.mkdir(parents=True, exist_ok=True)
        session = {
            "session_id": session_id,
            "created_utc": now.isoformat(),
            "project_type": project_type,
            "brief": brief,
            "selected_project": selected_project,
            "upload_batch": upload_batch,
            "status": "READY_FOR_WORKFLOW_SELECTION",
            "available_workflows": [
                x for x in self.workflows.describe() if x.get("available")
            ],
        }
        path = root / f"{session_id}.json"
        path.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {
            **session,
            "session_file": path.relative_to(self.repository).as_posix(),
            "runtime_dashboard": "/",
        }

    def save_uploads(self, files: Any) -> dict[str, Any]:
        if not isinstance(files, list) or not files:
            raise ValueError("Geen bestanden ontvangen.")
        if len(files) > 50:
            raise ValueError("Maximaal 50 bestanden per uploadbatch.")

        now = datetime.now(timezone.utc)
        batch_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}"
        root = (
            self.repository
            / "inputs"
            / "runtime"
            / "official_start_v3_uploads"
            / batch_id
        )
        root.mkdir(parents=True, exist_ok=False)

        total = 0
        saved = []
        max_total = 120 * 1024 * 1024
        max_file = 60 * 1024 * 1024

        for index, item in enumerate(files, 1):
            if not isinstance(item, dict):
                raise ValueError(f"Bestand {index} heeft geen geldig uploadobject.")
            raw_name = str(item.get("name", "")).strip()
            if not raw_name:
                raise ValueError(f"Bestand {index} heeft geen naam.")
            name = Path(raw_name).name
            name = re.sub(r"[^A-Za-z0-9._()\- ]+", "_", name).strip(" .")
            if not name:
                name = f"upload_{index}.bin"

            encoded = str(item.get("base64", ""))
            try:
                content = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValueError(f"Ongeldige base64 voor {name}.") from error

            if len(content) > max_file:
                raise ValueError(f"{name} is groter dan 60 MB.")
            total += len(content)
            if total > max_total:
                raise ValueError("Uploadbatch is groter dan 120 MB.")

            target = root / name
            if target.exists():
                target = root / f"{target.stem}_{index}{target.suffix}"
            target.write_bytes(content)
            saved.append(
                {
                    "name": target.name,
                    "size_bytes": len(content),
                    "relative_path": target.relative_to(self.repository).as_posix(),
                }
            )

        manifest = {
            "batch_id": batch_id,
            "created_utc": now.isoformat(),
            "file_count": len(saved),
            "total_bytes": total,
            "files": saved,
        }
        (root / "upload_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return manifest

    def resolve_start_asset(self, relative: str) -> Path:
        relative = urllib.parse.unquote(relative).lstrip("/")
        candidate = (self.start_screen_root / relative).resolve()
        if (
            candidate != self.start_screen_root
            and self.start_screen_root not in candidate.parents
        ):
            raise FileNotFoundError(relative)
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    def serve(self, host: str, port: int) -> None:
        application = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ProjectPhoenixLocal/1.5"

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)

                if parsed.path in {"/", "/index.html"}:
                    self._text(
                        application.render_dashboard(),
                        "text/html; charset=utf-8",
                    )
                elif parsed.path in {"/start-v3", "/start-v3/"}:
                    self._text(
                        application.render_start_v3(),
                        "text/html; charset=utf-8",
                    )
                elif parsed.path.startswith("/start-v3/"):
                    relative = parsed.path[len("/start-v3/") :]
                    try:
                        asset = application.resolve_start_asset(relative)
                    except FileNotFoundError:
                        self._json(
                            {"error": "Startscherm-asset niet gevonden."},
                            HTTPStatus.NOT_FOUND,
                        )
                    else:
                        self._file(asset)
                elif parsed.path == "/api/health":
                    self._json(
                        {
                            "status": "ok",
                            "version": application.VERSION,
                            "start_screen_version": application.START_SCREEN_VERSION,
                            "start_route": "/start-v3/",
                        }
                    )
                elif parsed.path == "/api/status":
                    self._json(application.status())
                elif parsed.path.startswith("/api/jobs/"):
                    job_id = parsed.path.rsplit("/", 1)[-1]
                    job = application.workflows.get(job_id)
                    if job is None:
                        self._json(
                            {"error": "Job niet gevonden."},
                            HTTPStatus.NOT_FOUND,
                        )
                    else:
                        self._json(job.to_dict())
                else:
                    self._json(
                        {"error": "Route niet gevonden."},
                        HTTPStatus.NOT_FOUND,
                    )

            def do_POST(self):
                if self.headers.get("X-Phoenix-Token") != application.token:
                    self._json(
                        {"error": "Ongeldig lokaal sessietoken."},
                        HTTPStatus.FORBIDDEN,
                    )
                    return

                parsed = urllib.parse.urlparse(self.path)
                try:
                    if parsed.path == "/api/uploads":
                        body = self._body(max_bytes=170_000_000)
                        self._json(
                            application.save_uploads(body.get("files")),
                            HTTPStatus.CREATED,
                        )
                    else:
                        body = self._body()
                        if (
                            parsed.path.startswith("/api/workflows/")
                            and parsed.path.endswith("/run")
                        ):
                            workflow_id = parsed.path.split("/")[3]
                            job = application.workflows.start(workflow_id)
                            self._json(job.to_dict(), HTTPStatus.ACCEPTED)
                        elif parsed.path == "/api/open":
                            self._json(
                                application.open_target(
                                    str(body.get("target_id", ""))
                                )
                            )
                        elif (
                            parsed.path.startswith("/api/modules/")
                            and parsed.path.endswith("/open")
                        ):
                            module_id = parsed.path.split("/")[3]
                            self._json(application.open_module(module_id))
                        elif parsed.path == "/api/project-analysis/start":
                            self._json(
                                application.create_analysis_session(body),
                                HTTPStatus.CREATED,
                            )
                        elif parsed.path == "/api/shutdown":
                            self._json({"status": "shutting_down"})
                            threading.Thread(
                                target=application.server.shutdown,
                                daemon=True,
                            ).start()
                        else:
                            self._json(
                                {"error": "Route niet gevonden."},
                                HTTPStatus.NOT_FOUND,
                            )
                except KeyError as error:
                    self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
                except (RuntimeError, FileNotFoundError, ValueError) as error:
                    self._json({"error": str(error)}, HTTPStatus.CONFLICT)

            def log_message(self, fmt, *args):
                return

            def _body(self, max_bytes: int = 64_000) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length > max_bytes:
                    raise ValueError("Aanvraag is te groot.")
                raw = self.rfile.read(length) if length else b"{}"
                return json.loads(raw.decode("utf-8"))

            def _json(
                self,
                value: Any,
                status: HTTPStatus = HTTPStatus.OK,
            ):
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)

            def _text(self, value: str, content_type: str):
                payload = value.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)

            def _file(self, path: Path):
                payload = path.read_bytes()
                content_type = (
                    mimetypes.guess_type(path.name)[0]
                    or "application/octet-stream"
                )
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.daemon_threads = True
        self.server.serve_forever(poll_interval=0.25)

    def _safe_repo_path(self, relative: str) -> Path:
        path = (self.repository / relative).resolve()
        if self.repository not in path.parents and path != self.repository:
            raise RuntimeError("Doel ligt buiten de repository.")
        return path

    def _orchestrator_status(self) -> dict[str, Any] | None:
        path = self.repository / (
            "artifacts/bb35/pilot_1_moskee_bunschoten/"
            "unified_model_driven_production_orchestrator_v1_0_0/"
            "01_orchestrator_summary.json"
        )
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return {
            "status": value.get("status"),
            "revision_code": value.get("revision_code"),
            "model_fingerprint_sha256": value.get(
                "model_fingerprint_sha256"
            ),
            "all_cross_checks_passed": value.get(
                "all_cross_checks_passed"
            ),
            "professional_blocker_count": value.get(
                "professional_blocker_count"
            ),
        }

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
        porcelain = run(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
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
            result.append(
                {
                    "file": path.relative_to(self.repository).as_posix(),
                    "project_id": (
                        value.get("project_id")
                        or value.get("id")
                        or path.stem
                    ),
                    "name": (
                        value.get("project_name")
                        or value.get("name")
                        or path.stem
                    ),
                }
            )
        return result

    @staticmethod
    def _open_path(path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":  # pragma: no cover
            subprocess.Popen(["open", str(path)])
        else:  # pragma: no cover
            subprocess.Popen(["xdg-open", str(path)])
