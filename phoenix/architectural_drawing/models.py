"""Canonical drawing package contracts for BB18.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DrawingType(str, Enum):
    SITE = "site"
    PLAN = "plan"
    ELEVATION = "elevation"
    SECTION = "section"
    SCHEDULE = "schedule"


@dataclass(frozen=True, slots=True)
class DrawingSheet:
    id: str
    number: str
    title: str
    drawing_type: DrawingType
    scale_denominator: int
    level_id: str | None = None
    view_direction: str | None = None
    model_object_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["drawing_type"] = self.drawing_type.value
        data["model_object_ids"] = list(self.model_object_ids)
        return data


@dataclass(slots=True)
class DrawingPackage:
    schema_version: str
    engine_version: str
    project_id: str
    project_name: str
    sheets: list[DrawingSheet] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
            "metadata": dict(self.metadata),
        }
