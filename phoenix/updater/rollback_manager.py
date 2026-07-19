"""Rollback manager for Phoenix Updater v2.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Iterable

from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


@dataclass(frozen=True)
class RollbackEntry:
    source: str
    backup: str
    sha256: str
    existed: bool


@dataclass(frozen=True)
class RollbackSnapshot:
    snapshot_id: str
    directory: Path
    manifest: Path
    entries: tuple[RollbackEntry, ...]


class RollbackManager:
    """Create filesystem rollback snapshots before an update."""

    def __init__(
        self,
        repository_root: str | Path,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
    ) -> None:
        self.repository_root = Path(repository_root)
        self.runtime_policy = runtime_policy
        self.rollback_root = self.repository_root / "runtime" / "rollback"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def create_snapshot(
        self,
        relative_paths: Iterable[str | Path],
        snapshot_id: str | None = None,
    ) -> RollbackSnapshot:
        if snapshot_id is None:
            snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        snapshot_directory = self.rollback_root / snapshot_id
        relative_snapshot = snapshot_directory.relative_to(self.repository_root)

        if not self.runtime_policy.is_runtime(relative_snapshot):
            raise RuntimeError("Rollback directory is not classified as runtime.")

        snapshot_directory.mkdir(parents=True, exist_ok=False)
        entries: list[RollbackEntry] = []

        for relative_path in relative_paths:
            relative = Path(relative_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe rollback path: {relative_path}")

            source = self.repository_root / relative
            backup = snapshot_directory / "files" / relative

            if source.exists() and source.is_file():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
                entries.append(
                    RollbackEntry(
                        source=relative.as_posix(),
                        backup=backup.relative_to(snapshot_directory).as_posix(),
                        sha256=self._sha256(backup),
                        existed=True,
                    )
                )
            else:
                entries.append(
                    RollbackEntry(
                        source=relative.as_posix(),
                        backup="",
                        sha256="",
                        existed=False,
                    )
                )

        manifest = snapshot_directory / "rollback_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "snapshot_id": snapshot_id,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "entries": [asdict(entry) for entry in entries],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return RollbackSnapshot(
            snapshot_id=snapshot_id,
            directory=snapshot_directory,
            manifest=manifest,
            entries=tuple(entries),
        )