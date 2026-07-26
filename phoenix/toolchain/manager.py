"""Core Phoenix Toolchain & Dependency Manager."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Iterable

from .catalog import default_dependency_catalog
from .detectors import detect_dependency
from .models import (
    DependencyResult,
    DependencySpec,
    DependencyStatus,
    ToolchainReport,
)


class ToolchainDependencyManager:
    SCHEMA_VERSION = "phoenix.toolchain-report/1.0"
    VERSION = "1.0.0"

    def __init__(
        self,
        catalog: Iterable[DependencySpec] | None = None,
    ) -> None:
        self.catalog = tuple(default_dependency_catalog() if catalog is None else catalog)

    def scan(self) -> ToolchainReport:
        results = [detect_dependency(spec) for spec in self.catalog]
        return ToolchainReport(
            schema_version=self.SCHEMA_VERSION,
            manager_version=self.VERSION,
            platform=platform.platform(),
            python_version=sys.version.split()[0],
            results=results,
            metadata={
                "dependency_count": len(results),
                "required_count": sum(1 for item in results if item.required),
            },
        )

    def create_installation_plan(
        self,
        report: ToolchainReport,
    ) -> list[dict[str, object]]:
        plan: list[dict[str, object]] = []
        spec_by_id = {spec.id: spec for spec in self.catalog}

        for result in report.results:
            if result.status == DependencyStatus.AVAILABLE:
                continue

            spec = spec_by_id[result.id]
            if spec.python_distribution_name:
                action = {
                    "dependency_id": result.id,
                    "name": result.name,
                    "required": result.required,
                    "action": "install_python_package",
                    "package": spec.python_distribution_name,
                    "command_template": (
                        f'python -m pip install "{spec.python_distribution_name}"'
                    ),
                    "automatic_execution": False,
                }
            else:
                action = {
                    "dependency_id": result.id,
                    "name": result.name,
                    "required": result.required,
                    "action": "install_or_register_external_application",
                    "environment_variables": list(spec.environment_variables),
                    "automatic_execution": False,
                }
            plan.append(action)

        return plan

    def fingerprint(self, report: ToolchainReport) -> str:
        payload = json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def export_report(
        self,
        report: ToolchainReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = report.to_dict()
        data["fingerprint_sha256"] = self.fingerprint(report)
        data["installation_plan"] = self.create_installation_plan(report)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
