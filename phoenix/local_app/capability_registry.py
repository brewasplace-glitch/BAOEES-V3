"""Dynamic Project Phoenix start-screen capability registry."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class StartCapabilityRegistry:
    def __init__(self, repository: Path):
        self.repository = Path(repository).resolve()
        self.registry_root = self.repository / "configs" / "phoenix" / "startscreen_capabilities"

    def describe(self) -> list[dict[str, Any]]:
        if not self.registry_root.is_dir():
            return []
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in sorted(self.registry_root.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict):
                continue
            capability_id = str(value.get("id", "")).strip()
            label = str(value.get("label", "")).strip()
            if not capability_id or not label or capability_id in seen:
                continue
            required_files = value.get("required_files", [])
            if not isinstance(required_files, list):
                required_files = []
            missing = [str(rel) for rel in required_files if not (self.repository / str(rel)).is_file()]
            action = value.get("action", {})
            if not isinstance(action, dict):
                action = {}
            result.append({
                "id": capability_id,
                "label": label,
                "description": str(value.get("description", "")).strip(),
                "category": str(value.get("category", "AUTOMATION")).strip(),
                "available": not missing,
                "status": "READY" if not missing else "UNAVAILABLE",
                "missing_required_files": missing,
                "project_types": value.get("project_types", []),
                "action": action,
                "release_status": str(value.get("release_status", "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")),
                "registry_file": path.relative_to(self.repository).as_posix(),
            })
            seen.add(capability_id)
        return result
