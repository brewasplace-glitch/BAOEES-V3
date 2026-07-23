"""Deterministic JSON persistence and SHA-256 evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checksum_payload(payload: Dict[str, Any]) -> str:
    return checksum_bytes(canonical_json_bytes(payload))


def save_json(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    path.write_bytes(data)
    return checksum_bytes(data)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
