"""Canonical BB17.3 source-acquisition and rule-mapping contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class SourceStatus(str, Enum):
    DISCOVERED = "discovered"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class RightsClass(str, Enum):
    METADATA_ONLY = "metadata_only"
    PUBLIC_TEXT = "public_text"
    RESTRICTED = "restricted"


class MappingStatus(str, Enum):
    DRAFT = "draft"
    MAPPED = "mapped"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class AcquisitionAction(str, Enum):
    VERIFY_METADATA = "verify_metadata"
    SNAPSHOT_PUBLIC_DOCUMENT = "snapshot_public_document"
    MANUAL_REVIEW = "manual_review"
    CHANGE_CHECK = "change_check"


@dataclass(frozen=True, slots=True)
class SourceRecord:
    id: str
    jurisdiction_id: str
    title: str
    authority: str
    canonical_uri: str
    status: SourceStatus
    rights_class: RightsClass
    content_storage_policy: str
    required: bool = True
    publication_id: str | None = None
    edition: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    verified_at: str | None = None
    verified_by: str | None = None
    snapshot_sha256: str | None = None
    topics: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["rights_class"] = self.rights_class.value
        data["topics"] = list(self.topics)
        return data


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    id: str
    jurisdiction_id: str
    version: str
    status: str
    sources: tuple[SourceRecord, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "version": self.version,
            "status": self.status,
            "sources": [source.to_dict() for source in self.sources],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RuleMapping:
    id: str
    jurisdiction_id: str
    phoenix_rule_id: str
    source_id: str
    locator: str
    status: MappingStatus
    interpretation_note: str = ""
    confidence: str = "unrated"
    reviewer: str | None = None
    reviewed_at: str | None = None
    evidence_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class RuleMappingSet:
    id: str
    jurisdiction_id: str
    version: str
    target_profile: str
    required_rule_ids: tuple[str, ...]
    mappings: tuple[RuleMapping, ...]
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "version": self.version,
            "target_profile": self.target_profile,
            "required_rule_ids": list(self.required_rule_ids),
            "mappings": [mapping.to_dict() for mapping in self.mappings],
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AcquisitionTask:
    id: str
    jurisdiction_id: str
    source_id: str
    action: AcquisitionAction
    priority: str
    automatic_execution: bool
    reason: str
    canonical_uri: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        return data


@dataclass(frozen=True, slots=True)
class ActivationAssessment:
    jurisdiction_id: str
    eligible: bool
    reasons: tuple[str, ...]
    source_coverage: dict[str, int]
    mapping_coverage: dict[str, int]
    fingerprint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
