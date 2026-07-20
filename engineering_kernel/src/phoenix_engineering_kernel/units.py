from __future__ import annotations
from dataclasses import dataclass
import math
import re
from typing import Mapping

class UnitError(ValueError):
    pass

Dimension = tuple[int, int, int, int]

@dataclass(frozen=True)
class UnitDefinition:
    symbol: str
    dimension: Dimension
    scale_to_si: float
    offset_to_si: float = 0.0
    def to_si(self, value: float) -> float:
        return (float(value) + self.offset_to_si) * self.scale_to_si
    def from_si(self, value: float) -> float:
        return float(value) / self.scale_to_si - self.offset_to_si

@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    dimension: Dimension
    si_value: float
    def convert_to(self, unit: str, registry: "UnitRegistry | None" = None) -> "Quantity":
        return (registry or DEFAULT_REGISTRY).convert(self, unit)

class UnitRegistry:
    def __init__(self, definitions: Mapping[str, UnitDefinition] | None = None) -> None:
        self._units = {}
        if definitions:
            for item in definitions.values():
                self.register(item)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        value = re.sub(r"\s+", "", str(symbol)).replace("²", "2").replace("³", "3")
        return {"N/mm2": "MPa", "kN/m2": "kPa"}.get(value, value)

    def register(self, item: UnitDefinition) -> None:
        symbol = self.normalize_symbol(item.symbol)
        if not symbol or not math.isfinite(item.scale_to_si) or item.scale_to_si <= 0:
            raise UnitError("Invalid unit definition.")
        self._units[symbol] = UnitDefinition(symbol, item.dimension, float(item.scale_to_si), float(item.offset_to_si))

    def definition(self, symbol: str) -> UnitDefinition:
        key = self.normalize_symbol(symbol)
        if key not in self._units:
            raise UnitError(f"Unknown unit: {symbol}")
        return self._units[key]

    def parse(self, value: float, unit: str) -> Quantity:
        number = float(value)
        if not math.isfinite(number):
            raise UnitError("Quantity value must be finite.")
        item = self.definition(unit)
        return Quantity(number, item.symbol, item.dimension, item.to_si(number))

    def compatible(self, first: str, second: str) -> bool:
        return self.definition(first).dimension == self.definition(second).dimension

    def require_compatible(self, first: str, second: str) -> None:
        if not self.compatible(first, second):
            raise UnitError(f"Incompatible units: {first} and {second}")

    def convert(self, value_or_quantity, target_unit: str, source_unit: str | None = None) -> Quantity:
        if isinstance(value_or_quantity, Quantity):
            source = self.definition(value_or_quantity.unit)
            si_value = value_or_quantity.si_value
        else:
            if source_unit is None:
                raise UnitError("source_unit is required.")
            source = self.definition(source_unit)
            si_value = source.to_si(float(value_or_quantity))
        target = self.definition(target_unit)
        if source.dimension != target.dimension:
            raise UnitError(f"Incompatible units: {source.symbol} and {target.symbol}")
        return Quantity(target.from_si(si_value), target.symbol, target.dimension, si_value)

LENGTH=(1,0,0,0); AREA=(2,0,0,0); VOLUME=(3,0,0,0); MASS=(0,1,0,0)
TIME=(0,0,1,0); TEMPERATURE=(0,0,0,1); FORCE=(1,1,-2,0); PRESSURE=(-1,1,-2,0)
DENSITY=(-3,1,0,0); ACCELERATION=(1,0,-2,0); ENERGY=(2,1,-2,0)
POWER=(2,1,-3,0); ANGLE=(0,0,0,0)

_defs = [
 UnitDefinition("m",LENGTH,1), UnitDefinition("mm",LENGTH,1e-3), UnitDefinition("cm",LENGTH,1e-2), UnitDefinition("km",LENGTH,1e3),
 UnitDefinition("m2",AREA,1), UnitDefinition("mm2",AREA,1e-6), UnitDefinition("cm2",AREA,1e-4),
 UnitDefinition("m3",VOLUME,1), UnitDefinition("mm3",VOLUME,1e-9), UnitDefinition("cm3",VOLUME,1e-6), UnitDefinition("L",VOLUME,1e-3),
 UnitDefinition("kg",MASS,1), UnitDefinition("g",MASS,1e-3), UnitDefinition("t",MASS,1e3),
 UnitDefinition("s",TIME,1), UnitDefinition("min",TIME,60), UnitDefinition("h",TIME,3600),
 UnitDefinition("N",FORCE,1), UnitDefinition("kN",FORCE,1e3), UnitDefinition("MN",FORCE,1e6),
 UnitDefinition("Pa",PRESSURE,1), UnitDefinition("kPa",PRESSURE,1e3), UnitDefinition("MPa",PRESSURE,1e6), UnitDefinition("GPa",PRESSURE,1e9),
 UnitDefinition("kg/m3",DENSITY,1), UnitDefinition("t/m3",DENSITY,1e3),
 UnitDefinition("m/s2",ACCELERATION,1), UnitDefinition("J",ENERGY,1), UnitDefinition("kJ",ENERGY,1e3),
 UnitDefinition("W",POWER,1), UnitDefinition("kW",POWER,1e3),
 UnitDefinition("rad",ANGLE,1), UnitDefinition("deg",ANGLE,math.pi/180),
 UnitDefinition("K",TEMPERATURE,1), UnitDefinition("degC",TEMPERATURE,1,273.15)
]
DEFAULT_REGISTRY = UnitRegistry({x.symbol:x for x in _defs})

def quantity(value, unit): return DEFAULT_REGISTRY.parse(value, unit)
def convert(value, source_unit, target_unit): return DEFAULT_REGISTRY.convert(value, target_unit, source_unit).value

def _typed(value, source, target, dimension):
    DEFAULT_REGISTRY.require_compatible(source, target)
    if DEFAULT_REGISTRY.definition(source).dimension != dimension:
        raise UnitError("Unexpected unit dimension.")
    return convert(value, source, target)

def convert_length(v,s,t): return _typed(v,s,t,LENGTH)
def convert_area(v,s,t): return _typed(v,s,t,AREA)
def convert_volume(v,s,t): return _typed(v,s,t,VOLUME)
def convert_mass(v,s,t): return _typed(v,s,t,MASS)
def convert_time(v,s,t): return _typed(v,s,t,TIME)
def convert_force(v,s,t): return _typed(v,s,t,FORCE)
def convert_pressure(v,s,t): return _typed(v,s,t,PRESSURE)
def convert_density(v,s,t): return _typed(v,s,t,DENSITY)
def convert_acceleration(v,s,t): return _typed(v,s,t,ACCELERATION)
def convert_energy(v,s,t): return _typed(v,s,t,ENERGY)
def convert_power(v,s,t): return _typed(v,s,t,POWER)
def convert_angle(v,s,t): return _typed(v,s,t,ANGLE)
def convert_temperature(v,s,t): return _typed(v,s,t,TEMPERATURE)
def to_si(value, unit): return DEFAULT_REGISTRY.definition(unit).to_si(value)
def from_si(value, unit): return DEFAULT_REGISTRY.definition(unit).from_si(value)
def are_compatible(a,b): return DEFAULT_REGISTRY.compatible(a,b)
def validate_dimension(unit, expected): return DEFAULT_REGISTRY.definition(unit).dimension == expected
def normalized_symbol(unit): return DEFAULT_REGISTRY.definition(unit).symbol
