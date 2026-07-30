from __future__ import annotations
from pathlib import Path
import os
import shutil
import subprocess

CANDIDATE_NAMES = (
    "ccx.exe",
    "ccx_static.exe",
    "ccx_2.23.exe",
    "ccx_2.23_MT.exe",
)

def find_calculix_ccx() -> Path | None:
    env = os.environ.get("CALCULIX_CCX_EXE", "").strip()
    if env and Path(env).is_file():
        return Path(env)

    candidates: list[Path] = []
    for name in CANDIDATE_NAMES:
        located = shutil.which(name)
        if located:
            candidates.append(Path(located))

    roots = (
        Path(r"C:\msys64\mingw64\bin"),
        Path(r"C:\PHOENIX-ENGINES\CalculiX"),
        Path(r"C:\CalculiX"),
        Path(r"C:\Program Files\CalculiX"),
        Path(r"C:\Program Files (x86)\CalculiX"),
    )
    for root in roots:
        if not root.exists():
            continue
        for name in CANDIDATE_NAMES:
            candidates.extend(root.rglob(name))

    return next((p for p in candidates if p.is_file()), None)

def build_calculix_environment(executable: Path) -> dict[str, str]:
    env = os.environ.copy()
    runtime_bin = executable.resolve().parent
    existing = env.get("PATH", "")
    env["PATH"] = str(runtime_bin) + (os.pathsep + existing if existing else "")
    return env

def probe_ccx(executable: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(executable.resolve())],
        cwd=str(executable.resolve().parent),
        env=build_calculix_environment(executable),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )

def run_ccx(
    executable: Path,
    model_stem: str,
    working_directory: Path,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(executable.resolve()), "-i", model_stem],
        cwd=str(working_directory.resolve()),
        env=build_calculix_environment(executable),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
