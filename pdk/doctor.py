"""Repository diagnostics for the Phoenix Development Kit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib
import json
from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = (
    "phoenix/updater/runtime_policy.py",
    "phoenix/updater/package_discovery.py",
    "phoenix/updater/report_writer.py",
    "phoenix/updater/rollback_manager.py",
    "phoenix/updater/integrated_engine.py",
    "phoenix/updater/api.py",
    "pdk/__init__.py",
    "pdk/__main__.py",
)


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    status: str
    repository_root: str
    diagnostics: tuple[Diagnostic, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


class Doctor:
    def __init__(self, repository_root: str | Path = ".") -> None:
        self.repository_root = Path(repository_root).resolve()

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def run(self) -> DoctorReport:
        checks: list[Diagnostic] = []

        checks.append(
            Diagnostic(
                name="python",
                status="PASS" if sys.version_info >= (3, 10) else "FAIL",
                detail=sys.version.split()[0],
            )
        )

        git_root = self._git("rev-parse", "--show-toplevel")
        checks.append(
            Diagnostic(
                name="git_repository",
                status="PASS" if git_root.returncode == 0 else "FAIL",
                detail=git_root.stdout.strip() or git_root.stderr.strip(),
            )
        )

        missing = [
            relative
            for relative in REQUIRED_FILES
            if not (self.repository_root / relative).is_file()
        ]
        checks.append(
            Diagnostic(
                name="required_files",
                status="PASS" if not missing else "FAIL",
                detail="complete" if not missing else ", ".join(missing),
            )
        )

        import_errors: list[str] = []
        for module_name in (
            "phoenix.updater.api",
            "phoenix.updater.integrated_engine",
            "pdk",
        ):
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                import_errors.append(f"{module_name}: {exc}")

        checks.append(
            Diagnostic(
                name="imports",
                status="PASS" if not import_errors else "FAIL",
                detail="complete" if not import_errors else " | ".join(import_errors),
            )
        )

        overall = "PASS" if all(item.status == "PASS" for item in checks) else "FAIL"
        return DoctorReport(
            status=overall,
            repository_root=str(self.repository_root),
            diagnostics=tuple(checks),
        )