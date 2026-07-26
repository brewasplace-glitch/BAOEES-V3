from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

class ElementCategory(str, Enum):
    SITE = "site"
    FOUNDATION = "foundation"
    COLUMN = "column"
    BEAM = "beam"
    WALL = "wall"
    SLAB = "slab"
    ROOF = "roof"
    DOOR = "door"
    WINDOW = "window"
    STAIR = "stair"
    MEP = "mep"
    GENERIC = "generic"

@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    object_id: str | None = None
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(slots=True)
class Level:
    id: str
    name: str
    elevation_m: float
    height_m: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(slots=True)
class Space:
    id: str
    name: str
    level_id: str
    area_m2: float | None = None
    volume_m3: float | None = None
    usage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(slots=True)
class BuildingElement:
    id: str
    name: str
    category: ElementCategory
    level_id: str | None = None
    geometry: dict[str, Any] = field(default_factory=dict)
    material: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

@dataclass(slots=True)
class BuildingModel:
    schema_version: str
    project_id: str
    name: str
    units: str = "SI"
    levels: dict[str, Level] = field(default_factory=dict)
    spaces: dict[str, Space] = field(default_factory=dict)
    elements: dict[str, BuildingElement] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "units": self.units,
            "levels": [self.levels[k].to_dict() for k in sorted(self.levels)],
            "spaces": [self.spaces[k].to_dict() for k in sorted(self.spaces)],
            "elements": [self.elements[k].to_dict() for k in sorted(self.elements)],
            "relationships": list(self.relationships),
            "metadata": dict(self.metadata),
        }
