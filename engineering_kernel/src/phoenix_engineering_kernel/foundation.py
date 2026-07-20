"""Phoenix Engineering Kernel Foundation & Geotechnical Design Wave 1.

Generic SI-based foundation design primitives. Project-specific standards,
partial factors, national annexes and soil model calibration remain external.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


class FoundationError(ValueError):
    """Raised when foundation design input is invalid."""


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise FoundationError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise FoundationError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise FoundationError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise FoundationError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class RectangularFoundation:
    width_m: float
    length_m: float
    thickness_m: float

    def __post_init__(self) -> None:
        _positive(self.width_m, "width_m")
        _positive(self.length_m, "length_m")
        _positive(self.thickness_m, "thickness_m")

    @property
    def area_m2(self) -> float:
        return self.width_m * self.length_m

    @property
    def volume_m3(self) -> float:
        return self.area_m2 * self.thickness_m


def foundation_area(width_m: float, length_m: float) -> float:
    return _positive(width_m, "width_m") * _positive(length_m, "length_m")


def foundation_volume(width_m: float, length_m: float, thickness_m: float) -> float:
    return foundation_area(width_m, length_m) * _positive(thickness_m, "thickness_m")


def foundation_self_weight(
    width_m: float,
    length_m: float,
    thickness_m: float,
    unit_weight_kn_m3: float,
) -> float:
    return foundation_volume(width_m, length_m, thickness_m) * _positive(
        unit_weight_kn_m3, "unit_weight_kn_m3"
    )


def average_contact_pressure(vertical_load_kn: float, area_m2: float) -> float:
    return _positive(vertical_load_kn, "vertical_load_kn", allow_zero=True) / _positive(
        area_m2, "area_m2"
    )


def net_foundation_pressure(
    gross_pressure_kpa: float,
    removed_overburden_kpa: float,
) -> float:
    return _finite(gross_pressure_kpa, "gross_pressure_kpa") - _finite(
        removed_overburden_kpa, "removed_overburden_kpa"
    )


def eccentricity(moment_kn_m: float, vertical_load_kn: float) -> float:
    return _finite(moment_kn_m, "moment_kn_m") / _positive(
        vertical_load_kn, "vertical_load_kn"
    )


def kern_limit(dimension_m: float) -> float:
    return _positive(dimension_m, "dimension_m") / 6.0


def within_kern(eccentricity_m: float, dimension_m: float) -> bool:
    return abs(_finite(eccentricity_m, "eccentricity_m")) <= kern_limit(dimension_m)


def rectangular_base_pressures(
    vertical_load_kn: float,
    width_m: float,
    length_m: float,
    moment_about_length_axis_kn_m: float = 0.0,
) -> tuple[float, float]:
    load = _positive(vertical_load_kn, "vertical_load_kn")
    width = _positive(width_m, "width_m")
    length = _positive(length_m, "length_m")
    moment = _finite(moment_about_length_axis_kn_m, "moment_about_length_axis_kn_m")
    area = width * length
    mean = load / area
    e = moment / load
    q_min = mean * (1.0 - 6.0 * e / width)
    q_max = mean * (1.0 + 6.0 * e / width)
    return q_min, q_max


def effective_width(width_m: float, eccentricity_m: float) -> float:
    result = _positive(width_m, "width_m") - 2.0 * abs(
        _finite(eccentricity_m, "eccentricity_m")
    )
    if result <= 0.0:
        raise FoundationError("effective width must remain greater than zero.")
    return result


def allowable_vertical_load(
    allowable_bearing_pressure_kpa: float,
    area_m2: float,
) -> float:
    return _positive(
        allowable_bearing_pressure_kpa, "allowable_bearing_pressure_kpa"
    ) * _positive(area_m2, "area_m2")


def bearing_utilization(
    applied_pressure_kpa: float,
    allowable_pressure_kpa: float,
) -> float:
    return _positive(applied_pressure_kpa, "applied_pressure_kpa", allow_zero=True) / _positive(
        allowable_pressure_kpa, "allowable_pressure_kpa"
    )


def bearing_safety_factor(
    ultimate_pressure_kpa: float,
    applied_pressure_kpa: float,
) -> float:
    return _positive(ultimate_pressure_kpa, "ultimate_pressure_kpa") / _positive(
        applied_pressure_kpa, "applied_pressure_kpa"
    )


def sliding_resistance(
    vertical_load_kn: float,
    friction_coefficient: float,
    passive_resistance_kn: float = 0.0,
) -> float:
    mu = _positive(friction_coefficient, "friction_coefficient", allow_zero=True)
    return (
        _positive(vertical_load_kn, "vertical_load_kn", allow_zero=True) * mu
        + _positive(passive_resistance_kn, "passive_resistance_kn", allow_zero=True)
    )


def sliding_safety_factor(
    vertical_load_kn: float,
    friction_coefficient: float,
    horizontal_load_kn: float,
    passive_resistance_kn: float = 0.0,
) -> float:
    return sliding_resistance(
        vertical_load_kn, friction_coefficient, passive_resistance_kn
    ) / _positive(horizontal_load_kn, "horizontal_load_kn")


def overturning_safety_factor(
    resisting_moment_kn_m: float,
    overturning_moment_kn_m: float,
) -> float:
    return _positive(resisting_moment_kn_m, "resisting_moment_kn_m") / _positive(
        overturning_moment_kn_m, "overturning_moment_kn_m"
    )


def one_dimensional_settlement(
    stress_increment_kpa: float,
    constrained_modulus_kpa: float,
    layer_thickness_m: float,
) -> float:
    return (
        _positive(stress_increment_kpa, "stress_increment_kpa", allow_zero=True)
        / _positive(constrained_modulus_kpa, "constrained_modulus_kpa")
        * _positive(layer_thickness_m, "layer_thickness_m")
    )


def total_settlement(settlements_m: Iterable[float]) -> float:
    values = tuple(_positive(v, "settlement", allow_zero=True) for v in settlements_m)
    if not values:
        raise FoundationError("settlements_m cannot be empty.")
    return sum(values)


def differential_settlement(settlement_a_m: float, settlement_b_m: float) -> float:
    return abs(
        _finite(settlement_a_m, "settlement_a_m")
        - _finite(settlement_b_m, "settlement_b_m")
    )


def angular_distortion(
    settlement_a_m: float,
    settlement_b_m: float,
    distance_m: float,
) -> float:
    return differential_settlement(settlement_a_m, settlement_b_m) / _positive(
        distance_m, "distance_m"
    )


def settlement_utilization(
    calculated_settlement_m: float,
    allowable_settlement_m: float,
) -> float:
    return _positive(
        calculated_settlement_m, "calculated_settlement_m", allow_zero=True
    ) / _positive(allowable_settlement_m, "allowable_settlement_m")


def strip_footing_line_load(
    wall_load_kn_per_m: float,
    footing_self_weight_kn_per_m: float = 0.0,
) -> float:
    return _positive(wall_load_kn_per_m, "wall_load_kn_per_m", allow_zero=True) + _positive(
        footing_self_weight_kn_per_m,
        "footing_self_weight_kn_per_m",
        allow_zero=True,
    )


def required_strip_width(
    line_load_kn_per_m: float,
    allowable_pressure_kpa: float,
) -> float:
    return _positive(line_load_kn_per_m, "line_load_kn_per_m") / _positive(
        allowable_pressure_kpa, "allowable_pressure_kpa"
    )


def simple_beam_reactions(
    span_m: float,
    point_load_kn: float,
    load_position_from_left_m: float,
) -> tuple[float, float]:
    span = _positive(span_m, "span_m")
    load = _positive(point_load_kn, "point_load_kn", allow_zero=True)
    position = _finite(load_position_from_left_m, "load_position_from_left_m")
    if not 0.0 <= position <= span:
        raise FoundationError("load position must lie within the span.")
    left = load * (span - position) / span
    right = load * position / span
    return left, right


def simply_supported_udl_max_moment(
    uniform_load_kn_per_m: float,
    span_m: float,
) -> float:
    w = _positive(uniform_load_kn_per_m, "uniform_load_kn_per_m", allow_zero=True)
    l = _positive(span_m, "span_m")
    return w * l**2 / 8.0


def simply_supported_udl_max_shear(
    uniform_load_kn_per_m: float,
    span_m: float,
) -> float:
    return _positive(
        uniform_load_kn_per_m, "uniform_load_kn_per_m", allow_zero=True
    ) * _positive(span_m, "span_m") / 2.0


def pile_group_capacity(
    pile_capacity_kn: float,
    number_of_piles: int,
    group_efficiency: float = 1.0,
) -> float:
    capacity = _positive(pile_capacity_kn, "pile_capacity_kn")
    if not isinstance(number_of_piles, int) or number_of_piles <= 0:
        raise FoundationError("number_of_piles must be a positive integer.")
    efficiency = _finite(group_efficiency, "group_efficiency")
    if not 0.0 < efficiency <= 1.0:
        raise FoundationError("group_efficiency must be greater than 0 and at most 1.")
    return capacity * number_of_piles * efficiency


def average_pile_load(total_load_kn: float, number_of_piles: int) -> float:
    if not isinstance(number_of_piles, int) or number_of_piles <= 0:
        raise FoundationError("number_of_piles must be a positive integer.")
    return _positive(total_load_kn, "total_load_kn", allow_zero=True) / number_of_piles


def pile_group_utilization(
    total_load_kn: float,
    pile_capacity_kn: float,
    number_of_piles: int,
    group_efficiency: float = 1.0,
) -> float:
    return _positive(total_load_kn, "total_load_kn", allow_zero=True) / pile_group_capacity(
        pile_capacity_kn, number_of_piles, group_efficiency
    )


def distribute_load_equally(total_load_kn: float, number_of_supports: int) -> tuple[float, ...]:
    if not isinstance(number_of_supports, int) or number_of_supports <= 0:
        raise FoundationError("number_of_supports must be a positive integer.")
    value = _positive(total_load_kn, "total_load_kn", allow_zero=True) / number_of_supports
    return tuple(value for _ in range(number_of_supports))


def load_uniformity_ratio(loads_kn: Sequence[float]) -> float:
    values = tuple(_positive(v, "load", allow_zero=True) for v in loads_kn)
    if not values:
        raise FoundationError("loads_kn cannot be empty.")
    mean = sum(values) / len(values)
    if mean == 0.0:
        return 0.0
    maximum_deviation = max(abs(value - mean) for value in values)
    return maximum_deviation / mean
