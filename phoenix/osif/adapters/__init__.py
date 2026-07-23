"""Open Source Adapter Framework."""

from .base import AdapterError, OSIFAdapter
from .builtin import (
    BlenderAdapter,
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
    "FreeCADAdapter",
    "FreeCADIntegrationError",
    "IfcOpenShellAdapter",
    "OSIFAdapter",
    "QGISAdapter",
    "register_builtin_adapters",
]
