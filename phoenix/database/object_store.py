"""Object registry for Phoenix Digital Twin entities."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, Optional

from .models import TwinObject, utc_now_iso


class ObjectStore:
    """In-memory registry with defensive copies and versioned updates."""

    def __init__(self) -> None:
        self._objects: Dict[str, TwinObject] = {}

    def add(self, twin_object: TwinObject) -> TwinObject:
        if twin_object.object_id in self._objects:
            raise ValueError(f"Object already exists: {twin_object.object_id}")
        self._objects[twin_object.object_id] = deepcopy(twin_object)
        return deepcopy(twin_object)

    def get(self, object_id: str) -> Optional[TwinObject]:
        item = self._objects.get(object_id)
        return deepcopy(item) if item is not None else None

    def require(self, object_id: str) -> TwinObject:
        item = self.get(object_id)
        if item is None:
            raise KeyError(f"Unknown object: {object_id}")
        return item

    def update(
        self,
        object_id: str,
        *,
        name: Optional[str] = None,
        properties: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> TwinObject:
        current = self._objects.get(object_id)
        if current is None:
            raise KeyError(f"Unknown object: {object_id}")
        if name is not None:
            current.name = name
        if properties is not None:
            current.properties = deepcopy(properties)
        if metadata is not None:
            current.metadata = deepcopy(metadata)
        current.version += 1
        current.updated_at = utc_now_iso()
        return deepcopy(current)

    def remove(self, object_id: str) -> None:
        if object_id not in self._objects:
            raise KeyError(f"Unknown object: {object_id}")
        del self._objects[object_id]

    def all(self) -> Iterable[TwinObject]:
        return [deepcopy(item) for item in self._objects.values()]

    def load(self, records: Iterable[dict]) -> None:
        self._objects.clear()
        for record in records:
            item = TwinObject(**record)
            self._objects[item.object_id] = item
