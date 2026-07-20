"""Integrated Phoenix Updater execution engine.

This module is intentionally conservative. It discovers one package, validates
its manifest, prepares rollback evidence, invokes an optional installer and
writes a runtime report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

from .package_discovery import PackageDiscovery, UpdatePackage
from .report_writer import RuntimeReportWriter
from .rollback_manager import RollbackManager, RollbackSnapshot
from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


class UpdateStatus(str, Enum):
    NO_UPDATE = "NO_UPDATE"
    READY = "READY"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PackageManifest:
    name: str
    version: str
    files: tuple[str, ...]
    checksum_sha256: str | None = None


@dataclass(frozen=True)
class UpdateContext:
    repository_root: Path
    package: UpdatePackage
    manifest: PackageManifest
    rollback: RollbackSnapshot


@dataclass(frozen=True)
class UpdateResult:
    status: UpdateStatus
    message: str
    package: str | None
    version: str | None
    rollback_snapshot: str | None
    report_path: str | None


class Installer(Protocol):
    def __call__(self, context: UpdateContext) -> None:
        """Apply a validated Phoenix update."""


class ManifestError(ValueError):
    """Raised when a package manifest is invalid."""


def _noop_installer(context: UpdateContext) -> None:
    del context


class Updater:
    """Single-entry Phoenix update orchestrator."""

    def __init__(
        self,
        repository_root: str | Path,
        *,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
        installer: Installer | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.runtime_policy = runtime_policy
        self.discovery = PackageDiscovery(self.repository_root, runtime_policy)
        self.reports = RuntimeReportWriter(self.repository_root, runtime_policy)
        self.rollback = RollbackManager(self.repository_root, runtime_policy)
        self.installer: Installer = installer or _noop_installer
        self._safe_mode = installer is None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _normalize_files(values: object) -> tuple[str, ...]:
        if not isinstance(values, list):
            raise ManifestError("Manifest field 'files' must be a list.")

        result: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ManifestError("Manifest paths must be non-empty strings.")

            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise ManifestError(f"Unsafe manifest path: {value}")

            normalized = path.as_posix()
            if normalized.startswith("./"):
                normalized = normalized[2:]

            if normalized not in result:
                result.append(normalized)

        return tuple(result)

    def load_manifest(self, package: UpdatePackage) -> PackageManifest:
        if package.suffix != ".json":
            return PackageManifest(
                name=package.name,
                version="unversioned",
                files=(),
            )

        try:
            document = json.loads(package.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ManifestError(f"Invalid JSON manifest: {package.name}") from exc

        if not isinstance(document, dict):
            raise ManifestError("Manifest root must be a JSON object.")

        name = document.get("name")
        version = document.get("version")
        checksum = document.get("checksum_sha256")

        if not isinstance(name, str) or not name.strip():
            raise ManifestError("Manifest field 'name' is required.")
        if not isinstance(version, str) or not version.strip():
            raise ManifestError("Manifest field 'version' is required.")
        if checksum is not None:
            if (
                not isinstance(checksum, str)
                or len(checksum) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in checksum)
            ):
                raise ManifestError(
                    "Manifest checksum_sha256 must contain 64 hexadecimal characters."
                )

        return PackageManifest(
            name=name.strip(),
            version=version.strip(),
            files=self._normalize_files(document.get("files", [])),
            checksum_sha256=checksum.lower() if checksum else None,
        )

    def validate_package(
        self,
        package: UpdatePackage,
        manifest: PackageManifest,
    ) -> None:
        if not package.path.is_file():
            raise ManifestError(f"Package does not exist: {package.name}")

        if manifest.checksum_sha256:
            actual = self._sha256(package.path)
            if actual != manifest.checksum_sha256:
                raise ManifestError(f"Checksum mismatch for {package.name}.")

        for relative_path in manifest.files:
            if self.runtime_policy.is_runtime(relative_path):
                raise ManifestError(
                    f"Manifest cannot update runtime path: {relative_path}"
                )

    def _report(
        self,
        result: UpdateResult,
        manifest: PackageManifest | None = None,
    ) -> Path:
        payload: dict[str, Any] = {
            "result": {
                **asdict(result),
                "status": result.status.value,
            }
        }
        if manifest is not None:
            payload["manifest"] = asdict(manifest)
        return self.reports.write("update_run", payload)

    @staticmethod
    def _with_report(result: UpdateResult, report: Path) -> UpdateResult:
        return UpdateResult(
            status=result.status,
            message=result.message,
            package=result.package,
            version=result.version,
            rollback_snapshot=result.rollback_snapshot,
            report_path=str(report),
        )

    def run(self) -> UpdateResult:
        package = self.discovery.next_package()

        if package is None:
            result = UpdateResult(
                status=UpdateStatus.NO_UPDATE,
                message="Geen updatepakketten beschikbaar.",
                package=None,
                version=None,
                rollback_snapshot=None,
                report_path=None,
            )
            return self._with_report(result, self._report(result))

        manifest: PackageManifest | None = None
        snapshot: RollbackSnapshot | None = None

        try:
            manifest = self.load_manifest(package)
            self.validate_package(package, manifest)
            snapshot = self.rollback.create_snapshot(
                manifest.files,
                snapshot_id=datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%S%fZ"
                ),
            )

            context = UpdateContext(
                repository_root=self.repository_root,
                package=package,
                manifest=manifest,
                rollback=snapshot,
            )
            self.installer(context)

            status = UpdateStatus.READY if self._safe_mode else UpdateStatus.APPLIED
            message = (
                "Update gevalideerd en rollback voorbereid."
                if self._safe_mode
                else "Update succesvol uitgevoerd."
            )
            result = UpdateResult(
                status=status,
                message=message,
                package=package.name,
                version=manifest.version,
                rollback_snapshot=snapshot.snapshot_id,
                report_path=None,
            )
            return self._with_report(result, self._report(result, manifest))

        except Exception as exc:
            result = UpdateResult(
                status=UpdateStatus.FAILED,
                message=str(exc),
                package=package.name,
                version=manifest.version if manifest else None,
                rollback_snapshot=snapshot.snapshot_id if snapshot else None,
                report_path=None,
            )
            return self._with_report(result, self._report(result, manifest))