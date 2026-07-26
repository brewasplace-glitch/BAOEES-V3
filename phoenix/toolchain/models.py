"""Data contracts for the Phoenix Toolchain & Dependency Manager."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DependencyKind(str, Enum):
    EXECUTABLE = "executable"
    PYTHON_PACKAGE = "python_package"


class DependencyStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    INVALID = "invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DependencySpec:
    id: str
    name: str
    kind: DependencyKind
    required: bool
    capability: str
    executable_names: tuple[str, ...] = ()
    environment_variables: tuple[str, ...] = ()
    windows_candidates: tuple[str, ...] = ()
    python_import_name: str | None = None
    python_distribution_name: str | None = None
    minimum_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["executable_names"] = list(self.executable_names)
        data["environment_variables"] = list(self.environment_variables)
        data["windows_candidates"] = list(self.windows_candidates)
        return data


@dataclass(frozen=True, slots=True)
class DependencyResult:
    id: str
    name: str
    kind: DependencyKind
    required: bool
    capability: str
    status: DependencyStatus
    detected_version: str | None = None
    detected_path: str | None = None
    source: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class ToolchainReport:
    schema_version: str
    manager_version: str
    platform: str
    python_version: str
    results: list[DependencyResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def required_ready(self) -> bool:
        return all(
            item.status == DependencyStatus.AVAILABLE
            for item in self.results
            if item.required
        )

    @property
    def missing_required(self) -> list[DependencyResult]:
        return [
            item
            for item in self.results
            if item.required and item.status != DependencyStatus.AVAILABLE
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manager_version": self.manager_version,
            "platform": self.platform,
            "python_version": self.python_version,
            "required_ready": self.required_ready,
            "results": [item.to_dict() for item in self.results],
            "metadata": dict(self.metadata),
        }
