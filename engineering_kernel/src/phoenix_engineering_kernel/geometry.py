"""Phoenix Engineering Kernel Geometry Wave 1.

Implements PEK-GEOM-0001 through PEK-GEOM-0025.
All calculations are deterministic and unit-agnostic: coordinates supplied
to one operation must use one consistent linear unit.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


class GeometryError(ValueError):
    """Raised when a geometric operation receives invalid input."""


def _finite(value: float, name: str = "value") -> float:
    number = float(value)
    if not math.isfinite(number):
        raise GeometryError(f"{name} must be finite.")
    return number


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, "x"))
        object.__setattr__(self, "y", _finite(self.y, "y"))


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, "x"))
        object.__setattr__(self, "y", _finite(self.y, "y"))
        object.__setattr__(self, "z", _finite(self.z, "z"))


@dataclass(frozen=True)
class BoundingBox2D:
    minimum: Point2D
    maximum: Point2D

    @property
    def width(self) -> float:
        return self.maximum.x - self.minimum.x

    @property
    def height(self) -> float:
        return self.maximum.y - self.minimum.y


def point_2d(x: float, y: float) -> Point2D:
    return Point2D(x, y)


def point_3d(x: float, y: float, z: float) -> Point3D:
    return Point3D(x, y, z)


def distance_2d(a: Point2D, b: Point2D) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def distance_3d(a: Point3D, b: Point3D) -> float:
    return math.sqrt((b.x-a.x)**2 + (b.y-a.y)**2 + (b.z-a.z)**2)


def midpoint_2d(a: Point2D, b: Point2D) -> Point2D:
    return Point2D((a.x+b.x)/2.0, (a.y+b.y)/2.0)


def midpoint_3d(a: Point3D, b: Point3D) -> Point3D:
    return Point3D((a.x+b.x)/2.0, (a.y+b.y)/2.0, (a.z+b.z)/2.0)


def vector_2d(a: Point2D, b: Point2D) -> tuple[float, float]:
    return b.x-a.x, b.y-a.y


def vector_3d(a: Point3D, b: Point3D) -> tuple[float, float, float]:
    return b.x-a.x, b.y-a.y, b.z-a.z


def dot_2d(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != 2 or len(b) != 2:
        raise GeometryError("2D vectors must contain exactly two values.")
    return _finite(a[0])*_finite(b[0]) + _finite(a[1])*_finite(b[1])


def dot_3d(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != 3 or len(b) != 3:
        raise GeometryError("3D vectors must contain exactly three values.")
    return sum(_finite(x)*_finite(y) for x, y in zip(a, b))


def cross_2d(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != 2 or len(b) != 2:
        raise GeometryError("2D vectors must contain exactly two values.")
    return _finite(a[0])*_finite(b[1]) - _finite(a[1])*_finite(b[0])


def cross_3d(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    if len(a) != 3 or len(b) != 3:
        raise GeometryError("3D vectors must contain exactly three values.")
    ax, ay, az = map(_finite, a)
    bx, by, bz = map(_finite, b)
    return ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx


def vector_length_2d(vector: Sequence[float]) -> float:
    if len(vector) != 2:
        raise GeometryError("2D vector must contain exactly two values.")
    return math.hypot(_finite(vector[0]), _finite(vector[1]))


def vector_length_3d(vector: Sequence[float]) -> float:
    if len(vector) != 3:
        raise GeometryError("3D vector must contain exactly three values.")
    return math.sqrt(sum(_finite(value)**2 for value in vector))


def normalize_vector_2d(vector: Sequence[float]) -> tuple[float, float]:
    length = vector_length_2d(vector)
    if length == 0.0:
        raise GeometryError("Zero vector cannot be normalized.")
    return _finite(vector[0])/length, _finite(vector[1])/length


def normalize_vector_3d(vector: Sequence[float]) -> tuple[float, float, float]:
    length = vector_length_3d(vector)
    if length == 0.0:
        raise GeometryError("Zero vector cannot be normalized.")
    return tuple(_finite(value)/length for value in vector)


def angle_between_vectors_2d(a: Sequence[float], b: Sequence[float]) -> float:
    la, lb = vector_length_2d(a), vector_length_2d(b)
    if la == 0.0 or lb == 0.0:
        raise GeometryError("Angle is undefined for a zero vector.")
    cosine = max(-1.0, min(1.0, dot_2d(a, b)/(la*lb)))
    return math.acos(cosine)


def polygon_area(points: Sequence[Point2D]) -> float:
    if len(points) < 3:
        raise GeometryError("Polygon requires at least three points.")
    twice_area = math.fsum(
        points[i].x*points[(i+1) % len(points)].y
        - points[(i+1) % len(points)].x*points[i].y
        for i in range(len(points))
    )
    return abs(twice_area)/2.0


def polygon_signed_area(points: Sequence[Point2D]) -> float:
    if len(points) < 3:
        raise GeometryError("Polygon requires at least three points.")
    return math.fsum(
        points[i].x*points[(i+1) % len(points)].y
        - points[(i+1) % len(points)].x*points[i].y
        for i in range(len(points))
    )/2.0


def polygon_perimeter(points: Sequence[Point2D]) -> float:
    if len(points) < 2:
        raise GeometryError("Polyline requires at least two points.")
    return math.fsum(distance_2d(points[i], points[(i+1) % len(points)]) for i in range(len(points)))


def polygon_centroid(points: Sequence[Point2D]) -> Point2D:
    area = polygon_signed_area(points)
    if area == 0.0:
        raise GeometryError("Centroid is undefined for a zero-area polygon.")
    factor = 1.0/(6.0*area)
    cx = cy = 0.0
    for i, current in enumerate(points):
        nxt = points[(i+1) % len(points)]
        cross = current.x*nxt.y - nxt.x*current.y
        cx += (current.x+nxt.x)*cross
        cy += (current.y+nxt.y)*cross
    return Point2D(cx*factor, cy*factor)


def bounding_box_2d(points: Iterable[Point2D]) -> BoundingBox2D:
    data = tuple(points)
    if not data:
        raise GeometryError("At least one point is required.")
    return BoundingBox2D(
        Point2D(min(p.x for p in data), min(p.y for p in data)),
        Point2D(max(p.x for p in data), max(p.y for p in data)),
    )


def translate_2d(point: Point2D, dx: float, dy: float) -> Point2D:
    return Point2D(point.x+_finite(dx, "dx"), point.y+_finite(dy, "dy"))


def rotate_2d(point: Point2D, angle_radians: float, origin: Point2D | None = None) -> Point2D:
    angle = _finite(angle_radians, "angle_radians")
    center = origin or Point2D(0.0, 0.0)
    x, y = point.x-center.x, point.y-center.y
    cosine, sine = math.cos(angle), math.sin(angle)
    return Point2D(center.x+x*cosine-y*sine, center.y+x*sine+y*cosine)


def line_intersection_2d(
    a1: Point2D, a2: Point2D, b1: Point2D, b2: Point2D,
    tolerance: float = 1e-12,
) -> Point2D:
    tol = _finite(tolerance, "tolerance")
    if tol < 0.0:
        raise GeometryError("tolerance cannot be negative.")
    r = vector_2d(a1, a2)
    s = vector_2d(b1, b2)
    denominator = cross_2d(r, s)
    if abs(denominator) <= tol:
        raise GeometryError("Lines are parallel or coincident.")
    q_minus_p = vector_2d(a1, b1)
    t = cross_2d(q_minus_p, s)/denominator
    return Point2D(a1.x+t*r[0], a1.y+t*r[1])
