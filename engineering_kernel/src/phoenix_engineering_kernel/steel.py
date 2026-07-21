"""Phoenix Engineering Kernel Steel Design Wave 1.

Generic SI-based steel design primitives. No specific design standard or
national annex is embedded; factors and resistance-model parameters are inputs.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


class SteelDesignError(ValueError):
    """Raised when steel-design input is invalid."""


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SteelDesignError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise SteelDesignError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise SteelDesignError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise SteelDesignError(f"{name} must be greater than zero.")
    return number


def _factor(value: float, name: str, *, upper: float | None = None) -> float:
    number = _positive(value, name, allow_zero=True)
    if upper is not None and number > upper:
        raise SteelDesignError(f"{name} cannot exceed {upper}.")
    return number


def steel_design_strength(yield_strength_mpa: float, gamma_m: float = 1.0) -> float:
    return _positive(yield_strength_mpa, "yield_strength_mpa") / _positive(gamma_m, "gamma_m")


def shear_modulus(elastic_modulus_mpa: float, poisson_ratio: float) -> float:
    e = _positive(elastic_modulus_mpa, "elastic_modulus_mpa")
    nu = _finite(poisson_ratio, "poisson_ratio")
    if not -1.0 < nu < 0.5:
        raise SteelDesignError("poisson_ratio must be between -1.0 and 0.5.")
    return e / (2.0 * (1.0 + nu))


def thermal_strain(thermal_expansion_per_c: float, temperature_change_c: float) -> float:
    return _finite(thermal_expansion_per_c, "thermal_expansion_per_c") * _finite(
        temperature_change_c, "temperature_change_c"
    )


def steel_member_self_weight(area_mm2: float, density_kg_m3: float = 7850.0, gravity_m_s2: float = 9.80665) -> float:
    return (
        _positive(area_mm2, "area_mm2") / 1e6
        * _positive(density_kg_m3, "density_kg_m3")
        * _positive(gravity_m_s2, "gravity_m_s2")
        / 1000.0
    )


def normal_stress(axial_force_kn: float, area_mm2: float) -> float:
    return _finite(axial_force_kn, "axial_force_kn") * 1000.0 / _positive(area_mm2, "area_mm2")


def shear_stress(shear_force_kn: float, shear_area_mm2: float) -> float:
    return _finite(shear_force_kn, "shear_force_kn") * 1000.0 / _positive(shear_area_mm2, "shear_area_mm2")


def elastic_strain(stress_mpa: float, elastic_modulus_mpa: float) -> float:
    return _finite(stress_mpa, "stress_mpa") / _positive(elastic_modulus_mpa, "elastic_modulus_mpa")


def von_mises_stress(sigma_x_mpa: float, sigma_y_mpa: float, tau_xy_mpa: float) -> float:
    sx = _finite(sigma_x_mpa, "sigma_x_mpa")
    sy = _finite(sigma_y_mpa, "sigma_y_mpa")
    tau = _finite(tau_xy_mpa, "tau_xy_mpa")
    return math.sqrt(sx**2 - sx * sy + sy**2 + 3.0 * tau**2)


def rectangular_second_moment(width_mm: float, depth_mm: float) -> float:
    return _positive(width_mm, "width_mm") * _positive(depth_mm, "depth_mm") ** 3 / 12.0


def rectangular_elastic_section_modulus(width_mm: float, depth_mm: float) -> float:
    return _positive(width_mm, "width_mm") * _positive(depth_mm, "depth_mm") ** 2 / 6.0


def rectangular_plastic_section_modulus(width_mm: float, depth_mm: float) -> float:
    return _positive(width_mm, "width_mm") * _positive(depth_mm, "depth_mm") ** 2 / 4.0


def circular_second_moment(diameter_mm: float) -> float:
    diameter = _positive(diameter_mm, "diameter_mm")
    return math.pi * diameter**4 / 64.0


def circular_elastic_section_modulus(diameter_mm: float) -> float:
    diameter = _positive(diameter_mm, "diameter_mm")
    return math.pi * diameter**3 / 32.0


def radius_of_gyration(second_moment_mm4: float, area_mm2: float) -> float:
    return math.sqrt(_positive(second_moment_mm4, "second_moment_mm4") / _positive(area_mm2, "area_mm2"))


def member_slenderness(effective_length_mm: float, radius_gyration_mm: float) -> float:
    return _positive(effective_length_mm, "effective_length_mm") / _positive(radius_gyration_mm, "radius_gyration_mm")


def euler_buckling_load(elastic_modulus_mpa: float, second_moment_mm4: float, effective_length_mm: float) -> float:
    return (
        math.pi**2
        * _positive(elastic_modulus_mpa, "elastic_modulus_mpa")
        * _positive(second_moment_mm4, "second_moment_mm4")
        / _positive(effective_length_mm, "effective_length_mm") ** 2
        / 1000.0
    )


def non_dimensional_slenderness(area_mm2: float, yield_strength_mpa: float, euler_load_kn: float) -> float:
    squash_load_kn = _positive(area_mm2, "area_mm2") * _positive(yield_strength_mpa, "yield_strength_mpa") / 1000.0
    return math.sqrt(squash_load_kn / _positive(euler_load_kn, "euler_load_kn"))


def buckling_reduction_factor(non_dimensional_slenderness_value: float, imperfection_factor: float) -> float:
    slenderness = _positive(non_dimensional_slenderness_value, "non_dimensional_slenderness_value", allow_zero=True)
    alpha = _positive(imperfection_factor, "imperfection_factor", allow_zero=True)
    phi = 0.5 * (1.0 + alpha * (slenderness - 0.2) + slenderness**2)
    denominator = phi + math.sqrt(max(phi**2 - slenderness**2, 0.0))
    if denominator <= 0.0:
        raise SteelDesignError("buckling reduction denominator must be positive.")
    return min(1.0, 1.0 / denominator)


def gross_tension_resistance(area_mm2: float, yield_strength_mpa: float, gamma_m: float = 1.0) -> float:
    return _positive(area_mm2, "area_mm2") * steel_design_strength(yield_strength_mpa, gamma_m) / 1000.0


def net_tension_resistance(net_area_mm2: float, ultimate_strength_mpa: float, gamma_m: float = 1.0, reduction_factor: float = 1.0) -> float:
    return (
        _positive(net_area_mm2, "net_area_mm2")
        * _positive(ultimate_strength_mpa, "ultimate_strength_mpa")
        * _factor(reduction_factor, "reduction_factor", upper=1.0)
        / _positive(gamma_m, "gamma_m")
        / 1000.0
    )


def tension_resistance(gross_resistance_kn: float, net_resistance_kn: float) -> float:
    return min(_positive(gross_resistance_kn, "gross_resistance_kn"), _positive(net_resistance_kn, "net_resistance_kn"))


def compression_resistance(area_mm2: float, yield_strength_mpa: float, buckling_factor: float, gamma_m: float = 1.0) -> float:
    return (
        _positive(area_mm2, "area_mm2")
        * _positive(yield_strength_mpa, "yield_strength_mpa")
        * _factor(buckling_factor, "buckling_factor", upper=1.0)
        / _positive(gamma_m, "gamma_m")
        / 1000.0
    )


def bending_resistance(section_modulus_mm3: float, yield_strength_mpa: float, gamma_m: float = 1.0) -> float:
    return _positive(section_modulus_mm3, "section_modulus_mm3") * _positive(yield_strength_mpa, "yield_strength_mpa") / _positive(gamma_m, "gamma_m") / 1e6


def shear_resistance(shear_area_mm2: float, yield_strength_mpa: float, gamma_m: float = 1.0) -> float:
    return _positive(shear_area_mm2, "shear_area_mm2") * _positive(yield_strength_mpa, "yield_strength_mpa") / (math.sqrt(3.0) * _positive(gamma_m, "gamma_m")) / 1000.0


def lateral_torsional_reduction(non_dimensional_slenderness_value: float, imperfection_factor: float) -> float:
    return buckling_reduction_factor(non_dimensional_slenderness_value, imperfection_factor)


def lateral_torsional_bending_resistance(base_bending_resistance_kn_m: float, reduction_factor: float) -> float:
    return _positive(base_bending_resistance_kn_m, "base_bending_resistance_kn_m") * _factor(reduction_factor, "reduction_factor", upper=1.0)


def axial_bending_interaction(axial_force_kn: float, axial_resistance_kn: float, moment_kn_m: float, moment_resistance_kn_m: float, interaction_exponent: float = 1.0) -> float:
    exponent = _positive(interaction_exponent, "interaction_exponent")
    return (
        (_positive(axial_force_kn, "axial_force_kn", allow_zero=True) / _positive(axial_resistance_kn, "axial_resistance_kn")) ** exponent
        + (_positive(moment_kn_m, "moment_kn_m", allow_zero=True) / _positive(moment_resistance_kn_m, "moment_resistance_kn_m")) ** exponent
    )


def plate_slenderness(width_mm: float, thickness_mm: float) -> float:
    return _positive(width_mm, "width_mm") / _positive(thickness_mm, "thickness_mm")


def bolt_shear_resistance(bolt_area_mm2: float, ultimate_strength_mpa: float, shear_factor: float, gamma_m: float = 1.0, shear_planes: int = 1) -> float:
    if not isinstance(shear_planes, int) or shear_planes <= 0:
        raise SteelDesignError("shear_planes must be a positive integer.")
    return (
        _positive(bolt_area_mm2, "bolt_area_mm2")
        * _positive(ultimate_strength_mpa, "ultimate_strength_mpa")
        * _positive(shear_factor, "shear_factor")
        * shear_planes
        / _positive(gamma_m, "gamma_m")
        / 1000.0
    )


def bolt_tension_resistance(tensile_area_mm2: float, ultimate_strength_mpa: float, tension_factor: float, gamma_m: float = 1.0) -> float:
    return _positive(tensile_area_mm2, "tensile_area_mm2") * _positive(ultimate_strength_mpa, "ultimate_strength_mpa") * _positive(tension_factor, "tension_factor") / _positive(gamma_m, "gamma_m") / 1000.0


def bolt_bearing_resistance(bolt_diameter_mm: float, plate_thickness_mm: float, plate_ultimate_strength_mpa: float, bearing_factor: float, gamma_m: float = 1.0) -> float:
    return _positive(bolt_diameter_mm, "bolt_diameter_mm") * _positive(plate_thickness_mm, "plate_thickness_mm") * _positive(plate_ultimate_strength_mpa, "plate_ultimate_strength_mpa") * _positive(bearing_factor, "bearing_factor") / _positive(gamma_m, "gamma_m") / 1000.0


def combined_bolt_utilization(applied_shear_kn: float, shear_resistance_kn: float, applied_tension_kn: float, tension_resistance_kn: float, shear_exponent: float = 2.0, tension_exponent: float = 2.0) -> float:
    return (
        (_positive(applied_shear_kn, "applied_shear_kn", allow_zero=True) / _positive(shear_resistance_kn, "shear_resistance_kn")) ** _positive(shear_exponent, "shear_exponent")
        + (_positive(applied_tension_kn, "applied_tension_kn", allow_zero=True) / _positive(tension_resistance_kn, "tension_resistance_kn")) ** _positive(tension_exponent, "tension_exponent")
    )


def required_bolt_count(applied_force_kn: float, resistance_per_bolt_kn: float) -> int:
    demand = _positive(applied_force_kn, "applied_force_kn", allow_zero=True)
    return max(1, math.ceil(demand / _positive(resistance_per_bolt_kn, "resistance_per_bolt_kn")))


def weld_effective_throat(leg_size_mm: float, throat_factor: float = 1.0 / math.sqrt(2.0)) -> float:
    return _positive(leg_size_mm, "leg_size_mm") * _positive(throat_factor, "throat_factor")


def weld_resistance(effective_throat_mm: float, effective_length_mm: float, design_shear_strength_mpa: float) -> float:
    return _positive(effective_throat_mm, "effective_throat_mm") * _positive(effective_length_mm, "effective_length_mm") * _positive(design_shear_strength_mpa, "design_shear_strength_mpa") / 1000.0


def connection_utilization(applied_actions: Iterable[float], resistances: Iterable[float]) -> float:
    actions = tuple(applied_actions)
    capacities = tuple(resistances)
    if not actions or len(actions) != len(capacities):
        raise SteelDesignError("actions and resistances must have equal non-zero length.")
    return sum(
        _positive(action, f"applied_actions[{index}]", allow_zero=True)
        / _positive(capacity, f"resistances[{index}]")
        for index, (action, capacity) in enumerate(zip(actions, capacities))
    )


def deflection_utilization(actual_deflection_mm: float, allowable_deflection_mm: float) -> float:
    return _positive(actual_deflection_mm, "actual_deflection_mm", allow_zero=True) / _positive(allowable_deflection_mm, "allowable_deflection_mm")


def fatigue_range_utilization(applied_stress_range_mpa: float, resistance_stress_range_mpa: float) -> float:
    return _positive(applied_stress_range_mpa, "applied_stress_range_mpa", allow_zero=True) / _positive(resistance_stress_range_mpa, "resistance_stress_range_mpa")


def utilization_passes(utilization: float, limit: float = 1.0) -> bool:
    return _positive(utilization, "utilization", allow_zero=True) <= _positive(limit, "limit")
