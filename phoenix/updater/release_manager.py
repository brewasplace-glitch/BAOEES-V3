"""Phoenix Release Manager v2.3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
from typing import Iterable

from .release_package_builder import BuiltPackage, ReleasePackageBuilder
from .report_writer import RuntimeReportWriter
from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


@dataclass(frozen=True)
class ReleaseResult:
    status: str
    name: str
    version: str
    archive: str
    manifest: str
    checksum: str
    archive_sha256: str
    report_path: str


class ReleaseManager:
    """Create tested and auditable Phoenix release packages."""

    def __init__(
        self,
        repository_root: str | Path,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.runtime_policy = runtime_policy
        self.builder = ReleasePackageBuilder(self.repository_root, runtime_policy)
        self.reports = RuntimeReportWriter(self.repository_root, runtime_policy)

    def tracked_files(self) -> tuple[str, ...]:
        process = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=self.repository_root,
            check=True,
            capture_output=True,
        )
        values = process.stdout.decode("utf-8").split("\0")
        files = [
            value
            for value in values
            if value
            and not self.runtime_policy.is_runtime(value)
            and (self.repository_root / value).is_file()
        ]
        return tuple(sorted(files, key=str.lower))

    def create_release(
        self,
        *,
        name: str,
        version: str,
        relative_paths: Iterable[str | Path] | None = None,
        changelog: str = "",
    ) -> ReleaseResult:
        selected_files = (
            tuple(relative_paths)
            if relative_paths is not None
            else self.tracked_files()
        )

        built: BuiltPackage = self.builder.build(
            name=name,
            version=version,
            relative_paths=selected_files,
            changelog=changelog,
        )

        report_payload = {
            "status": "PASS",
            "release": {
                "name": built.name,
                "version": built.version,
                "archive": str(built.archive),
                "manifest": str(built.manifest),
                "checksum": str(built.checksum),
                "archive_sha256": built.archive_sha256,
                "files": [asdict(record) for record in built.files],
            },
        }
        report = self.reports.write("release", report_payload)

        return ReleaseResult(
            status="PASS",
            name=built.name,
            version=built.version,
            archive=str(built.archive),
            manifest=str(built.manifest),
            checksum=str(built.checksum),
            archive_sha256=built.archive_sha256,
            report_path=str(report),
        )

    @staticmethod
    def to_json(result: ReleaseResult) -> str:
        return json.dumps(asdict(result), indent=2, sort_keys=True)