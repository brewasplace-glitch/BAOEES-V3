"""PROJECT-PHOENIX BB17.1 Codepack Governance & Source Registry."""

from .governance import CodepackGovernanceEngine
from .models import (
    ActivationDecision,
    ActivationState,
    CodepackManifest,
    ReviewStatus,
    SourceReference,
    SourceStatus,
)
from .registry import CodepackRegistry

__all__ = [
    "ActivationDecision",
    "ActivationState",
    "CodepackGovernanceEngine",
    "CodepackManifest",
    "CodepackRegistry",
    "ReviewStatus",
    "SourceReference",
    "SourceStatus",
]

__version__ = "1.0.0"
