"""Phoenix Engineering Kernel Geo Engine Wave 1.

Generic geotechnical calculation primitives with explicit SI inputs.
No national annexes or project-specific safety factors are hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


class GeoError(ValueError):
    """Raised when geotechnical input is invalid."""


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise GeoError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise GeoError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise GeoError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class SoilLayer:
    name: str
    top: float
    bottom: float
    dry_unit_weight: float
    saturated_unit_weight: float
    friction_angle_deg: float = 0.0
    cohesion: float = 0.0
    constrained_modulus: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise GeoError("name cannot be empty.")
        if self.bottom >= self.top:
            raise GeoError("bottom elevation must be below top elevation.")
        _positive(self.dry_unit_weight, "dry_unit_weight")
        _positive(self.saturated_unit_weight, "saturated_unit_weight")
        phi = _finite(self.friction_angle_deg, "friction_angle_deg")
        if not 0.0 <= phi < 90.0:
            raise GeoError("friction_angle_deg must be in [0, 90).")
        _positive(self.cohesion, "cohesion", allow_zero=True)
        if self.constrained_modulus is not None:
            _positive(self.constrained_modulus, "constrained_modulus")

    @property
    def thickness(self) -> float:
        return self.top - self.bottom


def create_soil_layer(
    name: str,
    top: float,
    bottom: float,
    dry_unit_weight: float,
    saturated_unit_weight: float,
    friction_angle_deg: float = 0.0,
    cohesion: float = 0.0,
    constrained_modulus: float | None = None,
) -> SoilLayer:
    return SoilLayer(
        name, top, bottom, dry_unit_weight, saturated_unit_weight,
        friction_angle_deg, cohesion, constrained_modulus
    )


def layer_thickness(layer: SoilLayer) -> float:
    return layer.thickness


def submerged_unit_weight(saturated_unit_weight: float, water_unit_weight: float = 9.81) -> float:
    gamma_sat = _positive(saturated_unit_weight, "saturated_unit_weight")
    gamma_w = _positive(water_unit_weight, "water_unit_weight")
    if gamma_sat <= gamma_w:
        raise GeoError("saturated_unit_weight must exceed water_unit_weight.")
    return gamma_sat - gamma_w


def pore_water_pressure(depth_below_water: float, water_unit_weight: float = 9.81) -> float:
    return _positive(depth_below_water, "depth_below_water", allow_zero=True) * _positive(
        water_unit_weight, "water_unit_weight"
    )


def total_vertical_stress(unit_weight: float, depth: float) -> float:
    return _positive(unit_weight, "unit_weight") * _positive(depth, "depth", allow_zero=True)


def effective_vertical_stress(total_stress: float, pore_pressure: float) -> float:
    return _finite(total_stress, "total_stress") - _finite(pore_pressure, "pore_pressure")


def stress_increment_uniform_load(load: float, influence_factor: float = 1.0) -> float:
    factor = _finite(influence_factor, "influence_factor")
    if not 0.0 <= factor <= 1.0:
        raise GeoError("influence_factor must be between 0 and 1.")
    return _finite(load, "load") * factor


def effective_stress_profile(
    layers: Sequence[SoilLayer],
    depth: float,
    groundwater_depth: float,
    water_unit_weight: float = 9.81,
) -> float:
    z = _positive(depth, "depth", allow_zero=True)
    gw = _positive(groundwater_depth, "groundwater_depth", allow_zero=True)
    if z == 0.0:
        return 0.0

    remaining = z
    total = 0.0
    for layer in layers:
        if remaining <= 0.0:
            break
        dz = min(layer.thickness, remaining)
        layer_top_depth = z - remaining
        layer_bottom_depth = layer_top_depth + dz
        dry_part = max(0.0, min(layer_bottom_depth, gw) - layer_top_depth)
        wet_part = dz - dry_part
        total += dry_part * layer.dry_unit_weight
        if wet_part > 0.0:
            total += wet_part * submerged_unit_weight(layer.saturated_unit_weight, water_unit_weight)
        remaining -= dz

    if remaining > 1e-12:
        raise GeoError("depth exceeds supplied soil profile.")
    return total


def rankine_active_coefficient(friction_angle_deg: float) -> float:
    phi = math.radians(_finite(friction_angle_deg, "friction_angle_deg"))
    if not 0.0 <= phi < math.pi / 2:
        raise GeoError("friction_angle_deg must be in [0, 90).")
    return math.tan(math.pi / 4 - phi / 2) ** 2


def rankine_passive_coefficient(friction_angle_deg: float) -> float:
    ka = rankine_active_coefficient(friction_angle_deg)
    if ka == 0.0:
        raise GeoError("passive coefficient is undefined.")
    return 1.0 / ka


def rankine_at_rest_coefficient(friction_angle_deg: float) -> float:
    phi = math.radians(_finite(friction_angle_deg, "friction_angle_deg"))
    if not 0.0 <= phi < math.pi / 2:
        raise GeoError("friction_angle_deg must be in [0, 90).")
    return 1.0 - math.sin(phi)


def lateral_earth_pressure(vertical_effective_stress: float, coefficient: float, cohesion: float = 0.0) -> float:
    sigma = _positive(vertical_effective_stress, "vertical_effective_stress", allow_zero=True)
    k = _positive(coefficient, "coefficient", allow_zero=True)
    c = _positive(cohesion, "cohesion", allow_zero=True)
    return max(0.0, k * sigma - 2.0 * c * math.sqrt(k))


def triangular_pressure_resultant(max_pressure: float, height: float) -> float:
    return 0.5 * _positive(max_pressure, "max_pressure", allow_zero=True) * _positive(height, "height")


def triangular_pressure_application_height(height: float) -> float:
    return _positive(height, "height") / 3.0


def bearing_capacity_factor_nq(friction_angle_deg: float) -> float:
    phi = math.radians(_finite(friction_angle_deg, "friction_angle_deg"))
    if not 0.0 <= phi < math.radians(89.0):
        raise GeoError("friction_angle_deg must be in [0, 89).")
    if phi == 0.0:
        return 1.0
    return math.exp(math.pi * math.tan(phi)) * math.tan(math.pi / 4 + phi / 2) ** 2


def bearing_capacity_factor_nc(friction_angle_deg: float) -> float:
    phi = math.radians(_finite(friction_angle_deg, "friction_angle_deg"))
    nq = bearing_capacity_factor_nq(friction_angle_deg)
    if phi == 0.0:
        return 5.14
    return (nq - 1.0) / math.tan(phi)


def bearing_capacity_factor_ngamma(friction_angle_deg: float) -> float:
    phi = math.radians(_finite(friction_angle_deg, "friction_angle_deg"))
    nq = bearing_capacity_factor_nq(friction_angle_deg)
    return 2.0 * (nq + 1.0) * math.tan(phi)


def ultimate_bearing_capacity_strip(
    cohesion: float,
    surcharge: float,
    unit_weight: float,
    width: float,
    friction_angle_deg: float,
) -> float:
    c = _positive(cohesion, "cohesion", allow_zero=True)
    q = _positive(surcharge, "surcharge", allow_zero=True)
    gamma = _positive(unit_weight, "unit_weight")
    b = _positive(width, "width")
    nc = bearing_capacity_factor_nc(friction_angle_deg)
    nq = bearing_capacity_factor_nq(friction_angle_deg)
    ng = bearing_capacity_factor_ngamma(friction_angle_deg)
    return c * nc + q * nq + 0.5 * gamma * b * ng


def allowable_bearing_capacity(ultimate_capacity: float, factor_of_safety: float) -> float:
    return _positive(ultimate_capacity, "ultimate_capacity") / _positive(
        factor_of_safety, "factor_of_safety"
    )


def one_dimensional_settlement(stress_increment: float, thickness: float, constrained_modulus: float) -> float:
    return (
        _positive(stress_increment, "stress_increment", allow_zero=True)
        * _positive(thickness, "thickness")
        / _positive(constrained_modulus, "constrained_modulus")
    )


def elastic_settlement(
    pressure: float,
    width: float,
    elastic_modulus: float,
    poisson_ratio: float,
    influence_factor: float = 1.0,
) -> float:
    p = _positive(pressure, "pressure", allow_zero=True)
    b = _positive(width, "width")
    e = _positive(elastic_modulus, "elastic_modulus")
    nu = _finite(poisson_ratio, "poisson_ratio")
    if not -1.0 < nu < 0.5:
        raise GeoError("poisson_ratio must be between -1 and 0.5.")
    i = _positive(influence_factor, "influence_factor")
    return p * b * (1.0 - nu * nu) * i / e


def consolidation_degree_time_factor(time_factor: float) -> float:
    tv = _positive(time_factor, "time_factor", allow_zero=True)
    if tv == 0.0:
        return 0.0
    if tv < 0.2:
        return math.sqrt(4.0 * tv / math.pi)
    return 1.0 - (8.0 / math.pi**2) * math.exp(-(math.pi**2 / 4.0) * tv)


def hydraulic_gradient(head_difference: float, flow_length: float) -> float:
    return _finite(head_difference, "head_difference") / _positive(flow_length, "flow_length")


def darcy_velocity(hydraulic_conductivity: float, gradient: float) -> float:
    return _positive(hydraulic_conductivity, "hydraulic_conductivity", allow_zero=True) * _finite(
        gradient, "gradient"
    )


def seepage_discharge(hydraulic_conductivity: float, gradient: float, area: float) -> float:
    return darcy_velocity(hydraulic_conductivity, gradient) * _positive(area, "area")


def critical_hydraulic_gradient(saturated_unit_weight: float, water_unit_weight: float = 9.81) -> float:
    return submerged_unit_weight(saturated_unit_weight, water_unit_weight) / _positive(
        water_unit_weight, "water_unit_weight"
    )


def liquefaction_safety_factor(cyclic_resistance_ratio: float, cyclic_stress_ratio: float) -> float:
    return _positive(cyclic_resistance_ratio, "cyclic_resistance_ratio") / _positive(
        cyclic_stress_ratio, "cyclic_stress_ratio"
    )


def slope_ratio(horizontal: float, vertical: float) -> float:
    return _positive(horizontal, "horizontal") / _positive(vertical, "vertical")


def slope_angle_deg(horizontal: float, vertical: float) -> float:
    return math.degrees(math.atan2(_positive(vertical, "vertical"), _positive(horizontal, "horizontal")))


def validate_soil_profile(layers: Iterable[SoilLayer], tolerance: float = 1e-9) -> bool:
    data = tuple(layers)
    if not data:
        raise GeoError("soil profile cannot be empty.")
    tol = _positive(tolerance, "tolerance", allow_zero=True)
    for previous, current in zip(data, data[1:]):
        if abs(previous.bottom - current.top) > tol:
            return False
    return True


def groundwater_elevation(reference_elevation: float, groundwater_depth: float) -> float:
    return _finite(reference_elevation, "reference_elevation") - _positive(
        groundwater_depth, "groundwater_depth", allow_zero=True
    )
