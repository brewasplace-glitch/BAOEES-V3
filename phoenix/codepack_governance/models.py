"""Canonical governance contracts for Phoenix codepacks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ActivationState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class SourceStatus(str, Enum):
    IDENTIFIED = "identified"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True, slots=True)
class SourceReference:
    id: str
    title: str
    publisher: str
    publication_id: str
    edition: str
    source_status: SourceStatus
    canonical_uri: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    license_class: str = "metadata-only"
    source_sha256: str | None = None
    rights_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_status"] = self.source_status.value
        return data


@dataclass(frozen=True, slots=True)
class CodepackManifest:
    id: str
    name: str
    version: str
    jurisdiction: str
    profile_path: str
    regulatory_claim: bool
    review_status: ReviewStatus
    activation_state: ActivationState
    sources: tuple[SourceReference, ...] = ()
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    supersedes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "jurisdiction": self.jurisdiction,
            "profile_path": self.profile_path,
            "regulatory_claim": self.regulatory_claim,
            "review_status": self.review_status.value,
            "activation_state": self.activation_state.value,
            "sources": [source.to_dict() for source in self.sources],
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "supersedes": list(self.supersedes),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    codepack_id: str
    eligible: bool
    reasons: tuple[str, ...]
    evaluated_at: str
    as_of_date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
