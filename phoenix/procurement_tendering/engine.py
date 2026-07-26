"""BB25 procurement packaging, bid normalization and award scenarios."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from .models import (
    AwardRecommendation,
    BidEvaluation,
    ProcurementIssue,
    ProcurementPackage,
    ProcurementReport,
    SupplierBid,
    SupplierRecord,
    TenderLine,
)


SCENARIOS = {
    "LOWEST_EVALUATED_COST": {
        "name": "Lowest evaluated cost",
        "price": 0.80,
        "completeness": 0.15,
        "delivery": 0.05,
    },
    "BALANCED": {
        "name": "Balanced award",
        "price": 0.55,
        "completeness": 0.30,
        "delivery": 0.15,
    },
    "SCHEDULE_PRIORITY": {
        "name": "Schedule priority",
        "price": 0.35,
        "completeness": 0.20,
        "delivery": 0.45,
    },
}


class ProcurementTenderingEngine:
    """Create tender packages and transparent bid evaluations."""

    SCHEMA_VERSION = "phoenix.procurement-tendering-report/1.0"
    VERSION = "1.0.0"

    def create_procurement(
        self,
        project_metadata: Mapping[str, Any] | Any,
        *,
        quantity_report: Mapping[str, Any] | Any,
        cost_report: Mapping[str, Any] | Any,
        planning_report: Mapping[str, Any] | Any,
        coordination_report: Mapping[str, Any] | Any,
        suppliers: Sequence[Mapping[str, Any] | SupplierRecord] = (),
        bids: Sequence[Mapping[str, Any] | SupplierBid] = (),
    ) -> ProcurementReport:
        metadata = self._normalise(project_metadata, "project_metadata")
        quantity = self._normalise(quantity_report, "quantity_report")
        cost = self._normalise(cost_report, "cost_report")
        planning = self._normalise(planning_report, "planning_report")
        coordination = self._normalise(coordination_report, "coordination_report")

        project_id = str(
            metadata.get("project_id")
            or quantity.get("project_id")
            or cost.get("project_id")
            or "PHX-UNSPECIFIED"
        ).strip()
        project_name = str(
            metadata.get("project_name")
            or metadata.get("name")
            or project_id
        ).strip()
        currency = str(
            metadata.get("currency")
            or cost.get("currency")
            or "USD"
        ).strip().upper()

        issues: list[ProcurementIssue] = []
        self._check_project_identity(
            project_id,
            {
                "quantity_report": quantity,
                "cost_report": cost,
                "planning_report": planning,
                "coordination_report": coordination,
            },
            issues,
        )
        self._check_currency(currency, cost, issues)
        self._check_upstream_gates(planning, coordination, issues)

        tender_lines, packages = self._derive_packages(
            project_id=project_id,
            currency=currency,
            quantity=quantity,
            cost=cost,
            planning=planning,
            issues=issues,
        )
        supplier_records = self._normalise_suppliers(suppliers, issues)
        bid_records = self._normalise_bids(bids, issues)

        evaluations: list[BidEvaluation] = []
        recommendations: list[AwardRecommendation] = []
        if not any(issue.blocking for issue in issues):
            evaluations = self._evaluate_bids(
                currency=currency,
                packages=packages,
                tender_lines=tender_lines,
                suppliers=supplier_records,
                bids=bid_records,
                issues=issues,
            )
            recommendations = self._recommend_awards(
                packages=packages,
                evaluations=evaluations,
                issues=issues,
            )

        fingerprints = {
            "project_metadata": self._fingerprint(metadata),
            "quantity_report": self._fingerprint(quantity),
            "cost_report": self._fingerprint(cost),
            "planning_report": self._fingerprint(planning),
            "coordination_report": self._fingerprint(coordination),
            "suppliers": self._fingerprint([item.to_dict() for item in supplier_records]),
            "bids": self._fingerprint([item.to_dict() for item in bid_records]),
        }
        return ProcurementReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            project_name=project_name,
            currency=currency,
            packages=packages,
            tender_lines=tender_lines,
            suppliers=supplier_records,
            bids=bid_records,
            evaluations=evaluations,
            recommendations=recommendations,
            issues=issues,
            source_fingerprints_sha256=fingerprints,
            metadata={
                "award_scenarios": list(SCENARIOS),
                "automatic_currency_conversion": False,
                "automatic_contract_award": False,
                "non_certifying_procurement": True,
                "bb23_documentation_link": True,
                "bb24_schedule_link": True,
            },
        )

    def fingerprint_report(self, report: ProcurementReport) -> str:
        return self._fingerprint(report.to_dict())

    def _derive_packages(
        self,
        *,
        project_id: str,
        currency: str,
        quantity: Mapping[str, Any],
        cost: Mapping[str, Any],
        planning: Mapping[str, Any],
        issues: list[ProcurementIssue],
    ) -> tuple[list[TenderLine], list[ProcurementPackage]]:
        records = self._records(quantity, ("records", "quantities", "items"))
        if not records:
            issues.append(ProcurementIssue(
                code="PROC-QTO-001",
                severity="error",
                message="BB20 quantity report contains no usable records.",
                source="quantity_report",
                blocking=True,
            ))
            return [], []

        cost_by_quantity = self._cost_by_quantity(cost)
        schedule_by_quantity = self._schedule_by_quantity(planning)
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for item in records:
            section = str(
                item.get("work_section")
                or self._work_section_from_category(str(item.get("category") or "generic"))
            ).strip()
            grouped[section].append(item)

        tender_lines: list[TenderLine] = []
        packages: list[ProcurementPackage] = []
        for section in sorted(grouped):
            package_id = self._stable_id("PKG", project_id, section)
            package_lines: list[TenderLine] = []
            start_dates: list[str] = []
            finish_dates: list[str] = []

            for item in sorted(
                grouped[section],
                key=lambda value: str(value.get("quantity_id") or value.get("source_object_id") or ""),
            ):
                quantity_id = str(item.get("quantity_id") or "").strip()
                value = self._number(item.get("value"))
                unit = str(item.get("unit") or "").strip()
                if not quantity_id:
                    issues.append(ProcurementIssue(
                        code="PROC-QTO-002",
                        severity="error",
                        message="Quantity record has no quantity_id.",
                        source="quantity_report",
                        package_id=package_id,
                        blocking=True,
                    ))
                    continue
                if value is None or value < 0 or not unit:
                    issues.append(ProcurementIssue(
                        code="PROC-QTO-003",
                        severity="error",
                        message=f"Quantity {quantity_id} has an invalid value or unit.",
                        source="quantity_report",
                        package_id=package_id,
                        blocking=True,
                    ))
                    continue

                benchmark_total = round(cost_by_quantity.get(quantity_id, 0.0), 2)
                benchmark_rate = round(benchmark_total / value, 4) if value > 0 else 0.0
                schedule = schedule_by_quantity.get(quantity_id, {})
                if schedule.get("start_date"):
                    start_dates.append(schedule["start_date"])
                if schedule.get("finish_date"):
                    finish_dates.append(schedule["finish_date"])
                source_ids = item.get("source_object_ids")
                if not isinstance(source_ids, list):
                    source_ids = [item.get("source_object_id")] if item.get("source_object_id") else []
                line = TenderLine(
                    line_id=self._stable_id("TL", package_id, quantity_id),
                    package_id=package_id,
                    quantity_id=quantity_id,
                    description=str(
                        item.get("description")
                        or item.get("quantity_type")
                        or item.get("category")
                        or quantity_id
                    ).replace("_", " ").title(),
                    work_section=section,
                    quantity=round(value, 6),
                    unit=unit,
                    benchmark_unit_rate=benchmark_rate,
                    benchmark_total=benchmark_total,
                    source_object_ids=tuple(sorted(str(value) for value in source_ids if value)),
                    required_by_date=schedule.get("finish_date") or None,
                )
                package_lines.append(line)
                tender_lines.append(line)

            packages.append(ProcurementPackage(
                package_id=package_id,
                title=section,
                work_section=section,
                scope=(
                    f"Provide all labor, materials, plant, coordination, submittals "
                    f"and completion obligations for {section}."
                ),
                currency=currency,
                benchmark_budget=round(sum(item.benchmark_total for item in package_lines), 2),
                planned_start_date=min(start_dates) if start_dates else None,
                planned_finish_date=max(finish_dates) if finish_dates else None,
                tender_line_ids=tuple(sorted(item.line_id for item in package_lines)),
                qualification_requirements=(
                    "Demonstrated relevant project experience",
                    "Program and resource proposal",
                    "Commercial qualifications and exclusions schedule",
                    "Quality and safety approach",
                ),
            ))

        tender_lines.sort(key=lambda item: (item.work_section, item.quantity_id))
        packages.sort(key=lambda item: item.work_section)
        return tender_lines, packages

    def _evaluate_bids(
        self,
        *,
        currency: str,
        packages: list[ProcurementPackage],
        tender_lines: list[TenderLine],
        suppliers: list[SupplierRecord],
        bids: list[SupplierBid],
        issues: list[ProcurementIssue],
    ) -> list[BidEvaluation]:
        package_by_id = {item.package_id: item for item in packages}
        line_by_id = {item.line_id: item for item in tender_lines}
        supplier_ids = {item.supplier_id for item in suppliers}
        raw: list[dict[str, Any]] = []

        for bid in bids:
            package = package_by_id.get(bid.package_id)
            if package is None:
                issues.append(ProcurementIssue(
                    code="PROC-BID-001", severity="error",
                    message=f"Bid {bid.bid_id} references unknown package {bid.package_id}.",
                    source="bids", bid_id=bid.bid_id,
                ))
                continue
            if bid.supplier_id not in supplier_ids:
                issues.append(ProcurementIssue(
                    code="PROC-BID-002", severity="error",
                    message=f"Bid {bid.bid_id} references unknown supplier {bid.supplier_id}.",
                    source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                ))

            expected = set(package.tender_line_ids)
            supplied: dict[str, float] = {}
            extra: set[str] = set()
            invalid = False
            for item in bid.line_items:
                line_id = str(item.get("line_id") or "").strip()
                if not line_id:
                    invalid = True
                    issues.append(ProcurementIssue(
                        code="PROC-BID-003", severity="error",
                        message=f"Bid {bid.bid_id} contains a line without line_id.",
                        source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                    ))
                    continue
                if line_id in supplied:
                    invalid = True
                    issues.append(ProcurementIssue(
                        code="PROC-BID-004", severity="error",
                        message=f"Bid {bid.bid_id} duplicates line {line_id}.",
                        source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                    ))
                    continue
                line = line_by_id.get(line_id)
                if line_id not in expected:
                    extra.add(line_id)
                    line = None
                total = self._bid_line_total(item, line)
                if total is None or total < 0:
                    invalid = True
                    issues.append(ProcurementIssue(
                        code="PROC-BID-005", severity="error",
                        message=f"Bid {bid.bid_id} line {line_id} has no valid price.",
                        source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                    ))
                    continue
                supplied[line_id] = round(total, 2)

            included = expected & set(supplied)
            missing = expected - included
            offered_total = round(sum(supplied.values()), 2)
            missing_allowance = round(sum(line_by_id[line_id].benchmark_total for line_id in missing), 2)
            evaluated_total = round(offered_total + missing_allowance, 2)
            completeness = (len(included) / len(expected) * 100.0) if expected else 100.0
            completeness = round(max(0.0, completeness - min(30.0, len(bid.exclusions) * 5.0)), 2)
            currency_match = bid.currency.upper() == currency
            responsive = currency_match and not invalid and len(included) > 0

            if not currency_match:
                issues.append(ProcurementIssue(
                    code="PROC-CURRENCY-002", severity="error",
                    message=(
                        f"Bid {bid.bid_id} uses {bid.currency}; project currency is "
                        f"{currency}. Automatic conversion is disabled."
                    ),
                    source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                ))
            if missing:
                issues.append(ProcurementIssue(
                    code="PROC-BID-006", severity="warning",
                    message=f"Bid {bid.bid_id} omits {len(missing)} required tender line(s).",
                    source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                ))
            if extra:
                issues.append(ProcurementIssue(
                    code="PROC-BID-007", severity="warning",
                    message=f"Bid {bid.bid_id} contains {len(extra)} extra line(s).",
                    source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                ))
            if bid.exclusions:
                issues.append(ProcurementIssue(
                    code="PROC-BID-008", severity="warning",
                    message=f"Bid {bid.bid_id} contains {len(bid.exclusions)} scope exclusion(s).",
                    source="bids", package_id=bid.package_id, bid_id=bid.bid_id,
                ))

            raw.append({
                "bid": bid,
                "offered_total": offered_total,
                "missing_allowance": missing_allowance,
                "evaluated_total": evaluated_total,
                "included": len(included),
                "expected": len(expected),
                "missing": tuple(sorted(missing)),
                "extra": tuple(sorted(extra)),
                "completeness": completeness,
                "responsive": responsive,
                "deviations": len(missing) + len(extra) + len(bid.exclusions) + (0 if currency_match else 1) + (1 if invalid else 0),
            })

        by_package: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in raw:
            by_package[row["bid"].package_id].append(row)

        evaluations: list[BidEvaluation] = []
        for package_id, rows in sorted(by_package.items()):
            eligible = [row for row in rows if row["responsive"]]
            lowest = min((row["evaluated_total"] for row in eligible if row["evaluated_total"] > 0), default=None)
            fastest = min((row["bid"].delivery_workdays for row in eligible if row["bid"].delivery_workdays > 0), default=None)
            for row in rows:
                bid = row["bid"]
                price_score = round(lowest / row["evaluated_total"] * 100.0, 2) if row["responsive"] and lowest and row["evaluated_total"] > 0 else 0.0
                delivery_score = round(fastest / bid.delivery_workdays * 100.0, 2) if row["responsive"] and fastest and bid.delivery_workdays > 0 else 0.0
                evaluations.append(BidEvaluation(
                    bid_id=bid.bid_id,
                    package_id=package_id,
                    supplier_id=bid.supplier_id,
                    supplier_name=bid.supplier_name,
                    currency=bid.currency.upper(),
                    offered_total=row["offered_total"],
                    missing_line_allowance=row["missing_allowance"],
                    evaluated_total=row["evaluated_total"],
                    included_line_count=row["included"],
                    expected_line_count=row["expected"],
                    missing_line_ids=row["missing"],
                    extra_line_ids=row["extra"],
                    exclusions=bid.exclusions,
                    completeness_score=row["completeness"],
                    price_score=price_score,
                    delivery_score=delivery_score,
                    responsive=row["responsive"],
                    deviation_count=row["deviations"],
                    delivery_workdays=bid.delivery_workdays,
                ))

        return sorted(evaluations, key=lambda item: (item.package_id, item.evaluated_total, item.bid_id))

    def _recommend_awards(
        self,
        *,
        packages: list[ProcurementPackage],
        evaluations: list[BidEvaluation],
        issues: list[ProcurementIssue],
    ) -> list[AwardRecommendation]:
        by_package: dict[str, list[BidEvaluation]] = defaultdict(list)
        for item in evaluations:
            by_package[item.package_id].append(item)
        recommendations: list[AwardRecommendation] = []

        for package in packages:
            eligible = [item for item in by_package.get(package.package_id, []) if item.responsive]
            if len(eligible) < 2:
                issues.append(ProcurementIssue(
                    code="PROC-COMPETITION-001", severity="warning",
                    message=f"Package {package.package_id} has fewer than two responsive bids.",
                    source="evaluations", package_id=package.package_id,
                ))
            for scenario_id, weights in SCENARIOS.items():
                ranked: list[tuple[float, BidEvaluation]] = []
                for item in eligible:
                    score = (
                        item.price_score * weights["price"]
                        + item.completeness_score * weights["completeness"]
                        + item.delivery_score * weights["delivery"]
                    )
                    ranked.append((round(score, 4), item))
                ranked.sort(key=lambda pair: (-pair[0], pair[1].evaluated_total, pair[1].bid_id))
                if not ranked:
                    recommendations.append(AwardRecommendation(
                        recommendation_id=self._stable_id("REC", package.package_id, scenario_id),
                        package_id=package.package_id,
                        scenario_id=scenario_id,
                        scenario_name=weights["name"],
                        recommended_bid_id=None,
                        recommended_supplier_id=None,
                        recommended_supplier_name=None,
                        evaluated_total=None,
                        weighted_score=None,
                        rationale="No responsive bid is available for recommendation.",
                        status="no_award",
                    ))
                    continue
                score, winner = ranked[0]
                recommendations.append(AwardRecommendation(
                    recommendation_id=self._stable_id("REC", package.package_id, scenario_id),
                    package_id=package.package_id,
                    scenario_id=scenario_id,
                    scenario_name=weights["name"],
                    recommended_bid_id=winner.bid_id,
                    recommended_supplier_id=winner.supplier_id,
                    recommended_supplier_name=winner.supplier_name,
                    evaluated_total=winner.evaluated_total,
                    weighted_score=round(score, 2),
                    rationale=(
                        f"Highest transparent weighted score; price {weights['price']:.0%}, "
                        f"completeness {weights['completeness']:.0%}, delivery {weights['delivery']:.0%}."
                    ),
                    status="recommended_for_review",
                ))
        return sorted(recommendations, key=lambda item: (item.package_id, item.scenario_id))

    def _normalise_suppliers(
        self,
        suppliers: Sequence[Mapping[str, Any] | SupplierRecord],
        issues: list[ProcurementIssue],
    ) -> list[SupplierRecord]:
        result: list[SupplierRecord] = []
        seen: set[str] = set()
        for raw in suppliers:
            if isinstance(raw, SupplierRecord):
                item = raw
            elif isinstance(raw, Mapping):
                item = SupplierRecord(
                    supplier_id=str(raw.get("supplier_id") or "").strip(),
                    supplier_name=str(raw.get("supplier_name") or "").strip(),
                    contact_name=str(raw.get("contact_name") or "").strip(),
                    email=str(raw.get("email") or "").strip(),
                    country=str(raw.get("country") or "").strip(),
                    approved=bool(raw.get("approved", False)),
                    categories=tuple(str(value) for value in raw.get("categories", ()) if str(value).strip()),
                )
            else:
                raise TypeError("Supplier must be a mapping or SupplierRecord.")
            if not item.supplier_id or not item.supplier_name:
                issues.append(ProcurementIssue(
                    code="PROC-SUP-001", severity="error",
                    message="Supplier ID and supplier name are required.",
                    source="suppliers", blocking=True,
                ))
                continue
            if item.supplier_id in seen:
                issues.append(ProcurementIssue(
                    code="PROC-SUP-002", severity="error",
                    message=f"Duplicate supplier ID: {item.supplier_id}.",
                    source="suppliers", blocking=True,
                ))
                continue
            seen.add(item.supplier_id)
            result.append(item)
        return sorted(result, key=lambda item: item.supplier_id)

    def _normalise_bids(
        self,
        bids: Sequence[Mapping[str, Any] | SupplierBid],
        issues: list[ProcurementIssue],
    ) -> list[SupplierBid]:
        result: list[SupplierBid] = []
        seen: set[str] = set()
        for raw in bids:
            if isinstance(raw, SupplierBid):
                item = raw
            elif isinstance(raw, Mapping):
                raw_lines = raw.get("line_items", ())
                if not isinstance(raw_lines, (list, tuple)):
                    raw_lines = ()
                item = SupplierBid(
                    bid_id=str(raw.get("bid_id") or "").strip(),
                    package_id=str(raw.get("package_id") or "").strip(),
                    supplier_id=str(raw.get("supplier_id") or "").strip(),
                    supplier_name=str(raw.get("supplier_name") or "").strip(),
                    currency=str(raw.get("currency") or "USD").strip().upper(),
                    submitted_date=str(raw.get("submitted_date") or date.today().isoformat()),
                    validity_days=int(raw.get("validity_days", 30)),
                    delivery_workdays=int(raw.get("delivery_workdays", 0)),
                    line_items=tuple(dict(value) for value in raw_lines if isinstance(value, Mapping)),
                    exclusions=tuple(str(value) for value in raw.get("exclusions", ()) if str(value).strip()),
                    qualifications=tuple(str(value) for value in raw.get("qualifications", ()) if str(value).strip()),
                    payment_terms=str(raw.get("payment_terms") or "").strip(),
                )
            else:
                raise TypeError("Bid must be a mapping or SupplierBid.")
            if not item.bid_id or not item.package_id or not item.supplier_id:
                issues.append(ProcurementIssue(
                    code="PROC-BID-009", severity="error",
                    message="Bid ID, package ID and supplier ID are required.",
                    source="bids", blocking=True,
                ))
                continue
            if item.bid_id in seen:
                issues.append(ProcurementIssue(
                    code="PROC-BID-010", severity="error",
                    message=f"Duplicate bid ID: {item.bid_id}.",
                    source="bids", bid_id=item.bid_id, blocking=True,
                ))
                continue
            if item.validity_days < 0 or item.delivery_workdays < 0:
                issues.append(ProcurementIssue(
                    code="PROC-BID-011", severity="error",
                    message=f"Bid {item.bid_id} has invalid validity or delivery.",
                    source="bids", bid_id=item.bid_id, blocking=True,
                ))
            seen.add(item.bid_id)
            result.append(item)
        return sorted(result, key=lambda item: item.bid_id)

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

    @staticmethod
    def _records(data: Mapping[str, Any], keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        return []

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        return float(value) if isinstance(value, (int, float)) else None

    @classmethod
    def _cost_by_quantity(cls, cost_report: Mapping[str, Any]) -> dict[str, float]:
        result: dict[str, float] = defaultdict(float)
        for item in cls._records(cost_report, ("items", "cost_items", "records", "lines")):
            quantity_id = str(item.get("quantity_id") or "").strip()
            if not quantity_id:
                continue
            for key in ("total_cost", "line_total", "amount"):
                value = cls._number(item.get(key))
                if value is not None:
                    result[quantity_id] += value
                    break
        return dict(result)

    @classmethod
    def _schedule_by_quantity(cls, planning_report: Mapping[str, Any]) -> dict[str, dict[str, str]]:
        scenarios = planning_report.get("scenarios")
        if not isinstance(scenarios, list):
            return {}
        baseline_id = str(planning_report.get("baseline_scenario_id") or "BASELINE")
        baseline = next(
            (
                item for item in scenarios
                if isinstance(item, Mapping) and str(item.get("scenario_id")) == baseline_id
            ),
            None,
        )
        if not isinstance(baseline, Mapping):
            return {}
        activities = baseline.get("activities")
        if not isinstance(activities, list):
            return {}
        result: dict[str, dict[str, str]] = {}
        for activity in activities:
            if not isinstance(activity, Mapping):
                continue
            quantity_ids = activity.get("quantity_ids")
            if not isinstance(quantity_ids, list):
                continue
            for quantity_id in quantity_ids:
                result[str(quantity_id)] = {
                    "start_date": str(activity.get("start_date") or ""),
                    "finish_date": str(activity.get("finish_date") or ""),
                }
        return result

    @staticmethod
    def _bid_line_total(item: Mapping[str, Any], tender_line: TenderLine | None) -> float | None:
        total = ProcurementTenderingEngine._number(item.get("total_price"))
        if total is not None:
            return total
        rate = ProcurementTenderingEngine._number(item.get("unit_rate"))
        if rate is None:
            return None
        quantity = tender_line.quantity if tender_line else ProcurementTenderingEngine._number(item.get("quantity"))
        return rate * quantity if quantity is not None else None

    @staticmethod
    def _check_project_identity(
        project_id: str,
        sources: Mapping[str, Mapping[str, Any]],
        issues: list[ProcurementIssue],
    ) -> None:
        for source_name, source in sources.items():
            source_id = source.get("project_id")
            if source_id and str(source_id).strip() != project_id:
                issues.append(ProcurementIssue(
                    code="PROC-PROJECT-001", severity="critical",
                    message=f"{source_name} belongs to {source_id}, not {project_id}.",
                    source=source_name, blocking=True,
                ))

    @staticmethod
    def _check_currency(currency: str, cost_report: Mapping[str, Any], issues: list[ProcurementIssue]) -> None:
        source_currency = str(cost_report.get("currency") or currency).strip().upper()
        if source_currency != currency:
            issues.append(ProcurementIssue(
                code="PROC-CURRENCY-001", severity="critical",
                message=(
                    f"Cost report currency {source_currency} differs from project currency "
                    f"{currency}. Automatic conversion is disabled."
                ),
                source="cost_report", blocking=True,
            ))

    @staticmethod
    def _check_upstream_gates(
        planning: Mapping[str, Any],
        coordination: Mapping[str, Any],
        issues: list[ProcurementIssue],
    ) -> None:
        if planning.get("planning_passed") is False:
            issues.append(ProcurementIssue(
                code="PROC-PLAN-001", severity="error",
                message="BB24 planning has not passed.",
                source="planning_report", blocking=True,
            ))
        if coordination.get("coordination_passed") is False:
            issues.append(ProcurementIssue(
                code="PROC-COORD-001", severity="error",
                message="BB22 coordination has not passed.",
                source="coordination_report", blocking=True,
            ))

    @staticmethod
    def _work_section_from_category(category: str) -> str:
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
        return mapping.get(category.strip().lower(), "99 General")

    @staticmethod
    def _stable_id(prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:18].upper()
        return f"{prefix}-{digest}"

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
