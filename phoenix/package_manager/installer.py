"""Permanent Phoenix Package Manager installation engine."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from .core import PackageManagerError, load_manifest


def command(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )
    if check and result.returncode != 0:
        details = ((result.stdout or "") + (result.stderr or "")).strip()
        raise PackageManagerError(
            f"Command failed ({result.returncode}): {' '.join(args)}"
            + (f"\n{details}" if details else "")
        )
    return result


def install_package(package_file: Path, repo: Path, skip_push: bool = False) -> None:
    if not (repo / ".git").exists():
        raise PackageManagerError(f"Not a Git repository: {repo}")

    work = repo / "outputs/runtime/ppm/package_extract"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(package_file) as archive:
        archive.extractall(work)

    manifest_path = work / "manifest.json"
    payload_root = work / "payload"
    manifest = load_manifest(manifest_path)

    status = command(
        ["git", "status", "--porcelain=v1", "-uall"],
        repo,
    ).stdout.strip()
    if status:
        raise PackageManagerError(
            "PPM requires a clean repository for normal package installation."
        )

    for relative in manifest.remove_files:
        destination = repo / relative
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()

    for relative in manifest.install_files:
        source = payload_root / relative
        if not source.is_file():
            raise PackageManagerError(f"Missing payload file: {relative}")
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)

    command([sys.executable, "-m", "compileall", "-q", "phoenix"], repo)
    for module in manifest.tests:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", module, "-v"],
            cwd=repo,
            env=env,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PackageManagerError(f"Test failed: {module}")

    command(["git", "diff", "--check"], repo)
    command(["git", "add", "-A", "--", "."], repo)
    command(["git", "diff", "--cached", "--check"], repo)
    command(
        ["git", "-c", "gc.auto=0", "commit", "-m", manifest.commit_message],
        repo,
    )

    if not skip_push:
        push = command(["git", "push"], repo, check=False)
        if push.returncode != 0:
            print("WARNING: package committed; push remains pending.")
            print("Retry later with: git push")
            return

    final = command(
        ["git", "status", "--porcelain=v1", "-uall"],
        repo,
    ).stdout.strip()
    if final:
        raise PackageManagerError("Repository is not clean after package installation.")


def main() -> int:
    parser = argparse.ArgumentParser(prog="phoenix-ppm")
    parser.add_argument("package")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--skip-push", action="store_true")
    args = parser.parse_args()
    install_package(
        Path(args.package).resolve(),
        Path(args.repo_root).resolve(),
        skip_push=args.skip_push,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackageManagerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
