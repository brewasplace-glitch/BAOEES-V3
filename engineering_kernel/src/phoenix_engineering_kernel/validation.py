"""Phoenix Engineering Kernel Validation Wave 1.

Implements the first 30 validation-domain functions.

The module provides deterministic validation primitives, issue collection,
engineering plausibility checks, tolerance checks, dependency checks and a
structured validation report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Mapping, Sequence


class ValidationError(ValueError):
    """Raised when a validation function itself receives invalid arguments."""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "ERROR"
    field: str | None = None
    value: Any = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValidationError("issue code cannot be empty.")
        if not self.message.strip():
            raise ValidationError("issue message cannot be empty.")
        severity = self.severity.upper()
        if severity not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValidationError(f"Unsupported severity: {self.severity}")


@dataclass
class ValidationReport:
    name: str
    issues: list[ValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(issue.severity.upper() in {"ERROR", "CRITICAL"} for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(issue.severity.upper() in {"ERROR", "CRITICAL"} for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity.upper() == "WARNING" for issue in self.issues)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)


def _finite_number(value: Any, name: str = "value") -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be numeric, not boolean.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{name} must be finite.")
    return number


def validate_type(value: Any, expected_type: type | tuple[type, ...]) -> bool:
    return isinstance(value, expected_type)


def validate_required(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (Sequence, Mapping, set, frozenset)):
        return len(value) > 0
    return True


def validate_not_nan(value: Any) -> bool:
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def validate_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_range(
    value: float,
    minimum: float | None = None,
    maximum: float | None = None,
    *,
    inclusive: bool = True,
) -> bool:
    number = _finite_number(value)
    lower = _finite_number(minimum, "minimum") if minimum is not None else None
    upper = _finite_number(maximum, "maximum") if maximum is not None else None

    if lower is not None and upper is not None and lower > upper:
        raise ValidationError("minimum cannot exceed maximum.")

    if lower is not None:
        if number < lower or (not inclusive and number == lower):
            return False
    if upper is not None:
        if number > upper or (not inclusive and number == upper):
            return False
    return True


def validate_positive(value: float, *, allow_zero: bool = False) -> bool:
    number = _finite_number(value)
    return number >= 0.0 if allow_zero else number > 0.0


def validate_non_negative(value: float) -> bool:
    return validate_positive(value, allow_zero=True)


def validate_choice(value: Any, allowed: Iterable[Any]) -> bool:
    return value in tuple(allowed)


def validate_length(
    value: Sequence[Any] | Mapping[Any, Any] | str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> bool:
    size = len(value)
    if minimum is not None and size < minimum:
        return False
    if maximum is not None and size > maximum:
        return False
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValidationError("minimum length cannot exceed maximum length.")
    return True


def validate_dimensions(actual: Sequence[int], expected: Sequence[int]) -> bool:
    return tuple(actual) == tuple(expected)


def validate_units(unit: str, allowed_units: Iterable[str]) -> bool:
    normalized = unit.strip().lower()
    return normalized in {candidate.strip().lower() for candidate in allowed_units}


def validate_consistency(values: Iterable[Any]) -> bool:
    data = tuple(values)
    if not data:
        return True
    first = data[0]
    return all(value == first for value in data[1:])


def validate_monotonic(values: Sequence[float], *, strictly: bool = False) -> bool:
    numbers = tuple(_finite_number(value) for value in values)
    comparator = (lambda a, b: a < b) if strictly else (lambda a, b: a <= b)
    return all(comparator(a, b) for a, b in zip(numbers, numbers[1:]))


def validate_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    tol = _finite_number(tolerance, "tolerance")
    if tol < 0.0:
        raise ValidationError("tolerance cannot be negative.")
    return abs(_finite_number(actual, "actual") - _finite_number(expected, "expected")) <= tol


def validate_relative_tolerance(
    actual: float,
    expected: float,
    relative_tolerance: float,
    absolute_tolerance: float = 0.0,
) -> bool:
    rel = _finite_number(relative_tolerance, "relative_tolerance")
    abs_tol = _finite_number(absolute_tolerance, "absolute_tolerance")
    if rel < 0.0 or abs_tol < 0.0:
        raise ValidationError("tolerances cannot be negative.")
    return math.isclose(
        _finite_number(actual, "actual"),
        _finite_number(expected, "expected"),
        rel_tol=rel,
        abs_tol=abs_tol,
    )


def validate_rounding(value: float, decimals: int) -> bool:
    if decimals < 0:
        raise ValidationError("decimals cannot be negative.")
    number = _finite_number(value)
    return number == round(number, decimals)


def validate_convergence(
    previous: float,
    current: float,
    tolerance: float,
    *,
    relative: bool = False,
) -> bool:
    if relative:
        return validate_relative_tolerance(current, previous, tolerance)
    return validate_tolerance(current, previous, tolerance)


def validate_factor_of_safety(
    capacity: float,
    demand: float,
    minimum_factor: float = 1.0,
) -> bool:
    cap = _finite_number(capacity, "capacity")
    dem = _finite_number(demand, "demand")
    minimum = _finite_number(minimum_factor, "minimum_factor")
    if cap < 0.0 or dem <= 0.0 or minimum <= 0.0:
        raise ValidationError("capacity must be non-negative; demand and minimum_factor must be positive.")
    return cap / dem >= minimum


def validate_utilization(utilization: float, limit: float = 1.0) -> bool:
    ratio = _finite_number(utilization, "utilization")
    maximum = _finite_number(limit, "limit")
    if ratio < 0.0 or maximum <= 0.0:
        raise ValidationError("utilization must be non-negative and limit must be positive.")
    return ratio <= maximum


def validate_material_property(
    value: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> bool:
    return validate_range(value, minimum, maximum)


def validate_geometry_non_degenerate(measure: float, tolerance: float = 1e-12) -> bool:
    tol = _finite_number(tolerance, "tolerance")
    if tol < 0.0:
        raise ValidationError("tolerance cannot be negative.")
    return abs(_finite_number(measure, "measure")) > tol


def validate_load_magnitude(magnitude: float, *, allow_negative: bool = True) -> bool:
    number = _finite_number(magnitude, "magnitude")
    return True if allow_negative else number >= 0.0


def validate_dependency_set(required: Iterable[str], available: Iterable[str]) -> bool:
    return set(required).issubset(set(available))


def validate_traceability(
    function_ids: Iterable[str],
    linked_function_ids: Iterable[str],
) -> bool:
    required = {value for value in function_ids if value}
    linked = {value for value in linked_function_ids if value}
    return required.issubset(linked)


def validate_registry_unique_ids(records: Iterable[Mapping[str, Any]]) -> bool:
    identifiers = [record.get("id") for record in records]
    return None not in identifiers and len(identifiers) == len(set(identifiers))


def classify_issue(severity: str) -> str:
    normalized = severity.strip().upper()
    aliases = {
        "WARN": "WARNING",
        "ERR": "ERROR",
        "FATAL": "CRITICAL",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValidationError(f"Unsupported severity: {severity}")
    return normalized


def create_issue(
    code: str,
    message: str,
    severity: str = "ERROR",
    field: str | None = None,
    value: Any = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        severity=classify_issue(severity),
        field=field,
        value=value,
    )


def create_validation_report(
    name: str,
    issues: Iterable[ValidationIssue] = (),
    metadata: Mapping[str, Any] | None = None,
) -> ValidationReport:
    if not name.strip():
        raise ValidationError("report name cannot be empty.")
    return ValidationReport(name=name, issues=list(issues), metadata=dict(metadata or {}))


def merge_validation_reports(
    name: str,
    reports: Iterable[ValidationReport],
) -> ValidationReport:
    data = tuple(reports)
    merged = create_validation_report(name)
    for report in data:
        merged.issues.extend(report.issues)
        merged.metadata.update(report.metadata)
    merged.metadata["merged_report_count"] = len(data)
    return merged


def validation_summary(report: ValidationReport) -> dict[str, Any]:
    counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    for issue in report.issues:
        counts[classify_issue(issue.severity)] += 1
    return {
        "name": report.name,
        "passed": report.passed,
        "issue_count": len(report.issues),
        "counts": counts,
        "metadata": dict(report.metadata),
    }
