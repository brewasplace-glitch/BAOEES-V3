from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shutil
import subprocess
import time

@dataclass(frozen=True)
class EngineSpec:
    engine_id: str
    display_name: str
    executable_candidates: tuple[str, ...]
    environment_variables: tuple[str, ...]
    supported_inputs: tuple[str, ...]
    supported_outputs: tuple[str, ...]
    official_url: str

@dataclass
class Detection:
    engine_id: str
    available: bool
    executable: str | None
    source: str
    version_text: str
    notes: list[str]

@dataclass
class RunResult:
    engine_id: str
    status: str
    command: list[str]
    cwd: str
    return_code: int | None
    started_utc: str
    duration_seconds: float
    stdout_file: str | None
    stderr_file: str | None
    output_inventory: list[dict[str, Any]]
    simulated: bool = False

def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def inventory(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    return [
        {
            "path": p.relative_to(root).as_posix(),
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        }
        for p in sorted(root.rglob("*")) if p.is_file()
    ]

class EngineAdapter:
    spec: EngineSpec

    def detect(self) -> Detection:
        notes: list[str] = []
        for var in self.spec.environment_variables:
            raw = os.environ.get(var)
            if raw:
                candidate = Path(raw)
                if candidate.is_file():
                    return self._detected(str(candidate), f"environment:{var}", notes)
                if candidate.is_dir():
                    for name in self.spec.executable_candidates:
                        exe = candidate / name
                        if exe.is_file():
                            return self._detected(str(exe), f"environment:{var}", notes)
                    notes.append(f"{var} exists but no candidate executable was found")
        for name in self.spec.executable_candidates:
            resolved = shutil.which(name)
            if resolved:
                return self._detected(resolved, "PATH", notes)
        return Detection(self.spec.engine_id, False, None, "not_found", "", notes)

    def _detected(self, executable: str, source: str, notes: list[str]) -> Detection:
        version = ""
        for args in (["--version"], ["-v"], ["--help"]):
            try:
                cp = subprocess.run(
                    [executable, *args],
                    text=True,
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                version = (cp.stdout or cp.stderr).strip().splitlines()[0][:300]
                if version:
                    break
            except Exception as exc:
                notes.append(f"version probe failed: {type(exc).__name__}")
        return Detection(self.spec.engine_id, True, executable, source, version, notes)

    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        raise NotImplementedError

    def validate_job(self, job: dict[str, Any]) -> list[str]:
        errors = []
        input_path = Path(job.get("input_path", ""))
        if not input_path.is_file():
            errors.append(f"input file not found: {input_path}")
        elif input_path.suffix.lower() not in self.spec.supported_inputs:
            errors.append(f"unsupported input extension: {input_path.suffix.lower()}")
        output_dir = Path(job.get("output_dir", ""))
        if not str(output_dir):
            errors.append("output_dir is required")
        return errors

    def run(self, job: dict[str, Any], dry_run: bool = False) -> RunResult:
        errors = self.validate_job(job)
        if errors:
            raise ValueError("; ".join(errors))
        detected = self.detect()
        if not detected.available or not detected.executable:
            raise RuntimeError(f"{self.spec.display_name} is not installed or not discoverable")
        command = self.build_command(job, detected.executable)
        output_dir = Path(job["output_dir"]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        logs = output_dir / "_phoenix_logs"
        logs.mkdir(exist_ok=True)
        stdout_path = logs / "stdout.txt"
        stderr_path = logs / "stderr.txt"
        start = time.monotonic()
        started = utc_now()
        if dry_run:
            return RunResult(
                self.spec.engine_id, "DRY_RUN", command, str(Path(job.get("working_directory", ".")).resolve()),
                None, started, round(time.monotonic() - start, 6), None, None, inventory(output_dir), False
            )
        cp = subprocess.run(
            command,
            cwd=job.get("working_directory") or None,
            text=True,
            capture_output=True,
            timeout=int(job.get("timeout_seconds", 3600)),
            check=False,
        )
        stdout_path.write_text(cp.stdout or "", encoding="utf-8", newline="\n")
        stderr_path.write_text(cp.stderr or "", encoding="utf-8", newline="\n")
        status = "COMPLETED" if cp.returncode == 0 else "FAILED"
        result = RunResult(
            self.spec.engine_id, status, command, str(Path(job.get("working_directory", ".")).resolve()),
            cp.returncode, started, round(time.monotonic() - start, 6),
            str(stdout_path), str(stderr_path), inventory(output_dir), False
        )
        (output_dir / "phoenix_engine_run.json").write_text(
            json.dumps(asdict(result), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n"
        )
        if cp.returncode != 0:
            raise RuntimeError(f"{self.spec.display_name} failed with exit code {cp.returncode}")
        return result
