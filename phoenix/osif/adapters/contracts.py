"""Adapter contracts for Phoenix Core v2.0 BB3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class AdapterLifecycleState(str, Enum):
    CREATED = "created"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class AdapterContext:
    project_id: str
    working_directory: str
    configuration: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project_id must not be empty.")
        if not self.working_directory.strip():
            raise ValueError("working_directory must not be empty.")


@dataclass(frozen=True)
class AdapterHealth:
    status: str
    message: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    SUPPORTED = {"available", "degraded", "unavailable", "unknown"}

    def validate(self) -> None:
        if self.status not in self.SUPPORTED:
            raise ValueError(f"Unsupported adapter health status: {self.status}")


@dataclass(frozen=True)
class AdapterExecutionRequest:
    request_id: str
    project_id: str
    capability_id: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    output_directory: str = ""
    timeout_seconds: int = 300

    def validate(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty.")
        if not self.project_id.strip():
            raise ValueError("project_id must not be empty.")
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")


@dataclass(frozen=True)
class AdapterExecutionResult:
    request_id: str
    adapter_id: str
    application_id: str
    status: str
    outputs: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    evidence_sha256: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    SUPPORTED = {"completed", "failed", "blocked", "timed_out"}

    def validate(self) -> None:
        if self.status not in self.SUPPORTED:
            raise ValueError(f"Unsupported execution status: {self.status}")
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty.")
        if not self.adapter_id.strip():
            raise ValueError("adapter_id must not be empty.")
        if not self.application_id.strip():
            raise ValueError("application_id must not be empty.")
