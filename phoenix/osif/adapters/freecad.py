"""Operational FreeCAD integration adapter for Phoenix Core v2.0 BB4."""

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


class FreeCADIntegrationError(AdapterError):
    """Raised when a FreeCAD request is invalid or execution fails."""


class FreeCADAdapter(OSIFAdapter):
    APPLICATION_ID = "freecad"
    ADAPTER_ID = "phoenix.osif.adapter.freecad"
    EXECUTABLE_NAMES = ("FreeCADCmd.exe", "FreeCADCmd", "freecadcmd")

    CAPABILITY_TO_OPERATION = {
        "freecad.document.create": "document.create",
        "freecad.document.import": "document.import",
        "freecad.document.export": "document.export",
        "freecad.document.inspect": "document.inspect",
        "freecad.geometry.validate": "geometry.validate",
        "freecad.macro.execute": "macro.execute",
        # Compatibility with the BB2/BB3 generic capability.
        "cad.convert": "document.export",
    }

    SUPPORTED_SOURCE_SUFFIXES = {
        ".fcstd", ".step", ".stp", ".iges", ".igs", ".brep", ".brp"
    }
    SUPPORTED_DESTINATION_SUFFIXES = {
        ".fcstd", ".step", ".stp", ".iges", ".igs", ".brep", ".brp",
        ".stl", ".obj"
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
            name="FreeCAD",
            adapter_id=self.ADAPTER_ID,
            execution_mode="cli",
            executable=self._configured_executable,
            license_id="LGPL-2.0-or-later",
            capabilities=(
                Capability(
                    "freecad.document.create",
                    "Create parametrical FreeCAD document",
                    ("json",),
                    ("fcstd",),
                ),
                Capability(
                    "freecad.document.import",
                    "Import geometry into FreeCAD",
                    ("step", "stp", "iges", "igs", "brep", "brp"),
                    ("fcstd",),
                ),
                Capability(
                    "freecad.document.export",
                    "Export FreeCAD geometry",
                    ("fcstd", "step", "stp", "iges", "igs", "brep", "brp"),
                    ("step", "stp", "iges", "igs", "brep", "brp", "stl", "obj"),
                ),
                Capability(
                    "freecad.document.inspect",
                    "Inspect FreeCAD document",
                    ("fcstd", "step", "stp", "iges", "igs"),
                    ("json",),
                ),
                Capability(
                    "freecad.geometry.validate",
                    "Validate FreeCAD geometry",
                    ("fcstd", "step", "stp", "iges", "igs"),
                    ("json",),
                ),
                Capability(
                    "freecad.macro.execute",
                    "Execute approved FreeCAD Python macro",
                    ("py", "json"),
                    ("fcstd", "json"),
                ),
                Capability(
                    "cad.convert",
                    "Convert CAD geometry",
                    ("step", "stp", "iges", "igs", "fcstd"),
                    ("step", "stl", "obj", "fcstd"),
                ),
            ),
            enabled=True,
            metadata={
                "bb4_status": "operational",
                "worker_protocol": "json-file-v1",
            },
        )

    def _context_configuration(self) -> Mapping[str, Any]:
        return self._context.configuration if self._context is not None else {}

    def locate_executable(self) -> str:
        configured = str(
            self._configured_executable
            or self._context_configuration().get("freecad_executable", "")
        ).strip()
        if configured:
            path = Path(configured).expanduser()
            if path.is_file():
                return str(path.resolve())
            found = shutil.which(configured)
            if found:
                return str(Path(found).resolve())
            return ""

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
                "FreeCADCmd was not found.",
                {"searched_names": list(self.EXECUTABLE_NAMES)},
            )

        version = ""
        exit_code = None
        try:
            completed = self._runner(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
                check=False,
            )
            exit_code = completed.returncode
            output = "\n".join(
                value.strip()
                for value in (completed.stdout, completed.stderr)
                if value and value.strip()
            )
            version = output.splitlines()[0][:300] if output else ""
        except (OSError, subprocess.TimeoutExpired) as exc:
            return AdapterHealth(
                "degraded",
                "FreeCADCmd was found but version probing failed.",
                {
                    "executable": executable,
                    "probe_error": type(exc).__name__,
                },
            )

        return AdapterHealth(
            "available" if exit_code == 0 else "degraded",
            "FreeCADCmd is available.",
            {
                "executable": executable,
                "version": version,
                "version_probe_exit_code": exit_code,
            },
        )

    @staticmethod
    def _required_path(inputs: Mapping[str, Any], key: str) -> Path:
        value = str(inputs.get(key, "")).strip()
        if not value:
            raise FreeCADIntegrationError(f"Missing required input: {key}")
        return Path(value).expanduser().resolve()

    @staticmethod
    def _ensure_output_directory(request: AdapterExecutionRequest) -> Path:
        raw = request.output_directory.strip()
        if not raw:
            raise FreeCADIntegrationError("output_directory must not be empty.")
        path = Path(raw).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_request(self, request: AdapterExecutionRequest) -> None:
        if request.capability_id not in self.CAPABILITY_TO_OPERATION:
            raise FreeCADIntegrationError(
                f"Unsupported FreeCAD capability: {request.capability_id}"
            )

        operation = self.CAPABILITY_TO_OPERATION[request.capability_id]
        inputs = request.inputs

        if operation in {
            "document.import",
            "document.export",
            "document.inspect",
            "geometry.validate",
        }:
            source = self._required_path(inputs, "source_file")
            if not source.is_file():
                raise FreeCADIntegrationError(
                    f"Source file does not exist: {source}"
                )
            if source.suffix.lower() not in self.SUPPORTED_SOURCE_SUFFIXES:
                raise FreeCADIntegrationError(
                    f"Unsupported source format: {source.suffix.lower()}"
                )

        if operation in {"document.create", "document.import", "document.export"}:
            destination = self._required_path(inputs, "destination_file")
            if destination.suffix.lower() not in self.SUPPORTED_DESTINATION_SUFFIXES:
                raise FreeCADIntegrationError(
                    f"Unsupported destination format: {destination.suffix.lower()}"
                )

        if operation == "document.create":
            primitives = inputs.get("primitives", [])
            if not isinstance(primitives, list) or not primitives:
                raise FreeCADIntegrationError(
                    "document.create requires a non-empty primitives list."
                )

        if operation == "macro.execute":
            if not bool(
                self._context_configuration().get("allow_custom_freecad_macros", False)
            ):
                raise FreeCADIntegrationError(
                    "Custom FreeCAD macros are disabled by policy."
                )
            macro = self._required_path(inputs, "macro_file")
            if not macro.is_file() or macro.suffix.lower() != ".py":
                raise FreeCADIntegrationError(
                    "macro_file must be an existing Python file."
                )

        self._ensure_output_directory(request)

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
                evidence[str(path.resolve())] = sha256(path.read_bytes()).hexdigest()
        return evidence

    def _build_job(
        self,
        request: AdapterExecutionRequest,
    ) -> dict[str, Any]:
        operation = self.CAPABILITY_TO_OPERATION[request.capability_id]
        job = {
            "schema_version": "1.0",
            "request_id": request.request_id,
            "project_id": request.project_id,
            "operation": operation,
            **dict(request.inputs),
        }
        return job

    def _execute(
        self,
        request: AdapterExecutionRequest,
    ) -> AdapterExecutionResult:
        executable = self.locate_executable()
        if not executable:
            raise FreeCADIntegrationError("FreeCADCmd is unavailable.")

        output_directory = self._ensure_output_directory(request)
        runtime_directory = output_directory / ".phoenix_freecad"
        runtime_directory.mkdir(parents=True, exist_ok=True)

        job_path = runtime_directory / f"{request.request_id}.job.json"
        result_path = runtime_directory / f"{request.request_id}.result.json"
        worker_path = Path(__file__).with_name("freecad_worker.py").resolve()
        job = self._build_job(request)
        self._write_json(job_path, job)

        try:
            completed = self._runner(
                [
                    executable,
                    str(worker_path),
                    str(job_path),
                    str(result_path),
                ],
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AdapterExecutionResult(
                request_id=request.request_id,
                adapter_id=self.ADAPTER_ID,
                application_id=self.APPLICATION_ID,
                status="timed_out",
                errors=(f"FreeCAD execution timed out after {request.timeout_seconds}s.",),
                metadata={"timeout_seconds": request.timeout_seconds},
                evidence_sha256=self.evidence_digest(
                    {
                        "request_id": request.request_id,
                        "status": "timed_out",
                        "timeout_seconds": request.timeout_seconds,
                    }
                ),
            )
        except OSError as exc:
            raise FreeCADIntegrationError(
                f"Unable to start FreeCADCmd: {exc}"
            ) from exc

        if not result_path.is_file():
            raise FreeCADIntegrationError(
                "FreeCAD worker did not produce a result file. "
                f"Exit code: {completed.returncode}; stderr: {completed.stderr[:1000]}"
            )

        worker_result = json.loads(result_path.read_text(encoding="utf-8"))
        worker_status = str(worker_result.get("status", "failed"))
        output_files = [str(Path(item).resolve()) for item in worker_result.get("output_files", [])]
        file_evidence = self._file_evidence(output_files)

        evidence_payload = {
            "request": job,
            "worker_result": worker_result,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "output_file_sha256": file_evidence,
        }
        evidence_sha256 = self.evidence_digest(evidence_payload)

        status = "completed" if completed.returncode == 0 and worker_status == "completed" else "failed"
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
            warnings=tuple(str(item) for item in worker_result.get("warnings", [])),
            errors=tuple(str(item) for item in worker_result.get("errors", [])),
            evidence_sha256=evidence_sha256,
            metadata={
                **dict(worker_result.get("metadata", {})),
                "freecad_exit_code": completed.returncode,
                "freecad_stdout": completed.stdout[-4000:],
                "freecad_stderr": completed.stderr[-4000:],
            },
        )
