"""Open Source Adapter Framework."""

from .base import AdapterError, OSIFAdapter
from .blender import BlenderAdapter, BlenderIntegrationError
from .builtin import (
    FreeCADAdapter,
    IfcOpenShellAdapter,
    QGISAdapter,
    register_builtin_adapters,
)
from .contracts import (
    AdapterContext,
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterHealth,
    AdapterLifecycleState,
)
from .executor import AdapterExecutor
from .freecad import FreeCADIntegrationError
from .ifcopenshell import IfcOpenShellIntegrationError
from .registry import AdapterRegistry, AdapterRegistryError

__all__ = [
    "AdapterContext",
    "AdapterError",
    "AdapterExecutionRequest",
    "AdapterExecutionResult",
    "AdapterExecutor",
    "AdapterHealth",
    "AdapterLifecycleState",
    "AdapterRegistry",
    "AdapterRegistryError",
    "BlenderAdapter",
    "BlenderIntegrationError",
    "FreeCADAdapter",
    "FreeCADIntegrationError",
    "IfcOpenShellAdapter",
    "IfcOpenShellIntegrationError",
    "OSIFAdapter",
    "QGISAdapter",
    "register_builtin_adapters",
]
