"""Canonical BB23 documentation, revision and release contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    FOR_REVIEW = "for_review"
    RELEASED = "released"
    BLOCKED = "blocked"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    FOR_REVIEW = "for_review"
    RELEASED = "released"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DocumentationIssue:
    code: str
    severity: str
    message: str
    source: str | None = None
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DocumentSection:
    section_id: str
    title: str
    paragraphs: tuple[str, ...] = ()
    entries: tuple[dict[str, Any], ...] = ()
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["paragraphs"] = list(self.paragraphs)
        data["entries"] = list(self.entries)
        data["source_refs"] = list(self.source_refs)
        return data


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: str
    title: str
    document_type: str
    revision: str
    status: DocumentStatus
    filename: str
    discipline: str
    source_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["source_refs"] = list(self.source_refs)
        return data


@dataclass(slots=True)
class ConstructionDocumentPackage:
    schema_version: str
    engine_version: str
    package_id: str
    project_id: str
    project_name: str
    revision: str
    stage: str
    status: PackageStatus
    sections: list[DocumentSection] = field(default_factory=list)
    document_register: list[DocumentRecord] = field(default_factory=list)
    issues: list[DocumentationIssue] = field(default_factory=list)
    source_fingerprints_sha256: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def blocking_issue_count(self) -> int:
        return sum(1 for issue in self.issues if issue.blocking)

    @property
    def release_ready(self) -> bool:
        return self.blocking_issue_count == 0 and self.status != PackageStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "package_id": self.package_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "revision": self.revision,
            "stage": self.stage,
            "status": self.status.value,
            "release_ready": self.release_ready,
            "blocking_issue_count": self.blocking_issue_count,
            "section_count": len(self.sections),
            "document_count": len(self.document_register),
            "source_fingerprints_sha256": dict(
                sorted(self.source_fingerprints_sha256.items())
            ),
            "sections": [section.to_dict() for section in self.sections],
            "document_register": [
                document.to_dict() for document in self.document_register
            ],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
