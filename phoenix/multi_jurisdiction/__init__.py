"""PROJECT-PHOENIX BB17.2 Multi-Jurisdiction Codepack Foundation."""

from .models import JurisdictionDefinition, JurisdictionSelection, LocationContext
from .registry import JurisdictionRegistry
from .resolver import JurisdictionResolver

__all__ = [
    "JurisdictionDefinition",
    "JurisdictionRegistry",
    "JurisdictionResolver",
    "JurisdictionSelection",
    "LocationContext",
]

__version__ = "1.0.0"
