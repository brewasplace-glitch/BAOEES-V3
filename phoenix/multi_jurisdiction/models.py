"""Canonical jurisdiction-selection contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LocationContext:
    country_code: str | None = None
    territory_code: str | None = None
    country_name: str | None = None
    island: str | None = None
    district: str | None = None
    municipality: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class JurisdictionDefinition:
    id: str
    name: str
    legal_scope: str
    country_codes: tuple[str, ...]
    aliases: tuple[str, ...]
    legal_codepack_manifest: str
    foundation_profile: str
    default_overlays: tuple[str, ...]
    island_overlays: dict[str, tuple[str, ...]]
    source_watch: tuple[str, ...]
    mixing_policy: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["country_codes"] = list(self.country_codes)
        data["aliases"] = list(self.aliases)
        data["default_overlays"] = list(self.default_overlays)
        data["island_overlays"] = {
            key: list(values) for key, values in self.island_overlays.items()
        }
        data["source_watch"] = list(self.source_watch)
        return data


@dataclass(frozen=True, slots=True)
class JurisdictionSelection:
    jurisdiction_id: str
    jurisdiction_name: str
    legal_codepack_manifest: str
    foundation_profile: str
    local_scope: str | None
    overlays: tuple[str, ...]
    confidence: str
    reasons: tuple[str, ...]
    legal_mixing_blocked: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["overlays"] = list(self.overlays)
        data["reasons"] = list(self.reasons)
        return data
