"""Canonical BB25 procurement, bid and award contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProcurementIssue:
    code: str
    severity: str
    message: str
    source: str | None = None
    package_id: str | None = None
    bid_id: str | None = None
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TenderLine:
    line_id: str
    package_id: str
    quantity_id: str
    description: str
    work_section: str
    quantity: float
    unit: str
    benchmark_unit_rate: float
    benchmark_total: float
    source_object_ids: tuple[str, ...] = ()
    required_by_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_object_ids"] = list(self.source_object_ids)
        return data


@dataclass(frozen=True, slots=True)
class ProcurementPackage:
    package_id: str
    title: str
    work_section: str
    scope: str
    currency: str
    benchmark_budget: float
    planned_start_date: str | None
    planned_finish_date: str | None
    tender_line_ids: tuple[str, ...]
    qualification_requirements: tuple[str, ...] = ()
    status: str = "for_tender"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tender_line_ids"] = list(self.tender_line_ids)
        data["qualification_requirements"] = list(self.qualification_requirements)
        return data


@dataclass(frozen=True, slots=True)
class SupplierRecord:
    supplier_id: str
    supplier_name: str
    contact_name: str = ""
    email: str = ""
    country: str = ""
    approved: bool = False
    categories: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["categories"] = list(self.categories)
        return data


@dataclass(frozen=True, slots=True)
class SupplierBid:
    bid_id: str
    package_id: str
    supplier_id: str
    supplier_name: str
    currency: str
    submitted_date: str
    validity_days: int
    delivery_workdays: int
    line_items: tuple[dict[str, Any], ...]
    exclusions: tuple[str, ...] = ()
    qualifications: tuple[str, ...] = ()
    payment_terms: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["line_items"] = list(self.line_items)
        data["exclusions"] = list(self.exclusions)
        data["qualifications"] = list(self.qualifications)
        return data


@dataclass(frozen=True, slots=True)
class BidEvaluation:
    bid_id: str
    package_id: str
    supplier_id: str
    supplier_name: str
    currency: str
    offered_total: float
    missing_line_allowance: float
    evaluated_total: float
    included_line_count: int
    expected_line_count: int
    missing_line_ids: tuple[str, ...]
    extra_line_ids: tuple[str, ...]
    exclusions: tuple[str, ...]
    completeness_score: float
    price_score: float
    delivery_score: float
    responsive: bool
    deviation_count: int
    delivery_workdays: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["missing_line_ids"] = list(self.missing_line_ids)
        data["extra_line_ids"] = list(self.extra_line_ids)
        data["exclusions"] = list(self.exclusions)
        return data


@dataclass(frozen=True, slots=True)
class AwardRecommendation:
    recommendation_id: str
    package_id: str
    scenario_id: str
    scenario_name: str
    recommended_bid_id: str | None
    recommended_supplier_id: str | None
    recommended_supplier_name: str | None
    evaluated_total: float | None
    weighted_score: float | None
    rationale: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProcurementReport:
    schema_version: str
    engine_version: str
    project_id: str
    project_name: str
    currency: str
    packages: list[ProcurementPackage] = field(default_factory=list)
    tender_lines: list[TenderLine] = field(default_factory=list)
    suppliers: list[SupplierRecord] = field(default_factory=list)
    bids: list[SupplierBid] = field(default_factory=list)
    evaluations: list[BidEvaluation] = field(default_factory=list)
    recommendations: list[AwardRecommendation] = field(default_factory=list)
    issues: list[ProcurementIssue] = field(default_factory=list)
    source_fingerprints_sha256: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def blocking_issue_count(self) -> int:
        return sum(1 for issue in self.issues if issue.blocking)

    @property
    def procurement_passed(self) -> bool:
        return self.blocking_issue_count == 0

    @property
    def benchmark_budget_total(self) -> float:
        return round(sum(item.benchmark_budget for item in self.packages), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "currency": self.currency,
            "procurement_passed": self.procurement_passed,
            "blocking_issue_count": self.blocking_issue_count,
            "benchmark_budget_total": self.benchmark_budget_total,
            "package_count": len(self.packages),
            "tender_line_count": len(self.tender_lines),
            "supplier_count": len(self.suppliers),
            "bid_count": len(self.bids),
            "evaluation_count": len(self.evaluations),
            "recommendation_count": len(self.recommendations),
            "source_fingerprints_sha256": dict(sorted(self.source_fingerprints_sha256.items())),
            "packages": [item.to_dict() for item in self.packages],
            "tender_lines": [item.to_dict() for item in self.tender_lines],
            "suppliers": [item.to_dict() for item in self.suppliers],
            "bids": [item.to_dict() for item in self.bids],
            "evaluations": [item.to_dict() for item in self.evaluations],
            "recommendations": [item.to_dict() for item in self.recommendations],
            "issues": [item.to_dict() for item in self.issues],
            "metadata": dict(self.metadata),
        }
