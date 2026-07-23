"""Core types for Phoenix Package Manager."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class PackageManagerError(RuntimeError):
    """Raised when a Phoenix package is invalid or unsafe."""


def normalize_path(value: str) -> str:
    normalized = value.strip().strip('"').replace("\\", "/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ".." in pure.parts:
        raise PackageManagerError(f"Unsafe package path: {value!r}")
    return pure.as_posix()


@dataclass(frozen=True)
class PackageManifest:
    package_id: str
    version: str
    commit_message: str
    install_files: tuple[str, ...]
    remove_files: tuple[str, ...]
    tests: tuple[str, ...]
    validation_config: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PackageManifest":
        try:
            manifest = cls(
                package_id=str(data["package_id"]).strip(),
                version=str(data["version"]).strip(),
                commit_message=str(data["commit_message"]).strip(),
                install_files=tuple(
                    normalize_path(str(item))
                    for item in data.get("install_files", ())
                ),
                remove_files=tuple(
                    normalize_path(str(item))
                    for item in data.get("remove_files", ())
                ),
                tests=tuple(str(item).strip() for item in data.get("tests", ())),
                validation_config=str(data.get("validation_config", "")).strip(),
            )
        except KeyError as exc:
            raise PackageManagerError(
                f"Missing package manifest key: {exc.args[0]}"
            ) from exc
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.package_id:
            raise PackageManagerError("package_id must not be empty.")
        if not self.version:
            raise PackageManagerError("version must not be empty.")
        if not self.commit_message:
            raise PackageManagerError("commit_message must not be empty.")
        if not self.install_files:
            raise PackageManagerError("install_files must not be empty.")
        all_paths = (*self.install_files, *self.remove_files)
        if len(all_paths) != len(set(all_paths)):
            raise PackageManagerError("Package paths must be unique.")
        if any(not test for test in self.tests):
            raise PackageManagerError("Test names must not be empty.")


def load_manifest(path: str | Path) -> PackageManifest:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageManagerError(f"Unable to read package manifest: {source}") from exc
    return PackageManifest.from_mapping(raw)
