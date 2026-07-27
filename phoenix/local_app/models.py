"""Data models for the Phoenix local runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DashboardCandidate:
    relative_path: str
    score: int
    matched_markers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["matched_markers"] = list(self.matched_markers)
        return value


@dataclass
class RuntimeJob:
    job_id: str
    workflow_id: str
    label: str
    status: str
    started_at: str
    output_dir: str
    log_path: str
    command: list[str] = field(default_factory=list)
    finished_at: str | None = None
    return_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
