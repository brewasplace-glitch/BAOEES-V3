"""Data models for the Phoenix QGIS integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SpatialExtent:
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    crs: str = "EPSG:4326"

    def validate(self) -> None:
        if self.xmin >= self.xmax:
            raise ValueError("xmin must be smaller than xmax")
        if self.ymin >= self.ymax:
            raise ValueError("ymin must be smaller than ymax")
        if not self.crs.strip():
            raise ValueError("crs must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class GISLayer:
    name: str
    source: str
    provider: str
    geometry_type: str = "unknown"
    crs: str = "EPSG:4326"
    layer_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    style_path: Optional[str] = None
    visible: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("layer name must not be empty")
        if not self.source.strip():
            raise ValueError("layer source must not be empty")
        if not self.provider.strip():
            raise ValueError("layer provider must not be empty")
        if not self.crs.strip():
            raise ValueError("layer crs must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class GISProject:
    name: str
    project_id: str
    crs: str = "EPSG:28992"
    layers: list[GISLayer] = field(default_factory=list)
    extent: Optional[SpatialExtent] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("project name must not be empty")
        if not self.project_id.strip():
            raise ValueError("project_id must not be empty")
        if not self.crs.strip():
            raise ValueError("project crs must not be empty")
        if self.extent is not None:
            self.extent.validate()
        for layer in self.layers:
            layer.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            **asdict(self),
            "layers": [layer.to_dict() for layer in self.layers],
            "extent": self.extent.to_dict() if self.extent else None,
        }
