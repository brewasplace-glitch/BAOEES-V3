"""Phoenix Engineering Kernel Hydraulics & Drainage Engine Wave 1.

Generic SI-based hydraulic and drainage primitives. Project-specific
design storms, standards and safety factors are intentionally external.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


class HydraulicsError(ValueError):
    """Raised when hydraulic input is invalid."""


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HydraulicsError(f"{name} must be numeric.") from exc
    if not math.isfinite(number):
        raise HydraulicsError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0:
            raise HydraulicsError(f"{name} cannot be negative.")
    elif number <= 0:
        raise HydraulicsError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class CircularConduit:
    diameter: float
    slope: float
    roughness_manning: float

    def __post_init__(self) -> None:
        _positive(self.diameter, "diameter")
        _positive(self.slope, "slope")
        _positive(self.roughness_manning, "roughness_manning")


def rainfall_depth(intensity_mm_per_h: float, duration_h: float) -> float:
    return _positive(intensity_mm_per_h, "intensity_mm_per_h", allow_zero=True) * _positive(
        duration_h, "duration_h", allow_zero=True
    )


def rainfall_volume(area_m2: float, rainfall_depth_mm: float) -> float:
    return _positive(area_m2, "area_m2", allow_zero=True) * _positive(
        rainfall_depth_mm, "rainfall_depth_mm", allow_zero=True
    ) / 1000.0


def runoff_volume(area_m2: float, rainfall_depth_mm: float, runoff_coefficient: float) -> float:
    c = _finite(runoff_coefficient, "runoff_coefficient")
    if not 0.0 <= c <= 1.0:
        raise HydraulicsError("runoff_coefficient must be between 0 and 1.")
    return rainfall_volume(area_m2, rainfall_depth_mm) * c


def rational_method_flow(runoff_coefficient: float, intensity_mm_per_h: float, area_m2: float) -> float:
    c = _finite(runoff_coefficient, "runoff_coefficient")
    if not 0.0 <= c <= 1.0:
        raise HydraulicsError("runoff_coefficient must be between 0 and 1.")
    intensity = _positive(intensity_mm_per_h, "intensity_mm_per_h", allow_zero=True)
    area = _positive(area_m2, "area_m2", allow_zero=True)
    return c * intensity * area / 3_600_000.0


def weighted_runoff_coefficient(areas_m2, coefficients) -> float:
    areas = tuple(float(v) for v in areas_m2)
    coeffs = tuple(float(v) for v in coefficients)
    if len(areas) != len(coeffs) or not areas:
        raise HydraulicsError("areas_m2 and coefficients must have equal non-zero length.")
    total = sum(_positive(v, "area", allow_zero=True) for v in areas)
    if total <= 0:
        raise HydraulicsError("total area must be greater than zero.")
    for c in coeffs:
        if not 0.0 <= c <= 1.0:
            raise HydraulicsError("all coefficients must be between 0 and 1.")
    return sum(a * c for a, c in zip(areas, coeffs)) / total


def circular_area(diameter: float) -> float:
    d = _positive(diameter, "diameter")
    return math.pi * d**2 / 4.0


def circular_wetted_perimeter_full(diameter: float) -> float:
    return math.pi * _positive(diameter, "diameter")


def circular_hydraulic_radius_full(diameter: float) -> float:
    return _positive(diameter, "diameter") / 4.0


def rectangular_area(width: float, depth: float) -> float:
    return _positive(width, "width") * _positive(depth, "depth")


def rectangular_wetted_perimeter(width: float, depth: float) -> float:
    return _positive(width, "width") + 2.0 * _positive(depth, "depth")


def hydraulic_radius(area: float, wetted_perimeter: float) -> float:
    return _positive(area, "area") / _positive(wetted_perimeter, "wetted_perimeter")


def manning_velocity(hydraulic_radius_m: float, slope: float, roughness_n: float) -> float:
    r = _positive(hydraulic_radius_m, "hydraulic_radius_m")
    s = _positive(slope, "slope")
    n = _positive(roughness_n, "roughness_n")
    return (r ** (2.0 / 3.0)) * math.sqrt(s) / n


def manning_discharge(area_m2: float, hydraulic_radius_m: float, slope: float, roughness_n: float) -> float:
    return _positive(area_m2, "area_m2") * manning_velocity(
        hydraulic_radius_m, slope, roughness_n
    )


def full_pipe_manning_discharge(diameter_m: float, slope: float, roughness_n: float) -> float:
    return manning_discharge(
        circular_area(diameter_m),
        circular_hydraulic_radius_full(diameter_m),
        slope,
        roughness_n,
    )


def chezy_velocity(chezy_coefficient: float, hydraulic_radius_m: float, slope: float) -> float:
    return _positive(chezy_coefficient, "chezy_coefficient") * math.sqrt(
        _positive(hydraulic_radius_m, "hydraulic_radius_m") * _positive(slope, "slope")
    )


def discharge_from_velocity(area_m2: float, velocity_m_per_s: float) -> float:
    return _positive(area_m2, "area_m2", allow_zero=True) * _finite(
        velocity_m_per_s, "velocity_m_per_s"
    )


def velocity_from_discharge(discharge_m3_per_s: float, area_m2: float) -> float:
    return _finite(discharge_m3_per_s, "discharge_m3_per_s") / _positive(area_m2, "area_m2")


def travel_time(length_m: float, velocity_m_per_s: float) -> float:
    return _positive(length_m, "length_m") / _positive(velocity_m_per_s, "velocity_m_per_s")


def storage_volume(inflow_m3_per_s: float, outflow_m3_per_s: float, duration_s: float) -> float:
    net = _finite(inflow_m3_per_s, "inflow_m3_per_s") - _finite(
        outflow_m3_per_s, "outflow_m3_per_s"
    )
    return max(0.0, net * _positive(duration_s, "duration_s", allow_zero=True))


def detention_time(volume_m3: float, outflow_m3_per_s: float) -> float:
    return _positive(volume_m3, "volume_m3", allow_zero=True) / _positive(
        outflow_m3_per_s, "outflow_m3_per_s"
    )


def infiltration_volume(infiltration_rate_mm_per_h: float, area_m2: float, duration_h: float) -> float:
    return (
        _positive(infiltration_rate_mm_per_h, "infiltration_rate_mm_per_h", allow_zero=True)
        * _positive(area_m2, "area_m2", allow_zero=True)
        * _positive(duration_h, "duration_h", allow_zero=True)
        / 1000.0
    )


def required_infiltration_area(volume_m3: float, infiltration_rate_mm_per_h: float, duration_h: float) -> float:
    rate = _positive(infiltration_rate_mm_per_h, "infiltration_rate_mm_per_h")
    duration = _positive(duration_h, "duration_h")
    return _positive(volume_m3, "volume_m3", allow_zero=True) * 1000.0 / (rate * duration)


def darcy_flow(hydraulic_conductivity_m_per_s: float, gradient: float, area_m2: float) -> float:
    return (
        _positive(hydraulic_conductivity_m_per_s, "hydraulic_conductivity_m_per_s", allow_zero=True)
        * _finite(gradient, "gradient")
        * _positive(area_m2, "area_m2", allow_zero=True)
    )


def pump_capacity(volume_m3: float, emptying_time_s: float) -> float:
    return _positive(volume_m3, "volume_m3", allow_zero=True) / _positive(
        emptying_time_s, "emptying_time_s"
    )


def number_of_outlets(required_flow_m3_per_s: float, outlet_capacity_m3_per_s: float) -> int:
    required = _positive(required_flow_m3_per_s, "required_flow_m3_per_s", allow_zero=True)
    capacity = _positive(outlet_capacity_m3_per_s, "outlet_capacity_m3_per_s")
    return math.ceil(required / capacity)


def water_balance(inflow_m3: float, outflow_m3: float, infiltration_m3: float = 0.0, evaporation_m3: float = 0.0) -> float:
    return (
        _finite(inflow_m3, "inflow_m3")
        - _finite(outflow_m3, "outflow_m3")
        - _positive(infiltration_m3, "infiltration_m3", allow_zero=True)
        - _positive(evaporation_m3, "evaporation_m3", allow_zero=True)
    )


def continuity_error(inflow_m3: float, outflow_m3: float, storage_change_m3: float) -> float:
    inflow = _finite(inflow_m3, "inflow_m3")
    outflow = _finite(outflow_m3, "outflow_m3")
    storage = _finite(storage_change_m3, "storage_change_m3")
    denominator = max(abs(inflow), 1e-12)
    return (inflow - outflow - storage) / denominator


def pipe_fill_ratio(flow_m3_per_s: float, full_capacity_m3_per_s: float) -> float:
    return _positive(flow_m3_per_s, "flow_m3_per_s", allow_zero=True) / _positive(
        full_capacity_m3_per_s, "full_capacity_m3_per_s"
    )


def drainage_specific_discharge(drainage_coefficient_mm_per_day: float) -> float:
    return _positive(
        drainage_coefficient_mm_per_day,
        "drainage_coefficient_mm_per_day",
        allow_zero=True,
    ) / 1000.0 / 86400.0


def roof_outlet_flow(area_m2: float, rainfall_intensity_mm_per_h: float, runoff_coefficient: float = 1.0) -> float:
    return rational_method_flow(runoff_coefficient, rainfall_intensity_mm_per_h, area_m2)


def required_pipe_area(discharge_m3_per_s: float, design_velocity_m_per_s: float) -> float:
    return _positive(discharge_m3_per_s, "discharge_m3_per_s", allow_zero=True) / _positive(
        design_velocity_m_per_s, "design_velocity_m_per_s"
    )


def equivalent_circular_diameter(area_m2: float) -> float:
    return math.sqrt(4.0 * _positive(area_m2, "area_m2") / math.pi)
