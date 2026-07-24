"""High-level Phoenix QGIS Integration Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .datasources import provider_for_path
from .layer_registry import LayerRegistry
from .models import GISLayer, GISProject, SpatialExtent
from .project_manager import QGISProjectManager
from .runtime import QGISRuntimeProbe


class QGISIntegrationEngine:
    def __init__(self) -> None:
        self.layers = LayerRegistry()
        self.projects = QGISProjectManager()
        self.runtime = QGISRuntimeProbe()

    def create_project(
        self,
        *,
        name: str,
        project_id: str,
        crs: str = "EPSG:28992",
        extent: Optional[SpatialExtent] = None,
    ) -> GISProject:
        return GISProject(
            name=name,
            project_id=project_id,
            crs=crs,
            extent=extent,
        )

    def add_file_layer(
        self,
        project: GISProject,
        *,
        name: str,
        path: str | Path,
        geometry_type: str = "unknown",
        crs: str = "EPSG:4326",
    ) -> GISLayer:
        source = str(Path(path))
        provider = provider_for_path(source)
        layer = self.layers.add(
            GISLayer(
                name=name,
                source=source,
                provider=provider,
                geometry_type=geometry_type,
                crs=crs,
            )
        )
        project.layers.append(layer)
        return layer

    def save_project(
        self,
        project: GISProject,
        *,
        manifest_path: str | Path,
        qgs_path: str | Path,
    ) -> dict:
        checksum = self.projects.save_manifest(project, manifest_path)
        qgs = self.projects.write_qgs(project, qgs_path)
        return {
            "manifest_checksum_sha256": checksum,
            "qgs_path": str(qgs),
            "runtime": self.runtime.probe().to_dict(),
        }
