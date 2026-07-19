"""Runtime report writer for Phoenix Updater v2.1."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .runtime_policy import DEFAULT_RUNTIME_POLICY, RuntimePolicy


class RuntimeReportWriter:
    """Write JSON reports only to runtime-controlled locations."""

    def __init__(
        self,
        repository_root: str | Path,
        runtime_policy: RuntimePolicy = DEFAULT_RUNTIME_POLICY,
    ) -> None:
        self.repository_root = Path(repository_root)
        self.runtime_policy = runtime_policy
        self.report_directory = self.repository_root / "runtime_reports" / "updater"

    def write(
        self,
        report_name: str,
        payload: dict[str, Any],
    ) -> Path:
        if not report_name or any(char in report_name for char in r'\/:*?"<>|'):
            raise ValueError("Invalid report name.")

        self.report_directory.mkdir(parents=True, exist_ok=True)
        relative_directory = self.report_directory.relative_to(self.repository_root)

        if not self.runtime_policy.is_runtime(relative_directory):
            raise RuntimeError("Report directory is not classified as runtime.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.report_directory / f"{timestamp}_{report_name}.json"

        document = {
            "engine": "Phoenix Updater",
            "version": "v2.1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "report": payload,
        }

        destination.write_text(
            json.dumps(document, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return destination