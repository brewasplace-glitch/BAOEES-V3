"""Phoenix Engineering Kernel Reinforced Concrete Design Wave 1.

Generic SI-based reinforced-concrete design primitives. Project-specific
standards, partial factors, detailing rules and national annexes remain external.
"""

from __future__ import annotations

import math
from typing import Iterable


class ConcreteDesignError(ValueError):
    """Raised when reinforced-concrete design input is invalid."""


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConcreteDesignError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise ConcreteDesignError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise ConcreteDesignError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise ConcreteDesignError(f"{name} must be greater than zero.")
    return number


def concrete_design_strength(fck_mpa: float, alpha_cc: float, gamma_c: float) -> float:
    return (
        _positive(fck_mpa, "fck_mpa")
        * _positive(alpha_cc, "alpha_cc")
        / _positive(gamma_c, "gamma_c")
    )


def concrete_mean_tensile_strength(fck_mpa: float) -> float:
    fck = _positive(fck_mpa, "fck_mpa")
    return 0.3 * fck ** (2.0 / 3.0)


def concrete_elastic_modulus(fcm_mpa: float) -> float:
    fcm = _positive(fcm_mpa, "fcm_mpa")
    return 22000.0 * (fcm / 10.0) ** 0.3


def concrete_unit_weight(
    density_kg_m3: float = 2400.0,
    gravity_m_s2: float = 9.80665,
) -> float:
    return (
        _positive(density_kg_m3, "density_kg_m3")
        * _positive(gravity_m_s2, "gravity_m_s2")
        / 1000.0
    )


def concrete_section_self_weight(
    width_m: float,
    depth_m: float,
    unit_weight_kn_m3: float = 24.0,
) -> float:
    return (
        _positive(width_m, "width_m")
        * _positive(depth_m, "depth_m")
        * _positive(unit_weight_kn_m3, "unit_weight_kn_m3")
    )


def steel_design_strength(fyk_mpa: float, gamma_s: float) -> float:
    return _positive(fyk_mpa, "fyk_mpa") / _positive(gamma_s, "gamma_s")


def bar_area(diameter_mm: float) -> float:
    diameter = _positive(diameter_mm, "diameter_mm")
    return math.pi * diameter**2 / 4.0


def total_reinforcement_area(diameter_mm: float, number_of_bars: int) -> float:
    if not isinstance(number_of_bars, int) or number_of_bars <= 0:
        raise ConcreteDesignError("number_of_bars must be a positive integer.")
    return bar_area(diameter_mm) * number_of_bars


def reinforcement_ratio(as_mm2: float, width_mm: float, effective_depth_mm: float) -> float:
    return _positive(as_mm2, "as_mm2") / (
        _positive(width_mm, "width_mm") * _positive(effective_depth_mm, "effective_depth_mm")
    )


def effective_depth(
    total_depth_mm: float,
    cover_mm: float,
    stirrup_diameter_mm: float,
    bar_diameter_mm: float,
) -> float:
    result = (
        _positive(total_depth_mm, "total_depth_mm")
        - _positive(cover_mm, "cover_mm", allow_zero=True)
        - _positive(stirrup_diameter_mm, "stirrup_diameter_mm", allow_zero=True)
        - 0.5 * _positive(bar_diameter_mm, "bar_diameter_mm")
    )
    if result <= 0.0:
        raise ConcreteDesignError("effective depth must be greater than zero.")
    return result


def lever_arm(effective_depth_mm: float, factor: float = 0.9) -> float:
    k = _positive(factor, "factor")
    if k > 1.0:
        raise ConcreteDesignError("factor cannot exceed 1.0.")
    return _positive(effective_depth_mm, "effective_depth_mm") * k


def required_tension_reinforcement(
    design_moment_kn_m: float,
    steel_design_strength_mpa: float,
    lever_arm_mm: float,
) -> float:
    moment_n_mm = _positive(design_moment_kn_m, "design_moment_kn_m", allow_zero=True) * 1e6
    return moment_n_mm / (
        _positive(steel_design_strength_mpa, "steel_design_strength_mpa")
        * _positive(lever_arm_mm, "lever_arm_mm")
    )


def minimum_reinforcement_area(
    ratio_min: float,
    width_mm: float,
    effective_depth_mm: float,
) -> float:
    return (
        _positive(ratio_min, "ratio_min", allow_zero=True)
        * _positive(width_mm, "width_mm")
        * _positive(effective_depth_mm, "effective_depth_mm")
    )


def maximum_reinforcement_area(
    ratio_max: float,
    width_mm: float,
    effective_depth_mm: float,
) -> float:
    return (
        _positive(ratio_max, "ratio_max")
        * _positive(width_mm, "width_mm")
        * _positive(effective_depth_mm, "effective_depth_mm")
    )


def flexural_utilization(provided_as_mm2: float, required_as_mm2: float) -> float:
    required = _positive(required_as_mm2, "required_as_mm2")
    provided = _positive(provided_as_mm2, "provided_as_mm2", allow_zero=True)
    if provided == 0.0:
        return math.inf
    return required / provided


def concrete_shear_stress(
    shear_force_kn: float,
    width_mm: float,
    effective_depth_mm: float,
) -> float:
    return (
        _positive(shear_force_kn, "shear_force_kn", allow_zero=True) * 1000.0
        / (_positive(width_mm, "width_mm") * _positive(effective_depth_mm, "effective_depth_mm"))
    )


