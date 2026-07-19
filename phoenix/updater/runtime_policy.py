"""Repository runtime policy for Project Phoenix.

This module separates version-controlled source files from generated runtime
data. It is intentionally dependency-free so it can be used by the updater,
repository checks and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


class PathClass(str, Enum):
    """Classification assigned to a repository-relative path."""

    SOURCE = "source"
    DOCUMENTATION = "documentation"
    TEST = "test"
    CONFIGURATION = "configuration"
    TRACKED_ARTIFACT = "tracked_artifact"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RuntimePolicy:
    """Classify repository paths and expose runtime locations."""

    runtime_prefixes: tuple[str, ...] = (
        "updates/",
        "runtime/",
        "runtime_reports/",
        ".phoenix/runtime/",
        "artifacts/runtime/",
    )
    documentation_prefixes: tuple[str, ...] = ("docs/",)
    test_prefixes: tuple[str, ...] = ("tests/",)
    configuration_prefixes: tuple[str, ...] = ("configs/", "pyproject.toml", ".gitignore")
    tracked_artifact_prefixes: tuple[str, ...] = ("artifacts/releases/",)
    source_prefixes: tuple[str, ...] = ("phoenix/", "apps/", "baoees/")

    @staticmethod
    def normalize(path: str | Path) -> str:
        """Return a normalized repository-relative POSIX path."""

        value = Path(path).as_posix()
        if value.startswith("./"):
            value = value[2:]
        while "//" in value:
            value = value.replace("//", "/")
        return value

    @staticmethod
    def _matches(path: str, prefixes: Iterable[str]) -> bool:
        for prefix in prefixes:
            normalized_prefix = prefix.replace("\\", "/")
            if normalized_prefix.endswith("/"):
                if path.startswith(normalized_prefix):
                    return True
            elif path == normalized_prefix or path.startswith(normalized_prefix + "/"):
                return True
        return False

    def classify(self, path: str | Path) -> PathClass:
        """Classify a repository-relative path."""

        normalized = self.normalize(path)

        if self._matches(normalized, self.runtime_prefixes):
            return PathClass.RUNTIME
        if self._matches(normalized, self.documentation_prefixes):
            return PathClass.DOCUMENTATION
        if self._matches(normalized, self.test_prefixes):
            return PathClass.TEST
        if self._matches(normalized, self.configuration_prefixes):
            return PathClass.CONFIGURATION
        if self._matches(normalized, self.tracked_artifact_prefixes):
            return PathClass.TRACKED_ARTIFACT
        if self._matches(normalized, self.source_prefixes):
            return PathClass.SOURCE

        return PathClass.UNKNOWN

    def is_runtime(self, path: str | Path) -> bool:
        """Return True when the path is generated runtime data."""

        return self.classify(path) is PathClass.RUNTIME

    def runtime_directories(self, repository_root: str | Path) -> tuple[Path, ...]:
        """Return all configured runtime directories below the repository root."""

        root = Path(repository_root)
        return tuple(
            root / prefix.rstrip("/")
            for prefix in self.runtime_prefixes
        )

    def ensure_runtime_directories(self, repository_root: str | Path) -> tuple[Path, ...]:
        """Create configured runtime directories and return their paths."""

        directories = self.runtime_directories(repository_root)
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        return directories


DEFAULT_RUNTIME_POLICY = RuntimePolicy()


def classify_path(path: str | Path) -> PathClass:
    """Classify a path with the default Phoenix runtime policy."""

    return DEFAULT_RUNTIME_POLICY.classify(path)