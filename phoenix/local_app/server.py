"""Local-only HTTP runtime for Project Phoenix.

v1.6.0 adds Phoenix 3.0.2:
- visual-stability friendly APIs
- results and progress APIs
- integrated module routing metadata
- desired-output persistence for start sessions
"""
from __future__ import annotations

import base64
import binascii
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
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
    VERSION = "1.6.0"
    START_SCREEN_VERSION = "3.0.2"

    def __init__(self, repository: Path, config: dict[str, Any]):
        self.repository = repository.resolve()
        self.config = config
        self.token = secrets.token_urlsafe(24)
        self.dashboard = DashboardAdapter(self.repository, config)
        self.workflows = WorkflowRegistry(self.repository, config)
        self.server: ThreadingHTTPServer | None = None
        self.dashboard_info: dict[str, Any] = {}
        self.start_screen_root = (
            self.repository / "phoenix" / "local_app" / "static" / "official_start_v3_0"
        ).resolve()

    # -------------------- API data builders --------------------
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
                "results_panel": True,
                "desired_output_selection": True,
                "visual_refresh_mode": "stable_delta_polling",
            },
        }

    def summary(self) -> dict[str, Any]:
        status = self.status()
        latest = status.get("latest_job")
        return {
            "git": status["git"],
            "project_count": len(status["projects"]),
            "workflow_count": len(status["workflows"]),
            "module_count": len(status["modules"]),
            "latest_job": latest,
            "progress": self.progress_snapshot(),
        }

    def progress_snapshot(self) -> dict[str, Any]:
        latest = self.workflows.latest()
        if latest is None:
            return {
                "active": False,
                "percent": 0,
                "status": "IDLE",
                "label": None,
                "step_label": "Geen actieve Phoenix-bewerking.",
                "job_id": None,
                "output_dir": None,
                "log_path": None,
                "result_count": self._result_count(),
            }
        status = (latest.status or "").upper()
        percent_map = {"PENDING": 5, "RUNNING": 55, "PASSED": 100, "SUCCEEDED": 100, "FAILED": 100}
        percent = percent_map.get(status, 10 if status else 0)
        if status in {"PASSED", "SUCCEEDED"}:
            step_label = "Workflow gereed."
        elif status == "FAILED":
            step_label = "Workflow mislukt."
        elif status == "RUNNING":
            step_label = "Phoenix voert de geselecteerde workflow uit."
        else:
            step_label = "Workflow wacht of wordt voorbereid."
        return {
            "active": status in {"RUNNING", "PENDING"},
            "percent": percent,
            "status": status or "UNKNOWN",
            "label": latest.label,
            "step_label": step_label,
            "job_id": latest.job_id,
            "output_dir": latest.output_dir,
            "log_path": latest.log_path,
            "result_count": self._result_count(),
        }

    def results_snapshot(self) -> dict[str, Any]:
        root = self.repository / "outputs" / "runtime"
        items = []
        if root.is_dir():
            for path in sorted(root.rglob("*"), key=lambda p: str(p).lower()):
                if len(items) >= 120:
                    break
                if path.is_file() and path.suffix.lower() in {
                    ".json", ".html", ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".log", ".png", ".jpg", ".jpeg", ".zip", ".ifc", ".dxf", ".dwg"
                }:
                    items.append(
                        {
                            "name": path.name,
                            "relative_path": path.relative_to(self.repository).as_posix(),
                            "size_bytes": path.stat().st_size,
                            "category": self._result_category(path),
                        }
                    )
        latest = self.workflows.latest()
        return {
            "count": len(items),
            "latest_job": latest.to_dict() if latest else None,
            "items": items,
        }

    def module_catalog(self) -> list[dict[str, Any]]:
        return [
            self._module_entry(
                "new_project", "Nieuw Project",
                "Start een nieuw project of intake-analyse.",
                "screen", None, "/start-v3/"
            ),
            self._module_entry(
                "projects", "Projecten",
                "Projectregister, projectconfiguraties en projectuitvoer.",
                "repository_view", "configs/projects", None
            ),
            self._module_entry(
                "digital_twin", "Digital Twin",
                "Central geometric / digital model en viewers.",
                "smart_open",
                [
                    "artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/16_model_browser.html",
                    "digital_twin",
                    "outputs/projects",
                ],
                None,
            ),
            self._module_entry(
                "ai_agents", "AI Agents",
                "Overzicht van AI-gedreven engines, workflows en orchestration.",
                "modal_info", None, None,
                extra={"engine_status": "Beschikbaar via workflow- en runtime-registratie."}
            ),
            self._module_entry(
                "simulations", "Simulaties",
                "Simulaties, berekeningen en solver-runs.",
                "smart_open",
                ["outputs/runtime", "reports", "artifacts/bb35"],
                None,
            ),
            self._module_entry(
                "documents", "Documenten",
                "Documenten, rapportages en geschreven outputs.",
                "smart_open",
                ["docs", "outputs/projects", "outputs/runtime"],
                None,
            ),
            self._module_entry(
                "reports", "Rapporten",
                "Rapporten, berekeningen en verificaties.",
                "smart_open",
                ["reports", "outputs/projects", "outputs/runtime"],
                None,
            ),
            self._module_entry(
                "asset_management", "Asset Management",
                "Asset- en projectdossier gerelateerde outputs.",
                "smart_open",
                ["outputs/projects", "artifacts/bb35"],
                None,
            ),
            self._module_entry(
                "dashboard", "Dashboard",
                "Phoenix runtime dashboard en statusoverzicht.",
                "screen", None, "/"
            ),
            self._module_entry(
                "settings", "Instellingen",
                "Configuraties, policies en lokale app-instellingen.",
                "smart_open",
                ["configs/phoenix", "configs/projects"],
                None,
            ),
            self._module_entry(
                "bouwkundig", "Bouwkundig",
                "Architectural Suite, tekeningen, BIM en constructieve overdracht.",
                "smart_open",
                ["architecture", "outputs/projects", "artifacts/bb35"],
                None,
            ),
            self._module_entry(
                "constructief", "Constructief",
                "Structural engineering v8.x keten, analyse en verificaties.",
                "smart_open",
                ["configs/phoenix/structural", "outputs/runtime", "artifacts/bb35"],
                None,
            ),
            self._module_entry(
                "civiel", "Civiel",
                "Civiele engineering en aanverwante projectproducten.",
                "smart_open",
                ["infrastructure", "outputs/projects"],
                None,
            ),
            self._module_entry(
                "infra", "Infra",
                "Infrastructuur, verkeer, parkeren, water en terrein.",
                "smart_open",
                ["infrastructure", "outputs/projects"],
                None,
            ),
            self._module_entry(
                "vergunningen", "Vergunningen",
                "Vergunningen, BOPA, AERIUS en participatie.",
                "smart_open",
                ["permit", "outputs/projects", "docs"],
                None,
            ),
            self._module_entry(
                "kosten_planning", "Kosten & Planning",
                "Raming, planning, hoeveelheden en aanbesteding.",
                "smart_open",
                ["configs/phoenix/cost_ratebooks", "reports", "outputs/projects"],
                None,
            ),
            self._module_entry(
                "qaqc", "QA/QC",
                "Evidence, review, validatie en kwaliteit.",
                "smart_open",
                [
                    "artifacts/bb35/pilot_1_moskee_bunschoten/professional_evidence_intake_closure_gate_v2_3_0/09_professional_evidence_intake_dashboard.html",
                    "reports",
                    "outputs/runtime",
                ],
                None,
            ),
            self._module_entry(
                "release_control", "Release Control",
                "Revisie, review, approval en release-control.",
                "smart_open",
                [
                    "artifacts/bb35/pilot_1_moskee_bunschoten/unified_model_driven_production_orchestrator_v1_0_0/11_orchestrator_dashboard.html",
                    "releases",
                    "outputs/runtime",
                ],
                None,
            ),
            self._module_entry(
                "knowledge", "BIB / Knowledge",
                "Phoenix kennisbibliotheek.",
                "smart_open",
                ["bib", "knowledge", "docs"],
                None,
            ),
            self._module_entry(
                "results", "Resultaten",
                "Bekijk tussenresultaten, logs en gegenereerde outputs.",
                "screen", None, "/start-v3/#results"
            ),
            self._module_entry(
                "system_status", "System Status",
                "Live API, Git, workflows en engines.",
                "screen", None, "/start-v3/#system"
            ),
        ]

    def module_view(self, module_id: str) -> dict[str, Any]:
        item = next((x for x in self.module_catalog() if x["id"] == module_id), None)
        if item is None:
            raise KeyError(f"Onbekende Phoenix-module: {module_id}")
        view = {
            "id": item["id"],
            "label": item["label"],
            "description": item["description"],
            "route_kind": item["route_kind"],
            "available": item["available"],
            "screen_route": item.get("screen_route"),
            "resolved_path": item.get("resolved_path"),
            "extra": item.get("extra", {}),
        }
        if item["route_kind"] == "smart_open":
            if item["available"]:
                view["summary"] = "Open echte Phoenix-locatie of viewer."
            else:
                view["summary"] = "Nog geen fysiek doelbestand gevonden; module-informatie is wel beschikbaar."
        elif item["route_kind"] == "screen":
            view["summary"] = "Deze module opent als Phoenix-scherm binnen de local runtime."
        else:
            view["summary"] = "Deze module toont informatie of integratiestatus."
        return view

    def open_module(self, module_id: str) -> dict[str, Any]:
        item = next((x for x in self.module_catalog() if x["id"] == module_id), None)
        if item is None:
            raise KeyError(f"Onbekende Phoenix-module: {module_id}")

        if item["route_kind"] == "screen":
            return {
                "mode": "screen",
                "module_id": module_id,
                "label": item["label"],
                "route": item["screen_route"],
            }

        if item["route_kind"] == "modal_info":
            return {
                "mode": "modal_info",
                "module_id": module_id,
                "label": item["label"],
                "description": item["description"],
                "extra": item.get("extra", {}),
            }

        if not item["available"] or not item.get("resolved_path"):
            raise FileNotFoundError(f"Modulepad is niet beschikbaar: {module_id}")

        path = self._safe_repo_path(item["resolved_path"])
        self._open_path(path)
        return {
            "mode": "opened_path",
            "opened": str(path),
            "module_id": module_id,
            "label": item["label"],
        }

    def open_target(self, target_id: str) -> dict[str, Any]:
        target = next((item for item in self.config["open_targets"] if item["id"] == target_id), None)
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
        desired_outputs = body.get("desired_outputs")
        if desired_outputs is None:
            desired_outputs = self.default_desired_outputs()
        if not isinstance(desired_outputs, list):
            raise ValueError("desired_outputs moet een lijst zijn.")

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
            "desired_outputs": desired_outputs,
            "status": "READY_FOR_WORKFLOW_SELECTION",
            "available_workflows": [x for x in self.workflows.describe() if x.get("available")],
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
        root = self.repository / "inputs" / "runtime" / "official_start_v3_uploads" / batch_id
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
            saved.append({
                "name": target.name,
                "size_bytes": len(content),
                "relative_path": target.relative_to(self.repository).as_posix(),
            })

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
            .replace("__PHOENIX_DESIRED_OUTPUTS__", json.dumps(self.desired_output_catalog(), ensure_ascii=False))
        )

    def resolve_start_asset(self, relative: str) -> Path:
        relative = urllib.parse.unquote(relative).lstrip("/")
        candidate = (self.start_screen_root / relative).resolve()
        if candidate != self.start_screen_root and self.start_screen_root not in candidate.parents:
            raise FileNotFoundError(relative)
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    # -------------------- Server --------------------
    def serve(self, host: str, port: int) -> None:
        application = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ProjectPhoenixLocal/1.6"

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)

                if parsed.path in {"/", "/index.html"}:
                    self._text(application.render_dashboard(), "text/html; charset=utf-8")
                elif parsed.path in {"/start-v3", "/start-v3/"}:
                    self._text(application.render_start_v3(), "text/html; charset=utf-8")
                elif parsed.path.startswith("/start-v3/"):
                    relative = parsed.path[len("/start-v3/") :]
                    try:
                        asset = application.resolve_start_asset(relative)
                    except FileNotFoundError:
                        self._json({"error": "Startscherm-asset niet gevonden."}, HTTPStatus.NOT_FOUND)
                    else:
                        self._file(asset)
                elif parsed.path == "/api/health":
                    self._json({
                        "status": "ok",
                        "version": application.VERSION,
                        "start_screen_version": application.START_SCREEN_VERSION,
                        "start_route": "/start-v3/",
                    })
                elif parsed.path == "/api/status":
                    self._json(application.status())
                elif parsed.path == "/api/summary":
                    self._json(application.summary())
                elif parsed.path == "/api/progress":
                    self._json(application.progress_snapshot())
                elif parsed.path == "/api/results":
                    self._json(application.results_snapshot())
                elif parsed.path == "/api/desired-outputs":
                    self._json({
                        "catalog": application.desired_output_catalog(),
                        "default": application.default_desired_outputs(),
                    })
                elif parsed.path == "/api/modules":
                    self._json(application.module_catalog())
                elif parsed.path.startswith("/api/modules/") and parsed.path.endswith("/view"):
                    module_id = parsed.path.split("/")[3]
                    try:
                        self._json(application.module_view(module_id))
                    except KeyError as error:
                        self._json({"error": str(error)}, HTTPStatus.NOT_FOUND)
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
                    if parsed.path == "/api/uploads":
                        body = self._body(max_bytes=170_000_000)
                        self._json(application.save_uploads(body.get("files")), HTTPStatus.CREATED)
                    else:
                        body = self._body()
                        if parsed.path.startswith("/api/workflows/") and parsed.path.endswith("/run"):
                            workflow_id = parsed.path.split("/")[3]
                            job = application.workflows.start(workflow_id)
                            self._json(job.to_dict(), HTTPStatus.ACCEPTED)
                        elif parsed.path == "/api/open":
                            self._json(application.open_target(str(body.get("target_id", ""))))
                        elif parsed.path.startswith("/api/modules/") and parsed.path.endswith("/open"):
                            module_id = parsed.path.split("/")[3]
                            self._json(application.open_module(module_id))
                        elif parsed.path == "/api/project-analysis/start":
                            self._json(application.create_analysis_session(body), HTTPStatus.CREATED)
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

            def _body(self, max_bytes: int = 64_000) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length > max_bytes:
                    raise ValueError("Aanvraag is te groot.")
                raw = self.rfile.read(length) if length else b"{}"
                return json.loads(raw.decode("utf-8"))

            def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK):
                payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
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
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
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

    # -------------------- Helpers --------------------
    def desired_output_catalog(self) -> list[dict[str, Any]]:
        return [
            {"group": "DOCUMENTEN", "items": [
                {"id": "reports", "label": "Rapporten"},
                {"id": "calculations", "label": "Berekeningen"},
                {"id": "specifications", "label": "Bestek"},
                {"id": "tender_docs", "label": "Aanbestedingsstukken"},
                {"id": "permit_dossier", "label": "Vergunningsdossier"},
                {"id": "cost_estimate", "label": "Kostenraming"},
                {"id": "planning", "label": "Planning"},
                {"id": "quantities", "label": "Hoeveelheden"},
            ]},
            {"group": "TEKENINGEN / MODELLEN", "items": [
                {"id": "site_plan", "label": "Situatietekening"},
                {"id": "floor_plans", "label": "Plattegronden"},
                {"id": "facades", "label": "Gevels"},
                {"id": "sections", "label": "Doorsneden"},
                {"id": "details", "label": "Detailtekeningen"},
                {"id": "structural_drawings", "label": "Constructietekeningen"},
                {"id": "foundation_drawings", "label": "Funderingstekeningen"},
                {"id": "infra_drawings", "label": "Infra-/terreintekeningen"},
                {"id": "digital_twin_output", "label": "Digital Twin"},
                {"id": "ifc_bim", "label": "IFC / BIM"},
                {"id": "dwg_dxf", "label": "DWG / DXF"},
            ]},
            {"group": "ANALYSES", "items": [
                {"id": "structural_analysis", "label": "Constructieve berekeningen"},
                {"id": "foundation_design", "label": "Fundering"},
                {"id": "traffic_parking", "label": "Verkeer & parkeren"},
                {"id": "drainage", "label": "Riolering & afwatering"},
                {"id": "aerius", "label": "AERIUS"},
                {"id": "permit_analysis", "label": "Vergunninganalyse"},
                {"id": "cost_optimization", "label": "Kostenoptimalisatie"},
                {"id": "variant_analysis", "label": "Variantenanalyse"},
            ]},
            {"group": "PRESENTATIE", "items": [
                {"id": "viewer_3d", "label": "3D Viewer"},
                {"id": "walkthrough", "label": "Walk-through"},
                {"id": "drivethrough", "label": "Drive-through"},
                {"id": "bird_view", "label": "Vogelvlucht"},
                {"id": "auto_video", "label": "Automatische videopresentatie"},
            ]},
            {"group": "PROJECTAFRONDING", "items": [
                {"id": "qaqc_output", "label": "QA/QC"},
                {"id": "source_evidence", "label": "Bronvermelding"},
                {"id": "engineering_review_package", "label": "Engineering review package"},
                {"id": "release_package", "label": "Release package"},
                {"id": "project_zip", "label": "Project-ZIP"},
            ]},
        ]

    def default_desired_outputs(self) -> list[str]:
        return [
            "reports", "calculations", "permit_dossier", "cost_estimate",
            "site_plan", "floor_plans", "facades", "sections",
            "digital_twin_output", "structural_analysis", "viewer_3d",
            "qaqc_output", "source_evidence", "project_zip",
        ]

    def _module_entry(
        self,
        module_id: str,
        label: str,
        description: str,
        route_kind: str,
        relative_candidates: str | list[str] | None,
        screen_route: str | None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved = None
        if isinstance(relative_candidates, str):
            resolved = relative_candidates if (self.repository / relative_candidates).exists() else None
        elif isinstance(relative_candidates, list):
            for rel in relative_candidates:
                if (self.repository / rel).exists():
                    resolved = rel
                    break
        return {
            "id": module_id,
            "label": label,
            "description": description,
            "route_kind": route_kind,
            "screen_route": screen_route,
            "resolved_path": resolved,
            "available": route_kind in {"screen", "modal_info"} or resolved is not None,
            "extra": extra or {},
        }

    def _result_category(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".docx", ".txt"}:
            return "document"
        if suffix in {".dwg", ".dxf", ".ifc"}:
            return "drawing_model"
        if suffix in {".xlsx", ".csv"}:
            return "table"
        if suffix in {".png", ".jpg", ".jpeg"}:
            return "image"
        if suffix in {".json", ".log", ".html"}:
            return "data_log"
        if suffix in {".zip"}:
            return "archive"
        return "other"

    def _result_count(self) -> int:
        root = self.repository / "outputs" / "runtime"
        if not root.is_dir():
            return 0
        count = 0
        for path in root.rglob("*"):
            if path.is_file():
                count += 1
                if count >= 9999:
                    break
        return count

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
            "model_fingerprint_sha256": value.get("model_fingerprint_sha256"),
            "all_cross_checks_passed": value.get("all_cross_checks_passed"),
            "professional_blocker_count": value.get("professional_blocker_count"),
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
        for path in sorted(root.glob("*.json"))[:300]:
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
