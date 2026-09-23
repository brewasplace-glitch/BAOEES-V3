#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from phoenix.autonomy import RepeatableLevel4CampaignService


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command, check=True, text=True, encoding="utf-8", errors="strict",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def git(root: Path, *args: str) -> str:
    return run([
        "git", "-c", "core.longpaths=true", "-c", "core.autocrlf=false",
        "-c", "core.eol=lf", "-C", str(root), *args,
    ])


def synthetic_repository(policy_root: Path, root: Path) -> tuple[Path, str]:
    repo = root / "repo"
    remote = root / "remote.git"
    shutil.copytree(
        policy_root, repo,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    run(["git", "init", "--bare", str(remote)])
    run(["git", "init", "-b", "project-phoenix", str(repo)])
    git(repo, "config", "user.name", "PROJECT PHOENIX")
    git(repo, "config", "user.email", "phoenix@local.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "phase14 synthetic package baseline")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "project-phoenix")
    return repo, git(repo, "rev-parse", "HEAD")


def synthetic_backup(repo: Path, baseline: str, root: Path, label: str) -> Path:
    target = root / label
    target.mkdir(parents=True, exist_ok=False)
    bundle = target / "repo.bundle"
    snapshot = target / "snapshot"
    git(repo, "bundle", "create", str(bundle), "--all")
    git(repo, "bundle", "verify", str(bundle))
    run(["git", "clone", str(repo), str(snapshot)])
    receipt = target / "BACKUP_RECEIPT.json"
    receipt.write_text(json.dumps({
        "schema": "PHOENIX_SYNTHETIC_BACKUP_RECEIPT_V1",
        "status": "PASS", "baseline": baseline,
        "bundle_verified": True, "snapshot_verified": True,
        "bundle_path": str(bundle), "snapshot_path": str(snapshot),
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    return receipt


def fast_gate(_: Path) -> dict[str, object]:
    return {
        "status": "PASS", "test_count": 424, "test_file_count": 16,
        "output_sha256": hashlib.sha256(b"PHASE14_SYNTHETIC_FAST_GATE").hexdigest(),
        "synthetic_fast_gate": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--policy-root")
    parser.add_argument("--runtime-root")
    parser.add_argument("--expected-baseline")
    parser.add_argument("--backup-receipt")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--synthetic-resume-proof", action="store_true")
    mode.add_argument("--campaign-status", action="store_true")
    mode.add_argument("--live-next-batch", action="store_true")
    mode.add_argument("--finalize-campaign", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    policy_root = Path(args.policy_root or repo).resolve()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else (
        Path.home() / ".project-phoenix" / "autonomy" / "phase14"
    )
    if args.probe:
        service = RepeatableLevel4CampaignService(
            repo, runtime, policy_root=policy_root, enable_gateway=False
        )
        result = service.probe()
    elif args.synthetic_resume_proof:
        with tempfile.TemporaryDirectory(prefix="phoenix-phase14-proof-") as temporary:
            root = Path(temporary)
            fixture, baseline = synthetic_repository(policy_root, root / "fixture")
            proof_runtime = root / "runtime"
            first_backup = synthetic_backup(fixture, baseline, root, "backup-1")
            first_service = RepeatableLevel4CampaignService(
                fixture, proof_runtime, policy_root=policy_root,
                enable_gateway=False, test_only_gateway=True,
                test_executor=fast_gate,
            )
            first = first_service.run_next_batch(
                baseline, first_backup, persist=True, test_only=True
            )
            resumed_baseline = str(first["promoted_commit"])
            second_backup = synthetic_backup(fixture, resumed_baseline, root, "backup-2")
            resumed_service = RepeatableLevel4CampaignService(
                fixture, proof_runtime, policy_root=policy_root,
                enable_gateway=False, test_only_gateway=True,
                test_executor=fast_gate,
            )
            second = resumed_service.run_next_batch(
                resumed_baseline, second_backup, persist=True, test_only=True
            )
            final_service = RepeatableLevel4CampaignService(
                fixture, proof_runtime, policy_root=policy_root,
                enable_gateway=False, test_only_gateway=True,
                test_executor=fast_gate,
            )
            completion = final_service.finalize_campaign(
                str(second["promoted_commit"]), persist=True, test_only=True
            )
            result = {
                "schema": "PHOENIX_PHASE14_SYNTHETIC_RESUME_PROOF_V1",
                "status": "PASS",
                "test_only": True,
                "synthetic_fast_gate": True,
                "process_restart_resume": "PASS",
                "first_batch": first,
                "second_batch": second,
                "campaign": completion,
            }
    elif args.campaign_status:
        if not args.expected_baseline:
            raise SystemExit("--expected-baseline is required")
        service = RepeatableLevel4CampaignService(
            repo, runtime, policy_root=policy_root, enable_gateway=True
        )
        result = service.inspect_state(
            args.expected_baseline, persist=True
        )
    elif args.live_next_batch:
        if not args.expected_baseline or not args.backup_receipt:
            raise SystemExit("--expected-baseline and --backup-receipt are required")
        service = RepeatableLevel4CampaignService(
            repo, runtime, policy_root=policy_root, enable_gateway=True
        )
        result = service.run_next_batch(
            args.expected_baseline, Path(args.backup_receipt),
            persist=True, test_only=False,
        )
    else:
        if not args.expected_baseline:
            raise SystemExit("--expected-baseline is required")
        service = RepeatableLevel4CampaignService(
            repo, runtime, policy_root=policy_root, enable_gateway=True
        )
        result = service.finalize_campaign(
            args.expected_baseline, persist=True, test_only=False
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
