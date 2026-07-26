"""Canonical contracts for BB17.4 compilation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CompilationStatus(str, Enum):
    BLOCKED = "blocked"
    COMPILED = "compiled"


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    id: str
    title: str
    description: str
    discipline: str
    severity: str
    expression: str
    failure_message: str
    applies_when: str | None = None
    evidence_paths: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_paths"] = list(self.evidence_paths)
        return data


@dataclass(frozen=True, slots=True)
class RuleDefinitionSet:
    id: str
    jurisdiction_id: str
    version: str
    status: str
    rules: tuple[RuleDefinition, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "version": self.version,
            "status": self.status,
            "rules": [rule.to_dict() for rule in self.rules],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CompilationIssue:
    code: str
    severity: str
    message: str
    object_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CompilationResult:
    schema_version: str
    compiler_version: str
    jurisdiction_id: str
    status: CompilationStatus
    source_catalog_id: str
    mapping_set_id: str
    definition_set_id: str
    profile: dict[str, Any] | None
    issues: list[CompilationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def compiled(self) -> bool:
        return self.status == CompilationStatus.COMPILED and self.profile is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "compiler_version": self.compiler_version,
            "jurisdiction_id": self.jurisdiction_id,
            "status": self.status.value,
            "compiled": self.compiled,
            "source_catalog_id": self.source_catalog_id,
            "mapping_set_id": self.mapping_set_id,
            "definition_set_id": self.definition_set_id,
            "profile": self.profile,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
