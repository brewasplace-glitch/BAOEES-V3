"""Unified Project Database facade for Phoenix Digital Twin Core."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .models import Relationship, SnapshotRecord, TwinObject
from .object_store import ObjectStore
from .persistence import load_json, save_json
from .relationship_store import RelationshipStore
from .snapshot import SnapshotManager


class ProjectDatabase:
    """Central object, relationship, persistence and audit facade."""

    schema_version = "33.0"

    def __init__(self, project_id: str, storage_root: Path | str) -> None:
        if not project_id.strip():
            raise ValueError("project_id must not be empty")
        self.project_id = project_id
        self.storage_root = Path(storage_root)
        self.objects = ObjectStore()
        self.relationships = RelationshipStore()
        self.snapshots = SnapshotManager(
            self.storage_root / project_id / "snapshots"
        )
        self.audit_log: list[dict[str, Any]] = []

    @property
    def database_path(self) -> Path:
        return self.storage_root / self.project_id / "digital_twin.json"

    def create_object(
        self,
        object_type: str,
        name: str,
        properties: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> TwinObject:
        if not object_type.strip() or not name.strip():
            raise ValueError("object_type and name must not be empty")
        created = self.objects.add(
            TwinObject(
                object_type=object_type,
                name=name,
                properties=properties or {},
                metadata=metadata or {},
            )
        )
        self._audit("object.created", created.object_id)
        return created

    def update_object(self, object_id: str, **changes: Any) -> TwinObject:
        updated = self.objects.update(object_id, **changes)
        self._audit("object.updated", object_id)
        return updated

    def delete_object(self, object_id: str) -> None:
        if self.relationships.for_object(object_id):
            raise ValueError("Cannot delete object with active relationships")
        self.objects.remove(object_id)
        self._audit("object.deleted", object_id)

    def relate(
        self,
        source_id: str,
        relationship_type: str,
        target_id: str,
        properties: Optional[dict] = None,
    ) -> Relationship:
        self.objects.require(source_id)
        self.objects.require(target_id)
        if not relationship_type.strip():
            raise ValueError("relationship_type must not be empty")
        created = self.relationships.add(
            Relationship(
                source_id=source_id,
                relationship_type=relationship_type,
                target_id=target_id,
                properties=properties or {},
            )
        )
        self._audit("relationship.created", created.relationship_id)
        return created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "objects": [item.to_dict() for item in self.objects.all()],
            "relationships": [
                item.to_dict() for item in self.relationships.all()
            ],
            "audit_log": list(self.audit_log),
        }

    def save(self) -> str:
        self._audit("database.saving", str(self.database_path))
        return save_json(self.database_path, self.to_dict())

    def load(self) -> None:
        data = load_json(self.database_path)
        if data.get("project_id") != self.project_id:
            raise ValueError("Project ID mismatch")
        self.objects.load(data.get("objects", []))
        self.relationships.load(data.get("relationships", []))
        self.audit_log = list(data.get("audit_log", []))
        self._audit("database.loaded", str(self.database_path))

    def create_snapshot(self) -> SnapshotRecord:
        record = self.snapshots.create(self.to_dict())
        self._audit("snapshot.created", record.snapshot_id)
        return record

    def restore_snapshot(self, record: SnapshotRecord) -> None:
        data = self.snapshots.restore(record)
        if data.get("project_id") != self.project_id:
            raise ValueError("Snapshot project ID mismatch")
        self.objects.load(data.get("objects", []))
        self.relationships.load(data.get("relationships", []))
        self.audit_log = list(data.get("audit_log", []))
        self._audit("snapshot.restored", record.snapshot_id)

    def _audit(self, event: str, subject: str) -> None:
        self.audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "subject": subject,
            }
        )
