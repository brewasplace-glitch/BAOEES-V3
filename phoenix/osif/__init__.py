"""Phoenix Core v2.0 — Open Source Integration Framework Foundation."""

from .contracts import (
    ApplicationDescriptor,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    HealthStatus,
)
from .registry import ApplicationRegistry, RegistryError
from .runtime import RuntimeErrorOSIF, RuntimeManager, RuntimePolicy
from .version import OSIF_VERSION

__all__ = [
    "ApplicationDescriptor",
    "ApplicationRegistry",
    "Capability",
    "ExecutionRequest",
    "ExecutionResult",
    "HealthStatus",
    "OSIF_VERSION",
    "RegistryError",
    "RuntimeErrorOSIF",
    "RuntimeManager",
    "RuntimePolicy",
]
