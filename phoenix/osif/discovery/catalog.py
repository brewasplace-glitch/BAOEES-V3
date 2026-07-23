"""Default discovery candidate catalog for BB2."""

from __future__ import annotations

from phoenix.osif import Capability
from .service import DiscoveryCandidate


def default_candidates() -> tuple[DiscoveryCandidate, ...]:
    return (
        DiscoveryCandidate(
            application_id="ifcopenshell",
            name="IfcOpenShell",
            adapter_id="phoenix.osif.adapter.ifcopenshell",
            execution_mode="python",
            python_modules=("ifcopenshell",),
            capabilities=(
                Capability(
                    "ifc.read",
                    "Read IFC",
                    ("ifc",),
                    ("json",),
                ),
                Capability(
                    "ifc.write",
                    "Write IFC",
                    ("json",),
                    ("ifc",),
                ),
            ),
            license_id="LGPL-3.0-or-later",
            metadata={"integration_status": "planned_adapter"},
        ),
        DiscoveryCandidate(
            application_id="freecad",
            name="FreeCAD",
            adapter_id="phoenix.osif.adapter.freecad",
            execution_mode="cli",
            executable_names=("FreeCADCmd.exe", "FreeCADCmd", "freecadcmd"),
            capabilities=(
                Capability(
                    "cad.convert",
                    "Convert CAD geometry",
                    ("step", "stp", "iges", "igs"),
                    ("step", "stl", "obj"),
                ),
            ),
            license_id="LGPL-2.0-or-later",
            metadata={"integration_status": "planned_adapter"},
        ),
        DiscoveryCandidate(
            application_id="blender",
            name="Blender",
            adapter_id="phoenix.osif.adapter.blender",
            execution_mode="cli",
            executable_names=("blender.exe", "blender"),
            capabilities=(
                Capability(
                    "visualization.render",
                    "Render visualization",
                    ("blend", "obj", "gltf", "glb"),
                    ("png", "jpg", "mp4"),
                ),
            ),
            license_id="GPL-3.0-or-later",
            metadata={"integration_status": "planned_adapter"},
        ),
        DiscoveryCandidate(
            application_id="qgis",
            name="QGIS",
            adapter_id="phoenix.osif.adapter.qgis",
            execution_mode="cli",
            executable_names=("qgis_process.exe", "qgis_process"),
            python_modules=("qgis.core",),
            capabilities=(
                Capability(
                    "gis.process",
                    "Run GIS processing",
                    ("geojson", "gpkg", "shp", "tif"),
                    ("geojson", "gpkg", "csv", "png"),
                ),
            ),
            license_id="GPL-2.0-or-later",
            metadata={"integration_status": "planned_adapter"},
        ),
    )
