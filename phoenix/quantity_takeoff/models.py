"""Canonical BB20 quantity and evidence contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class QuantityUnit(str, Enum):
    EACH = "ea"
    METRE = "m"
    SQUARE_METRE = "m2"
    CUBIC_METRE = "m3"
    KILOGRAM = "kg"


class MeasurementBasis(str, Enum):
    COUNTED = "counted"
    CALCULATED = "calculated"
    DECLARED = "declared"


class QuantityStatus(str, Enum):
    COMPLETE = "complete"
    ESTIMATED = "estimated"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class QuantityIssue:
    code: str
    severity: str
    message: str
    source_object_id: str | None = None
    source_model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QuantityRecord:
    quantity_id: str
    source_object_id: str
    source_model: str
    source_level_id: str | None
    category: str
    work_section: str
    material: str | None
    quantity_type: str
    value: float
    unit: QuantityUnit
    basis: MeasurementBasis
    status: QuantityStatus
    formula: str
    inputs: dict[str, float] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    drawing_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["unit"] = self.unit.value
        data["basis"] = self.basis.value
        data["status"] = self.status.value
        data["assumptions"] = list(self.assumptions)
        data["drawing_refs"] = list(self.drawing_refs)
        return data


@dataclass(slots=True)
class QuantityTakeoffReport:
    schema_version: str
    engine_version: str
    project_id: str
    model_fingerprint_sha256: str
    records: list[QuantityRecord] = field(default_factory=list)
    issues: list[QuantityIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def totals_by_unit(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for record in self.records:
            totals[record.unit.value] = totals.get(record.unit.value, 0.0) + record.value
        return {key: round(value, 6) for key, value in sorted(totals.items())}

    @property
    def totals_by_work_section(self) -> dict[str, dict[str, float]]:
        totals: dict[str, dict[str, float]] = {}
        for record in self.records:
            bucket = totals.setdefault(record.work_section, {})
            bucket[record.unit.value] = bucket.get(record.unit.value, 0.0) + record.value
        return {
            section: {
                unit: round(value, 6)
                for unit, value in sorted(values.items())
            }
            for section, values in sorted(totals.items())
        }

    @property
    def totals_by_material(self) -> dict[str, dict[str, float]]:
        totals: dict[str, dict[str, float]] = {}
        for record in self.records:
            if not record.material:
                continue
            bucket = totals.setdefault(record.material, {})
            bucket[record.unit.value] = bucket.get(record.unit.value, 0.0) + record.value
        return {
            material: {
                unit: round(value, 6)
                for unit, value in sorted(values.items())
            }
            for material, values in sorted(totals.items())
        }

    @property
    def totals_by_level(self) -> dict[str, dict[str, float]]:
        totals: dict[str, dict[str, float]] = {}
        for record in self.records:
            level = record.source_level_id or "UNASSIGNED"
            bucket = totals.setdefault(level, {})
            bucket[record.unit.value] = bucket.get(record.unit.value, 0.0) + record.value
        return {
            level: {
                unit: round(value, 6)
                for unit, value in sorted(values.items())
            }
            for level, values in sorted(totals.items())
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "model_fingerprint_sha256": self.model_fingerprint_sha256,
            "record_count": len(self.records),
            "issue_count": len(self.issues),
            "totals_by_unit": self.totals_by_unit,
            "totals_by_work_section": self.totals_by_work_section,
            "totals_by_material": self.totals_by_material,
            "totals_by_level": self.totals_by_level,
            "records": [record.to_dict() for record in self.records],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
