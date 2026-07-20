"""Release package builder separated from the legacy updater builder."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


TEXT_SUFFIXES = {
    ".cfg", ".csv", ".html", ".ini", ".json", ".md", ".py", ".rst",
    ".toml", ".tsv", ".txt", ".xml", ".yaml", ".yml",
}


@dataclass(frozen=True)
class PackageFile:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class BuiltPackage:
    name: str
    version: str
    archive: Path
    manifest: Path
    checksum: Path
    files: tuple[PackageFile, ...]
    archive_sha256: str


class PackageBuildError(ValueError):
    pass


class ReleasePackageBuilder:
    def __init__(
        self,
        repository_root: str | Path,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.runtime_policy = runtime_policy
        self.release_root = self.repository_root / "runtime" / "releases"

    @staticmethod
    def _sha256_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _validate_identifier(value: str, field: str) -> str:
        cleaned = value.strip()
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
        if not cleaned or any(character not in allowed for character in cleaned):
            raise PackageBuildError(f"Invalid {field}: {value}")
        return cleaned

    def _normalize_files(self, values: Iterable[str | Path]) -> tuple[Path, ...]:
        result: list[Path] = []
        for value in values:
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise PackageBuildError(f"Unsafe package path: {value}")
            relative = Path(path.as_posix().removeprefix("./"))
            source = self.repository_root / relative
            if not source.is_file():
                raise PackageBuildError(f"Package file does not exist: {relative}")
            if self.runtime_policy.is_runtime(relative):
                raise PackageBuildError(f"Runtime file is not allowed: {relative}")
            if relative not in result:
                result.append(relative)
        result.sort(key=lambda item: item.as_posix().lower())
        if not result:
            raise PackageBuildError("At least one package file is required.")
        return tuple(result)

    @staticmethod
    def _zip_info(name: str) -> ZipInfo:
        info = ZipInfo(name)
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        return info

    @staticmethod
    def _payload_bytes(path: Path) -> bytes:
        content = path.read_bytes()
        if path.suffix.lower() not in TEXT_SUFFIXES:
            return content
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return content
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")

    def build(
        self,
        *,
        name: str,
        version: str,
        relative_paths: Iterable[str | Path],
        changelog: str = "",
    ) -> BuiltPackage:
        package_name = self._validate_identifier(name, "name")
        package_version = self._validate_identifier(version, "version")
        files = self._normalize_files(relative_paths)

        destination = self.release_root / package_name / package_version
        relative_destination = destination.relative_to(self.repository_root)
        if not self.runtime_policy.is_runtime(relative_destination):
            raise PackageBuildError("Release output is not classified as runtime.")
        destination.mkdir(parents=True, exist_ok=True)

        archive = destination / f"{package_name}-{package_version}.zip"
        manifest = destination / "manifest.json"
        checksum = destination / "SHA256SUMS.txt"

        payloads = {
            relative: self._payload_bytes(self.repository_root / relative)
            for relative in files
        }
        records = tuple(
            PackageFile(
                path=relative.as_posix(),
                size_bytes=len(payloads[relative]),
                sha256=self._sha256_bytes(payloads[relative]),
            )
            for relative in files
        )

        manifest_document = {
            "schema": "phoenix.release-manifest.v1",
            "name": package_name,
            "version": package_version,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "files": [asdict(record) for record in records],
            "changelog": changelog.strip(),
        }
        manifest_bytes = (
            json.dumps(manifest_document, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

        with ZipFile(archive, "w") as handle:
            for relative in files:
                archive_name = (PurePosixPath("payload") / relative.as_posix()).as_posix()
                handle.writestr(self._zip_info(archive_name), payloads[relative])
            handle.writestr(self._zip_info("manifest.json"), manifest_bytes)

        manifest.write_bytes(manifest_bytes)
        archive_sha256 = self._sha256_file(archive)
        checksum.write_text(
            f"{archive_sha256}  {archive.name}\n",
            encoding="utf-8",
            newline="\n",
        )

        return BuiltPackage(
            name=package_name,
            version=package_version,
            archive=archive,
            manifest=manifest,
            checksum=checksum,
            files=records,
            archive_sha256=archive_sha256,
        )


PackageBuilder = ReleasePackageBuilder