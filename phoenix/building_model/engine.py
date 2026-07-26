from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any
from .models import BuildingElement, BuildingModel, ElementCategory, Level, Space, ValidationIssue

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")

class BuildingModelEngine:
    SCHEMA_VERSION = "phoenix.building-model/1.0"

    def create_model(self, project_id: str, name: str, *, metadata: dict[str, Any] | None = None) -> BuildingModel:
        self._require_id(project_id, "project_id")
        if not name.strip():
            raise ValueError("name must not be empty")
        return BuildingModel(self.SCHEMA_VERSION, project_id, name.strip(), metadata=dict(metadata or {}))

    def add_level(self, model: BuildingModel, *, level_id: str, name: str,
                  elevation_m: float, height_m: float | None = None,
                  metadata: dict[str, Any] | None = None) -> Level:
        self._require_id(level_id, "level_id")
        self._require_unique(level_id, model.levels, "level")
        if height_m is not None and height_m <= 0:
            raise ValueError("height_m must be greater than zero")
        level = Level(level_id, name.strip() or level_id, float(elevation_m),
                      float(height_m) if height_m is not None else None, dict(metadata or {}))
        model.levels[level_id] = level
        return level

    def add_space(self, model: BuildingModel, *, space_id: str, name: str, level_id: str,
                  area_m2: float | None = None, volume_m3: float | None = None,
                  usage: str | None = None, metadata: dict[str, Any] | None = None) -> Space:
        self._require_id(space_id, "space_id")
        self._require_unique(space_id, model.spaces, "space")
        if level_id not in model.levels:
            raise KeyError(f"Unknown level_id: {level_id}")
        if area_m2 is not None and area_m2 < 0:
            raise ValueError("area_m2 must not be negative")
        if volume_m3 is not None and volume_m3 < 0:
            raise ValueError("volume_m3 must not be negative")
        space = Space(space_id, name.strip() or space_id, level_id,
                      float(area_m2) if area_m2 is not None else None,
                      float(volume_m3) if volume_m3 is not None else None,
                      usage, dict(metadata or {}))
        model.spaces[space_id] = space
        return space

    def add_element(self, model: BuildingModel, *, element_id: str, name: str,
                    category: ElementCategory | str, level_id: str | None = None,
                    geometry: dict[str, Any] | None = None,
                    material: dict[str, Any] | None = None,
                    properties: dict[str, Any] | None = None,
                    source_refs: list[str] | None = None) -> BuildingElement:
        self._require_id(element_id, "element_id")
        self._require_unique(element_id, model.elements, "element")
        if level_id is not None and level_id not in model.levels:
            raise KeyError(f"Unknown level_id: {level_id}")
        resolved = category if isinstance(category, ElementCategory) else ElementCategory(category)
        element = BuildingElement(element_id, name.strip() or element_id, resolved, level_id,
                                  dict(geometry or {}), dict(material or {}),
                                  dict(properties or {}), list(source_refs or []))
        model.elements[element_id] = element
        return element

    def add_relationship(self, model: BuildingModel, *, relation_type: str,
                         source_id: str, target_id: str,
                         metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        known = set(model.levels) | set(model.spaces) | set(model.elements)
        if source_id not in known:
            raise KeyError(f"Unknown source_id: {source_id}")
        if target_id not in known:
            raise KeyError(f"Unknown target_id: {target_id}")
        relation = {"type": relation_type.strip(), "source_id": source_id,
                    "target_id": target_id, "metadata": dict(metadata or {})}
        model.relationships.append(relation)
        return relation

    def validate(self, model: BuildingModel) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.schema_version != self.SCHEMA_VERSION:
            issues.append(ValidationIssue("BME-SCHEMA-001", "error",
                                          f"Unsupported schema version: {model.schema_version}",
                                          model.project_id))
        if model.units != "SI":
            issues.append(ValidationIssue("BME-UNITS-001", "error",
                                          "BB16 v1.0 requires SI units.", model.project_id))
        elevations: dict[float, str] = {}
        for level in model.levels.values():
            if level.elevation_m in elevations:
                issues.append(ValidationIssue("BME-LEVEL-002", "warning",
                                              f"Level elevation duplicates {elevations[level.elevation_m]}.",
                                              level.id))
            elevations[level.elevation_m] = level.id
        for space in model.spaces.values():
            if space.level_id not in model.levels:
                issues.append(ValidationIssue("BME-SPACE-001", "error",
                                              f"Unknown level: {space.level_id}", space.id))
        for element in model.elements.values():
            if element.level_id is not None and element.level_id not in model.levels:
                issues.append(ValidationIssue("BME-ELEMENT-001", "error",
                                              f"Unknown level: {element.level_id}", element.id))
            if not element.geometry:
                issues.append(ValidationIssue("BME-GEOMETRY-001", "warning",
                                              "Element has no geometry payload.", element.id))
        return issues

    def assert_valid(self, model: BuildingModel) -> None:
        errors = [i for i in self.validate(model) if i.severity == "error"]
        if errors:
            raise ValueError("Building model validation failed: " +
                             "; ".join(f"{i.code}: {i.message}" for i in errors))

    def fingerprint(self, model: BuildingModel) -> str:
        raw = json.dumps(model.to_dict(), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def export_json(self, model: BuildingModel, output_path: str | Path) -> Path:
        self.assert_valid(model)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = model.to_dict()
        data["fingerprint_sha256"] = self.fingerprint(model)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        return path

    @staticmethod
    def _require_id(value: str, field_name: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"{field_name} has invalid Phoenix ID syntax: {value!r}")

    @staticmethod
    def _require_unique(value: str, collection: dict[str, Any], label: str) -> None:
        if value in collection:
            raise ValueError(f"Duplicate {label} id: {value}")
