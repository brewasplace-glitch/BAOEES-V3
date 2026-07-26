"""Canonical BB17 rule and compliance data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RuleSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleResultStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CodeRule:
    id: str
    title: str
    description: str
    discipline: str
    severity: RuleSeverity
    expression: str
    failure_message: str
    applies_when: str | None = None
    evidence_paths: tuple[str, ...] = ()
    references: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["evidence_paths"] = list(self.evidence_paths)
        data["references"] = list(self.references)
        return data


@dataclass(frozen=True, slots=True)
class CodeProfile:
    id: str
    name: str
    version: str
    jurisdiction: str
    status: str
    rules: tuple[CodeRule, ...]
    fail_severities: tuple[RuleSeverity, ...] = (
        RuleSeverity.ERROR,
        RuleSeverity.CRITICAL,
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "jurisdiction": self.jurisdiction,
            "status": self.status,
            "rules": [rule.to_dict() for rule in self.rules],
            "fail_severities": [item.value for item in self.fail_severities],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    evaluation_id: str
    rule_id: str
    title: str
    discipline: str
    severity: RuleSeverity
    status: RuleResultStatus
    message: str
    evidence: tuple[dict[str, Any], ...] = ()
    references: tuple[dict[str, Any], ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        data["evidence"] = list(self.evidence)
        data["references"] = list(self.references)
        return data


@dataclass(slots=True)
class ComplianceReport:
    schema_version: str
    engine_version: str
    profile_id: str
    profile_version: str
    jurisdiction: str
    profile_status: str
    model_fingerprint_sha256: str
    evaluations: list[RuleEvaluation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in RuleResultStatus}
        for evaluation in self.evaluations:
            counts[evaluation.status.value] += 1
        counts["total"] = len(self.evaluations)
        return counts

    def is_compliant_for(self, fail_severities: tuple[RuleSeverity, ...]) -> bool:
        blocked = set(fail_severities)
        return not any(
            item.severity in blocked
            and item.status in (RuleResultStatus.FAIL, RuleResultStatus.ERROR)
            for item in self.evaluations
        )

    def to_dict(self, fail_severities: tuple[RuleSeverity, ...]) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "jurisdiction": self.jurisdiction,
            "profile_status": self.profile_status,
            "model_fingerprint_sha256": self.model_fingerprint_sha256,
            "compliant": self.is_compliant_for(fail_severities),
            "summary": self.summary,
            "evaluations": [item.to_dict() for item in self.evaluations],
            "metadata": dict(self.metadata),
        }
