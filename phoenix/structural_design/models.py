"""Canonical preliminary structural-design contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class StructuralMember:
    id: str
    source_element_id: str
    member_type: str
    level_id: str | None
    material_name: str
    length_m: float | None = None
    section: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LoadCase:
    id: str
    name: str
    category: str
    factor_hint: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LoadCombination:
    id: str
    name: str
    limit_state: str
    factors: dict[str, float]
    jurisdiction_profile_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StructuralValidationIssue:
    code: str
    severity: str
    message: str
    object_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StructuralModel:
    schema_version: str
    engine_version: str
    project_id: str
    members: list[StructuralMember] = field(default_factory=list)
    load_cases: list[LoadCase] = field(default_factory=list)
    combinations: list[LoadCombination] = field(default_factory=list)
    supports: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "members": [member.to_dict() for member in self.members],
            "load_cases": [item.to_dict() for item in self.load_cases],
            "combinations": [item.to_dict() for item in self.combinations],
            "supports": list(self.supports),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AnalysisHandoff:
    schema_version: str
    engine: str
    project_id: str
    structural_model_path: str
    requested_actions: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    prerequisites: tuple[str, ...]
    non_certifying: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["requested_actions"] = list(self.requested_actions)
        data["expected_outputs"] = list(self.expected_outputs)
        data["prerequisites"] = list(self.prerequisites)
        return data
