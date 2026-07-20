"""Test runner used by Phoenix Development Kit commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class TestSuiteResult:
    name: str
    command: tuple[str, ...]
    returncode: int


@dataclass(frozen=True)
class CommandResult:
    status: str
    suites: tuple[TestSuiteResult, ...]
    returncode: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _run_suite(
    repository_root: Path,
    *,
    name: str,
    start_directory: str,
) -> TestSuiteResult:
    command = (
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        start_directory,
        "-p",
        "test*.py",
    )
    process = subprocess.run(command, cwd=repository_root)
    return TestSuiteResult(
        name=name,
        command=command,
        returncode=process.returncode,
    )


def run_tests(repository_root: str | Path = ".") -> CommandResult:
    root = Path(repository_root).resolve()

    suites = (
        _run_suite(
            root,
            name="updater",
            start_directory="tests/updater",
        ),
        _run_suite(
            root,
            name="pdk",
            start_directory="tests/pdk",
        ),
    )

    returncode = max(suite.returncode for suite in suites)
    return CommandResult(
        status="PASS" if returncode == 0 else "FAIL",
        suites=suites,
        returncode=returncode,
    )