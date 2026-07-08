from dataclasses import dataclass, asdict
from typing import Dict, Any
from project_phoenix.geometry.core.primitives_2d import Point2D, Rectangle2D


@dataclass
class SpaceGeometry:
    space_id: str
    name: str
    function: str
    floor: str
    rectangle: Rectangle2D

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "space_geometry",
            "space_id": self.space_id,
            "name": self.name,
            "function": self.function,
            "floor": self.floor,
            "geometry": self.rectangle.to_dict()
        }


@dataclass
class WallGeometry:
    wall_id: str
    floor: str
    start: Point2D
    end: Point2D
    thickness_m: float = 0.2
    height_m: float = 3.2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "wall_geometry",
            "wall_id": self.wall_id,
            "floor": self.floor,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "thickness_m": self.thickness_m,
            "height_m": self.height_m
        }


@dataclass
class OpeningGeometry:
    opening_id: str
    floor: str
    opening_type: str
    x: float
    y: float
    width_m: float
    height_m: float
    sill_height_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
