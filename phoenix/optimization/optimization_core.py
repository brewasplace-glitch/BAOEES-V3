"""Deterministic multi-objective optimization core for Project Phoenix.

Wave 15.1 provides a dependency-free optimization kernel:
- hard-constraint evaluation;
- objective normalization;
- Pareto dominance analysis;
- deterministic weighted ranking;
- sensitivity scenarios;
- SHA-256 evidence generation.

The engine evaluates supplied variants. Domain-specific variant generation and
material design are intentionally delegated to later Wave 15 increments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ENGINE_ID = "phoenix.optimization_core.wave15_1"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"


class OptimizationError(ValueError):
    """Raised when optimization input or configuration is invalid."""


@dataclass(frozen=True)
class Objective:
    """Definition of one optimization objective."""

    name: str
    direction: str = "minimize"
    weight: float = 1.0
    lower_bound: float | None = None
    upper_bound: float | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise OptimizationError("Objective name must not be empty.")
        if self.direction not in {"minimize", "maximize"}:
            raise OptimizationError(
                f"Objective {self.name!r} direction must be minimize or maximize."
            )
        if not math.isfinite(self.weight) or self.weight < 0:
            raise OptimizationError(
                f"Objective {self.name!r} weight must be finite and non-negative."
            )
        if self.lower_bound is not None and not math.isfinite(self.lower_bound):
            raise OptimizationError(f"Objective {self.name!r} lower_bound is invalid.")
        if self.upper_bound is not None and not math.isfinite(self.upper_bound):
            raise OptimizationError(f"Objective {self.name!r} upper_bound is invalid.")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise OptimizationError(
                f"Objective {self.name!r} lower_bound exceeds upper_bound."
            )


@dataclass(frozen=True)
class Constraint:
    """Hard constraint evaluated against a variant metric."""

    name: str
    metric: str
    operator: str
    limit: float
    tolerance: float = 1e-9

    def validate(self) -> None:
        if not self.name.strip() or not self.metric.strip():
            raise OptimizationError("Constraint name and metric must not be empty.")
        if self.operator not in {"<=", ">=", "=="}:
            raise OptimizationError(
                f"Constraint {self.name!r} operator must be <=, >= or ==."
            )
        if not math.isfinite(self.limit) or not math.isfinite(self.tolerance):
            raise OptimizationError(f"Constraint {self.name!r} contains non-finite data.")
        if self.tolerance < 0:
            raise OptimizationError(
                f"Constraint {self.name!r} tolerance must be non-negative."
            )


@dataclass(frozen=True)
class Variant:
    """One design variant and its already-computed engineering metrics."""

    variant_id: str
    metrics: Mapping[str, float]
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.variant_id.strip():
            raise OptimizationError("variant_id must not be empty.")
        if not self.metrics:
            raise OptimizationError(
                f"Variant {self.variant_id!r} must contain at least one metric."
            )
        for key, value in self.metrics.items():
            if not str(key).strip():
                raise OptimizationError(
                    f"Variant {self.variant_id!r} contains an empty metric name."
                )
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise OptimizationError(
                    f"Variant {self.variant_id!r} metric {key!r} must be numeric."
                )
            if not math.isfinite(float(value)):
                raise OptimizationError(
                    f"Variant {self.variant_id!r} metric {key!r} must be finite."
                )


@dataclass(frozen=True)
class OptimizationConfig:
    """Runtime behavior for deterministic ranking and evidence output."""

    project_id: str
    objectives: Sequence[Objective]
    constraints: Sequence[Constraint] = field(default_factory=tuple)
    sensitivity_delta: float = 0.10
    rounding_digits: int = 9

    def validate(self) -> None:
        if not self.project_id.strip():
            raise OptimizationError("project_id must not be empty.")
        if not self.objectives:
            raise OptimizationError("At least one objective is required.")
        names: set[str] = set()
        for objective in self.objectives:
            objective.validate()
            if objective.name in names:
                raise OptimizationError(
                    f"Duplicate objective name: {objective.name!r}."
                )
            names.add(objective.name)
        for constraint in self.constraints:
            constraint.validate()
        if not math.isfinite(self.sensitivity_delta):
            raise OptimizationError("sensitivity_delta must be finite.")
        if not 0 <= self.sensitivity_delta < 1:
            raise OptimizationError(
                "sensitivity_delta must be greater than or equal to 0 and less than 1."
            )
        if not 0 <= self.rounding_digits <= 15:
            raise OptimizationError("rounding_digits must be between 0 and 15.")


class OptimizationCore:
    """Dependency-free deterministic multi-objective optimization kernel."""

    def __init__(self, config: OptimizationConfig):
        config.validate()
        self.config = config

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    def _constraint_passes(self, constraint: Constraint, value: float) -> bool:
        if constraint.operator == "<=":
            return value <= constraint.limit + constraint.tolerance
        if constraint.operator == ">=":
            return value >= constraint.limit - constraint.tolerance
        return abs(value - constraint.limit) <= constraint.tolerance

    def _evaluate_constraints(self, variant: Variant) -> dict[str, Any]:
        evaluations: list[dict[str, Any]] = []
        feasible = True
        for constraint in self.config.constraints:
            if constraint.metric not in variant.metrics:
                passed = False
                actual = None
                reason = "metric_missing"
            else:
                actual = float(variant.metrics[constraint.metric])
                passed = self._constraint_passes(constraint, actual)
                reason = "passed" if passed else "limit_exceeded"
            feasible = feasible and passed
            evaluations.append(
                {
                    "name": constraint.name,
                    "metric": constraint.metric,
                    "operator": constraint.operator,
                    "limit": constraint.limit,
                    "actual": actual,
                    "passed": passed,
                    "reason": reason,
                }
            )
        return {"feasible": feasible, "evaluations": evaluations}

    def _objective_ranges(
        self, feasible_variants: Sequence[Variant]
    ) -> dict[str, tuple[float, float]]:
        ranges: dict[str, tuple[float, float]] = {}
        for objective in self.config.objectives:
            values = [float(v.metrics[objective.name]) for v in feasible_variants]
            lower = (
                objective.lower_bound
                if objective.lower_bound is not None
                else min(values)
            )
            upper = (
                objective.upper_bound
                if objective.upper_bound is not None
                else max(values)
            )
            if lower > upper:
                raise OptimizationError(
                    f"Objective {objective.name!r} normalization range is invalid."
                )
            ranges[objective.name] = (float(lower), float(upper))
        return ranges

    def _normalize(
        self,
        objective: Objective,
        value: float,
        lower: float,
        upper: float,
    ) -> float:
        if upper == lower:
            return 1.0
        clipped = min(max(value, lower), upper)
        if objective.direction == "minimize":
            score = (upper - clipped) / (upper - lower)
        else:
            score = (clipped - lower) / (upper - lower)
        return round(score, self.config.rounding_digits)

    def _dominates(self, left: Variant, right: Variant) -> bool:
        no_worse = True
        strictly_better = False
        for objective in self.config.objectives:
            lv = float(left.metrics[objective.name])
            rv = float(right.metrics[objective.name])
            if objective.direction == "minimize":
                no_worse = no_worse and lv <= rv
                strictly_better = strictly_better or lv < rv
            else:
                no_worse = no_worse and lv >= rv
                strictly_better = strictly_better or lv > rv
        return no_worse and strictly_better

    def _rank(
        self,
        feasible_variants: Sequence[Variant],
        ranges: Mapping[str, tuple[float, float]],
        weights: Mapping[str, float],
    ) -> list[dict[str, Any]]:
        total_weight = sum(weights.values())
        if total_weight <= 0:
            raise OptimizationError("Total objective weight must be greater than zero.")

        rows: list[dict[str, Any]] = []
        for variant in feasible_variants:
            normalized: dict[str, float] = {}
            weighted_score = 0.0
            for objective in self.config.objectives:
                lower, upper = ranges[objective.name]
                value = float(variant.metrics[objective.name])
                score = self._normalize(objective, value, lower, upper)
                normalized[objective.name] = score
                weighted_score += score * weights[objective.name]
            rows.append(
                {
                    "variant_id": variant.variant_id,
                    "score": round(
                        weighted_score / total_weight,
                        self.config.rounding_digits,
                    ),
                    "normalized_objectives": normalized,
                }
            )

        rows.sort(key=lambda row: (-row["score"], row["variant_id"]))
        for index, row in enumerate(rows, start=1):
            row["rank"] = index
        return rows

    def _sensitivity(
        self,
        feasible_variants: Sequence[Variant],
        ranges: Mapping[str, tuple[float, float]],
    ) -> list[dict[str, Any]]:
        baseline = {o.name: float(o.weight) for o in self.config.objectives}
        scenarios: list[dict[str, Any]] = []
        for focus in self.config.objectives:
            weights = dict(baseline)
            weights[focus.name] *= 1.0 + self.config.sensitivity_delta
            ranking = self._rank(feasible_variants, ranges, weights)
            scenarios.append(
                {
                    "focus_objective": focus.name,
                    "weight_multiplier": round(
                        1.0 + self.config.sensitivity_delta,
                        self.config.rounding_digits,
                    ),
                    "winner": ranking[0]["variant_id"],
                    "ranking": [
                        {
                            "variant_id": row["variant_id"],
                            "rank": row["rank"],
                            "score": row["score"],
                        }
                        for row in ranking
                    ],
                }
            )
        return scenarios

    def evaluate(self, variants: Iterable[Variant]) -> dict[str, Any]:
        ordered = sorted(list(variants), key=lambda item: item.variant_id)
        if not ordered:
            raise OptimizationError("At least one variant is required.")

        ids: set[str] = set()
        constraint_results: dict[str, Any] = {}
        for variant in ordered:
            variant.validate()
            if variant.variant_id in ids:
                raise OptimizationError(
                    f"Duplicate variant_id: {variant.variant_id!r}."
                )
            ids.add(variant.variant_id)
            for objective in self.config.objectives:
                if objective.name not in variant.metrics:
                    raise OptimizationError(
                        f"Variant {variant.variant_id!r} is missing objective metric "
                        f"{objective.name!r}."
                    )
            constraint_results[variant.variant_id] = self._evaluate_constraints(
                variant
            )

        feasible = [
            variant
            for variant in ordered
            if constraint_results[variant.variant_id]["feasible"]
        ]
        rejected = [
            variant.variant_id
            for variant in ordered
            if not constraint_results[variant.variant_id]["feasible"]
        ]
        if not feasible:
            raise OptimizationError("No feasible variants remain after constraints.")

        pareto_ids: list[str] = []
        dominance: dict[str, dict[str, list[str]]] = {}
        for candidate in feasible:
            dominates: list[str] = []
            dominated_by: list[str] = []
            for other in feasible:
                if candidate.variant_id == other.variant_id:
                    continue
                if self._dominates(candidate, other):
                    dominates.append(other.variant_id)
                if self._dominates(other, candidate):
                    dominated_by.append(other.variant_id)
            dominates.sort()
            dominated_by.sort()
            dominance[candidate.variant_id] = {
                "dominates": dominates,
                "dominated_by": dominated_by,
            }
            if not dominated_by:
                pareto_ids.append(candidate.variant_id)

        pareto_ids.sort()
        ranges = self._objective_ranges(feasible)
        weights = {o.name: float(o.weight) for o in self.config.objectives}
        ranking = self._rank(feasible, ranges, weights)
        sensitivity = self._sensitivity(feasible, ranges)

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
            "project_id": self.config.project_id,
            "status": "optimization_complete",
            "objectives": [asdict(item) for item in self.config.objectives],
            "constraints": [asdict(item) for item in self.config.constraints],
            "variant_count": len(ordered),
            "feasible_variant_ids": [item.variant_id for item in feasible],
            "rejected_variant_ids": rejected,
            "constraint_results": constraint_results,
            "normalization_ranges": {
                key: {"lower": value[0], "upper": value[1]}
                for key, value in sorted(ranges.items())
            },
            "dominance": dominance,
            "pareto_front": pareto_ids,
            "ranking": ranking,
            "recommended_variant_id": ranking[0]["variant_id"],
            "sensitivity_analysis": sensitivity,
            "limitations": [
                "Wave 15.1 evaluates supplied engineering metrics only.",
                "Domain-specific structural variant generation is outside this release.",
                "Cost and carbon source datasets are outside this release.",
                "Results are generated for engineering review and are not approval evidence.",
            ],
        }
        payload["evidence"] = {
            "algorithm": "sha256",
            "payload_sha256": self._digest(payload),
        }
        return payload

    def write_result(
        self,
        variants: Iterable[Variant],
        destination: str | Path,
    ) -> Path:
        result = self.evaluate(variants)
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination_path.with_suffix(destination_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination_path)
        return destination_path
