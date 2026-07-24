"""Offline-safe spatial analysis primitives."""

from __future__ import annotations

from math import hypot

from .models import SpatialExtent


def extent_intersects(left: SpatialExtent, right: SpatialExtent) -> bool:
    left.validate()
    right.validate()
    if left.crs != right.crs:
        raise ValueError("extent CRS mismatch")
    return not (
        left.xmax < right.xmin
        or left.xmin > right.xmax
        or left.ymax < right.ymin
        or left.ymin > right.ymax
    )


def extent_intersection(
    left: SpatialExtent,
    right: SpatialExtent,
) -> SpatialExtent | None:
    if not extent_intersects(left, right):
        return None
    return SpatialExtent(
        xmin=max(left.xmin, right.xmin),
        ymin=max(left.ymin, right.ymin),
        xmax=min(left.xmax, right.xmax),
        ymax=min(left.ymax, right.ymax),
        crs=left.crs,
    )


def point_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])