def concrete_shear_capacity(
    shear_resistance_mpa: float,
    width_mm: float,
    effective_depth_mm: float,
) -> float:
    return (
        _positive(shear_resistance_mpa, "shear_resistance_mpa")
        * _positive(width_mm, "width_mm")
        * _positive(effective_depth_mm, "effective_depth_mm")
        / 1000.0
    )


def required_shear_reinforcement_per_length(
    shear_force_kn: float,
    steel_design_strength_mpa: float,
    lever_arm_mm: float,
    cot_theta: float = 1.0,
) -> float:
    return (
        _positive(shear_force_kn, "shear_force_kn", allow_zero=True) * 1000.0
        / (
            _positive(steel_design_strength_mpa, "steel_design_strength_mpa")
            * _positive(lever_arm_mm, "lever_arm_mm")
            * _positive(cot_theta, "cot_theta")
        )
    )


def stirrup_spacing(
    stirrup_area_mm2: float,
    required_asw_per_s_mm2_per_mm: float,
) -> float:
    demand = _positive(
        required_asw_per_s_mm2_per_mm,
        "required_asw_per_s_mm2_per_mm",
    )
    return _positive(stirrup_area_mm2, "stirrup_area_mm2") / demand


def shear_utilization(applied_shear_kn: float, resistance_shear_kn: float) -> float:
    return _positive(applied_shear_kn, "applied_shear_kn", allow_zero=True) / _positive(
        resistance_shear_kn, "resistance_shear_kn"
    )


def axial_concrete_capacity(
    concrete_design_strength_mpa: float,
    concrete_area_mm2: float,
    reduction_factor: float = 1.0,
) -> float:
    return (
        _positive(concrete_design_strength_mpa, "concrete_design_strength_mpa")
        * _positive(concrete_area_mm2, "concrete_area_mm2")
        * _positive(reduction_factor, "reduction_factor")
        / 1000.0
    )


def axial_steel_capacity(
    steel_design_strength_mpa: float,
    steel_area_mm2: float,
) -> float:
    return (
        _positive(steel_design_strength_mpa, "steel_design_strength_mpa")
        * _positive(steel_area_mm2, "steel_area_mm2")
        / 1000.0
    )


def combined_axial_capacity(
    concrete_capacity_kn: float,
    steel_capacity_kn: float,
) -> float:
    return _positive(
        concrete_capacity_kn, "concrete_capacity_kn", allow_zero=True
    ) + _positive(steel_capacity_kn, "steel_capacity_kn", allow_zero=True)


def column_slenderness(effective_length_mm: float, radius_of_gyration_mm: float) -> float:
    return _positive(effective_length_mm, "effective_length_mm") / _positive(
        radius_of_gyration_mm, "radius_of_gyration_mm"
    )


def interaction_index(
    axial_load_kn: float,
    axial_capacity_kn: float,
    design_moment_kn_m: float,
    moment_capacity_kn_m: float,
) -> float:
    return (
        _positive(axial_load_kn, "axial_load_kn", allow_zero=True)
        / _positive(axial_capacity_kn, "axial_capacity_kn")
        + _positive(design_moment_kn_m, "design_moment_kn_m", allow_zero=True)
        / _positive(moment_capacity_kn_m, "moment_capacity_kn_m")
    )


def crack_control_ratio(provided_area_mm2: float, required_area_mm2: float) -> float:
    return _positive(provided_area_mm2, "provided_area_mm2", allow_zero=True) / _positive(
        required_area_mm2, "required_area_mm2"
    )


def deflection_utilization(calculated_deflection_mm: float, allowable_deflection_mm: float) -> float:
    return _positive(
        calculated_deflection_mm, "calculated_deflection_mm", allow_zero=True
    ) / _positive(allowable_deflection_mm, "allowable_deflection_mm")


def nominal_cover(
    minimum_cover_mm: float,
    deviation_allowance_mm: float,
) -> float:
    return _positive(
        minimum_cover_mm, "minimum_cover_mm", allow_zero=True
    ) + _positive(deviation_allowance_mm, "deviation_allowance_mm", allow_zero=True)


def anchorage_length(
    bar_diameter_mm: float,
    steel_stress_mpa: float,
    design_bond_strength_mpa: float,
    coefficient: float = 4.0,
) -> float:
    return (
        _positive(bar_diameter_mm, "bar_diameter_mm")
        * _positive(steel_stress_mpa, "steel_stress_mpa")
        / (
            _positive(coefficient, "coefficient")
            * _positive(design_bond_strength_mpa, "design_bond_strength_mpa")
        )
    )


def development_length(
    basic_anchorage_length_mm: float,
    modification_factors: Iterable[float],
) -> float:
    length = _positive(basic_anchorage_length_mm, "basic_anchorage_length_mm")
    factors = tuple(_positive(v, "modification_factor") for v in modification_factors)
    if not factors:
        raise ConcreteDesignError("modification_factors cannot be empty.")
    for factor in factors:
        length *= factor
    return length


def serviceability_passes(utilization: float, limit: float = 1.0) -> bool:
    return _positive(utilization, "utilization", allow_zero=True) <= _positive(limit, "limit")
