"""Operational Blender visualization adapter for Phoenix Core v2.0 BB6."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Mapping

from phoenix.osif import ApplicationDescriptor, Capability
from .base import AdapterError, OSIFAdapter
from .contracts import (
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterHealth,
)


Runner = Callable[..., subprocess.CompletedProcess[str]]


class BlenderIntegrationError(AdapterError):
    """Raised when Blender visualization execution cannot proceed."""


class BlenderAdapter(OSIFAdapter):
    APPLICATION_ID = "blender"
    ADAPTER_ID = "phoenix.osif.adapter.blender"
    EXECUTABLE_NAMES = ("blender.exe", "blender")

    CAPABILITY_TO_OPERATION = {
        "blender.scene.inspect": "scene.inspect",
        "blender.scene.save": "scene.save",
        "blender.scene.export": "scene.export",
        "blender.render.still": "render.still",
        "blender.render.animation": "render.animation",
        "visualization.render": "render.still",
    }

    SOURCE_SUFFIXES = {".blend", ".obj", ".gltf", ".glb", ".stl", ".fbx"}
    DESTINATION_SUFFIXES = {
        "scene.save": {".blend"},
        "scene.export": {".obj", ".gltf", ".glb", ".stl"},
        "render.still": {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"},
        "render.animation": {".mp4", ".mov", ".mkv", ".avi"},
    }

    def __init__(
        self,
        *,
        executable: str = "",
        runner: Runner = subprocess.run,
    ) -> None:
        super().__init__()
        self._configured_executable = executable
        self._runner = runner

    def descriptor(self) -> ApplicationDescriptor:
        return ApplicationDescriptor(
            application_id=self.APPLICATION_ID,
            name="Blender",
            adapter_id=self.ADAPTER_ID,
            execution_mode="cli",
            executable=self._configured_executable,
            license_id="GPL-3.0-or-later",
            capabilities=(
                Capability(
                    "blender.scene.inspect",
                    "Inspect Blender scene",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("json",),
                ),
                Capability(
                    "blender.scene.save",
                    "Save normalized Blender scene",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("blend",),
                ),
                Capability(
                    "blender.scene.export",
                    "Export Blender scene",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("obj", "gltf", "glb", "stl"),
                ),
                Capability(
                    "blender.render.still",
                    "Render still image",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("png", "jpg", "tif", "exr"),
                ),
                Capability(
                    "blender.render.animation",
                    "Render animation",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("mp4", "mov", "mkv", "avi"),
                ),
                Capability(
                    "visualization.render",
                    "Render visualization",
                    ("blend", "obj", "gltf", "glb", "stl", "fbx"),
                    ("png", "jpg"),
                ),
            ),
            enabled=True,
            metadata={
                "bb6_status": "operational",
                "worker_protocol": "json-file-v1",
            },
        )

    def _context_configuration(self) -> Mapping[str, Any]:
        return self._context.configuration if self._context is not None else {}

    def locate_executable(self) -> str:
        configured = str(
            self._configured_executable
            or self._context_configuration().get("blender_executable", "")
        ).strip()
        if configured:
            path = Path(configured).expanduser()
            if path.is_file():
                return str(path.resolve())
            found = shutil.which(configured)
            return str(Path(found).resolve()) if found else ""

        for name in self.EXECUTABLE_NAMES:
            found = shutil.which(name)
            if found:
                return str(Path(found).resolve())
        return ""

    def health_check(self) -> AdapterHealth:
        executable = self.locate_executable()
        if not executable:
            return AdapterHealth(
                "unavailable",
                "Blender executable was not found.",
                {"searched_names": list(self.EXECUTABLE_NAMES)},
            )
        try:
            completed = self._runner(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
                check=False,
            )
            output = "\n".join(
                value.strip()
                for value in (completed.stdout, completed.stderr)
                if value and value.strip()
            )
            version = output.splitlines()[0][:300] if output else ""
            return AdapterHealth(
                "available" if completed.returncode == 0 else "degraded",
                "Blender executable is available.",
                {
                    "executable": executable,
                    "version": version,
                    "version_probe_exit_code": completed.returncode,
                },
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return AdapterHealth(
                "degraded",
                "Blender was found but version probing failed.",
                {
                    "executable": executable,
                    "probe_error": type(exc).__name__,
                },
            )

    @staticmethod
    def _required_path(inputs: Mapping[str, Any], key: str) -> Path:
        value = str(inputs.get(key, "")).strip()
        if not value:
            raise BlenderIntegrationError(f"Missing required input: {key}")
        return Path(value).expanduser().resolve()

    def validate_request(self, request: AdapterExecutionRequest) -> None:
        if request.capability_id not in self.CAPABILITY_TO_OPERATION:
            raise BlenderIntegrationError(
                f"Unsupported Blender capability: {request.capability_id}"
            )

        source = self._required_path(request.inputs, "source_file")
        if not source.is_file():
            raise BlenderIntegrationError(
                f"Source file does not exist: {source}"
            )
        if source.suffix.lower() not in self.SOURCE_SUFFIXES:
            raise BlenderIntegrationError(
                f"Unsupported source format: {source.suffix.lower()}"
            )

        operation = self.CAPABILITY_TO_OPERATION[request.capability_id]
        if operation != "scene.inspect":
            destination = self._required_path(
                request.inputs,
                "destination_file",
            )
            supported = self.DESTINATION_SUFFIXES[operation]
            if destination.suffix.lower() not in supported:
                raise BlenderIntegrationError(
                    f"Unsupported destination format for {operation}: "
                    f"{destination.suffix.lower()}"
                )

        if not request.output_directory.strip():
            raise BlenderIntegrationError(
                "output_directory must not be empty."
            )

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)

    @staticmethod
    def _file_evidence(paths: list[str]) -> dict[str, str]:
        evidence = {}
        for value in paths:
            path = Path(value)
            if path.is_file():
                evidence[str(path.resolve())] = sha256(
                    path.read_bytes()
                ).hexdigest()
        return evidence

    def _execute(
        self,
        request: AdapterExecutionRequest,
    ) -> AdapterExecutionResult:
        executable = self.locate_executable()
        if not executable:
            raise BlenderIntegrationError("Blender is unavailable.")

        output_directory = Path(request.output_directory).expanduser().resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        runtime_directory = output_directory / ".phoenix_blender"
        runtime_directory.mkdir(parents=True, exist_ok=True)

        job_path = runtime_directory / f"{request.request_id}.job.json"
        result_path = runtime_directory / f"{request.request_id}.result.json"
        worker_path = Path(__file__).with_name("blender_worker.py").resolve()

        job = {
            "schema_version": "1.0",
            "request_id": request.request_id,
            "project_id": request.project_id,
            "operation": self.CAPABILITY_TO_OPERATION[
                request.capability_id
            ],
            **dict(request.inputs),
        }
        self._write_json(job_path, job)

        try:
            completed = self._runner(
                [
                    executable,
                    "--background",
                    "--factory-startup",
                    "--python",
                    str(worker_path),
                    "--",
                    str(job_path),
                    str(result_path),
                ],
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return AdapterExecutionResult(
                request_id=request.request_id,
                adapter_id=self.ADAPTER_ID,
                application_id=self.APPLICATION_ID,
                status="timed_out",
                errors=(
                    "Blender execution timed out after "
                    f"{request.timeout_seconds}s.",
                ),
                evidence_sha256=self.evidence_digest(
                    {
                        "request_id": request.request_id,
                        "status": "timed_out",
                    }
                ),
            )
        except OSError as exc:
            raise BlenderIntegrationError(
                f"Unable to start Blender: {exc}"
            ) from exc

        if not result_path.is_file():
            raise BlenderIntegrationError(
                "Blender worker did not produce a result file. "
                f"Exit code: {completed.returncode}; "
                f"stderr: {completed.stderr[:1000]}"
            )

        worker_result = json.loads(
            result_path.read_text(encoding="utf-8")
        )
        output_files = [
            str(Path(item).resolve())
            for item in worker_result.get("output_files", [])
        ]
        file_evidence = self._file_evidence(output_files)
        status = (
            "completed"
            if completed.returncode == 0
            and worker_result.get("status") == "completed"
            else "failed"
        )

        evidence_payload = {
            "request": job,
            "worker_result": worker_result,
            "exit_code": completed.returncode,
            "output_file_sha256": file_evidence,
        }

        return AdapterExecutionResult(
            request_id=request.request_id,
            adapter_id=self.ADAPTER_ID,
            application_id=self.APPLICATION_ID,
            status=status,
            outputs={
                "output_files": output_files,
                "output_file_sha256": file_evidence,
                "runtime_result_file": str(result_path),
            },
            warnings=tuple(
                str(item)
                for item in worker_result.get("warnings", [])
            ),
            errors=tuple(
                str(item)
                for item in worker_result.get("errors", [])
            ),
            evidence_sha256=self.evidence_digest(evidence_payload),
            metadata={
                **dict(worker_result.get("metadata", {})),
                "blender_exit_code": completed.returncode,
                "blender_stdout": completed.stdout[-4000:],
                "blender_stderr": completed.stderr[-4000:],
                "digital_twin_visualization_ready": True,
            },
        )
