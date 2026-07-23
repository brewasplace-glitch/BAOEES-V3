"""Relationship graph storage for Phoenix Digital Twin entities."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List

from .models import Relationship


class RelationshipStore:
    """Stores typed graph edges between registered objects."""

    def __init__(self) -> None:
        self._relationships: Dict[str, Relationship] = {}

    def add(self, relationship: Relationship) -> Relationship:
        if relationship.relationship_id in self._relationships:
            raise ValueError(
                f"Relationship already exists: {relationship.relationship_id}"
            )
        self._relationships[relationship.relationship_id] = deepcopy(relationship)
        return deepcopy(relationship)

    def remove(self, relationship_id: str) -> None:
        if relationship_id not in self._relationships:
            raise KeyError(f"Unknown relationship: {relationship_id}")
        del self._relationships[relationship_id]

    def for_object(self, object_id: str) -> List[Relationship]:
        return [
            deepcopy(item)
            for item in self._relationships.values()
            if item.source_id == object_id or item.target_id == object_id
        ]

    def all(self) -> Iterable[Relationship]:
        return [deepcopy(item) for item in self._relationships.values()]

    def load(self, records: Iterable[dict]) -> None:
        self._relationships.clear()
        for record in records:
            item = Relationship(**record)
            self._relationships[item.relationship_id] = item
