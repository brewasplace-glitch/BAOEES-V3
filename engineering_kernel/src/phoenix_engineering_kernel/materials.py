"""Phoenix Engineering Kernel Materials Wave 1.

Implements PEK-MATL-0001 through PEK-MATL-0030.

The module provides deterministic material-property containers and common
engineering transformations. Values remain unit-agnostic but must use one
consistent unit system per calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Mapping


class MaterialError(ValueError):
    """Raised when material data or a material calculation is invalid."""


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise MaterialError(f"{name} must be finite.")
    return number


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    number = _finite(value, name)
    if allow_zero:
        if number < 0.0:
            raise MaterialError(f"{name} cannot be negative.")
    elif number <= 0.0:
        raise MaterialError(f"{name} must be greater than zero.")
    return number


@dataclass(frozen=True)
class Material:
    name: str
    category: str
    density: float
    elastic_modulus: float
    poisson_ratio: float
    tensile_strength: float | None = None
    compressive_strength: float | None = None
    shear_strength: float | None = None
    thermal_expansion: float | None = None
    moisture_factor: float = 1.0
    temperature_factor: float = 1.0
    metadata: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise MaterialError("name cannot be empty.")
        if not self.category.strip():
            raise MaterialError("category cannot be empty.")
        _positive(self.density, "density")
        _positive(self.elastic_modulus, "elastic_modulus")
        nu = _finite(self.poisson_ratio, "poisson_ratio")
        if not -1.0 < nu < 0.5:
            raise MaterialError("poisson_ratio must lie between -1.0 and 0.5.")
        for field_name in ("tensile_strength", "compressive_strength", "shear_strength"):
            value = getattr(self, field_name)
            if value is not None:
                _positive(value, field_name)
        if self.thermal_expansion is not None:
            _positive(self.thermal_expansion, "thermal_expansion", allow_zero=True)
        _positive(self.moisture_factor, "moisture_factor")
        _positive(self.temperature_factor, "temperature_factor")


def create_material(
    name: str,
    category: str,
    density: float,
    elastic_modulus: float,
    poisson_ratio: float,
    **properties: float,
) -> Material:
    return Material(
        name=name,
        category=category,
        density=density,
        elastic_modulus=elastic_modulus,
        poisson_ratio=poisson_ratio,
        **properties,
    )


def concrete_material(
    name: str, density: float, elastic_modulus: float,
    compressive_strength: float, tensile_strength: float,
    poisson_ratio: float = 0.20,
) -> Material:
    return Material(name, "concrete", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength, compressive_strength=compressive_strength)


def structural_steel_material(
    name: str, yield_strength: float, tensile_strength: float,
    density: float = 7850.0, elastic_modulus: float = 210000.0,
    poisson_ratio: float = 0.30,
) -> Material:
    return Material(name, "structural_steel", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength, metadata={"yield_strength": str(_positive(yield_strength, "yield_strength"))})


def reinforcement_steel_material(
    name: str, yield_strength: float, tensile_strength: float,
    density: float = 7850.0, elastic_modulus: float = 200000.0,
    poisson_ratio: float = 0.30,
) -> Material:
    return Material(name, "reinforcement_steel", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength, metadata={"yield_strength": str(_positive(yield_strength, "yield_strength"))})


def timber_material(
    name: str, density: float, elastic_modulus: float,
    tensile_strength: float, compressive_strength: float,
    shear_strength: float, poisson_ratio: float = 0.35,
) -> Material:
    return Material(name, "timber", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength, compressive_strength=compressive_strength,
                    shear_strength=shear_strength)


def masonry_material(
    name: str, density: float, elastic_modulus: float,
    compressive_strength: float, tensile_strength: float,
    poisson_ratio: float = 0.20,
) -> Material:
    return Material(name, "masonry", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength, compressive_strength=compressive_strength)


def aluminium_material(
    name: str, tensile_strength: float, density: float = 2700.0,
    elastic_modulus: float = 70000.0, poisson_ratio: float = 0.33,
) -> Material:
    return Material(name, "aluminium", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength)


def glass_material(
    name: str, tensile_strength: float, density: float = 2500.0,
    elastic_modulus: float = 70000.0, poisson_ratio: float = 0.22,
) -> Material:
    return Material(name, "glass", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength)


def plastic_material(
    name: str, density: float, elastic_modulus: float,
    tensile_strength: float, poisson_ratio: float,
) -> Material:
    return Material(name, "plastic", density, elastic_modulus, poisson_ratio,
                    tensile_strength=tensile_strength)


def soil_material(
    name: str, density: float, elastic_modulus: float,
    shear_strength: float, poisson_ratio: float,
) -> Material:
    return Material(name, "soil", density, elastic_modulus, poisson_ratio,
                    shear_strength=shear_strength)


def shear_modulus(elastic_modulus: float, poisson_ratio: float) -> float:
    e = _positive(elastic_modulus, "elastic_modulus")
    nu = _finite(poisson_ratio, "poisson_ratio")
    if not -1.0 < nu < 0.5:
        raise MaterialError("poisson_ratio must lie between -1.0 and 0.5.")
    return e / (2.0 * (1.0 + nu))


def bulk_modulus(elastic_modulus: float, poisson_ratio: float) -> float:
    e = _positive(elastic_modulus, "elastic_modulus")
    nu = _finite(poisson_ratio, "poisson_ratio")
    if not -1.0 < nu < 0.5:
        raise MaterialError("poisson_ratio must lie between -1.0 and 0.5.")
    denominator = 3.0 * (1.0 - 2.0 * nu)
    if denominator == 0.0:
        raise MaterialError("bulk modulus is undefined for poisson_ratio = 0.5.")
    return e / denominator


def specific_weight(density: float, gravitational_acceleration: float = 9.80665) -> float:
    return _positive(density, "density") * _positive(gravitational_acceleration, "gravitational_acceleration")


def stress(force: float, area: float) -> float:
    return _finite(force, "force") / _positive(area, "area")


def strain(change_in_length: float, original_length: float) -> float:
    return _finite(change_in_length, "change_in_length") / _positive(original_length, "original_length")


def elastic_stress(elastic_modulus: float, strain_value: float) -> float:
    return _positive(elastic_modulus, "elastic_modulus") * _finite(strain_value, "strain")


def elastic_strain(stress_value: float, elastic_modulus: float) -> float:
    return _finite(stress_value, "stress") / _positive(elastic_modulus, "elastic_modulus")


def characteristic_to_design_value(characteristic_value: float, partial_factor: float) -> float:
    return _positive(characteristic_value, "characteristic_value") / _positive(partial_factor, "partial_factor")


def design_to_characteristic_value(design_value: float, partial_factor: float) -> float:
    return _positive(design_value, "design_value") * _positive(partial_factor, "partial_factor")


def safety_factor(capacity: float, demand: float) -> float:
    demand_value = _positive(demand, "demand")
    return _positive(capacity, "capacity") / demand_value


def utilization_ratio(demand: float, design_capacity: float) -> float:
    return _positive(demand, "demand", allow_zero=True) / _positive(design_capacity, "design_capacity")


def apply_temperature_factor(value: float, factor: float) -> float:
    return _finite(value, "value") * _positive(factor, "factor")


def apply_moisture_factor(value: float, factor: float) -> float:
    return _finite(value, "value") * _positive(factor, "factor")


def thermal_strain(thermal_expansion: float, temperature_change: float) -> float:
    return _positive(thermal_expansion, "thermal_expansion", allow_zero=True) * _finite(temperature_change, "temperature_change")


def thermal_expansion_length(length: float, thermal_expansion: float, temperature_change: float) -> float:
    return _positive(length, "length") * thermal_strain(thermal_expansion, temperature_change)


def creep_adjusted_modulus(elastic_modulus: float, creep_coefficient: float) -> float:
    e = _positive(elastic_modulus, "elastic_modulus")
    phi = _positive(creep_coefficient, "creep_coefficient", allow_zero=True)
    return e / (1.0 + phi)


def shrinkage_deformation(length: float, shrinkage_strain: float) -> float:
    return _positive(length, "length") * _finite(shrinkage_strain, "shrinkage_strain")


def classify_material(material: Material) -> str:
    return material.category.strip().lower()


def validate_material(material: Material) -> bool:
    Material(**material.__dict__)
    return True


def adjusted_material(
    material: Material,
    *,
    moisture_factor: float | None = None,
    temperature_factor: float | None = None,
) -> Material:
    updates = {}
    if moisture_factor is not None:
        updates["moisture_factor"] = _positive(moisture_factor, "moisture_factor")
    if temperature_factor is not None:
        updates["temperature_factor"] = _positive(temperature_factor, "temperature_factor")
    return replace(material, **updates)
