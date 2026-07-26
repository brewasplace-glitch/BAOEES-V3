"""PROJECT-PHOENIX BB17.3 source acquisition and rule mapping."""

from .acquisition import SourceAcquisitionPlanner
from .mapping import RuleMappingEngine
from .models import (
    AcquisitionAction,
    AcquisitionTask,
    ActivationAssessment,
    MappingStatus,
    RightsClass,
    RuleMapping,
    RuleMappingSet,
    SourceCatalog,
    SourceRecord,
    SourceStatus,
)
from .registry import SourceMappingRegistry

__all__ = [
    "AcquisitionAction",
    "AcquisitionTask",
    "ActivationAssessment",
    "MappingStatus",
    "RightsClass",
    "RuleMapping",
    "RuleMappingEngine",
    "RuleMappingSet",
    "SourceAcquisitionPlanner",
    "SourceCatalog",
    "SourceMappingRegistry",
    "SourceRecord",
    "SourceStatus",
]

__version__ = "1.0.0"
