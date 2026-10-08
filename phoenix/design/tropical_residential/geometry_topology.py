from __future__ import annotations

from typing import Any, Mapping

from .open_source_spatial_engine import synthesize_with_open_source_engines


def apply_geometry_topology(
    layout: Mapping[str, Any],
    variant: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Thin Phoenix adapter around the open-source spatial engine stack."""
    return synthesize_with_open_source_engines(layout, variant)
