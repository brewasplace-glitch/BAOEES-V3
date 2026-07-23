"""Core data models for the Phoenix Digital Twin."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TwinObject:
    """A versioned object in the Phoenix Digital Twin."""

    object_type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    object_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Relationship:
    """A typed relationship between two Digital Twin objects."""

    source_id: str
    relationship_type: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    relationship_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotRecord:
    """Evidence record for a stored Digital Twin snapshot."""

    snapshot_id: str
    created_at: str
    object_count: int
    relationship_count: int
    checksum_sha256: str
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
