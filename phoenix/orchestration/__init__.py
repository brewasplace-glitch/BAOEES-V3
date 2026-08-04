"""Project Phoenix orchestration package."""

# Backward-compatible public exception contract retained for PXO clients/tests.
class OrchestrationError(RuntimeError):
    pass
from .phoenix_orchestrator import OrchestrationState

# PXO public API compatibility exports (R3)
from .phoenix_orchestrator import PhoenixOrchestrator
from .phoenix_orchestrator import ProjectContext

# PXO canonical public API identity exports (R4)
# These imports intentionally occur last so package-level names are the
# exact same class/function objects used internally by PhoenixOrchestrator.
from .phoenix_orchestrator import OrchestrationError
from .phoenix_orchestrator import OrchestrationState
from .phoenix_orchestrator import PhoenixOrchestrator
from .phoenix_orchestrator import ProjectContext
