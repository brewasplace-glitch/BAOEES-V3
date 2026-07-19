"""Package discovery for Phoenix Updater v2.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


SUPPORTED_PACKAGE_SUFFIXES = (".zip", ".phx", ".json")


@dataclass(frozen=True)
class UpdatePackage:
    """Discovered update package."""

    path: Path
    name: str
    suffix: str
    size_bytes: int


class PackageDiscovery:
    """Discover update packages from the configured incoming directory."""

    def __init__(
        self,
        repository_root: str | Path,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
    ) -> None:
        self.repository_root = Path(repository_root)
        self.runtime_policy = runtime_policy
        self.incoming_directory = self.repository_root / "updates" / "incoming"

    def ensure_incoming_directory(self) -> Path:
        self.incoming_directory.mkdir(parents=True, exist_ok=True)
        return self.incoming_directory

    def discover(
        self,
        suffixes: Iterable[str] = SUPPORTED_PACKAGE_SUFFIXES,
    ) -> tuple[UpdatePackage, ...]:
        directory = self.ensure_incoming_directory()
        allowed = {suffix.lower() for suffix in suffixes}

        packages: list[UpdatePackage] = []
        for candidate in directory.iterdir():
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in allowed:
                continue

            relative = candidate.relative_to(self.repository_root)
            if not self.runtime_policy.is_runtime(relative):
                continue

            packages.append(
                UpdatePackage(
                    path=candidate,
                    name=candidate.name,
                    suffix=candidate.suffix.lower(),
                    size_bytes=candidate.stat().st_size,
                )
            )

        packages.sort(key=lambda package: package.name.lower())
        return tuple(packages)

    def next_package(self) -> UpdatePackage | None:
        packages = self.discover()
        return packages[0] if packages else None