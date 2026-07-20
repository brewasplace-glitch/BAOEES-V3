"""Phoenix Engineering Kernel Mathematics Wave 1.

Implements PEK-MATH-0001 through PEK-MATH-0025.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


class MathematicsError(ValueError):
    """Raised when a mathematical operation receives invalid input."""


def _finite(value: float, name: str = "value") -> float:
    number = float(value)
    if not math.isfinite(number):
        raise MathematicsError(f"{name} must be finite.")
    return number


def _finite_sequence(values: Iterable[float], name: str = "values") -> tuple[float, ...]:
    result = tuple(_finite(value, name) for value in values)
    if not result:
        raise MathematicsError(f"{name} cannot be empty.")
    return result


def add(a: float, b: float) -> float:
    return _finite(a, "a") + _finite(b, "b")


def subtract(a: float, b: float) -> float:
    return _finite(a, "a") - _finite(b, "b")


def multiply(a: float, b: float) -> float:
    return _finite(a, "a") * _finite(b, "b")


def divide(a: float, b: float) -> float:
    denominator = _finite(b, "b")
    if denominator == 0.0:
        raise MathematicsError("Division by zero.")
    return _finite(a, "a") / denominator


def power(base: float, exponent: float) -> float:
    base_value = _finite(base, "base")
    exponent_value = _finite(exponent, "exponent")
    try:
        result = math.pow(base_value, exponent_value)
    except ValueError as exc:
        raise MathematicsError("Invalid real-valued power operation.") from exc
    return _finite(result, "result")


def square_root(value: float) -> float:
    number = _finite(value)
    if number < 0.0:
        raise MathematicsError("Square root requires a non-negative value.")
    return math.sqrt(number)


def absolute(value: float) -> float:
    return abs(_finite(value))


def minimum(values: Iterable[float]) -> float:
    return min(_finite_sequence(values))


def maximum(values: Iterable[float]) -> float:
    return max(_finite_sequence(values))


def clamp(value: float, lower: float, upper: float) -> float:
    number = _finite(value)
    low = _finite(lower, "lower")
    high = _finite(upper, "upper")
    if low > high:
        raise MathematicsError("lower cannot exceed upper.")
    return min(max(number, low), high)


def arithmetic_mean(values: Iterable[float]) -> float:
    data = _finite_sequence(values)
    return math.fsum(data) / len(data)


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    data = _finite_sequence(values)
    weight_data = _finite_sequence(weights, "weights")
    if len(data) != len(weight_data):
        raise MathematicsError("values and weights must have equal length.")
    if any(weight < 0.0 for weight in weight_data):
        raise MathematicsError("weights cannot be negative.")
    total_weight = math.fsum(weight_data)
    if total_weight == 0.0:
        raise MathematicsError("sum of weights must be greater than zero.")
    return math.fsum(value * weight for value, weight in zip(data, weight_data)) / total_weight


def percentage(part: float, whole: float) -> float:
    denominator = _finite(whole, "whole")
    if denominator == 0.0:
        raise MathematicsError("whole cannot be zero.")
    return 100.0 * _finite(part, "part") / denominator


def percentage_change(original: float, new: float) -> float:
    base = _finite(original, "original")
    if base == 0.0:
        raise MathematicsError("original cannot be zero.")
    return 100.0 * (_finite(new, "new") - base) / abs(base)


def apply_factor(value: float, factor: float) -> float:
    factor_value = _finite(factor, "factor")
    if factor_value < 0.0:
        raise MathematicsError("factor cannot be negative.")
    return _finite(value) * factor_value


def margin(value: float, limit: float) -> float:
    return _finite(limit, "limit") - _finite(value)


def utilization(value: float, capacity: float) -> float:
    capacity_value = _finite(capacity, "capacity")
    if capacity_value <= 0.0:
        raise MathematicsError("capacity must be greater than zero.")
    return _finite(value) / capacity_value


def is_close(a: float, b: float, relative_tolerance: float = 1e-9, absolute_tolerance: float = 0.0) -> bool:
    rel = _finite(relative_tolerance, "relative_tolerance")
    abs_tol = _finite(absolute_tolerance, "absolute_tolerance")
    if rel < 0.0 or abs_tol < 0.0:
        raise MathematicsError("tolerances cannot be negative.")
    return math.isclose(_finite(a, "a"), _finite(b, "b"), rel_tol=rel, abs_tol=abs_tol)


def round_to_decimals(value: float, decimals: int) -> float:
    if not isinstance(decimals, int):
        raise MathematicsError("decimals must be an integer.")
    return round(_finite(value), decimals)


def round_to_increment(value: float, increment: float) -> float:
    step = _finite(increment, "increment")
    if step <= 0.0:
        raise MathematicsError("increment must be greater than zero.")
    return round(_finite(value) / step) * step


def normalize(value: float, lower: float, upper: float) -> float:
    low = _finite(lower, "lower")
    high = _finite(upper, "upper")
    if high <= low:
        raise MathematicsError("upper must be greater than lower.")
    return (_finite(value) - low) / (high - low)


def linear_interpolate(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    x0_value = _finite(x0, "x0")
    x1_value = _finite(x1, "x1")
    if x1_value == x0_value:
        raise MathematicsError("x0 and x1 cannot be equal.")
    ratio = (_finite(x) - x0_value) / (x1_value - x0_value)
    return _finite(y0, "y0") + ratio * (_finite(y1, "y1") - _finite(y0, "y0"))


def dot_product(a: Sequence[float], b: Sequence[float]) -> float:
    left = _finite_sequence(a, "a")
    right = _finite_sequence(b, "b")
    if len(left) != len(right):
        raise MathematicsError("vectors must have equal length.")
    return math.fsum(x * y for x, y in zip(left, right))


def vector_magnitude(vector: Sequence[float]) -> float:
    values = _finite_sequence(vector, "vector")
    return math.sqrt(math.fsum(value * value for value in values))


def vector_normalize(vector: Sequence[float]) -> tuple[float, ...]:
    values = _finite_sequence(vector, "vector")
    magnitude = vector_magnitude(values)
    if magnitude == 0.0:
        raise MathematicsError("zero vector cannot be normalized.")
    return tuple(value / magnitude for value in values)
