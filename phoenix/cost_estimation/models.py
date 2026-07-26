"""Canonical BB21 rate, scenario and cost-report contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RateBookStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class RateSelector:
    quantity_types: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    work_sections: tuple[str, ...] = ()
    materials: tuple[str, ...] = ()
    source_models: tuple[str, ...] = ()

    @property
    def specificity(self) -> int:
        return sum(
            bool(values)
            for values in (
                self.quantity_types,
                self.categories,
                self.work_sections,
                self.materials,
                self.source_models,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "quantity_types": list(self.quantity_types),
            "categories": list(self.categories),
            "work_sections": list(self.work_sections),
            "materials": list(self.materials),
            "source_models": list(self.source_models),
        }


@dataclass(frozen=True, slots=True)
class RateItem:
    id: str
    cost_code: str
    description: str
    unit: str
    selector: RateSelector
    material_rate: float = 0.0
    labor_rate: float = 0.0
    equipment_rate: float = 0.0
    subcontract_rate: float = 0.0
    other_rate: float = 0.0
    waste_percent: float = 0.0
    source_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def base_unit_rate(self) -> float:
        return round(
            self.material_rate
            + self.labor_rate
            + self.equipment_rate
            + self.subcontract_rate
            + self.other_rate,
            6,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["selector"] = self.selector.to_dict()
        data["base_unit_rate"] = self.base_unit_rate
        return data


@dataclass(frozen=True, slots=True)
class RateBook:
    id: str
    name: str
    version: str
    status: RateBookStatus
    currency: str
    price_date: str
    jurisdiction: str
    location_profile: str
    rates: tuple[RateItem, ...]
    source_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "currency": self.currency,
            "price_date": self.price_date,
            "jurisdiction": self.jurisdiction,
            "location_profile": self.location_profile,
            "source_reference": self.source_reference,
            "rates": [rate.to_dict() for rate in self.rates],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CostScenario:
    id: str
    name: str
    currency: str
    quantity_factor: float = 1.0
    location_factor: float = 1.0
    escalation_percent: float = 0.0
    material_factor: float = 1.0
    labor_factor: float = 1.0
    equipment_factor: float = 1.0
    subcontract_factor: float = 1.0
    other_factor: float = 1.0
    overhead_percent: float = 0.0
    risk_percent: float = 0.0
    contingency_percent: float = 0.0
    profit_percent: float = 0.0
    tax_percent: float = 0.0
    require_validated_ratebook: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CostIssue:
    code: str
    severity: str
    message: str
    scenario_id: str | None = None
    quantity_id: str | None = None
    source_object_id: str | None = None
    rate_item_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CostLine:
    line_id: str
    scenario_id: str
    quantity_id: str
    source_object_id: str
    source_model: str
    source_level_id: str | None
    category: str
    work_section: str
    material: str | None
    quantity_type: str
    cost_code: str
    description: str
    rate_item_id: str
    base_quantity: float
    waste_percent: float
    priced_quantity: float
    unit: str
    base_unit_rate: float
    adjusted_unit_rate: float
    material_cost: float
    labor_cost: float
    equipment_cost: float
    subcontract_cost: float
    other_cost: float
    direct_cost: float
    currency: str
    drawing_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["drawing_refs"] = list(self.drawing_refs)
        return data


@dataclass(slots=True)
class ScenarioEstimate:
    scenario: CostScenario
    lines: list[CostLine] = field(default_factory=list)
    unmatched_quantities: list[str] = field(default_factory=list)
    ambiguous_quantities: list[str] = field(default_factory=list)
    direct_cost: float = 0.0
    overhead_cost: float = 0.0
    risk_cost: float = 0.0
    contingency_cost: float = 0.0
    profit_cost: float = 0.0
    pre_tax_cost: float = 0.0
    tax_cost: float = 0.0
    total_cost: float = 0.0

    @property
    def totals_by_work_section(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for line in self.lines:
            totals[line.work_section] = totals.get(line.work_section, 0.0) + line.direct_cost
        return {key: round(value, 2) for key, value in sorted(totals.items())}

    @property
    def totals_by_level(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for line in self.lines:
            key = line.source_level_id or "UNASSIGNED"
            totals[key] = totals.get(key, 0.0) + line.direct_cost
        return {key: round(value, 2) for key, value in sorted(totals.items())}

    @property
    def totals_by_cost_code(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for line in self.lines:
            totals[line.cost_code] = totals.get(line.cost_code, 0.0) + line.direct_cost
        return {key: round(value, 2) for key, value in sorted(totals.items())}

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.to_dict(),
            "matched_line_count": len(self.lines),
            "unmatched_quantities": list(self.unmatched_quantities),
            "ambiguous_quantities": list(self.ambiguous_quantities),
            "direct_cost": round(self.direct_cost, 2),
            "overhead_cost": round(self.overhead_cost, 2),
            "risk_cost": round(self.risk_cost, 2),
            "contingency_cost": round(self.contingency_cost, 2),
            "profit_cost": round(self.profit_cost, 2),
            "pre_tax_cost": round(self.pre_tax_cost, 2),
            "tax_cost": round(self.tax_cost, 2),
            "total_cost": round(self.total_cost, 2),
            "totals_by_work_section": self.totals_by_work_section,
            "totals_by_level": self.totals_by_level,
            "totals_by_cost_code": self.totals_by_cost_code,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass(slots=True)
class CostEstimateReport:
    schema_version: str
    engine_version: str
    project_id: str
    quantity_report_fingerprint_sha256: str
    ratebook_fingerprint_sha256: str
    ratebook_id: str
    ratebook_version: str
    ratebook_status: str
    currency: str
    price_date: str
    jurisdiction: str
    location_profile: str
    scenarios: list[ScenarioEstimate] = field(default_factory=list)
    issues: list[CostIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "quantity_report_fingerprint_sha256": self.quantity_report_fingerprint_sha256,
            "ratebook_fingerprint_sha256": self.ratebook_fingerprint_sha256,
            "ratebook_id": self.ratebook_id,
            "ratebook_version": self.ratebook_version,
            "ratebook_status": self.ratebook_status,
            "currency": self.currency,
            "price_date": self.price_date,
            "jurisdiction": self.jurisdiction,
            "location_profile": self.location_profile,
            "scenario_count": len(self.scenarios),
            "issue_count": len(self.issues),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
