"""BB21 Cost Estimation Engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .models import (
    CostEstimateReport,
    CostIssue,
    CostLine,
    CostScenario,
    RateBook,
    RateBookStatus,
    RateItem,
    ScenarioEstimate,
)
from .ratebook import RateBookLoader

_CENT = Decimal("0.01")


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> float:
    return float(value.quantize(_CENT, rounding=ROUND_HALF_UP))


class CostEstimationEngine:
    """Price BB20 quantities against a validated, single-currency rate book."""

    SCHEMA_VERSION = "phoenix.cost-estimate-report/1.0"
    VERSION = "1.0.0"

    def estimate(
        self,
        quantity_report: Mapping[str, Any] | Any,
        ratebook: RateBook,
        scenarios: tuple[CostScenario, ...] | list[CostScenario],
    ) -> CostEstimateReport:
        quantity_data = self._normalise(quantity_report, "quantity_report")
        records = quantity_data.get("records")
        if not isinstance(records, list):
            raise ValueError("Quantity report must contain a records list.")
        if not scenarios:
            raise ValueError("At least one cost scenario is required.")

        loader = RateBookLoader()
        ratebook_fingerprint = loader.fingerprint(ratebook)
        quantity_fingerprint = self._fingerprint_quantity_report(quantity_data)
        project_id = str(quantity_data.get("project_id") or "PHX-UNSPECIFIED")

        scenario_ids = [scenario.id for scenario in scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("Cost scenario identifiers must be unique.")

        issues: list[CostIssue] = []
        estimates: list[ScenarioEstimate] = []
        for scenario in scenarios:
            self._validate_scenario(scenario, ratebook)
            estimates.append(
                self._estimate_scenario(records, ratebook, scenario, issues)
            )

        issues.sort(
            key=lambda item: (
                item.severity,
                item.scenario_id or "",
                item.quantity_id or "",
                item.code,
            )
        )

        return CostEstimateReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            quantity_report_fingerprint_sha256=quantity_fingerprint,
            ratebook_fingerprint_sha256=ratebook_fingerprint,
            ratebook_id=ratebook.id,
            ratebook_version=ratebook.version,
            ratebook_status=ratebook.status.value,
            currency=ratebook.currency,
            price_date=ratebook.price_date,
            jurisdiction=ratebook.jurisdiction,
            location_profile=ratebook.location_profile,
            scenarios=estimates,
            issues=issues,
            metadata={
                "currency_conversion_performed": False,
                "non_certifying_estimate": True,
                "quantity_record_count": len(records),
                "rate_item_count": len(ratebook.rates),
                "allowance_sequence": [
                    "direct",
                    "overhead",
                    "risk",
                    "contingency",
                    "profit",
                    "tax",
                ],
            },
        )

    def fingerprint_report(self, report: CostEstimateReport) -> str:
        payload = json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _estimate_scenario(
        self,
        records: list[Any],
        ratebook: RateBook,
        scenario: CostScenario,
        issues: list[CostIssue],
    ) -> ScenarioEstimate:
        estimate = ScenarioEstimate(scenario=scenario)
        direct_total = Decimal("0")

        for raw_record in records:
            if not isinstance(raw_record, Mapping):
                issues.append(
                    CostIssue(
                        code="COST-QTO-001",
                        severity="error",
                        message="Quantity record is not an object.",
                        scenario_id=scenario.id,
                    )
                )
                continue
            record = dict(raw_record)
            quantity_id = str(record.get("quantity_id") or "")
            source_object_id = str(record.get("source_object_id") or "")
            match, ambiguous = self._match_rate(record, ratebook)
            if ambiguous:
                estimate.ambiguous_quantities.append(quantity_id)
                issues.append(
                    CostIssue(
                        code="COST-RATE-AMBIGUOUS",
                        severity="error",
                        message="Multiple equally specific rates match this quantity.",
                        scenario_id=scenario.id,
                        quantity_id=quantity_id,
                        source_object_id=source_object_id,
                    )
                )
                continue
            if match is None:
                estimate.unmatched_quantities.append(quantity_id)
                issues.append(
                    CostIssue(
                        code="COST-RATE-MISSING",
                        severity="warning",
                        message="No compatible rate item was found; quantity excluded.",
                        scenario_id=scenario.id,
                        quantity_id=quantity_id,
                        source_object_id=source_object_id,
                    )
                )
                continue

            line = self._price_line(record, match, ratebook, scenario)
            estimate.lines.append(line)
            direct_total += _decimal(line.direct_cost)

        estimate.lines.sort(
            key=lambda line: (
                line.cost_code,
                line.source_level_id or "",
                line.source_object_id,
                line.quantity_id,
            )
        )
        estimate.unmatched_quantities.sort()
        estimate.ambiguous_quantities.sort()

        overhead = direct_total * _decimal(scenario.overhead_percent) / Decimal("100")
        after_overhead = direct_total + overhead
        risk = after_overhead * _decimal(scenario.risk_percent) / Decimal("100")
        after_risk = after_overhead + risk
        contingency = after_risk * _decimal(scenario.contingency_percent) / Decimal("100")
        after_contingency = after_risk + contingency
        profit = after_contingency * _decimal(scenario.profit_percent) / Decimal("100")
        pre_tax = after_contingency + profit
        tax = pre_tax * _decimal(scenario.tax_percent) / Decimal("100")
        total = pre_tax + tax

        estimate.direct_cost = _money(direct_total)
        estimate.overhead_cost = _money(overhead)
        estimate.risk_cost = _money(risk)
        estimate.contingency_cost = _money(contingency)
        estimate.profit_cost = _money(profit)
        estimate.pre_tax_cost = _money(pre_tax)
        estimate.tax_cost = _money(tax)
        estimate.total_cost = _money(total)
        return estimate

    def _price_line(
        self,
        record: Mapping[str, Any],
        rate: RateItem,
        ratebook: RateBook,
        scenario: CostScenario,
    ) -> CostLine:
        base_quantity = _decimal(record.get("value", 0))
        waste_factor = Decimal("1") + _decimal(rate.waste_percent) / Decimal("100")
        quantity_factor = _decimal(scenario.quantity_factor)
        priced_quantity = base_quantity * waste_factor * quantity_factor
        common_factor = (
            _decimal(scenario.location_factor)
            * (Decimal("1") + _decimal(scenario.escalation_percent) / Decimal("100"))
        )

        material_rate = _decimal(rate.material_rate) * common_factor * _decimal(scenario.material_factor)
        labor_rate = _decimal(rate.labor_rate) * common_factor * _decimal(scenario.labor_factor)
        equipment_rate = _decimal(rate.equipment_rate) * common_factor * _decimal(scenario.equipment_factor)
        subcontract_rate = _decimal(rate.subcontract_rate) * common_factor * _decimal(scenario.subcontract_factor)
        other_rate = _decimal(rate.other_rate) * common_factor * _decimal(scenario.other_factor)

        material_cost = priced_quantity * material_rate
        labor_cost = priced_quantity * labor_rate
        equipment_cost = priced_quantity * equipment_rate
        subcontract_cost = priced_quantity * subcontract_rate
        other_cost = priced_quantity * other_rate
        direct_cost = material_cost + labor_cost + equipment_cost + subcontract_cost + other_cost
        adjusted_unit_rate = material_rate + labor_rate + equipment_rate + subcontract_rate + other_rate

        quantity_id = str(record.get("quantity_id") or "")
        line_id = self._line_id(scenario.id, quantity_id, rate.id)
        drawing_refs = record.get("drawing_refs", [])
        if not isinstance(drawing_refs, list):
            drawing_refs = []

        return CostLine(
            line_id=line_id,
            scenario_id=scenario.id,
            quantity_id=quantity_id,
            source_object_id=str(record.get("source_object_id") or ""),
            source_model=str(record.get("source_model") or ""),
            source_level_id=(
                str(record.get("source_level_id"))
                if record.get("source_level_id") not in (None, "")
                else None
            ),
            category=str(record.get("category") or ""),
            work_section=str(record.get("work_section") or ""),
            material=(
                str(record.get("material"))
                if record.get("material") not in (None, "")
                else None
            ),
            quantity_type=str(record.get("quantity_type") or ""),
            cost_code=rate.cost_code,
            description=rate.description,
            rate_item_id=rate.id,
            base_quantity=float(base_quantity),
            waste_percent=rate.waste_percent,
            priced_quantity=float(priced_quantity.quantize(Decimal("0.000001"))),
            unit=rate.unit,
            base_unit_rate=rate.base_unit_rate,
            adjusted_unit_rate=_money(adjusted_unit_rate),
            material_cost=_money(material_cost),
            labor_cost=_money(labor_cost),
            equipment_cost=_money(equipment_cost),
            subcontract_cost=_money(subcontract_cost),
            other_cost=_money(other_cost),
            direct_cost=_money(direct_cost),
            currency=ratebook.currency,
            drawing_refs=tuple(sorted(set(str(item) for item in drawing_refs if item))),
            metadata={
                "rate_source_reference": rate.source_reference,
                "ratebook_price_date": ratebook.price_date,
                "ratebook_location_profile": ratebook.location_profile,
            },
        )

    def _match_rate(
        self,
        record: Mapping[str, Any],
        ratebook: RateBook,
    ) -> tuple[RateItem | None, bool]:
        candidates: list[tuple[int, RateItem]] = []
        explicit_cost_code = None
        metadata = record.get("metadata")
        if isinstance(metadata, Mapping):
            value = metadata.get("cost_code")
            if value not in (None, ""):
                explicit_cost_code = str(value)

        for rate in ratebook.rates:
            if str(record.get("unit") or "") != rate.unit:
                continue
            selector = rate.selector
            if selector.quantity_types and str(record.get("quantity_type") or "") not in selector.quantity_types:
                continue
            if selector.categories and str(record.get("category") or "") not in selector.categories:
                continue
            if selector.work_sections and str(record.get("work_section") or "") not in selector.work_sections:
                continue
            if selector.materials and str(record.get("material") or "") not in selector.materials:
                continue
            if selector.source_models and str(record.get("source_model") or "") not in selector.source_models:
                continue
            score = selector.specificity
            if explicit_cost_code and explicit_cost_code == rate.cost_code:
                score += 100
            candidates.append((score, rate))

        if not candidates:
            return None, False
        highest = max(score for score, _ in candidates)
        best = [rate for score, rate in candidates if score == highest]
        if len(best) != 1:
            return None, True
        return best[0], False

    @staticmethod
    def _validate_scenario(scenario: CostScenario, ratebook: RateBook) -> None:
        if scenario.currency != ratebook.currency:
            raise ValueError(
                "Scenario currency differs from the rate-book currency. "
                "BB21 v1.0 performs no currency conversion."
            )
        if scenario.require_validated_ratebook and ratebook.status not in (
            RateBookStatus.VALIDATED,
            RateBookStatus.APPROVED,
        ):
            raise ValueError(
                f"Scenario {scenario.id} requires a validated or approved rate book."
            )
        for field_name in (
            "quantity_factor",
            "location_factor",
            "material_factor",
            "labor_factor",
            "equipment_factor",
            "subcontract_factor",
            "other_factor",
        ):
            if getattr(scenario, field_name) <= 0:
                raise ValueError(f"Scenario {field_name} must be greater than zero.")
        for field_name in (
            "escalation_percent",
            "overhead_percent",
            "risk_percent",
            "contingency_percent",
            "profit_percent",
            "tax_percent",
        ):
            if getattr(scenario, field_name) < 0:
                raise ValueError(f"Scenario {field_name} must not be negative.")

    @staticmethod
    def _normalise(value: Mapping[str, Any] | Any, label: str) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            data = to_dict()
            if not isinstance(data, Mapping):
                raise TypeError(f"{label}.to_dict() must return a mapping.")
            return dict(data)
        raise TypeError(f"{label} must be a mapping or expose to_dict().")

    @staticmethod
    def _fingerprint_quantity_report(report: Mapping[str, Any]) -> str:
        payload = json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _line_id(scenario_id: str, quantity_id: str, rate_item_id: str) -> str:
        digest = hashlib.sha256(
            f"{scenario_id}|{quantity_id}|{rate_item_id}".encode("utf-8")
        ).hexdigest()[:20].upper()
        return f"COST-{digest}"
