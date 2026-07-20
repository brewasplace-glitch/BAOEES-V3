"""Phoenix Engineering Kernel Structural Engine Wave 1.

Generic SI-based structural mechanics primitives. No material-specific
national-code partial factors are hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


class StructuralError(ValueError):
    """Raised when structural input is invalid."""


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StructuralError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise StructuralError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise StructuralError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise StructuralError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class SectionProperties:
    area: float
    centroid_y: float
    inertia_y: float
    section_modulus_y: float
    radius_of_gyration_y: float

    def __post_init__(self) -> None:
        _positive(self.area, "area")
        _finite(self.centroid_y, "centroid_y")
        _positive(self.inertia_y, "inertia_y")
        _positive(self.section_modulus_y, "section_modulus_y")
        _positive(self.radius_of_gyration_y, "radius_of_gyration_y")


def rectangle_area(width: float, height: float) -> float:
    return _positive(width, "width") * _positive(height, "height")


def rectangle_centroid_y(height: float) -> float:
    return _positive(height, "height") / 2.0


def rectangle_inertia_y(width: float, height: float) -> float:
    b = _positive(width, "width")
    h = _positive(height, "height")
    return b * h**3 / 12.0


def rectangle_section_modulus_y(width: float, height: float) -> float:
    return rectangle_inertia_y(width, height) / rectangle_centroid_y(height)


def rectangle_radius_of_gyration_y(width: float, height: float) -> float:
    area = rectangle_area(width, height)
    return math.sqrt(rectangle_inertia_y(width, height) / area)


def rectangle_section_properties(width: float, height: float) -> SectionProperties:
    return SectionProperties(
        area=rectangle_area(width, height),
        centroid_y=rectangle_centroid_y(height),
        inertia_y=rectangle_inertia_y(width, height),
        section_modulus_y=rectangle_section_modulus_y(width, height),
        radius_of_gyration_y=rectangle_radius_of_gyration_y(width, height),
    )


def circle_area(diameter: float) -> float:
    d = _positive(diameter, "diameter")
    return math.pi * d**2 / 4.0


def circle_inertia(diameter: float) -> float:
    d = _positive(diameter, "diameter")
    return math.pi * d**4 / 64.0


def circle_section_modulus(diameter: float) -> float:
    d = _positive(diameter, "diameter")
    return circle_inertia(d) / (d / 2.0)


def parallel_axis_inertia(centroidal_inertia: float, area: float, offset: float) -> float:
    return (
        _positive(centroidal_inertia, "centroidal_inertia")
        + _positive(area, "area") * _finite(offset, "offset")**2
    )


def normal_stress(axial_force: float, area: float) -> float:
    return _finite(axial_force, "axial_force") / _positive(area, "area")


def bending_stress(moment: float, distance: float, inertia: float) -> float:
    return (
        _finite(moment, "moment")
        * _finite(distance, "distance")
        / _positive(inertia, "inertia")
    )


def combined_normal_stress(
    axial_force: float,
    area: float,
    moment: float,
    distance: float,
    inertia: float,
) -> float:
    return normal_stress(axial_force, area) + bending_stress(moment, distance, inertia)


def shear_stress_average(shear_force: float, area: float) -> float:
    return _finite(shear_force, "shear_force") / _positive(area, "area")


def strain_from_stress(stress: float, elastic_modulus: float) -> float:
    return _finite(stress, "stress") / _positive(elastic_modulus, "elastic_modulus")


def axial_deformation(force: float, length: float, area: float, elastic_modulus: float) -> float:
    return (
        _finite(force, "force")
        * _positive(length, "length")
        / (_positive(area, "area") * _positive(elastic_modulus, "elastic_modulus"))
    )


def simply_supported_reactions_uniform_load(load_per_length: float, length: float) -> tuple[float, float]:
    total = _finite(load_per_length, "load_per_length") * _positive(length, "length")
    return total / 2.0, total / 2.0


def simply_supported_max_moment_uniform_load(load_per_length: float, length: float) -> float:
    w = _finite(load_per_length, "load_per_length")
    l = _positive(length, "length")
    return w * l**2 / 8.0


def simply_supported_max_deflection_uniform_load(
    load_per_length: float,
    length: float,
    elastic_modulus: float,
    inertia: float,
) -> float:
    w = _finite(load_per_length, "load_per_length")
    l = _positive(length, "length")
    e = _positive(elastic_modulus, "elastic_modulus")
    i = _positive(inertia, "inertia")
    return 5.0 * w * l**4 / (384.0 * e * i)


def simply_supported_center_deflection_point_load(
    point_load: float,
    length: float,
    elastic_modulus: float,
    inertia: float,
) -> float:
    p = _finite(point_load, "point_load")
    l = _positive(length, "length")
    e = _positive(elastic_modulus, "elastic_modulus")
    i = _positive(inertia, "inertia")
    return p * l**3 / (48.0 * e * i)


def cantilever_end_deflection_point_load(
    point_load: float,
    length: float,
    elastic_modulus: float,
    inertia: float,
) -> float:
    p = _finite(point_load, "point_load")
    l = _positive(length, "length")
    e = _positive(elastic_modulus, "elastic_modulus")
    i = _positive(inertia, "inertia")
    return p * l**3 / (3.0 * e * i)


def cantilever_end_rotation_point_load(
    point_load: float,
    length: float,
    elastic_modulus: float,
    inertia: float,
) -> float:
    p = _finite(point_load, "point_load")
    l = _positive(length, "length")
    e = _positive(elastic_modulus, "elastic_modulus")
    i = _positive(inertia, "inertia")
    return p * l**2 / (2.0 * e * i)


def slenderness_ratio(effective_length: float, radius_of_gyration: float) -> float:
    return _positive(effective_length, "effective_length") / _positive(
        radius_of_gyration, "radius_of_gyration"
    )


def euler_buckling_load(
    elastic_modulus: float,
    inertia: float,
    effective_length: float,
) -> float:
    e = _positive(elastic_modulus, "elastic_modulus")
    i = _positive(inertia, "inertia")
    l = _positive(effective_length, "effective_length")
    return math.pi**2 * e * i / l**2


def effective_length(actual_length: float, effective_length_factor: float) -> float:
    return _positive(actual_length, "actual_length") * _positive(
        effective_length_factor, "effective_length_factor"
    )


def second_order_moment_amplification(
    first_order_moment: float,
    axial_force: float,
    critical_force: float,
) -> float:
    m1 = _finite(first_order_moment, "first_order_moment")
    n = _positive(axial_force, "axial_force", allow_zero=True)
    ncr = _positive(critical_force, "critical_force")
    if n >= ncr:
        raise StructuralError("axial_force must be smaller than critical_force.")
    return m1 / (1.0 - n / ncr)


def utilization_ratio(demand: float, resistance: float) -> float:
    return abs(_finite(demand, "demand")) / _positive(resistance, "resistance")


def factor_of_safety(resistance: float, demand: float) -> float:
    d = abs(_finite(demand, "demand"))
    if d == 0.0:
        raise StructuralError("demand magnitude must be greater than zero.")
    return _positive(resistance, "resistance") / d


def resultant_force_2d(force_x: float, force_y: float) -> float:
    return math.hypot(_finite(force_x, "force_x"), _finite(force_y, "force_y"))


def transform_vector_2d_local_to_global(
    local_x: float,
    local_y: float,
    angle_deg: float,
) -> tuple[float, float]:
    x = _finite(local_x, "local_x")
    y = _finite(local_y, "local_y")
    angle = math.radians(_finite(angle_deg, "angle_deg"))
    return (
        x * math.cos(angle) - y * math.sin(angle),
        x * math.sin(angle) + y * math.cos(angle),
    )


def transform_vector_2d_global_to_local(
    global_x: float,
    global_y: float,
    angle_deg: float,
) -> tuple[float, float]:
    return transform_vector_2d_local_to_global(global_x, global_y, -angle_deg)
