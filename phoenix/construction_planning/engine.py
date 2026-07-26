"""BB24 WBS derivation, CPM scheduling, resources, cashflow and scenarios."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from .calendar import WorkdayCalendar
from .models import (
    ActivityDefinition,
    ActivitySchedule,
    PlanningIssue,
    PlanningReport,
    PlanningScenario,
    ScenarioResult,
)


_DEFAULT_PRODUCTIVITY: dict[str, dict[str, float]] = {
    "01 Site and earthworks": {"m3": 60.0, "m2": 250.0, "ea": 20.0, "m": 150.0},
    "02 Foundations": {"m3": 12.0, "m2": 50.0, "kg": 1200.0, "ea": 8.0, "m": 35.0},
    "03 Structural frame": {"m3": 10.0, "kg": 1500.0, "ea": 12.0, "m": 45.0, "m2": 80.0},
    "04 Walls and partitions": {"m2": 45.0, "m3": 12.0, "ea": 20.0, "m": 60.0},
    "05 Floors and slabs": {"m2": 120.0, "m3": 18.0, "kg": 1800.0, "ea": 20.0},
    "06 Roofs": {"m2": 100.0, "m3": 15.0, "kg": 1500.0, "ea": 20.0},
    "07 Doors": {"ea": 10.0, "m2": 25.0},
    "08 Windows": {"ea": 12.0, "m2": 35.0},
    "09 Stairs": {"ea": 2.0, "m2": 20.0, "m3": 5.0},
    "10 Building services": {"ea": 25.0, "m": 150.0, "m2": 200.0},
    "99 General": {"ea": 10.0, "m": 50.0, "m2": 50.0, "m3": 10.0, "kg": 1000.0},
}

_DEFAULT_RESOURCES: dict[str, dict[str, float]] = {
    "01 Site and earthworks": {"site_crew": 5.0, "excavator": 1.0},
    "02 Foundations": {"concrete_crew": 6.0, "carpentry_crew": 4.0},
    "03 Structural frame": {"structural_crew": 6.0, "crane": 1.0},
    "04 Walls and partitions": {"masonry_crew": 5.0},
    "05 Floors and slabs": {"concrete_crew": 7.0},
    "06 Roofs": {"roofing_crew": 5.0},
    "07 Doors": {"carpentry_crew": 3.0},
    "08 Windows": {"facade_crew": 3.0},
    "09 Stairs": {"structural_crew": 4.0},
    "10 Building services": {"services_crew": 6.0},
    "99 General": {"general_crew": 4.0},
}


class ConstructionPlanningEngine:
    """Create deterministic construction schedules and scenario comparisons."""

    SCHEMA_VERSION = "phoenix.construction-planning-report/1.0"
    VERSION = "1.0.0"

    def create_plan(
        self,
        project_metadata: Mapping[str, Any] | Any,
        *,
        activities: Sequence[Mapping[str, Any] | ActivityDefinition] | None = None,
        quantity_report: Mapping[str, Any] | Any | None = None,
        cost_report: Mapping[str, Any] | Any | None = None,
        coordination_report: Mapping[str, Any] | Any | None = None,
        project_start_date: str | date = "2026-01-05",
        holidays: Sequence[str | date] = (),
        scenarios: Sequence[Mapping[str, Any] | PlanningScenario] | None = None,
    ) -> PlanningReport:
        metadata = self._normalise(project_metadata, "project_metadata")
        quantity = self._optional_normalise(quantity_report, "quantity_report")
        cost = self._optional_normalise(cost_report, "cost_report")
        coordination = self._optional_normalise(
            coordination_report,
            "coordination_report",
        )

        start = self._parse_date(project_start_date)
        calendar = WorkdayCalendar(
            {self._parse_date(item) for item in holidays}
        )
        start = calendar.normalize_start(start)

        project_id = str(
            metadata.get("project_id")
            or (quantity or {}).get("project_id")
            or (cost or {}).get("project_id")
            or "PHX-UNSPECIFIED"
        ).strip()
        project_name = str(
            metadata.get("project_name")
            or metadata.get("name")
            or project_id
        ).strip()
        currency = str(
            (cost or {}).get("currency")
            or metadata.get("currency")
            or "USD"
        ).strip().upper()

        issues: list[PlanningIssue] = []
        self._check_project_identity(
            project_id,
            {
                "quantity_report": quantity,
                "cost_report": cost,
                "coordination_report": coordination,
            },
            issues,
        )
        self._check_coordination_gate(coordination, issues)

        if activities is None:
            definitions = self.derive_activities(
                quantity or {},
                cost_report=cost,
            )
        else:
            definitions = [
                self._activity_from_value(item)
                for item in activities
            ]

        definitions = self._validate_activities(definitions, issues)
        scenario_definitions = self._normalise_scenarios(scenarios)

        scenario_results: list[ScenarioResult] = []
        if not any(issue.blocking for issue in issues):
            for scenario in scenario_definitions:
                scaled = self._scale_activities(definitions, scenario)
                scenario_results.append(
                    self._schedule_scenario(
                        scaled,
                        scenario,
                        start,
                        calendar,
                    )
                )

        fingerprints: dict[str, str] = {
            "project_metadata": self._fingerprint(metadata),
            "activities": self._fingerprint(
                [item.to_dict() for item in definitions]
            ),
        }
        if quantity is not None:
            fingerprints["quantity_report"] = self._fingerprint(quantity)
        if cost is not None:
            fingerprints["cost_report"] = self._fingerprint(cost)
        if coordination is not None:
            fingerprints["coordination_report"] = self._fingerprint(
                coordination
            )

        return PlanningReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            project_name=project_name,
            project_start_date=start.isoformat(),
            currency=currency,
            baseline_scenario_id="BASELINE",
            scenarios=scenario_results,
            issues=issues,
            source_fingerprints_sha256=fingerprints,
            metadata={
                "calendar": "Monday-Friday",
                "holiday_count": len(calendar.holidays),
                "dependency_type": "finish-to-start",
                "non_certifying_schedule": True,
                "bb23_documentation_link": True,
            },
        )

    def derive_activities(
        self,
        quantity_report: Mapping[str, Any] | Any,
        *,
        cost_report: Mapping[str, Any] | Any | None = None,
    ) -> list[ActivityDefinition]:
        quantity = self._normalise(
            quantity_report,
            "quantity_report",
        )
        cost = self._optional_normalise(cost_report, "cost_report")
        records = self._records(
            quantity,
            ("records", "quantities", "items"),
        )
        cost_by_quantity = self._cost_by_quantity(cost or {})

        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for record in records:
            work_section = str(
                record.get("work_section")
                or self._work_section_from_category(
                    str(record.get("category") or "generic")
                )
            )
            groups[work_section].append(record)

        if not groups:
            raise ValueError(
                "No usable BB20 quantity records were supplied to derive activities."
            )

        activities: list[ActivityDefinition] = []
        previous_id: str | None = None
        for index, work_section in enumerate(sorted(groups), start=1):
            group = groups[work_section]
            duration = self._derived_duration(work_section, group)
            activity_id = f"ACT-{index:03d}"
            quantity_ids = tuple(
                sorted(
                    {
                        str(item.get("quantity_id"))
                        for item in group
                        if item.get("quantity_id")
                    }
                )
            )
            source_object_ids = tuple(
                sorted(
                    {
                        str(item.get("source_object_id"))
                        for item in group
                        if item.get("source_object_id")
                    }
                )
            )
            direct_cost = round(
                sum(cost_by_quantity.get(item, 0.0) for item in quantity_ids),
                2,
            )
            wbs_prefix = work_section.split(" ", 1)[0]
            predecessor_ids = (previous_id,) if previous_id else ()
            activities.append(
                ActivityDefinition(
                    activity_id=activity_id,
                    name=work_section,
                    wbs_code=f"{wbs_prefix}.1",
                    discipline=self._discipline(work_section),
                    duration_workdays=duration,
                    predecessor_ids=predecessor_ids,
                    source_object_ids=source_object_ids,
                    quantity_ids=quantity_ids,
                    resource_requirements=dict(
                        _DEFAULT_RESOURCES.get(
                            work_section,
                            _DEFAULT_RESOURCES["99 General"],
                        )
                    ),
                    direct_cost=direct_cost,
                    metadata={
                        "derived_from_bb20": True,
                        "quantity_record_count": len(group),
                    },
                )
            )
            previous_id = activity_id

        completion_id = f"ACT-{len(activities) + 1:03d}"
        activities.append(
            ActivityDefinition(
                activity_id=completion_id,
                name="Construction completion milestone",
                wbs_code="90.1",
                discipline="project_controls",
                duration_workdays=0,
                predecessor_ids=(previous_id,) if previous_id else (),
                milestone=True,
                metadata={"derived_milestone": True},
            )
        )
        return activities

    def fingerprint_report(self, report: PlanningReport) -> str:
        return self._fingerprint(report.to_dict())

    @staticmethod
    def _normalise(value: Mapping[str, Any] | Any, label: str) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            if not isinstance(result, Mapping):
                raise TypeError(f"{label}.to_dict() must return a mapping.")
            return dict(result)
        raise TypeError(f"{label} must be a mapping or expose to_dict().")

    def _optional_normalise(
        self,
        value: Mapping[str, Any] | Any | None,
        label: str,
    ) -> dict[str, Any] | None:
        return None if value is None else self._normalise(value, label)

    @staticmethod
    def _parse_date(value: str | date) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _records(
        data: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> list[Mapping[str, Any]]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [
                    item for item in value if isinstance(item, Mapping)
                ]
        return []

    def _activity_from_value(
        self,
        value: Mapping[str, Any] | ActivityDefinition,
    ) -> ActivityDefinition:
        if isinstance(value, ActivityDefinition):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("Activity must be a mapping or ActivityDefinition.")

        milestone = bool(value.get("milestone", False))
        raw_duration = value.get("duration_workdays", 0 if milestone else None)
        if raw_duration is None:
            raise ValueError("Activity duration_workdays is required.")

        return ActivityDefinition(
            activity_id=str(value.get("activity_id") or "").strip(),
            name=str(value.get("name") or "").strip(),
            wbs_code=str(value.get("wbs_code") or "").strip(),
            discipline=str(value.get("discipline") or "general").strip(),
            duration_workdays=int(raw_duration),
            predecessor_ids=tuple(
                str(item)
                for item in value.get("predecessor_ids", ())
                if str(item).strip()
            ),
            lag_workdays=int(value.get("lag_workdays", 0)),
            milestone=milestone,
            source_object_ids=tuple(
                str(item)
                for item in value.get("source_object_ids", ())
                if str(item).strip()
            ),
            quantity_ids=tuple(
                str(item)
                for item in value.get("quantity_ids", ())
                if str(item).strip()
            ),
            resource_requirements={
                str(key): float(amount)
                for key, amount in dict(
                    value.get("resource_requirements", {})
                ).items()
            },
            direct_cost=float(value.get("direct_cost", 0.0)),
            metadata=dict(value.get("metadata", {})),
        )

    def _validate_activities(
        self,
        activities: list[ActivityDefinition],
        issues: list[PlanningIssue],
    ) -> list[ActivityDefinition]:
        if not activities:
            issues.append(
                PlanningIssue(
                    code="PLAN-ACT-001",
                    severity="error",
                    message="No planning activities were supplied.",
                    blocking=True,
                )
            )
            return []

        by_id: dict[str, ActivityDefinition] = {}
        for activity in activities:
            if not activity.activity_id:
                issues.append(
                    PlanningIssue(
                        code="PLAN-ID-001",
                        severity="error",
                        message="Activity has no stable activity_id.",
                        blocking=True,
                    )
                )
                continue
            if activity.activity_id in by_id:
                issues.append(
                    PlanningIssue(
                        code="PLAN-ID-002",
                        severity="error",
                        message=f"Duplicate activity ID: {activity.activity_id}.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
                continue
            if not activity.name:
                issues.append(
                    PlanningIssue(
                        code="PLAN-NAME-001",
                        severity="error",
                        message="Activity has no name.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if activity.duration_workdays < 0:
                issues.append(
                    PlanningIssue(
                        code="PLAN-DUR-001",
                        severity="error",
                        message="Activity duration must not be negative.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if activity.milestone and activity.duration_workdays != 0:
                issues.append(
                    PlanningIssue(
                        code="PLAN-DUR-002",
                        severity="error",
                        message="Milestones must have zero duration.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if not activity.milestone and activity.duration_workdays == 0:
                issues.append(
                    PlanningIssue(
                        code="PLAN-DUR-003",
                        severity="error",
                        message="Non-milestone activities require positive duration.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if activity.lag_workdays < 0:
                issues.append(
                    PlanningIssue(
                        code="PLAN-LAG-001",
                        severity="error",
                        message="Negative dependency lag is not supported in BB24 v1.0.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if activity.direct_cost < 0:
                issues.append(
                    PlanningIssue(
                        code="PLAN-COST-001",
                        severity="error",
                        message="Activity direct cost must not be negative.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            if any(amount < 0 for amount in activity.resource_requirements.values()):
                issues.append(
                    PlanningIssue(
                        code="PLAN-RES-001",
                        severity="error",
                        message="Resource requirements must not be negative.",
                        activity_id=activity.activity_id,
                        blocking=True,
                    )
                )
            by_id[activity.activity_id] = activity

        known = set(by_id)
        for activity in by_id.values():
            for predecessor in activity.predecessor_ids:
                if predecessor not in known:
                    issues.append(
                        PlanningIssue(
                            code="PLAN-DEP-001",
                            severity="error",
                            message=(
                                f"Unknown predecessor {predecessor} for "
                                f"{activity.activity_id}."
                            ),
                            activity_id=activity.activity_id,
                            blocking=True,
                        )
                    )
                if predecessor == activity.activity_id:
                    issues.append(
                        PlanningIssue(
                            code="PLAN-DEP-002",
                            severity="error",
                            message="Activity cannot depend on itself.",
                            activity_id=activity.activity_id,
                            blocking=True,
                        )
                    )

        if not any(issue.blocking for issue in issues):
            try:
                self._topological_order(list(by_id.values()))
            except ValueError as exc:
                issues.append(
                    PlanningIssue(
                        code="PLAN-DEP-003",
                        severity="error",
                        message=str(exc),
                        blocking=True,
                    )
                )

        return [by_id[key] for key in sorted(by_id)]

    @staticmethod
    def _normalise_scenarios(
        scenarios: Sequence[Mapping[str, Any] | PlanningScenario] | None,
    ) -> list[PlanningScenario]:
        if scenarios is None:
            return [
                PlanningScenario(
                    scenario_id="BASELINE",
                    name="Baseline",
                    duration_factor=1.0,
                    cost_factor=1.0,
                ),
                PlanningScenario(
                    scenario_id="ACCELERATED",
                    name="Accelerated",
                    duration_factor=0.85,
                    cost_factor=1.08,
                ),
                PlanningScenario(
                    scenario_id="DELAYED",
                    name="Delayed",
                    duration_factor=1.20,
                    cost_factor=1.03,
                ),
            ]

        result: list[PlanningScenario] = []
        seen: set[str] = set()
        for item in scenarios:
            if isinstance(item, PlanningScenario):
                scenario = item
            elif isinstance(item, Mapping):
                scenario = PlanningScenario(
                    scenario_id=str(item.get("scenario_id") or "").strip().upper(),
                    name=str(item.get("name") or "").strip(),
                    duration_factor=float(item.get("duration_factor", 1.0)),
                    cost_factor=float(item.get("cost_factor", 1.0)),
                    metadata=dict(item.get("metadata", {})),
                )
            else:
                raise TypeError(
                    "Scenario must be a mapping or PlanningScenario."
                )
            if not scenario.scenario_id:
                raise ValueError("Scenario ID is required.")
            if scenario.scenario_id in seen:
                raise ValueError(
                    f"Duplicate scenario ID: {scenario.scenario_id}."
                )
            if scenario.duration_factor <= 0 or scenario.cost_factor <= 0:
                raise ValueError("Scenario factors must be greater than zero.")
            seen.add(scenario.scenario_id)
            result.append(scenario)

        if "BASELINE" not in seen:
            result.insert(
                0,
                PlanningScenario(
                    scenario_id="BASELINE",
                    name="Baseline",
                ),
            )
        return result

    @staticmethod
    def _scale_activities(
        activities: list[ActivityDefinition],
        scenario: PlanningScenario,
    ) -> list[ActivityDefinition]:
        scaled: list[ActivityDefinition] = []
        for activity in activities:
            if activity.milestone:
                duration = 0
            else:
                duration = max(
                    1,
                    int(math.ceil(
                        activity.duration_workdays
                        * scenario.duration_factor
                    )),
                )
            scaled.append(
                ActivityDefinition(
                    activity_id=activity.activity_id,
                    name=activity.name,
                    wbs_code=activity.wbs_code,
                    discipline=activity.discipline,
                    duration_workdays=duration,
                    predecessor_ids=activity.predecessor_ids,
                    lag_workdays=activity.lag_workdays,
                    milestone=activity.milestone,
                    source_object_ids=activity.source_object_ids,
                    quantity_ids=activity.quantity_ids,
                    resource_requirements=dict(
                        activity.resource_requirements
                    ),
                    direct_cost=round(
                        activity.direct_cost * scenario.cost_factor,
                        2,
                    ),
                    metadata={
                        **activity.metadata,
                        "scenario_id": scenario.scenario_id,
                    },
                )
            )
        return scaled

    def _schedule_scenario(
        self,
        activities: list[ActivityDefinition],
        scenario: PlanningScenario,
        project_start: date,
        calendar: WorkdayCalendar,
    ) -> ScenarioResult:
        order = self._topological_order(activities)
        by_id = {item.activity_id: item for item in activities}
        successors: dict[str, list[str]] = defaultdict(list)
        for activity in activities:
            for predecessor in activity.predecessor_ids:
                successors[predecessor].append(activity.activity_id)

        early_start: dict[str, int] = {}
        early_finish: dict[str, int] = {}
        for activity_id in order:
            activity = by_id[activity_id]
            constraint = 0
            for predecessor in activity.predecessor_ids:
                constraint = max(
                    constraint,
                    early_finish[predecessor] + activity.lag_workdays,
                )
            early_start[activity_id] = constraint
            early_finish[activity_id] = (
                constraint + activity.duration_workdays
            )

        project_duration = max(early_finish.values(), default=0)
        late_finish: dict[str, int] = {}
        late_start: dict[str, int] = {}
        for activity_id in reversed(order):
            activity = by_id[activity_id]
            next_ids = successors.get(activity_id, [])
            if not next_ids:
                finish = project_duration
            else:
                finish = min(
                    late_start[next_id] - by_id[next_id].lag_workdays
                    for next_id in next_ids
                )
            late_finish[activity_id] = finish
            late_start[activity_id] = finish - activity.duration_workdays

        scheduled: list[ActivitySchedule] = []
        for activity_id in order:
            activity = by_id[activity_id]
            es = early_start[activity_id]
            ef = early_finish[activity_id]
            ls = late_start[activity_id]
            lf = late_finish[activity_id]
            total_float = ls - es
            start_date = calendar.add_workdays(project_start, es)
            if activity.duration_workdays == 0:
                finish_date = start_date
            else:
                finish_date = calendar.add_workdays(
                    project_start,
                    ef - 1,
                )
            scheduled.append(
                ActivitySchedule(
                    activity_id=activity.activity_id,
                    name=activity.name,
                    wbs_code=activity.wbs_code,
                    discipline=activity.discipline,
                    predecessor_ids=activity.predecessor_ids,
                    duration_workdays=activity.duration_workdays,
                    early_start_day=es,
                    early_finish_day=ef,
                    late_start_day=ls,
                    late_finish_day=lf,
                    total_float_workdays=total_float,
                    critical=(total_float == 0),
                    milestone=activity.milestone,
                    start_date=start_date.isoformat(),
                    finish_date=finish_date.isoformat(),
                    source_object_ids=activity.source_object_ids,
                    quantity_ids=activity.quantity_ids,
                    resource_requirements=dict(
                        activity.resource_requirements
                    ),
                    direct_cost=activity.direct_cost,
                    metadata=dict(activity.metadata),
                )
            )

        resource_summary = self._resource_summary(scheduled)
        cashflow = self._cashflow(
            scheduled,
            project_start,
            calendar,
        )
        finish_date = calendar.add_workdays(
            project_start,
            max(project_duration - 1, 0),
        )

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            duration_factor=scenario.duration_factor,
            cost_factor=scenario.cost_factor,
            project_duration_workdays=project_duration,
            project_finish_date=finish_date.isoformat(),
            total_direct_cost=round(
                sum(item.direct_cost for item in scheduled),
                2,
            ),
            critical_path=[
                item.activity_id
                for item in scheduled
                if item.critical
            ],
            activities=scheduled,
            resource_summary=resource_summary,
            cashflow_by_month=cashflow,
        )

    @staticmethod
    def _topological_order(
        activities: list[ActivityDefinition],
    ) -> list[str]:
        by_id = {item.activity_id: item for item in activities}
        indegree = {
            item.activity_id: len(item.predecessor_ids)
            for item in activities
        }
        successors: dict[str, list[str]] = defaultdict(list)
        for item in activities:
            for predecessor in item.predecessor_ids:
                successors[predecessor].append(item.activity_id)

        ready = deque(sorted(
            key for key, degree in indegree.items() if degree == 0
        ))
        result: list[str] = []
        while ready:
            current = ready.popleft()
            result.append(current)
            for successor in sorted(successors.get(current, [])):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)

        if len(result) != len(by_id):
            raise ValueError("Activity dependency graph contains a cycle.")
        return result

    @staticmethod
    def _resource_summary(
        activities: list[ActivitySchedule],
    ) -> dict[str, dict[str, float]]:
        daily: dict[str, dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        totals: dict[str, float] = defaultdict(float)
        for activity in activities:
            for resource, amount in activity.resource_requirements.items():
                totals[resource] += amount * activity.duration_workdays
                for day in range(
                    activity.early_start_day,
                    activity.early_finish_day,
                ):
                    daily[resource][day] += amount

        return {
            resource: {
                "total_resource_days": round(totals[resource], 3),
                "peak_concurrent": round(
                    max(daily[resource].values(), default=0.0),
                    3,
                ),
            }
            for resource in sorted(totals)
        }

    @staticmethod
    def _cashflow(
        activities: list[ActivitySchedule],
        project_start: date,
        calendar: WorkdayCalendar,
    ) -> list[dict[str, Any]]:
        monthly: dict[str, float] = defaultdict(float)
        for activity in activities:
            if activity.direct_cost == 0:
                continue
            if activity.duration_workdays == 0:
                value_date = calendar.add_workdays(
                    project_start,
                    activity.early_start_day,
                )
                monthly[value_date.strftime("%Y-%m")] += (
                    activity.direct_cost
                )
                continue

            daily_cost = activity.direct_cost / activity.duration_workdays
            for day in range(
                activity.early_start_day,
                activity.early_finish_day,
            ):
                value_date = calendar.add_workdays(project_start, day)
                monthly[value_date.strftime("%Y-%m")] += daily_cost

        cumulative = 0.0
        result: list[dict[str, Any]] = []
        for month in sorted(monthly):
            amount = round(monthly[month], 2)
            cumulative = round(cumulative + amount, 2)
            result.append(
                {
                    "month": month,
                    "period_cost": amount,
                    "cumulative_cost": cumulative,
                }
            )
        return result

    @staticmethod
    def _cost_by_quantity(
        cost_report: Mapping[str, Any],
    ) -> dict[str, float]:
        items = []
        for key in ("items", "cost_items", "records", "lines"):
            value = cost_report.get(key)
            if isinstance(value, list):
                items = value
                break
        result: dict[str, float] = defaultdict(float)
        for item in items:
            if not isinstance(item, Mapping):
                continue
            quantity_id = str(item.get("quantity_id") or "").strip()
            if not quantity_id:
                continue
            value = None
            for key in ("total_cost", "line_total", "amount"):
                candidate = item.get(key)
                if (
                    isinstance(candidate, (int, float))
                    and not isinstance(candidate, bool)
                ):
                    value = float(candidate)
                    break
            if value is not None:
                result[quantity_id] += value
        return dict(result)

    @staticmethod
    def _derived_duration(
        work_section: str,
        records: list[Mapping[str, Any]],
    ) -> int:
        rules = _DEFAULT_PRODUCTIVITY.get(
            work_section,
            _DEFAULT_PRODUCTIVITY["99 General"],
        )
        workload = 0.0
        counted = False
        for record in records:
            unit = str(record.get("unit") or "").strip()
            value = record.get("value")
            if (
                not unit
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or float(value) <= 0
            ):
                continue
            productivity = rules.get(unit)
            if productivity is None:
                productivity = _DEFAULT_PRODUCTIVITY[
                    "99 General"
                ].get(unit)
            if productivity:
                workload += float(value) / productivity
                counted = True
        return max(1, int(math.ceil(workload))) if counted else 1

    @staticmethod
    def _work_section_from_category(category: str) -> str:
        value = category.strip().lower()
        mapping = {
            "site": "01 Site and earthworks",
            "foundation": "02 Foundations",
            "column": "03 Structural frame",
            "beam": "03 Structural frame",
            "wall": "04 Walls and partitions",
            "slab": "05 Floors and slabs",
            "roof": "06 Roofs",
            "door": "07 Doors",
            "window": "08 Windows",
            "stair": "09 Stairs",
            "mep": "10 Building services",
        }
        return mapping.get(value, "99 General")

    @staticmethod
    def _discipline(work_section: str) -> str:
        if work_section.startswith(("01", "02", "03", "05", "09")):
            return "construction"
        if work_section.startswith(("04", "06", "07", "08")):
            return "architecture"
        if work_section.startswith("10"):
            return "building_services"
        return "general"

    @staticmethod
    def _check_project_identity(
        project_id: str,
        sources: Mapping[str, Mapping[str, Any] | None],
        issues: list[PlanningIssue],
    ) -> None:
        for source_name, source in sources.items():
            if not source or not source.get("project_id"):
                continue
            source_project_id = str(source["project_id"]).strip()
            if source_project_id == project_id:
                continue
            issues.append(
                PlanningIssue(
                    code="PLAN-PROJECT-001",
                    severity="critical",
                    message=(
                        f"{source_name} belongs to {source_project_id}, "
                        f"not {project_id}."
                    ),
                    source=source_name,
                    blocking=True,
                )
            )

    @staticmethod
    def _check_coordination_gate(
        coordination: Mapping[str, Any] | None,
        issues: list[PlanningIssue],
    ) -> None:
        if coordination is None:
            return
        if coordination.get("coordination_passed") is False:
            issues.append(
                PlanningIssue(
                    code="PLAN-COORD-001",
                    severity="error",
                    message=(
                        "BB22 coordination has not passed; planning is blocked."
                    ),
                    source="coordination_report",
                    blocking=True,
                )
            )

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
