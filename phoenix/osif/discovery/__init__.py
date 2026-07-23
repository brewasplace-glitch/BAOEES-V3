"""Application Registry & Discovery Service — Phoenix Core v2.0 BB2."""

from .service import (
    ApplicationDiscoveryService,
    DiscoveryCandidate,
    DiscoveryResult,
    DiscoveryError,
)

__all__ = [
    "ApplicationDiscoveryService",
    "DiscoveryCandidate",
    "DiscoveryResult",
    "DiscoveryError",
]
