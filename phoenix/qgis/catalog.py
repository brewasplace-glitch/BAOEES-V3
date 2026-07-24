"""Provider-neutral GIS service catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GISService:
    service_id: str
    title: str
    service_type: str
    endpoint: str
    crs: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class GISServiceCatalog:
    """Registers WMS/WFS/XYZ endpoints without performing network calls."""

    def __init__(self) -> None:
        self._services: dict[str, GISService] = {}

    def register(self, service: GISService) -> GISService:
        if service.service_id in self._services:
            raise ValueError(f"Service already exists: {service.service_id}")
        if service.service_type not in {"WMS", "WFS", "XYZ", "WMTS"}:
            raise ValueError("Unsupported service type")
        if not service.endpoint.strip():
            raise ValueError("Service endpoint must not be empty")
        self._services[service.service_id] = service
        return service

    def all(self) -> list[GISService]:
        return list(self._services.values())
