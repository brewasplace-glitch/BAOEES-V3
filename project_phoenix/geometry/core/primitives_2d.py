from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import math


@dataclass
class Point2D:
    x: float
    y: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class Line2D:
    start: Point2D
    end: Point2D
    layer: str = "0"

    def length(self) -> float:
        return round(math.sqrt((self.end.x - self.start.x) ** 2 + (self.end.y - self.start.y) ** 2), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "line2d",
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "layer": self.layer,
            "length": self.length()
        }


@dataclass
class Rectangle2D:
    origin: Point2D
    width: float
    depth: float
    layer: str = "0"
    name: str = ""

    def area(self) -> float:
        return round(self.width * self.depth, 4)

    def perimeter(self) -> float:
        return round(2 * (self.width + self.depth), 4)

    def corners(self) -> List[Point2D]:
        x = self.origin.x
        y = self.origin.y
        return [
            Point2D(x, y),
            Point2D(x + self.width, y),
            Point2D(x + self.width, y + self.depth),
            Point2D(x, y + self.depth)
        ]

    def edges(self) -> List[Line2D]:
        c = self.corners()
        return [
            Line2D(c[0], c[1], self.layer),
            Line2D(c[1], c[2], self.layer),
            Line2D(c[2], c[3], self.layer),
            Line2D(c[3], c[0], self.layer),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "rectangle2d",
            "name": self.name,
            "origin": self.origin.to_dict(),
            "width": self.width,
            "depth": self.depth,
            "area": self.area(),
            "perimeter": self.perimeter(),
            "layer": self.layer,
            "corners": [p.to_dict() for p in self.corners()]
        }
