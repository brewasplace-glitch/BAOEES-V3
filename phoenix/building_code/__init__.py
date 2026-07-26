"""PROJECT-PHOENIX BB17 Building Code Engine."""

from .engine import BuildingCodeEngine
from .models import (
    CodeProfile,
    CodeRule,
    ComplianceReport,
    RuleEvaluation,
    RuleResultStatus,
    RuleSeverity,
)
from .registry import CodeProfileRegistry

__all__ = [
    "BuildingCodeEngine",
    "CodeProfile",
    "CodeProfileRegistry",
    "CodeRule",
    "ComplianceReport",
    "RuleEvaluation",
    "RuleResultStatus",
    "RuleSeverity",
]

__version__ = "1.0.0"
