"""Safe inspection helpers for interrupted Phoenix installations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class RecoveryError(RuntimeError):
    """Raised when a repository state cannot be recovered safely."""


@dataclass(frozen=True)
class RecoveryInspection:
    changed_paths: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    unexpected_paths: tuple[str, ...]

    @property
    def is_safe(self) -> bool:
        return not self.unexpected_paths


def normalize_porcelain_path(line: str) -> str:
    """Extract a normalized path from one porcelain-v1 status line."""
    if len(line) < 4:
        raise RecoveryError(f"Invalid git status line: {line!r}")
    value = line[3:].strip()
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace("\\", "/")


def inspect_porcelain(
    lines: Iterable[str],
    allowed_paths: Iterable[str],
) -> RecoveryInspection:
    """Validate that all changed paths belong to an explicitly allowed set."""
    allowed = tuple(sorted({path.replace("\\", "/") for path in allowed_paths}))
    changed = tuple(sorted({normalize_porcelain_path(line) for line in lines if line}))
    unexpected = tuple(path for path in changed if path not in allowed)
    return RecoveryInspection(
        changed_paths=changed,
        allowed_paths=allowed,
        unexpected_paths=unexpected,
    )
