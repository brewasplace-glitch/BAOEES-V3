"""Dependency detection helpers."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .models import (
    DependencyKind,
    DependencyResult,
    DependencySpec,
    DependencyStatus,
)


def _expand_windows_pattern(pattern: str) -> Iterable[Path]:
    expanded = os.path.expandvars(pattern)
    path = Path(expanded)
    if "*" not in expanded and "?" not in expanded:
        yield path
        return

    parts = path.parts
    wildcard_index = next(
        (index for index, part in enumerate(parts) if "*" in part or "?" in part),
        None,
    )
    if wildcard_index is None:
        yield path
        return

    root = Path(*parts[:wildcard_index])
    if not root.exists():
        return

    pattern_tail = str(Path(*parts[wildcard_index:]))
    for candidate in sorted(root.glob(pattern_tail), reverse=True):
        yield candidate


def _detect_version(executable: Path) -> str | None:
    attempts = (
        [str(executable), "--version"],
        [str(executable), "-version"],
        [str(executable), "-v"],
    )
    for command in attempts:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        output = (completed.stdout or completed.stderr or "").strip()
        if output:
            return output.splitlines()[0][:200]
    return None


def detect_executable(spec: DependencySpec) -> DependencyResult:
    for variable in spec.environment_variables:
        explicit = os.environ.get(variable)
        if explicit:
            candidate = Path(explicit)
            if candidate.is_file():
                return DependencyResult(
                    id=spec.id,
                    name=spec.name,
                    kind=spec.kind,
                    required=spec.required,
                    capability=spec.capability,
                    status=DependencyStatus.AVAILABLE,
                    detected_version=_detect_version(candidate),
                    detected_path=str(candidate),
                    source=f"environment:{variable}",
                    message="Detected through an explicit Phoenix environment variable.",
                )
            return DependencyResult(
                id=spec.id,
                name=spec.name,
                kind=spec.kind,
                required=spec.required,
                capability=spec.capability,
                status=DependencyStatus.INVALID,
                detected_path=str(candidate),
                source=f"environment:{variable}",
                message="Configured executable path does not exist.",
            )

    for executable_name in spec.executable_names:
        resolved = shutil.which(executable_name)
        if resolved:
            candidate = Path(resolved)
            return DependencyResult(
                id=spec.id,
                name=spec.name,
                kind=spec.kind,
                required=spec.required,
                capability=spec.capability,
                status=DependencyStatus.AVAILABLE,
                detected_version=_detect_version(candidate),
                detected_path=str(candidate),
                source="PATH",
                message="Detected on the operating-system PATH.",
            )

    for pattern in spec.windows_candidates:
        for candidate in _expand_windows_pattern(pattern):
            if candidate.is_file():
                return DependencyResult(
                    id=spec.id,
                    name=spec.name,
                    kind=spec.kind,
                    required=spec.required,
                    capability=spec.capability,
                    status=DependencyStatus.AVAILABLE,
                    detected_version=_detect_version(candidate),
                    detected_path=str(candidate),
                    source="standard_windows_path",
                    message="Detected in a standard Windows installation path.",
                )

    return DependencyResult(
        id=spec.id,
        name=spec.name,
        kind=spec.kind,
        required=spec.required,
        capability=spec.capability,
        status=DependencyStatus.MISSING,
        message="Dependency was not detected.",
    )


def detect_python_package(spec: DependencySpec) -> DependencyResult:
    import_name = spec.python_import_name
    if not import_name:
        return DependencyResult(
            id=spec.id,
            name=spec.name,
            kind=spec.kind,
            required=spec.required,
            capability=spec.capability,
            status=DependencyStatus.INVALID,
            message="Python package specification has no import name.",
        )

    module_spec = importlib.util.find_spec(import_name)
    if module_spec is None:
        return DependencyResult(
            id=spec.id,
            name=spec.name,
            kind=spec.kind,
            required=spec.required,
            capability=spec.capability,
            status=DependencyStatus.MISSING,
            message="Python package is not importable in the active runtime.",
        )

    distribution_name = spec.python_distribution_name or import_name
    try:
        version = importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        version = None

    return DependencyResult(
        id=spec.id,
        name=spec.name,
        kind=spec.kind,
        required=spec.required,
        capability=spec.capability,
        status=DependencyStatus.AVAILABLE,
        detected_version=version,
        detected_path=str(module_spec.origin) if module_spec.origin else None,
        source="python_runtime",
        message="Python package is importable in the active runtime.",
    )


def detect_dependency(spec: DependencySpec) -> DependencyResult:
    if spec.kind == DependencyKind.EXECUTABLE:
        return detect_executable(spec)
    if spec.kind == DependencyKind.PYTHON_PACKAGE:
        return detect_python_package(spec)
    return DependencyResult(
        id=spec.id,
        name=spec.name,
        kind=spec.kind,
        required=spec.required,
        capability=spec.capability,
        status=DependencyStatus.UNKNOWN,
        message="Unsupported dependency kind.",
    )
