"""Application discovery and capability indexing for Phoenix OSIF."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterable, Mapping

from phoenix.osif import ApplicationDescriptor, ApplicationRegistry, Capability


class DiscoveryError(RuntimeError):
    """Raised when application discovery cannot be completed safely."""


@dataclass(frozen=True)
class DiscoveryCandidate:
    application_id: str
    name: str
    adapter_id: str
    execution_mode: str
    executable_names: tuple[str, ...] = ()
    python_modules: tuple[str, ...] = ()
    version_arguments: tuple[str, ...] = ("--version",)
    capabilities: tuple[Capability, ...] = ()
    license_id: str = ""
    enabled_when_found: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.application_id.strip():
            raise DiscoveryError("application_id must not be empty.")
        if not self.name.strip():
            raise DiscoveryError("name must not be empty.")
        if not self.adapter_id.strip():
            raise DiscoveryError("adapter_id must not be empty.")
        if self.execution_mode not in ApplicationDescriptor.SUPPORTED_EXECUTION_MODES:
            raise DiscoveryError(
                f"Unsupported execution_mode: {self.execution_mode}"
            )
        if not self.executable_names and not self.python_modules:
            raise DiscoveryError(
                f"{self.application_id} requires executable_names or python_modules."
            )
        for capability in self.capabilities:
            capability.validate()


@dataclass(frozen=True)
class DiscoveryResult:
    application_id: str
    found: bool
    health_status: str
    executable: str = ""
    python_module: str = ""
    version: str = ""
    evidence_sha256: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


class ApplicationDiscoveryService:
    """Discovers local applications and updates an OSIF application registry."""

    def __init__(self, *, timeout_seconds: int = 10) -> None:
        if timeout_seconds <= 0:
            raise DiscoveryError("timeout_seconds must be positive.")
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    def _find_executable(self, names: Iterable[str]) -> str:
        for name in names:
            found = shutil.which(name)
            if found:
                return str(Path(found).resolve())
        return ""

    @staticmethod
    def _find_python_module(names: Iterable[str]) -> str:
        for name in names:
            if importlib.util.find_spec(name) is not None:
                return name
        return ""

    def _read_version(
        self,
        executable: str,
        arguments: tuple[str, ...],
    ) -> tuple[str, dict[str, Any]]:
        if not executable:
            return "", {}
        try:
            completed = subprocess.run(
                [executable, *arguments],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "", {"version_probe_error": type(exc).__name__}

        combined = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )
        first_line = combined.splitlines()[0] if combined else ""
        return first_line[:300], {
            "version_probe_exit_code": completed.returncode,
            "version_probe_output": combined[:2000],
        }

    def discover_candidate(
        self,
        candidate: DiscoveryCandidate,
    ) -> DiscoveryResult:
        candidate.validate()

        executable = self._find_executable(candidate.executable_names)
        python_module = self._find_python_module(candidate.python_modules)
        found = bool(executable or python_module)

        version = ""
        details: dict[str, Any] = {
            "execution_mode": candidate.execution_mode,
            "executable_names": list(candidate.executable_names),
            "python_modules": list(candidate.python_modules),
        }
        if executable:
            version, probe = self._read_version(
                executable,
                candidate.version_arguments,
            )
            details.update(probe)

        health_status = "available" if found else "unavailable"
        evidence_payload = {
            "application_id": candidate.application_id,
            "found": found,
            "health_status": health_status,
            "executable": executable,
            "python_module": python_module,
            "version": version,
            "details": details,
        }

        return DiscoveryResult(
            application_id=candidate.application_id,
            found=found,
            health_status=health_status,
            executable=executable,
            python_module=python_module,
            version=version,
            evidence_sha256=self._digest(evidence_payload),
            details=details,
        )

    def discover_all(
        self,
        candidates: Iterable[DiscoveryCandidate],
    ) -> tuple[DiscoveryResult, ...]:
        seen: set[str] = set()
        results = []
        for candidate in candidates:
            if candidate.application_id in seen:
                raise DiscoveryError(
                    f"Duplicate application_id: {candidate.application_id}"
                )
            seen.add(candidate.application_id)
            results.append(self.discover_candidate(candidate))
        return tuple(results)

    def update_registry(
        self,
        *,
        registry: ApplicationRegistry,
        candidates: Iterable[DiscoveryCandidate],
    ) -> dict[str, Any]:
        candidates = tuple(candidates)
        results = self.discover_all(candidates)
        by_id = {item.application_id: item for item in candidates}

        for result in results:
            candidate = by_id[result.application_id]
            descriptor = ApplicationDescriptor(
                application_id=candidate.application_id,
                name=candidate.name,
                adapter_id=candidate.adapter_id,
                execution_mode=candidate.execution_mode,
                version=result.version,
                executable=result.executable,
                license_id=candidate.license_id,
                capabilities=candidate.capabilities,
                enabled=result.found and candidate.enabled_when_found,
                metadata={
                    **dict(candidate.metadata),
                    "discovery": {
                        "found": result.found,
                        "health_status": result.health_status,
                        "python_module": result.python_module,
                        "evidence_sha256": result.evidence_sha256,
                    },
                },
            )
            registry.register(descriptor, replace=True)

        report = {
            "schema_version": "1.0",
            "service": {
                "id": "phoenix.osif.discovery.bb2",
                "version": "1.0.0",
            },
            "results": [asdict(item) for item in results],
            "registry": registry.to_dict(),
        }
        report["evidence_sha256"] = self._digest(report)
        return report

    def write_report(
        self,
        report: Mapping[str, Any],
        destination: str | Path,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path
