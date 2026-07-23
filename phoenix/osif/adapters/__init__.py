"""Open Source Adapter Framework — Phoenix Core v2.0 BB3."""

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
    "IfcOpenShellAdapter",
    "OSIFAdapter",
    "QGISAdapter",
    "register_builtin_adapters",
]
