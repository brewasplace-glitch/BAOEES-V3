"""Layer registration and validation."""

from __future__ import annotations

from copy import deepcopy

from .models import GISLayer


class LayerRegistry:
    def __init__(self) -> None:
        self._layers: dict[str, GISLayer] = {}

    def add(self, layer: GISLayer) -> GISLayer:
        layer.validate()
        if layer.layer_id in self._layers:
            raise ValueError(f"Layer already exists: {layer.layer_id}")
        if any(existing.name == layer.name for existing in self._layers.values()):
            raise ValueError(f"Layer name already exists: {layer.name}")
        self._layers[layer.layer_id] = deepcopy(layer)
        return deepcopy(layer)

    def get(self, layer_id: str) -> GISLayer:
        if layer_id not in self._layers:
            raise KeyError(f"Unknown layer: {layer_id}")
        return deepcopy(self._layers[layer_id])

    def all(self) -> list[GISLayer]:
        return [deepcopy(layer) for layer in self._layers.values()]

    def remove(self, layer_id: str) -> None:
        if layer_id not in self._layers:
            raise KeyError(f"Unknown layer: {layer_id}")
        del self._layers[layer_id]
