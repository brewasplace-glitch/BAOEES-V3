"""Core build-plan validation and evidence generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable


@dataclass
class BuildPlan:
    build_block: str
    version: str
    files: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    commit_message: str = ""

    def validate(self) -> None:
        if not self.build_block.strip():
            raise ValueError("build_block must not be empty")
        if not self.version.strip():
            raise ValueError("version must not be empty")
        if not self.files:
            raise ValueError("at least one file must be declared")
        if len(set(self.files)) != len(self.files):
            raise ValueError("duplicate files are not allowed")
        if not self.commit_message.strip():
            raise ValueError("commit_message must not be empty")


class BuildSystem:
    """Produces deterministic build evidence for Phoenix build blocks."""

    def __init__(self, repository_root: Path | str) -> None:
        self.repository_root = Path(repository_root)

    def verify_files(self, paths: Iterable[str]) -> list[str]:
        missing = [
            path for path in paths
            if not (self.repository_root / path).exists()
        ]
        return missing

    def create_evidence(self, plan: BuildPlan, output_path: Path | str) -> dict:
        plan.validate()
        missing = self.verify_files(plan.files)
        if missing:
            raise FileNotFoundError("Missing build files: " + ", ".join(missing))

        records = []
        for relative in sorted(plan.files):
            path = self.repository_root / relative
            data = path.read_bytes()
            records.append(
                {
                    "path": relative.replace("\\", "/"),
                    "size": len(data),
                    "sha256": sha256(data).hexdigest(),
                }
            )

        payload = {
            "schema_version": "1.0",
            "build_block": plan.build_block,
            "version": plan.version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "commit_message": plan.commit_message,
            "tests": list(plan.tests),
            "files": records,
        }
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return payload
