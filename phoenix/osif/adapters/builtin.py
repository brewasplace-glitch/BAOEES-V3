"""Built-in OSIF adapters."""

from __future__ import annotations

import importlib.util
import shutil

from phoenix.osif import ApplicationDescriptor, Capability
from .base import AdapterError, OSIFAdapter
from .blender import BlenderAdapter
from .contracts import (
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterHealth,
)
from .freecad import FreeCADAdapter
from .ifcopenshell import IfcOpenShellAdapter


class _DiscoveryOnlyAdapter(OSIFAdapter):
    APPLICATION_ID = ""
    APPLICATION_NAME = ""
    ADAPTER_ID = ""
    EXECUTION_MODE = "cli"
    EXECUTABLE_NAMES: tuple[str, ...] = ()
    PYTHON_MODULES: tuple[str, ...] = ()
    CAPABILITIES: tuple[Capability, ...] = ()

    def descriptor(self) -> ApplicationDescriptor:
        return ApplicationDescriptor(
            application_id=self.APPLICATION_ID,
            name=self.APPLICATION_NAME,
            adapter_id=self.ADAPTER_ID,
            execution_mode=self.EXECUTION_MODE,
            capabilities=self.CAPABILITIES,
            enabled=False,
            metadata={"status": "foundation_only"},
        )

    def _locate(self) -> tuple[str, str]:
        executable = ""
        for name in self.EXECUTABLE_NAMES:
            executable = shutil.which(name) or ""
            if executable:
                break
        module = ""
        for name in self.PYTHON_MODULES:
            if importlib.util.find_spec(name) is not None:
                module = name
                break
        return executable, module

    def health_check(self) -> AdapterHealth:
        executable, module = self._locate()
        available = bool(executable or module)
        return AdapterHealth(
            status="available" if available else "unavailable",
            message=(
                "Dependency discovered."
                if available
                else "Dependency not found."
            ),
            details={"executable": executable, "python_module": module},
        )

    def validate_request(self, request: AdapterExecutionRequest) -> None:
        supported = {item.capability_id for item in self.CAPABILITIES}
        if request.capability_id not in supported:
            raise AdapterError(
                f"Unsupported capability for {self.ADAPTER_ID}: "
                f"{request.capability_id}"
            )

    def _execute(
        self,
        request: AdapterExecutionRequest,
    ) -> AdapterExecutionResult:
        raise AdapterError(
            f"{self.ADAPTER_ID} is a foundation adapter."
        )


class QGISAdapter(_DiscoveryOnlyAdapter):
    APPLICATION_ID = "qgis"
    APPLICATION_NAME = "QGIS"
    ADAPTER_ID = "phoenix.osif.adapter.qgis"
    EXECUTABLE_NAMES = ("qgis_process.exe", "qgis_process")
    PYTHON_MODULES = ("qgis.core",)
    CAPABILITIES = (
        Capability(
            "gis.process",
            "Run GIS processing",
            ("geojson", "gpkg", "shp", "tif"),
            ("geojson", "gpkg", "csv", "png"),
        ),
    )


def register_builtin_adapters(registry) -> None:
    for adapter_type in (
        FreeCADAdapter,
        IfcOpenShellAdapter,
        BlenderAdapter,
        QGISAdapter,
    ):
        registry.register(adapter_type, replace=True)
