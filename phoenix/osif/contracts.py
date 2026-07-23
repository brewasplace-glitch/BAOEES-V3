"""Stable contracts for Phoenix Open Source Integration Framework."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Capability:
    capability_id: str
    name: str
    input_formats: tuple[str, ...] = ()
    output_formats: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty.")
        if not self.name.strip():
            raise ValueError("capability name must not be empty.")


@dataclass(frozen=True)
class ApplicationDescriptor:
    application_id: str
    name: str
    adapter_id: str
    execution_mode: str
    version: str = ""
    executable: str = ""
    license_id: str = ""
    homepage: str = ""
    capabilities: tuple[Capability, ...] = ()
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    SUPPORTED_EXECUTION_MODES = {
        "native", "cli", "python", "container", "wsl", "file"
    }

    def validate(self) -> None:
        if not self.application_id.strip():
            raise ValueError("application_id must not be empty.")
        if not self.name.strip():
            raise ValueError("application name must not be empty.")
        if not self.adapter_id.strip():
            raise ValueError("adapter_id must not be empty.")
        if self.execution_mode not in self.SUPPORTED_EXECUTION_MODES:
            raise ValueError(f"Unsupported execution_mode: {self.execution_mode}")
        seen: set[str] = set()
        for capability in self.capabilities:
            capability.validate()
            if capability.capability_id in seen:
                raise ValueError(
                    f"Duplicate capability_id: {capability.capability_id}"
                )
            seen.add(capability.capability_id)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = [asdict(item) for item in self.capabilities]
        return data


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    application_id: str
    capability_id: str
    arguments: tuple[str, ...] = ()
    input_files: tuple[str, ...] = ()
    output_directory: str = ""
    environment: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty.")
        if not self.application_id.strip():
            raise ValueError("application_id must not be empty.")
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty.")


@dataclass(frozen=True)
class ExecutionResult:
    request_id: str
    application_id: str
    status: str
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    output_files: tuple[str, ...] = ()
    evidence_sha256: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
