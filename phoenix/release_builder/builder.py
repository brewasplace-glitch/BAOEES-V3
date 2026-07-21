"""Phoenix Release Builder.

PRB creates deterministic release archives from an explicit manifest.
It never guesses which files belong to a release.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Iterable, Mapping
import zipfile


PRB_ID = "phoenix.release_builder"
PRB_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"


class BuildError(RuntimeError):
    """Raised when a deterministic release build cannot be completed."""


@dataclass(frozen=True)
class BuildRequest:
    repo_root: Path
    release_id: str
    version: str
    output_dir: Path
    include_files: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.release_id.strip():
            raise BuildError("release_id must not be empty.")
        if not self.version.strip():
            raise BuildError("version must not be empty.")
        if not self.include_files:
            raise BuildError("include_files must contain at least one file.")
        if len(set(self.include_files)) != len(self.include_files):
            raise BuildError("include_files contains duplicate paths.")
        if not self.repo_root.is_dir():
            raise BuildError(f"Repository root does not exist: {self.repo_root}")
        for item in self.include_files:
            path = PurePosixPath(item)
            if path.is_absolute() or ".." in path.parts:
                raise BuildError(f"Unsafe manifest path: {item!r}")


@dataclass(frozen=True)
class BuildResult:
    release_id: str
    version: str
    archive_path: str
    manifest_path: str
    checksums_path: str
    archive_sha256: str
    file_count: int


class PhoenixReleaseBuilder:
    """Create a deterministic ZIP release and evidence files."""

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def _collect(self, request: BuildRequest) -> list[tuple[str, Path]]:
        collected: list[tuple[str, Path]] = []
        for relative in sorted(request.include_files):
            source = request.repo_root / Path(relative)
            if not source.is_file():
                raise BuildError(f"Manifest file does not exist: {relative}")
            collected.append((PurePosixPath(relative).as_posix(), source))
        return collected

    def build(self, request: BuildRequest) -> BuildResult:
        request.validate()
        collected = self._collect(request)
        output_dir = request.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        archive_path = output_dir / f"{request.release_id}_v{request.version}.zip"
        manifest_path = output_dir / f"{request.release_id}_v{request.version}.manifest.json"
        checksums_path = output_dir / f"{request.release_id}_v{request.version}.sha256"

        with tempfile.TemporaryDirectory(prefix="phoenix-prb-") as temp_name:
            staging = Path(temp_name) / request.release_id
            staging.mkdir(parents=True)

            entries: list[dict[str, Any]] = []
            for relative, source in collected:
                target = staging / Path(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                entries.append(
                    {
                        "path": relative,
                        "size_bytes": target.stat().st_size,
                        "sha256": self._sha256(target),
                    }
                )

            manifest = {
                "schema_version": SCHEMA_VERSION,
                "builder": {"id": PRB_ID, "version": PRB_VERSION},
                "release_id": request.release_id,
                "version": request.version,
                "metadata": dict(request.metadata),
                "file_count": len(entries),
                "files": entries,
            }
            manifest["manifest_sha256"] = sha256(
                self._canonical_json(manifest).encode("utf-8")
            ).hexdigest()
            staged_manifest = staging / "RELEASE_MANIFEST.json"
            staged_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            staged_checksums = staging / "SHA256SUMS.txt"
            staged_checksums.write_text(
                "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
                + f"{self._sha256(staged_manifest)}  RELEASE_MANIFEST.json\n",
                encoding="utf-8",
                newline="\n",
            )

            fixed_time = (2026, 1, 1, 0, 0, 0)
            temporary_archive = archive_path.with_suffix(".zip.tmp")
            with zipfile.ZipFile(
                temporary_archive, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for file_path in sorted(staging.rglob("*")):
                    if not file_path.is_file():
                        continue
                    arcname = (
                        PurePosixPath(request.release_id)
                        / file_path.relative_to(staging).as_posix()
                    ).as_posix()
                    info = zipfile.ZipInfo(arcname, fixed_time)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    archive.writestr(info, file_path.read_bytes())
            temporary_archive.replace(archive_path)

            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            checksums_path.write_text(
                staged_checksums.read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )

        return BuildResult(
            release_id=request.release_id,
            version=request.version,
            archive_path=str(archive_path),
            manifest_path=str(manifest_path),
            checksums_path=str(checksums_path),
            archive_sha256=self._sha256(archive_path),
            file_count=len(collected),
        )
