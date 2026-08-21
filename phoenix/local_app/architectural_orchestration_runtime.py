"""Architectural A-E orchestration jobs for the local Phoenix runtime."""
from __future__ import annotations
import json, os, subprocess, sys, threading, uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELEASE_STATUS = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

@dataclass
class ArchitecturalOrchestrationJob:
    job_id: str
    project_file: str
    project_id: str
    status: str
    started_at: str
    output_dir: str
    log_path: str
    command: list[str]
    finished_at: str | None = None
    return_code: int | None = None
    error: str | None = None
    recommended_variant_id: str | None = None
    delivery_manifest: str | None = None
    release_status: str = RELEASE_STATUS
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ArchitecturalOrchestrationRuntime:
    def __init__(self, repository: Path):
        self.repository = Path(repository).resolve()
        self.runtime_root = self.repository / "projects" / "runtime"
        self.jobs_root = self.runtime_root / "_architectural_orchestration_jobs"
        self._jobs: dict[str, ArchitecturalOrchestrationJob] = {}
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def required_files(self) -> list[str]:
        return [
            "phoenix/design/tropical_residential/project_orchestration.py",
            "phoenix/design/tropical_residential/project_orchestration_cli.py",
            "phoenix/design/tropical_residential/tropical_3d_detv_pipeline.py",
            "phoenix/design/tropical_residential/freecad_bridge.py",
            "phoenix/design/tropical_residential/blender_tropical_scene_script.py",
        ]

    def capability(self) -> dict[str, Any]:
        missing = [rel for rel in self.required_files() if not (self.repository / rel).is_file()]
        return {
            "id": "architectural_ae",
            "available": not missing,
            "status": "READY" if not missing else "UNAVAILABLE",
            "missing_required_files": missing,
            "runtime_root": self.runtime_root.relative_to(self.repository).as_posix(),
            "release_status": RELEASE_STATUS,
            "production_locked": True,
            "for_construction_locked": True,
        }

    @staticmethod
    def _project_identity(project: dict[str, Any]) -> tuple[str, str]:
        candidates = [
            project,
            project.get("project") if isinstance(project.get("project"), dict) else {},
            project.get("metadata") if isinstance(project.get("metadata"), dict) else {},
        ]
        for candidate in candidates:
            project_id = str(
                candidate.get("project_id") or candidate.get("id") or ""
            ).strip()
            if not project_id:
                continue
            project_name = str(
                candidate.get("project_name")
                or candidate.get("name")
                or project.get("project_name")
                or project.get("name")
                or project_id
            ).strip()
            return project_id, project_name or project_id
        return "", ""

    def project_catalog(self) -> list[dict[str, Any]]:
        projects_root = self.repository / "configs" / "projects"
        if not projects_root.is_dir():
            return []

        catalog: list[dict[str, Any]] = []
        seen: set[str] = set()

        for path in sorted(projects_root.glob("*.json")):
            if "index" in path.stem.lower():
                continue
            try:
                project = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(project, dict):
                continue

            project_id, project_name = self._project_identity(project)
            if not project_id or project_id in seen:
                continue

            catalog.append({
                "project_id": project_id,
                "name": project_name,
                "file": path.relative_to(self.repository).as_posix(),
                "architectural_ae_ready": True,
            })
            seen.add(project_id)

        return catalog

    def describe(self) -> dict[str, Any]:
        latest = self.latest()
        return {
            **self.capability(),
            "projects": self.project_catalog(),
            "active_job_id": self._active_job_id,
            "latest_job": latest.to_dict() if latest else None,
        }

    def _resolve_project(self, project_file: str) -> tuple[Path, dict[str, Any]]:
        raw = str(project_file or "").strip()
        if not raw:
            raise ValueError("project_file is verplicht.")
        path = (self.repository / raw).resolve()
        projects_root = (self.repository / "configs" / "projects").resolve()
        if projects_root not in path.parents:
            raise ValueError("Projectconfiguratie moet onder configs/projects staan.")
        if path.suffix.lower() != ".json" or not path.is_file():
            raise FileNotFoundError(path)
        try:
            project = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Ongeldige project-JSON: {path.name}") from error
        if not isinstance(project, dict):
            raise ValueError("Projectconfiguratie moet een JSON-object zijn.")

        project_id, _project_name = self._project_identity(project)
        if not project_id:
            raise ValueError(
                "Projectconfiguratie bevat geen geldige projectidentiteit "
                "(project_id/id, eventueel onder project/metadata)."
            )
        return path, project

    @staticmethod
    def _delivery_folder(project: dict[str, Any]) -> str:
        metadata = project.get("metadata") if isinstance(project.get("metadata"), dict) else {}
        route_value = metadata.get("phoenix_architectural_engine_route")
        route_config = route_value if isinstance(route_value, dict) else {}
        route = str(route_config.get("route") or "")
        if route == "NONRESIDENTIAL_REUSE_V1":
            return "nonresidential_reuse_v1"
        return "architectural_ae_v1_0"

    def _planned_delivery_manifest(self, project_id: str, project: dict[str, Any]) -> Path:
        return (
            self.runtime_root
            / project_id
            / "delivery"
            / self._delivery_folder(project)
            / "delivery_manifest.json"
        )

    def _result_manifest_from_log(
        self,
        job: ArchitecturalOrchestrationJob,
        log_path: Path,
    ) -> Path | None:
        try:
            text = log_path.read_text(encoding="utf-8")
        except OSError:
            return None

        payload_text = text.split("\n\n", 1)[1].strip() if "\n\n" in text else text.strip()
        decoder = json.JSONDecoder()
        payload = None
        for offset, char in enumerate(payload_text):
            if char != "{":
                continue
            try:
                candidate, _end = decoder.raw_decode(payload_text[offset:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and (
                candidate.get("manifest_path") or candidate.get("delivery_manifest")
            ):
                payload = candidate
                break

        if payload is None:
            return None

        payload_project_id = str(payload.get("project_id") or "")
        if payload_project_id and payload_project_id != job.project_id:
            raise RuntimeError(
                "Architectural orchestration result project_id mismatch: "
                f"{payload_project_id!r} != {job.project_id!r}"
            )

        manifest_value = payload.get("manifest_path") or payload.get("delivery_manifest")
        manifest = Path(str(manifest_value))
        if not manifest.is_absolute():
            manifest = self.repository / manifest
        manifest = manifest.resolve()

        project_runtime = (self.runtime_root / job.project_id).resolve()
        try:
            manifest.relative_to(project_runtime)
        except ValueError as error:
            raise RuntimeError(
                "Architectural orchestration manifest escapes project runtime: "
                + str(manifest)
            ) from error

        if manifest.name != "delivery_manifest.json":
            raise RuntimeError(
                "Architectural orchestration result does not reference delivery_manifest.json: "
                + str(manifest)
            )

        return manifest

    def _structural_bridge_tokens(self, project: dict[str, Any]) -> list[str]:
        metadata = project.get("metadata") if isinstance(project.get("metadata"), dict) else {}
        activation = metadata.get("phoenix_structural_capability_activation")
        activation = activation if isinstance(activation, dict) else {}
        if str(activation.get("route") or "") != "structural_engineering":
            return []

        config_path = (
            self.repository
            / "configs"
            / "phoenix"
            / "autonomous_project_orchestrator_v1_0.json"
        )
        if not config_path.is_file():
            raise RuntimeError(
                "Structural bridge requires autonomous_project_orchestrator_v1_0.json"
            )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        output_map = config.get("output_capability_map")
        if not isinstance(output_map, dict):
            raise RuntimeError("Structural bridge output_capability_map ontbreekt.")

        requested = project.get("requested_outputs")
        requested = requested if isinstance(requested, list) else []
        tokens: list[str] = []
        for item in requested:
            token = str(item)
            mapped = output_map.get(token)
            if isinstance(mapped, list) and "structural_engineering" in [
                str(value) for value in mapped
            ]:
                tokens.append(token)
        return list(dict.fromkeys(tokens))

    def _run_structural_capability_bridge(
        self,
        job: ArchitecturalOrchestrationJob,
        project: dict[str, Any],
        log_path: Path,
    ) -> dict[str, Any] | None:
        tokens = self._structural_bridge_tokens(project)
        if not tokens:
            return None

        from phoenix.autonomy.canonical_v4_structural_bridge import (
            cleanup_bridge_upload,
            prepare_isolated_structural_bridge,
            publish_structural_bridge_outputs,
        )

        runner = (
            self.repository
            / "runners"
            / "PROJECT_PHOENIX_autonomous_session_orchestrator_v1_0_0.py"
        )
        if not runner.is_file():
            raise RuntimeError(
                "Structural bridge runner ontbreekt: "
                + runner.relative_to(self.repository).as_posix()
            )

        bridge_root = log_path.parent / "structural_session_bridge"
        bridge_root.mkdir(parents=True, exist_ok=True)
        session_file = bridge_root / "session.json"
        output_dir = bridge_root / "output"
        project_runtime = self.runtime_root / job.project_id

        session = {
            "session_id": f"PHX-AE-BRIDGE-{job.job_id}",
            "project_type": "BOUW",
            "project_mode": "autonomous",
            "brief": job.project_id,
            "selected_project": job.project_id,
            "desired_outputs": tokens,
            "status": "READY_FOR_AUTONOMOUS_ORCHESTRATION",
            "bridge": {
                "schema_version": "phoenix.architectural-to-session-bridge/1.1",
                "source_job_id": job.job_id,
                "source_project_file": job.project_file,
                "scope": "STRUCTURAL_ENGINEERING_ONLY",
                "primary_ae_workspace_overwrite": False,
                "production_release": "LOCKED",
                "for_construction": "LOCKED",
            },
        }

        preparation = prepare_isolated_structural_bridge(
            repository=self.repository,
            project_runtime=project_runtime,
            bridge_root=bridge_root,
            session=session,
        )
        session_file.write_text(
            json.dumps(session, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        command = [
            sys.executable,
            str(runner),
            "--session-file",
            str(session_file),
            "--output-dir",
            str(output_dir),
            "--expect-session-orchestrated",
        ]

        process_return_code = 99
        try:
            with log_path.open("a", encoding="utf-8", newline="\n") as log:
                log.write("\nPHOENIX_STRUCTURAL_SESSION_BRIDGE=START\n")
                log.write("Structural desired outputs: " + json.dumps(tokens) + "\n")
                log.write(
                    "Bridge canonical source: "
                    + str(preparation["source_path"])
                    + "\n"
                )
                log.write(
                    "Bridge normalized SHA256: "
                    + str(preparation["normalized_sha256"])
                    + "\n"
                )
                log.write(
                    "Bridge isolated workspace: "
                    + str(preparation["workspace"])
                    + "\n"
                )
                log.write("Bridge session: " + str(session_file) + "\n")
                log.write("Bridge command: " + json.dumps(command) + "\n")
                log.flush()
                process = subprocess.run(
                    command,
                    cwd=self.repository,
                    env={
                        **os.environ,
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONPATH": (
                            str(self.repository)
                            if not os.environ.get("PYTHONPATH")
                            else str(self.repository)
                            + os.pathsep
                            + os.environ["PYTHONPATH"]
                        ),
                    },
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                process_return_code = int(process.returncode)
                log.write(
                    "PHOENIX_STRUCTURAL_SESSION_BRIDGE_RETURN_CODE="
                    + str(process_return_code)
                    + "\n"
                )
        finally:
            cleanup_bridge_upload(preparation)

        publication = publish_structural_bridge_outputs(
            repository=self.repository,
            project_runtime=project_runtime,
            preparation=preparation,
            runner_return_code=process_return_code,
            session_id=session["session_id"],
        )

        isolated_adapter = publication["isolated_structural_adapter_dir"]
        isolated_inp = publication["isolated_inp"]
        published_adapter = publication["published_structural_adapter_dir"]
        published_inp = publication["published_inp"]

        result = {
            "schema_version": "phoenix.architectural-to-session-bridge-result/1.1",
            "project_id": job.project_id,
            "job_id": job.job_id,
            "desired_outputs": tokens,
            "return_code": process_return_code,
            "bridge_workspace": (
                isolated_adapter.parents[2].relative_to(self.repository).as_posix()
                if isolated_adapter.exists()
                else Path(preparation["workspace"]).relative_to(self.repository).as_posix()
            ),
            "source_canonical_model": str(preparation["source_path"]),
            "source_canonical_sha256": preparation["source_sha256"],
            "recommended_variant_id": preparation["recommended_variant_id"],
            "normalized_model_sha256": preparation["normalized_sha256"],
            "normalization_stats": preparation["stats"],
            "isolated_structural_adapter_dir": (
                isolated_adapter.relative_to(self.repository).as_posix()
                if isolated_adapter.exists()
                else None
            ),
            "isolated_project_scoped_inp": [
                path.relative_to(self.repository).as_posix()
                for path in isolated_inp
            ],
            "published_structural_adapter_dir": (
                published_adapter.relative_to(self.repository).as_posix()
                if published_adapter.exists()
                else None
            ),
            "project_scoped_inp": [
                path.relative_to(self.repository).as_posix()
                for path in published_inp
            ],
            "published": bool(publication["published"]),
            "passed": (
                process_return_code == 0
                and isolated_adapter.is_dir()
                and bool(isolated_inp)
                and published_adapter.is_dir()
                and bool(published_inp)
            ),
            "primary_ae_workspace_overwrite": False,
            "production_release": "LOCKED",
            "for_construction": "LOCKED",
        }
        (bridge_root / "bridge_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        with log_path.open("a", encoding="utf-8", newline="\n") as log:
            log.write(
                "PHOENIX_STRUCTURAL_ISOLATED_ADAPTER_DIR_EXISTS="
                + ("YES" if isolated_adapter.is_dir() else "NO")
                + "\n"
            )
            log.write(
                "PHOENIX_STRUCTURAL_ISOLATED_INP_COUNT="
                + str(len(isolated_inp))
                + "\n"
            )
            log.write(
                "PHOENIX_STRUCTURAL_ADAPTER_DIR_EXISTS="
                + ("YES" if published_adapter.is_dir() else "NO")
                + "\n"
            )
            log.write(
                "PHOENIX_PROJECT_SCOPED_INP_COUNT="
                + str(len(published_inp))
                + "\n"
            )
            log.write(
                "PHOENIX_STRUCTURAL_SESSION_BRIDGE="
                + ("PASS" if result["passed"] else "FAILED")
                + "\n"
            )

        return result

    def plan(self, project_file: str) -> dict[str, Any]:
        capability = self.capability()
        if not capability["available"]:
            raise RuntimeError("Architectural A-E orchestration is niet beschikbaar: " + ", ".join(capability["missing_required_files"]))
        path, project = self._resolve_project(project_file)
        project_id, _project_name = self._project_identity(project)
        command = [
            sys.executable, "-m",
            "phoenix.design.tropical_residential.project_orchestration_cli",
            "--project-json", str(path),
            "--runtime-root", str(self.runtime_root),
        ]
        manifest = self._planned_delivery_manifest(project_id, project)
        return {
            "project_id": project_id,
            "project_file": path.relative_to(self.repository).as_posix(),
            "command": command,
            "runtime_root": self.runtime_root.relative_to(self.repository).as_posix(),
            "delivery_manifest": manifest.relative_to(self.repository).as_posix(),
            "release_status": RELEASE_STATUS,
            "production_locked": True,
            "for_construction_locked": True,
        }

    def start(self, project_file: str) -> ArchitecturalOrchestrationJob:
        plan = self.plan(project_file)
        with self._lock:
            if self._active_job_id:
                active = self._jobs.get(self._active_job_id)
                if active and active.status in {"QUEUED", "RUNNING"}:
                    raise RuntimeError(f"Er draait al een architectuur-orchestration: {active.job_id}")
            job_id = uuid.uuid4().hex[:12]
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_dir = self.jobs_root / f"{stamp}_{job_id}"
            job_dir.mkdir(parents=True, exist_ok=False)
            log_path = job_dir / "workflow.log"
            job = ArchitecturalOrchestrationJob(
                job_id=job_id,
                project_file=plan["project_file"],
                project_id=plan["project_id"],
                status="QUEUED",
                started_at=utc_now(),
                output_dir=f"projects/runtime/{plan['project_id']}",
                log_path=log_path.relative_to(self.repository).as_posix(),
                command=plan["command"],
            )
            self._jobs[job_id] = job
            self._active_job_id = job_id
            self._persist(job)
            threading.Thread(target=self._run, args=(job, log_path), daemon=True).start()
            return job

    def get(self, job_id: str) -> ArchitecturalOrchestrationJob | None:
        if job_id in self._jobs:
            return self._jobs[job_id]
        path = self.jobs_root / f"{job_id}.json"
        return self._load_job(path) if path.is_file() else None

    def latest(self) -> ArchitecturalOrchestrationJob | None:
        if self._jobs:
            return sorted(self._jobs.values(), key=lambda item: item.started_at)[-1]
        path = self.jobs_root / "latest_job.json"
        return self._load_job(path) if path.is_file() else None

    def _run(self, job: ArchitecturalOrchestrationJob, log_path: Path) -> None:
        job.status = "RUNNING"
        self._persist(job)
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        old_pp = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = str(self.repository) if not old_pp else str(self.repository) + os.pathsep + old_pp
        try:
            with log_path.open("w", encoding="utf-8", newline="\n") as log:
                log.write("PROJECT PHOENIX ARCHITECTURAL A-E ORCHESTRATION\n")
                log.write("Command: " + json.dumps(job.command) + "\n\n")
                log.flush()
                process = subprocess.Popen(job.command, cwd=self.repository, env=environment, stdout=log, stderr=subprocess.STDOUT, shell=False)
                return_code = process.wait()
            job.return_code = return_code
            if return_code != 0:
                job.status = "FAILED"
                job.error = f"Orchestration stopte met exitcode {return_code}."
            else:
                manifest = self._result_manifest_from_log(job, log_path)
                if manifest is None:
                    _project_path, project = self._resolve_project(job.project_file)
                    manifest = self._planned_delivery_manifest(job.project_id, project)
                if not manifest.is_file():
                    job.status = "FAILED"
                    job.error = (
                        "Delivery manifest ontbreekt na geslaagde proces-exit: "
                        + str(manifest)
                    )
                else:
                    value = json.loads(manifest.read_text(encoding="utf-8"))
                    job.recommended_variant_id = str(value.get("recommended_variant_id", "")) or None
                    job.delivery_manifest = manifest.relative_to(self.repository).as_posix()
                    _project_path, project = self._resolve_project(job.project_file)
                    bridge = self._run_structural_capability_bridge(job, project, log_path)
                    if bridge is not None and not bool(bridge.get("passed")):
                        job.status = "FAILED"
                        job.error = (
                            "Structural session bridge faalde na geslaagde architectuur-orchestration."
                        )
                    else:
                        job.status = "PASSED"
        except Exception as error:
            job.status = "FAILED"
            job.error = str(error)
        finally:
            job.finished_at = utc_now()
            with self._lock:
                if self._active_job_id == job.job_id:
                    self._active_job_id = None
            self._persist(job)

    def _persist(self, job: ArchitecturalOrchestrationJob) -> None:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(job.to_dict(), ensure_ascii=False, indent=2) + "\n"
        (self.jobs_root / f"{job.job_id}.json").write_text(payload, encoding="utf-8", newline="\n")
        (self.jobs_root / "latest_job.json").write_text(payload, encoding="utf-8", newline="\n")

    @staticmethod
    def _load_job(path: Path) -> ArchitecturalOrchestrationJob | None:
        try:
            return ArchitecturalOrchestrationJob(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None
