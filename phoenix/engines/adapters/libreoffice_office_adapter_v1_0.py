"""Project Phoenix LibreOffice Office Adapter v1.0.

Open-source office bridge for Phoenix document workflows.

Primary engine: LibreOffice.
Windows automation route: soffice.com with an isolated UserInstallation profile.
GUI route: soffice.exe.

The adapter is intentionally generic and does not require openpyxl, python-pptx,
or Microsoft Office. It delegates real office-format conversion to LibreOffice.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

SUPPORTED_INPUT_EXTENSIONS = {
    ".doc", ".docx", ".odt", ".rtf", ".txt",
    ".xls", ".xlsx", ".ods", ".csv",
    ".ppt", ".pptx", ".odp",
}

TARGET_FILTERS = {
    "pdf": {
        "writer": "pdf:writer_pdf_Export",
        "calc": "pdf:calc_pdf_Export",
        "impress": "pdf:impress_pdf_Export",
    },
    "docx": {"writer": "docx:Office Open XML Text"},
    "xlsx": {"calc": "xlsx:Calc MS Excel 2007 XML"},
    "pptx": {"impress": "pptx:Impress MS PowerPoint 2007 XML"},
    "odt": {"writer": "odt:writer8"},
    "ods": {"calc": "ods:calc8"},
    "odp": {"impress": "odp:impress8"},
}

WRITER_EXTS = {".doc", ".docx", ".odt", ".rtf", ".txt"}
CALC_EXTS = {".xls", ".xlsx", ".ods", ".csv"}
IMPRESS_EXTS = {".ppt", ".pptx", ".odp"}


class LibreOfficeAdapterError(RuntimeError):
    """Fail-closed LibreOffice adapter error."""


@dataclass(frozen=True)
class LibreOfficeDiscovery:
    console_executable: Path
    gui_executable: Path | None


def _file_uri(path: Path) -> str:
    absolute = path.resolve()
    # Windows file URI accepted by LibreOffice UserInstallation.
    return absolute.as_uri()


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def discover_libreoffice() -> LibreOfficeDiscovery:
    env_path = os.environ.get("PHOENIX_LIBREOFFICE_EXE")
    candidates: list[Path] = []

    if env_path:
        p = Path(env_path)
        if p.name.lower() == "soffice.exe":
            candidates.extend([p.with_name("soffice.com"), p])
        else:
            candidates.append(p)

    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    for root in (program_files, program_files_x86):
        if root:
            base = Path(root) / "LibreOffice" / "program"
            candidates.extend([base / "soffice.com", base / "soffice.exe"])

    which_com = shutil.which("soffice.com")
    which_exe = shutil.which("soffice.exe")
    if which_com:
        candidates.append(Path(which_com))
    if which_exe:
        candidates.append(Path(which_exe))

    existing: list[Path] = []
    for candidate in candidates:
        if candidate and candidate.is_file() and candidate not in existing:
            existing.append(candidate)

    if not existing:
        raise LibreOfficeAdapterError("LibreOffice executable not found")

    console = next(
        (p for p in existing if p.name.lower() == "soffice.com"),
        existing[0],
    )
    gui = next(
        (p for p in existing if p.name.lower() == "soffice.exe"),
        None,
    )

    return LibreOfficeDiscovery(
        console_executable=console,
        gui_executable=gui,
    )


def _family_for_extension(extension: str) -> str:
    ext = extension.lower()
    if ext in WRITER_EXTS:
        return "writer"
    if ext in CALC_EXTS:
        return "calc"
    if ext in IMPRESS_EXTS:
        return "impress"
    raise LibreOfficeAdapterError(f"unsupported input extension: {ext}")


def resolve_conversion_filter(input_path: str | Path, target_format: str) -> str:
    path = Path(input_path)
    family = _family_for_extension(path.suffix)
    target = target_format.lower().lstrip(".")

    filters = TARGET_FILTERS.get(target)
    if not filters:
        raise LibreOfficeAdapterError(f"unsupported target format: {target}")

    filter_spec = filters.get(family)
    if not filter_spec:
        raise LibreOfficeAdapterError(
            f"conversion {path.suffix.lower()} -> {target} is not enabled"
        )
    return filter_spec


class LibreOfficeOfficeAdapter:
    def __init__(
        self,
        *,
        timeout_seconds: int = 90,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def capability(self) -> dict[str, Any]:
        discovery = discover_libreoffice()
        version = subprocess.run(
            [str(discovery.console_executable), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if version.returncode != 0:
            raise LibreOfficeAdapterError(
                f"LibreOffice version probe failed: {version.stderr.strip()}"
            )
        return {
            "engine": "LibreOffice",
            "console_executable": str(discovery.console_executable),
            "gui_executable": (
                str(discovery.gui_executable)
                if discovery.gui_executable
                else None
            ),
            "version_output": (version.stdout or version.stderr).strip(),
            "headless_conversion": True,
            "gui_open": discovery.gui_executable is not None,
            "supported_input_extensions": sorted(SUPPORTED_INPUT_EXTENSIONS),
            "supported_target_formats": sorted(TARGET_FILTERS),
        }

    def convert(
        self,
        input_path: str | Path,
        target_format: str,
        output_dir: str | Path,
    ) -> dict[str, Any]:
        source = Path(input_path).resolve()
        if not source.is_file():
            raise LibreOfficeAdapterError(f"input file not found: {source}")
        if source.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
            raise LibreOfficeAdapterError(
                f"unsupported input extension: {source.suffix.lower()}"
            )

        target = target_format.lower().lstrip(".")
        filter_spec = resolve_conversion_filter(source, target)
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)

        discovery = discover_libreoffice()

        with tempfile.TemporaryDirectory(prefix="PHX_LIBREOFFICE_PROFILE_") as td:
            profile = Path(td) / "profile"
            profile.mkdir(parents=True, exist_ok=True)

            command = [
                str(discovery.console_executable),
                f"-env:UserInstallation={_file_uri(profile)}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                "--convert-to",
                filter_spec,
                "--outdir",
                str(output),
                str(source),
            ]

            started = time.time()
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            elapsed = time.time() - started

        if completed.returncode != 0:
            raise LibreOfficeAdapterError(
                "LibreOffice conversion failed: "
                + (completed.stderr or completed.stdout).strip()
            )

        expected = output / f"{source.stem}.{target}"
        deadline = time.time() + 30
        while time.time() < deadline and not expected.is_file():
            time.sleep(self.poll_interval_seconds)

        if not expected.is_file():
            raise LibreOfficeAdapterError(
                "LibreOffice returned success but expected output was not created: "
                f"{expected}; stdout={completed.stdout.strip()!r}; "
                f"stderr={completed.stderr.strip()!r}"
            )

        if expected.stat().st_size <= 0:
            raise LibreOfficeAdapterError(
                f"LibreOffice output is empty: {expected}"
            )

        return {
            "status": "PASS",
            "engine": "LibreOffice",
            "input": str(source),
            "input_sha256": _sha256(source),
            "target_format": target,
            "filter": filter_spec,
            "output": str(expected),
            "output_sha256": _sha256(expected),
            "output_bytes": expected.stat().st_size,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    def open_document(self, input_path: str | Path) -> dict[str, Any]:
        source = Path(input_path).resolve()
        if not source.is_file():
            raise LibreOfficeAdapterError(f"input file not found: {source}")

        discovery = discover_libreoffice()
        executable = discovery.gui_executable or discovery.console_executable

        subprocess.Popen(
            [str(executable), str(source)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "status": "STARTED",
            "engine": "LibreOffice",
            "input": str(source),
            "executable": str(executable),
        }
