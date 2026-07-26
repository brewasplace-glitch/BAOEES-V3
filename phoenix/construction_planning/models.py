"""Canonical BB24 activity, scenario and schedule contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PlanningIssue:
    code: str
    severity: str
    message: str
    activity_id: str | None = None
    source: str | None = None
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivityDefinition:
    activity_id: str
    name: str
    wbs_code: str
    discipline: str
    duration_workdays: int
    predecessor_ids: tuple[str, ...] = ()
    lag_workdays: int = 0
    milestone: bool = False
    source_object_ids: tuple[str, ...] = ()
    quantity_ids: tuple[str, ...] = ()
    resource_requirements: dict[str, float] = field(default_factory=dict)
    direct_cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["predecessor_ids"] = list(self.predecessor_ids)
        data["source_object_ids"] = list(self.source_object_ids)
        data["quantity_ids"] = list(self.quantity_ids)
        return data


@dataclass(frozen=True, slots=True)
class ActivitySchedule:
    activity_id: str
    name: str
    wbs_code: str
    discipline: str
    predecessor_ids: tuple[str, ...]
    duration_workdays: int
    early_start_day: int
    early_finish_day: int
    late_start_day: int
    late_finish_day: int
    total_float_workdays: int
    critical: bool
    milestone: bool
    start_date: str
    finish_date: str
    source_object_ids: tuple[str, ...]
    quantity_ids: tuple[str, ...]
    resource_requirements: dict[str, float]
    direct_cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["predecessor_ids"] = list(self.predecessor_ids)
        data["source_object_ids"] = list(self.source_object_ids)
        data["quantity_ids"] = list(self.quantity_ids)
        return data


@dataclass(frozen=True, slots=True)
class PlanningScenario:
    scenario_id: str
    name: str
    duration_factor: float = 1.0
    cost_factor: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScenarioResult:
    scenario_id: str
    name: str
    duration_factor: float
    cost_factor: float
    project_duration_workdays: int
    project_finish_date: str
    total_direct_cost: float
    critical_path: list[str] = field(default_factory=list)
    activities: list[ActivitySchedule] = field(default_factory=list)
    resource_summary: dict[str, dict[str, float]] = field(default_factory=dict)
    cashflow_by_month: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "duration_factor": self.duration_factor,
            "cost_factor": self.cost_factor,
            "project_duration_workdays": self.project_duration_workdays,
            "project_finish_date": self.project_finish_date,
            "total_direct_cost": round(self.total_direct_cost, 2),
            "critical_path": list(self.critical_path),
            "activities": [item.to_dict() for item in self.activities],
            "resource_summary": {
                key: dict(value)
                for key, value in sorted(self.resource_summary.items())
            },
            "cashflow_by_month": list(self.cashflow_by_month),
        }


@dataclass(slots=True)
class PlanningReport:
    schema_version: str
    engine_version: str
    project_id: str
    project_name: str
    project_start_date: str
    currency: str
    baseline_scenario_id: str
    scenarios: list[ScenarioResult] = field(default_factory=list)
    issues: list[PlanningIssue] = field(default_factory=list)
    source_fingerprints_sha256: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def blocking_issue_count(self) -> int:
        return sum(1 for issue in self.issues if issue.blocking)

    @property
    def planning_passed(self) -> bool:
        return self.blocking_issue_count == 0

    @property
    def baseline(self) -> ScenarioResult:
        for scenario in self.scenarios:
            if scenario.scenario_id == self.baseline_scenario_id:
                return scenario
        raise KeyError(f"Baseline scenario not found: {self.baseline_scenario_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_start_date": self.project_start_date,
            "currency": self.currency,
            "planning_passed": self.planning_passed,
            "blocking_issue_count": self.blocking_issue_count,
            "baseline_scenario_id": self.baseline_scenario_id,
            "scenario_count": len(self.scenarios),
            "activity_count": (
                len(self.baseline.activities) if self.scenarios else 0
            ),
            "source_fingerprints_sha256": dict(
                sorted(self.source_fingerprints_sha256.items())
            ),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": dict(self.metadata),
        }
