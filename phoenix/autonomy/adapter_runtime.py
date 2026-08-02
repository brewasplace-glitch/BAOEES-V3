"""Shared runtime contract for Phoenix Generic Session Adapters v1.0."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ADAPTER_PROTOCOL_VERSION = "1.0.0"
EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_BLOCKED = 10


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def repo_ref(path: Path, repository: Path) -> str:
    path = path.resolve()
    repository = repository.resolve()
    try:
        return path.relative_to(repository).as_posix()
    except ValueError:
        return str(path)


def resolve_ref(value: str | None, repository: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = repository / path
    return path.resolve()


def load_session_context(
    repository: Path,
    session_file: Path,
    workspace: Path,
    output_dir: Path,
) -> dict[str, Any]:
    repository = repository.resolve()
    session_file = session_file.resolve()
    workspace = workspace.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = read_json(session_file)
    bootstrap = session.get("bootstrap") or {}
    project_id = str(bootstrap.get("project_id") or session.get("selected_project") or "UNKNOWN")
    manifest_path = workspace / "project_manifest.json"
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}

    return {
        "repository": repository,
        "session_file": session_file,
        "session": session,
        "bootstrap": bootstrap,
        "workspace": workspace,
        "output_dir": output_dir,
        "project_id": project_id,
        "manifest_path": manifest_path,
        "manifest": manifest,
    }


def adapter_result_path(ctx: dict[str, Any]) -> Path:
    return ctx["output_dir"] / "adapter_result.json"


def finish(
    ctx: dict[str, Any],
    *,
    capability_id: str,
    label: str,
    status: str,
    outputs: list[str] | None = None,
    blockers: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    status = status.upper()
    result = {
        "schema_version": "phoenix.session-adapter-result/1.0",
        "adapter_protocol_version": ADAPTER_PROTOCOL_VERSION,
        "capability_id": capability_id,
        "label": label,
        "status": status,
        "project_id": ctx["project_id"],
        "session_id": ctx["session"].get("session_id"),
        "session_file": repo_ref(ctx["session_file"], ctx["repository"]),
        "workspace": repo_ref(ctx["workspace"], ctx["repository"]),
        "outputs": outputs or [],
        "blockers": blockers or [],
        "warnings": warnings or [],
        "metadata": metadata or {},
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
        "finished_utc": utc_now(),
    }
    write_json(adapter_result_path(ctx), result)

    project_result = (
        ctx["workspace"] / "results" / "session_adapters" / capability_id / "adapter_result.json"
    )
    write_json(project_result, result)

    if status == "PASSED":
        return EXIT_PASSED
    if status in {"BLOCKED", "BLOCKED_INPUT", "BLOCKED_DEPENDENCY"}:
        return EXIT_BLOCKED
    return EXIT_FAILED


def adapter_state(workspace: Path) -> dict[str, Any]:
    path = workspace / "orchestration" / "adapter_state.json"
    if not path.is_file():
        return {"capabilities": {}}
    try:
        return read_json(path)
    except Exception:
        return {"capabilities": {}}


def discover_upload_files(ctx: dict[str, Any]) -> list[Path]:
    batch = str(ctx["session"].get("upload_batch") or "").strip()
    if not batch:
        return []
    root = (
        ctx["repository"]
        / "inputs"
        / "runtime"
        / "official_start_v3_uploads"
        / batch
    )
    if not root.is_dir():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.name != "upload_manifest.json"]


def discover_json_uploads(ctx: dict[str, Any]) -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for path in discover_upload_files(ctx):
        if path.suffix.lower() not in {".json", ".geojson"}:
            continue
        try:
            value = read_json(path)
        except Exception:
            continue
        if isinstance(value, dict):
            result.append((path, value))
    return result


def run_subprocess(command: list[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        log.write("PROJECT PHOENIX GENERIC SESSION ADAPTER SUBPROCESS\n")
        log.write(json.dumps(command, ensure_ascii=False) + "\n\n")
        log.flush()
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        return int(proc.returncode)


def python_command(runner: Path, *args: str) -> list[str]:
    return [sys.executable, str(runner), *[str(x) for x in args]]
