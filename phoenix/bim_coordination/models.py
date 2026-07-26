"""Canonical BB22 coordination issue contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


@dataclass(frozen=True, slots=True)
class CoordinationIssue:
    issue_id: str
    issue_type: str
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus
    discipline: str
    source_model: str | None = None
    source_object_id: str | None = None
    target_model: str | None = None
    target_object_id: str | None = None
    level_id: str | None = None
    location: dict[str, float] = field(default_factory=dict)
    evidence: tuple[dict[str, Any], ...] = ()
    assigned_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        data["evidence"] = list(self.evidence)
        return data


@dataclass(slots=True)
class CoordinationReport:
    schema_version: str
    engine_version: str
    project_id: str
    model_fingerprints_sha256: dict[str, str]
    issues: list[CoordinationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def summary_by_severity(self) -> dict[str, int]:
        summary = {severity.value: 0 for severity in IssueSeverity}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary

    @property
    def summary_by_type(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for issue in self.issues:
            summary[issue.issue_type] = summary.get(issue.issue_type, 0) + 1
        return dict(sorted(summary.items()))

    @property
    def open_issue_count(self) -> int:
        return sum(1 for issue in self.issues if issue.status == IssueStatus.OPEN)

    @property
    def coordination_passed(self) -> bool:
        return not any(
            issue.status == IssueStatus.OPEN
            and issue.severity in (IssueSeverity.ERROR, IssueSeverity.CRITICAL)
            for issue in self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "coordination_passed": self.coordination_passed,
            "issue_count": len(self.issues),
            "open_issue_count": self.open_issue_count,
            "summary_by_severity": self.summary_by_severity,
            "summary_by_type": self.summary_by_type,
            "model_fingerprints_sha256": dict(
                sorted(self.model_fingerprints_sha256.items())
            ),
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
