#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from phoenix.autonomy import BoundedLevel4BatchService


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def git(root: Path, *args: str) -> str:
    return run([
        "git", "-c", "core.longpaths=true", "-c", "core.autocrlf=false",
        "-c", "core.eol=lf", "-C", str(root), *args,
    ])


def synthetic_repository(policy_root: Path, root: Path) -> tuple[Path, str, Path]:
    repo = root / "repo"
    remote = root / "remote.git"
    snapshot = root / "backup_snapshot"
    shutil.copytree(
        policy_root,
        repo,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    run(["git", "init", "--bare", str(remote)])
    run(["git", "init", "-b", "project-phoenix", str(repo)])
    git(repo, "config", "user.name", "PROJECT PHOENIX")
    git(repo, "config", "user.email", "phoenix@local.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "phase13 synthetic package baseline")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "project-phoenix")
    baseline = git(repo, "rev-parse", "HEAD")
    bundle = root / "backup.bundle"
    git(repo, "bundle", "create", str(bundle), "--all")
    git(repo, "bundle", "verify", str(bundle))
    run(["git", "clone", str(repo), str(snapshot)])
    receipt = root / "BACKUP_RECEIPT.json"
    receipt.write_text(json.dumps({
        "schema": "PHOENIX_SYNTHETIC_BACKUP_RECEIPT_V1",
        "status": "PASS",
        "baseline": baseline,
        "bundle_verified": True,
        "snapshot_verified": True,
        "bundle_path": str(bundle),
        "snapshot_path": str(snapshot),
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    return repo, baseline, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--policy-root")
    parser.add_argument("--runtime-root")
    parser.add_argument("--expected-baseline")
    parser.add_argument("--backup-receipt")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--synthetic-proof", action="store_true")
    mode.add_argument("--live-batch", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    policy_root = Path(args.policy_root or repo).resolve()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else (
        Path.home() / ".project-phoenix" / "autonomy" / "phase13"
    )
    if args.probe:
        service = BoundedLevel4BatchService(
            repo, runtime, policy_root=policy_root, enable_gateway=False
        )
        result = service.probe()
    elif args.synthetic_proof:
        with tempfile.TemporaryDirectory(prefix="phoenix-phase13-proof-") as temporary:
            fixture, baseline, receipt = synthetic_repository(policy_root, Path(temporary))
            service = BoundedLevel4BatchService(
                fixture,
                runtime,
                policy_root=policy_root,
                enable_gateway=False,
                test_only_gateway=True,
            )
            result = service.run_batch(
                baseline, receipt, persist=False, test_only=True
            )
    else:
        if not args.expected_baseline or not args.backup_receipt:
            raise SystemExit("--expected-baseline and --backup-receipt are required")
        service = BoundedLevel4BatchService(
            repo, runtime, policy_root=policy_root, enable_gateway=True
        )
        result = service.run_batch(
            args.expected_baseline,
            Path(args.backup_receipt),
            persist=True,
            test_only=False,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
