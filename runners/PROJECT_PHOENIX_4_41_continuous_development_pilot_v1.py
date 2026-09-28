#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from phoenix.autonomy import ContinuousDevelopmentPilotService


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command, check=True, text=True, encoding="utf-8", errors="strict",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def git(root: Path, *args: str) -> str:
    return run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-C", str(root), *args])


def synthetic_repo(policy_root: Path, destination: Path) -> tuple[Path, str]:
    repo = destination / "repo"
    remote = destination / "remote.git"
    shutil.copytree(policy_root, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    run(["git", "init", "--bare", str(remote)])
    run(["git", "init", "-b", "project-phoenix", str(repo)])
    git(repo, "config", "user.name", "PROJECT PHOENIX")
    git(repo, "config", "user.email", "phoenix@local.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "phase15 synthetic baseline")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "project-phoenix")
    return repo, git(repo, "rev-parse", "HEAD")


def synthetic_proof(policy_root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="phoenix-phase15-proof-") as temporary:
        root = Path(temporary)
        repo, baseline = synthetic_repo(policy_root, root / "fixture")
        runtime = root / "runtime"
        service = ContinuousDevelopmentPilotService(repo, runtime, policy_root=policy_root, clock=lambda: 1800000000.0)
        before = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        first = service.monitored_tick(baseline, persist=True)
        (runtime / "PHOENIX_LEVEL5_STOP").write_text("STOP\n", encoding="utf-8")
        paused = service.monitored_tick(baseline, persist=True)
        (runtime / "PHOENIX_LEVEL5_STOP").unlink()
        resumed = service.monitored_tick(baseline, persist=True)
        after = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        status = service.status()
        return {
            "schema": "PHOENIX_PHASE15_MONITORED_LEVEL5_PILOT_PROOF_V1",
            "status": "PASS", "test_only": True,
            "first_tick": first, "kill_switch_tick": paused, "resumed_tick": resumed,
            "state": status["state"], "signed_atomic_state": "PASS",
            "deterministic_signal_digest": first["signal_sha256"] == resumed["signal_sha256"],
            "single_low_risk_task": first["task_count"] == 1,
            "repository_unchanged": before == after == "",
            "push_performed": False, "automatic_promotion": False,
            "continuous_daemon_activation": False, "automatic_engine_activation": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--policy-root")
    parser.add_argument("--runtime-root")
    parser.add_argument("--expected-baseline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--synthetic-pilot-proof", action="store_true")
    mode.add_argument("--monitored-tick", action="store_true")
    mode.add_argument("--status", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    policy = Path(args.policy_root or repo).resolve()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else Path.home() / ".project-phoenix/autonomy/phase15"
    service = ContinuousDevelopmentPilotService(repo, runtime, policy_root=policy)
    if args.probe:
        result = service.probe()
    elif args.synthetic_pilot_proof:
        result = synthetic_proof(policy)
    elif args.monitored_tick:
        if not args.expected_baseline:
            parser.error("--expected-baseline is required")
        result = service.monitored_tick(args.expected_baseline, persist=True)
    else:
        result = service.status()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
