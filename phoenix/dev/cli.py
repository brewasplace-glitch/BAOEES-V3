from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


def run(command: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=check,
    )


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def git_status(root: Path) -> list[str]:
    result = run(["git", "status", "--porcelain"], root)
    return [line for line in result.stdout.splitlines() if line.strip()]


def doctor(root: Path) -> dict[str, Any]:
    checks: list[Check] = []

    checks.append(Check("repository", (root / ".git").exists(), str(root)))
    checks.append(Check("python", sys.version_info >= (3, 10), sys.version.split()[0]))
    checks.append(Check("git", shutil.which("git") is not None, shutil.which("git") or "not found"))

    branch = run(["git", "branch", "--show-current"], root).stdout.strip()
    checks.append(Check("branch", bool(branch), branch or "detached HEAD"))

    required = [
        "phoenix",
        "tests",
        "configs",
        "docs",
        "runners",
    ]
    for relative in required:
        checks.append(
            Check(
                f"path:{relative}",
                (root / relative).exists(),
                str(root / relative),
            )
        )

    graph_engine = root / "phoenix/graph/phoenix_project_graph_v34_0.py"
    checks.append(Check("project_graph_v34", graph_engine.exists(), str(graph_engine)))

    database_engine = root / "phoenix/database/phoenix_unified_project_database_v33_0.py"
    checks.append(Check("database_v33", database_engine.exists(), str(database_engine)))

    status = git_status(root)
    result = {
        "engine": "Phoenix Development Workflow",
        "version": "v1.0",
        "command": "doctor",
        "branch": branch,
        "working_tree_clean": not status,
        "working_tree_entries": status,
        "checks": [asdict(check) for check in checks],
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    return result


def cleanup(root: Path) -> dict[str, Any]:
    removed: list[str] = []

    for cache in root.rglob("__pycache__"):
        if ".git" in cache.parts:
            continue
        shutil.rmtree(cache, ignore_errors=True)
        removed.append(str(cache.relative_to(root)))

    for pattern in ("*.pyc", "*.pyo"):
        for item in root.rglob(pattern):
            if ".git" in item.parts:
                continue
            try:
                item.unlink()
                removed.append(str(item.relative_to(root)))
            except FileNotFoundError:
                pass

    runtime = root / ".runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
        removed.append(".runtime")

    return {
        "engine": "Phoenix Development Workflow",
        "version": "v1.0",
        "command": "cleanup",
        "removed": sorted(set(removed)),
        "status": "PASS",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def validate_manifest(root: Path, manifest: Path) -> dict[str, Any]:
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    errors: list[str] = []

    for key in ("release", "source_paths", "required_tests", "commit_message"):
        if key not in data:
            errors.append(f"missing key: {key}")

    for relative in data.get("source_paths", []):
        if not (root / relative).exists():
            errors.append(f"missing source path: {relative}")

    return {
        "engine": "Phoenix Development Workflow",
        "version": "v1.0",
        "command": "validate-manifest",
        "manifest": str(manifest),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def tests(root: Path) -> dict[str, Any]:
    commands = [
        [sys.executable, "-m", "unittest", "tests/automation/test_phoenix_development_workflow_v1_0.py"],
    ]

    graph_test = root / "tests/automation/test_phoenix_project_graph_v34_0.py"
    if graph_test.exists():
        commands.append([sys.executable, "-m", "unittest", str(graph_test)])

    results = []
    passed = True

    for command in commands:
        completed = run(command, root, check=False)
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        passed = passed and completed.returncode == 0

    return {
        "engine": "Phoenix Development Workflow",
        "version": "v1.0",
        "command": "test",
        "results": results,
        "status": "PASS" if passed else "FAIL",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def status(root: Path) -> dict[str, Any]:
    branch = run(["git", "branch", "--show-current"], root).stdout.strip()
    latest = run(["git", "log", "-1", "--pretty=%h %s"], root).stdout.strip()
    changes = git_status(root)

    return {
        "engine": "Phoenix Development Workflow",
        "version": "v1.0",
        "command": "status",
        "branch": branch,
        "latest_commit": latest,
        "working_tree_clean": not changes,
        "changes": changes,
        "status": "PASS",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def emit(result: dict[str, Any], root: Path) -> None:
    output = root / "artifacts/releases/development_workflow_v1_0"
    output.mkdir(parents=True, exist_ok=True)
    command = result.get("command", "result")
    (output / f"{command}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m phoenix")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")
    sub.add_parser("cleanup")
    sub.add_parser("test")
    sub.add_parser("status")

    validate = sub.add_parser("validate-manifest")
    validate.add_argument("manifest")

    args = parser.parse_args()
    root = find_root()

    if args.command == "doctor":
        result = doctor(root)
    elif args.command == "cleanup":
        result = cleanup(root)
    elif args.command == "test":
        result = tests(root)
    elif args.command == "status":
        result = status(root)
    else:
        result = validate_manifest(root, (root / args.manifest).resolve())

    emit(result, root)

    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
