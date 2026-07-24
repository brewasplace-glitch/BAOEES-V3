"""GIS datasource helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_FILE_EXTENSIONS = {
    ".geojson": "ogr",
    ".json": "ogr",
    ".gpkg": "ogr",
    ".shp": "ogr",
    ".dxf": "ogr",
    ".csv": "delimitedtext",
    ".tif": "gdal",
    ".tiff": "gdal",
}


def provider_for_path(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_FILE_EXTENSIONS:
        raise ValueError(f"Unsupported GIS datasource extension: {suffix}")
    return SUPPORTED_FILE_EXTENSIONS[suffix]


def validate_geojson(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("type") not in {"FeatureCollection", "Feature"}:
        raise ValueError("GeoJSON must be a FeatureCollection or Feature")
    return payload


def write_geojson(path: str | Path, features: list[dict]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "features": features,
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
