"""Snapshot creation, validation, restore and comparison."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .models import SnapshotRecord
from .persistence import checksum_bytes, load_json, save_json


class SnapshotManager:
    """Creates immutable snapshot files with SHA-256 verification."""

    def __init__(self, snapshot_dir: Path) -> None:
        self.snapshot_dir = snapshot_dir

    def create(self, payload: Dict[str, Any]) -> SnapshotRecord:
        snapshot_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        envelope = {
            "snapshot_id": snapshot_id,
            "created_at": created_at,
            "payload": payload,
        }
        path = self.snapshot_dir / f"{snapshot_id}.json"
        checksum = save_json(path, envelope)
        return SnapshotRecord(
            snapshot_id=snapshot_id,
            created_at=created_at,
            object_count=len(payload.get("objects", [])),
            relationship_count=len(payload.get("relationships", [])),
            checksum_sha256=checksum,
            path=str(path),
        )

    def restore(self, record: SnapshotRecord) -> Dict[str, Any]:
        path = Path(record.path)
        actual = checksum_bytes(path.read_bytes())
        if actual != record.checksum_sha256:
            raise ValueError("Snapshot checksum mismatch")
        envelope = load_json(path)
        return envelope["payload"]

    @staticmethod
    def compare(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
        left_ids = {item["object_id"] for item in left.get("objects", [])}
        right_ids = {item["object_id"] for item in right.get("objects", [])}
        return {
            "objects_added": sorted(right_ids - left_ids),
            "objects_removed": sorted(left_ids - right_ids),
            "object_count_delta": len(right_ids) - len(left_ids),
            "relationship_count_delta": (
                len(right.get("relationships", []))
                - len(left.get("relationships", []))
            ),
        }
