"""Safe repository synchronization for the Phoenix Development Kit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .doctor import Doctor


@dataclass(frozen=True)
class SyncResult:
    status: str
    created_directories: tuple[str, ...]
    doctor_status: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


class Synchronizer:
    REQUIRED_DIRECTORIES = (
        "docs/automation",
        "phoenix/updater",
        "runtime",
        "runtime_reports",
        "tests/updater",
    )

    def __init__(self, repository_root: str | Path = ".") -> None:
        self.repository_root = Path(repository_root).resolve()

    def run(self) -> SyncResult:
        created: list[str] = []

        for relative in self.REQUIRED_DIRECTORIES:
            directory = self.repository_root / relative
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created.append(relative)

        doctor = Doctor(self.repository_root).run()
        return SyncResult(
            status="PASS" if doctor.status == "PASS" else "FAIL",
            created_directories=tuple(created),
            doctor_status=doctor.status,
        )