"""Phoenix Engineering Kernel Loads Wave 1.

Implements the first 30 load-domain functions.

The module provides deterministic load records, load transformations and
generic combination mechanics. Code-specific coefficients remain external and
must be supplied by higher standards layers.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence


class LoadError(ValueError):
    """Raised when load data or a load calculation is invalid."""


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise LoadError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise LoadError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise LoadError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class Load:
    name: str
    category: str
    magnitude: float
    direction: tuple[float, float, float]
    metadata: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise LoadError("name cannot be empty.")
        if not self.category.strip():
            raise LoadError("category cannot be empty.")
        _finite(self.magnitude, "magnitude")
        if len(self.direction) != 3:
            raise LoadError("direction must contain exactly three values.")
        dx, dy, dz = (_finite(v, "direction") for v in self.direction)
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length == 0.0:
            raise LoadError("direction cannot be the zero vector.")


@dataclass(frozen=True)
class LoadCombinationTerm:
    load: Load
    factor: float

    def __post_init__(self) -> None:
        _finite(self.factor, "factor")


def normalize_direction(direction: Sequence[float]) -> tuple[float, float, float]:
    if len(direction) != 3:
        raise LoadError("direction must contain exactly three values.")
    values = tuple(_finite(value, "direction") for value in direction)
    length = math.sqrt(sum(value * value for value in values))
    if length == 0.0:
        raise LoadError("direction cannot be the zero vector.")
    return tuple(value / length for value in values)


def create_load(
    name: str,
    category: str,
    magnitude: float,
    direction: Sequence[float],
    metadata: Mapping[str, str] | None = None,
) -> Load:
    return Load(
        name=name,
        category=category,
        magnitude=_finite(magnitude, "magnitude"),
        direction=normalize_direction(direction),
        metadata=metadata,
    )


def dead_load(name: str, magnitude: float, direction: Sequence[float] = (0, 0, -1)) -> Load:
    return create_load(name, "dead", magnitude, direction)


def imposed_load(name: str, magnitude: float, direction: Sequence[float] = (0, 0, -1)) -> Load:
    return create_load(name, "imposed", magnitude, direction)


def wind_load(name: str, magnitude: float, direction: Sequence[float]) -> Load:
    return create_load(name, "wind", magnitude, direction)


def snow_load(name: str, magnitude: float, direction: Sequence[float] = (0, 0, -1)) -> Load:
    return create_load(name, "snow", magnitude, direction)


def seismic_load(name: str, magnitude: float, direction: Sequence[float]) -> Load:
    return create_load(name, "seismic", magnitude, direction)


def thermal_load(name: str, magnitude: float, direction: Sequence[float]) -> Load:
    return create_load(name, "thermal", magnitude, direction)


def hydrostatic_pressure(fluid_density: float, gravity: float, depth: float) -> float:
    return (
        _positive(fluid_density, "fluid_density")
        * _positive(gravity, "gravity")
        * _positive(depth, "depth", allow_zero=True)
    )


def earth_pressure_unit_weight(unit_weight: float, depth: float, coefficient: float) -> float:
    return (
        _positive(unit_weight, "unit_weight")
        * _positive(depth, "depth", allow_zero=True)
        * _positive(coefficient, "coefficient", allow_zero=True)
    )


def uniform_line_load(area_load: float, tributary_width: float) -> float:
    return _finite(area_load, "area_load") * _positive(tributary_width, "tributary_width")


def uniform_area_load(total_load: float, area: float) -> float:
    return _finite(total_load, "total_load") / _positive(area, "area")


def point_load_from_pressure(pressure: float, area: float) -> float:
    return _finite(pressure, "pressure") * _positive(area, "area")


def resultant_of_uniform_line_load(load_per_length: float, length: float) -> float:
    return _finite(load_per_length, "load_per_length") * _positive(length, "length")


def resultant_of_uniform_area_load(load_per_area: float, area: float) -> float:
    return _finite(load_per_area, "load_per_area") * _positive(area, "area")


def triangular_line_load_resultant(max_load: float, length: float) -> float:
    return 0.5 * _finite(max_load, "max_load") * _positive(length, "length")


def triangular_line_load_position(length: float) -> float:
    return (2.0 / 3.0) * _positive(length, "length")


def trapezoidal_line_load_resultant(start_load: float, end_load: float, length: float) -> float:
    return 0.5 * (_finite(start_load, "start_load") + _finite(end_load, "end_load")) * _positive(length, "length")


def moment_from_force(force: float, lever_arm: float) -> float:
    return _finite(force, "force") * _finite(lever_arm, "lever_arm")


def load_component(load: Load, axis: int) -> float:
    if axis not in (0, 1, 2):
        raise LoadError("axis must be 0, 1 or 2.")
    return load.magnitude * load.direction[axis]


def load_vector(load: Load) -> tuple[float, float, float]:
    return tuple(load.magnitude * component for component in load.direction)


def scale_load(load: Load, factor: float, name: str | None = None) -> Load:
    multiplier = _finite(factor, "factor")
    return Load(
        name=name or load.name,
        category=load.category,
        magnitude=load.magnitude * multiplier,
        direction=load.direction,
        metadata=load.metadata,
    )


def sum_load_vectors(loads: Iterable[Load]) -> tuple[float, float, float]:
    data = tuple(loads)
    if not data:
        raise LoadError("At least one load is required.")
    vectors = [load_vector(load) for load in data]
    return tuple(math.fsum(vector[i] for vector in vectors) for i in range(3))


def resultant_load(loads: Iterable[Load], name: str = "resultant") -> Load:
    vector = sum_load_vectors(loads)
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude == 0.0:
        raise LoadError("Resultant load is zero and has no unique direction.")
    return create_load(name, "resultant", magnitude, vector)


def combination_value(terms: Iterable[LoadCombinationTerm]) -> float:
    data = tuple(terms)
    if not data:
        raise LoadError("At least one combination term is required.")
    return math.fsum(term.load.magnitude * term.factor for term in data)


def combination_vector(terms: Iterable[LoadCombinationTerm]) -> tuple[float, float, float]:
    data = tuple(terms)
    if not data:
        raise LoadError("At least one combination term is required.")
    return tuple(
        math.fsum(term.factor * load_vector(term.load)[axis] for term in data)
        for axis in range(3)
    )


def characteristic_combination(loads: Iterable[Load]) -> float:
    data = tuple(loads)
    if not data:
        raise LoadError("At least one load is required.")
    return math.fsum(load.magnitude for load in data)


def design_combination(loads: Iterable[Load], factors: Sequence[float]) -> float:
    data = tuple(loads)
    if len(data) != len(factors):
        raise LoadError("loads and factors must have equal length.")
    if not data:
        raise LoadError("At least one load is required.")
    return math.fsum(load.magnitude * _finite(factor, "factor") for load, factor in zip(data, factors))


def accidental_combination(
    permanent_loads: Iterable[Load],
    variable_loads: Iterable[Load],
    accidental_load: Load,
    variable_factors: Sequence[float],
) -> float:
    permanent = tuple(permanent_loads)
    variable = tuple(variable_loads)
    if len(variable) != len(variable_factors):
        raise LoadError("variable_loads and variable_factors must have equal length.")
    return (
        math.fsum(load.magnitude for load in permanent)
        + accidental_load.magnitude
        + math.fsum(load.magnitude * _finite(factor, "variable_factor")
                    for load, factor in zip(variable, variable_factors))
    )


def dynamic_amplification(static_value: float, amplification_factor: float) -> float:
    return _finite(static_value, "static_value") * _positive(amplification_factor, "amplification_factor")


def tributary_load(area_load: float, tributary_area: float) -> float:
    return _finite(area_load, "area_load") * _positive(tributary_area, "tributary_area")


def validate_load(load: Load) -> bool:
    Load(**load.__dict__)
    return True
