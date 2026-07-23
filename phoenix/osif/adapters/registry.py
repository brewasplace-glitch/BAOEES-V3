"""Adapter registry and capability resolution for Phoenix OSIF."""

from __future__ import annotations

from typing import Iterable

from .base import OSIFAdapter


class AdapterRegistryError(RuntimeError):
    pass


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, type[OSIFAdapter]] = {}

    def register(
        self,
        adapter_type: type[OSIFAdapter],
        *,
        replace: bool = False,
    ) -> None:
        adapter = adapter_type()
        descriptor = adapter.descriptor()
        descriptor.validate()
        adapter_id = descriptor.adapter_id
        if adapter_id in self._adapters and not replace:
            raise AdapterRegistryError(f"Adapter already registered: {adapter_id}")
        self._adapters[adapter_id] = adapter_type

    def create(self, adapter_id: str) -> OSIFAdapter:
        try:
            return self._adapters[adapter_id]()
        except KeyError as exc:
            raise AdapterRegistryError(
                f"Adapter not registered: {adapter_id}"
            ) from exc

    def list_adapter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def find_by_capability(self, capability_id: str) -> tuple[str, ...]:
        matches: list[str] = []
        for adapter_id, adapter_type in self._adapters.items():
            descriptor = adapter_type().descriptor()
            if any(
                item.capability_id == capability_id
                for item in descriptor.capabilities
            ):
                matches.append(adapter_id)
        return tuple(sorted(matches))
