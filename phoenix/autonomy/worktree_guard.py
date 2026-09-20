from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import hashlib
import os
import shutil
import subprocess
import tempfile

from .change_classifier import ChangeRecord


@dataclass(frozen=True)
class GuardedRepositorySnapshot:
    branch: str
    head: str
    origin_head: str | None
    clean: bool
    status: tuple[str, ...]


@dataclass(frozen=True)
class CandidateWorktree:
    cycle_id: str
    branch: str
    path: Path
    baseline: str


class GuardedWorktreeManager:
    def __init__(self, repo_root: Path, branch: str = "project-phoenix"):
        self.repo_root = Path(repo_root).resolve()
        self.branch = str(branch)

    def _run(
        self,
        root: Path,
        args: Iterable[str],
        *,
        check: bool = True,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        command = [
            "git",
            "-c",
            "core.longpaths=true",
            "-c",
            "core.quotepath=false",
            "-C",
            str(Path(root).resolve()),
            *[str(x) for x in args],
        ]
        cp = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check and cp.returncode:
            output = cp.stdout.decode("utf-8", errors="replace").rstrip()
            raise RuntimeError(f"{' '.join(command)} failed: {output}")
        return cp

    def git(self, *args: str, root: Path | None = None, check: bool = True) -> str:
        cp = self._run(root or self.repo_root, args, check=check)
        return cp.stdout.decode("utf-8", errors="strict").rstrip("\r\n")

    def git_bytes(
        self,
        *args: str,
        root: Path | None = None,
        check: bool = True,
        input_bytes: bytes | None = None,
    ) -> bytes:
        return self._run(
            root or self.repo_root, args, check=check, input_bytes=input_bytes
        ).stdout

    def snapshot(self, *, fetch: bool = False) -> GuardedRepositorySnapshot:
        if fetch:
            self.git("fetch", "origin", self.branch)
        branch = self.git("branch", "--show-current")
        head = self.git("rev-parse", "HEAD")
        origin_cp = self._run(
            self.repo_root,
            ("rev-parse", f"origin/{self.branch}"),
            check=False,
        )
        origin = None
        if origin_cp.returncode == 0:
            origin = origin_cp.stdout.decode("utf-8", errors="strict").strip()
        lines = tuple(
            x
            for x in self.git(
                "status", "--porcelain=v1", "--untracked-files=all"
            ).splitlines()
            if x
        )
        return GuardedRepositorySnapshot(branch, head, origin, not lines, lines)

    def assert_exact_baseline(
        self,
        expected_head: str,
        *,
        require_remote: bool = True,
        fetch: bool = False,
    ) -> GuardedRepositorySnapshot:
        snap = self.snapshot(fetch=fetch)
        errors: list[str] = []
        if snap.branch != self.branch:
            errors.append(f"branch={snap.branch},expected={self.branch}")
        if snap.head != expected_head:
            errors.append(f"head={snap.head},expected={expected_head}")
        if not snap.clean:
            errors.append("main_worktree_dirty")
        if require_remote:
            if not snap.origin_head:
                errors.append("origin_head_missing")
            elif snap.origin_head != expected_head:
                errors.append("origin_baseline_mismatch")
        if errors:
            raise RuntimeError("PHASE10_BASELINE_DENY:" + ";".join(errors))
        return snap

    @staticmethod
    def _safe_cycle_id(cycle_id: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in cycle_id)
        safe = "-".join(x for x in safe.split("-") if x)
        if not safe:
            raise ValueError("cycle_id contains no safe characters")
        return safe[:48]

    def create_candidate(
        self,
        cycle_id: str,
        expected_head: str,
        *,
        parent: Path | None = None,
    ) -> CandidateWorktree:
        safe = self._safe_cycle_id(cycle_id)
        branch = f"auto/phase10-low-{safe}"
        base_parent = Path(parent or self.repo_root.parent).resolve()
        base_parent.mkdir(parents=True, exist_ok=True)
        candidate_path = (base_parent / f"PROJECT-PHOENIX-PHASE10-{safe}").resolve()
        try:
            candidate_path.relative_to(self.repo_root)
        except ValueError:
            pass
        else:
            raise PermissionError("PHASE10_CANDIDATE_WORKTREE_INSIDE_MAIN_DENY")
        if candidate_path.exists():
            raise FileExistsError(f"candidate worktree already exists: {candidate_path}")
        branch_probe = self._run(
            self.repo_root,
            ("show-ref", "--verify", f"refs/heads/{branch}"),
            check=False,
        )
        if branch_probe.returncode == 0:
            raise RuntimeError(f"candidate branch already exists: {branch}")
        self.git("worktree", "add", "-b", branch, str(candidate_path), expected_head)
        actual = self.git("rev-parse", "HEAD", root=candidate_path)
        if actual != expected_head:
            self.cleanup(CandidateWorktree(cycle_id, branch, candidate_path, expected_head))
            raise RuntimeError("PHASE10_CANDIDATE_BASELINE_MISMATCH")
        return CandidateWorktree(cycle_id, branch, candidate_path, expected_head)

    def status_records(self, candidate: CandidateWorktree) -> tuple[ChangeRecord, ...]:
        raw = self.git_bytes(
            "-c",
            "status.renames=false",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            root=candidate.path,
        )
        entries = [x for x in raw.decode("utf-8", errors="strict").split("\x00") if x]
        records: list[ChangeRecord] = []
        for entry in entries:
            if len(entry) < 4 or entry[2] != " ":
                raise RuntimeError(f"PHASE10_STATUS_PARSE_DENY:{entry!r}")
            xy = entry[:2]
            path = entry[3:]
            if "R" in xy or "C" in xy:
                raise PermissionError("PHASE10_RENAME_OR_COPY_DENY")
            if "D" in xy:
                status = "D"
            elif xy == "??" or "A" in xy:
                status = "A"
            elif "M" in xy:
                status = "M"
            else:
                raise PermissionError(f"PHASE10_STATUS_DENY:{xy}")
            absolute = candidate.path / Path(path)
            if status == "D":
                records.append(ChangeRecord(status, path, 0, "0" * 64, False))
            else:
                records.append(ChangeRecord.from_file(status, path, absolute))
        return tuple(records)

    def stage_and_patch(
        self, candidate: CandidateWorktree, paths: Iterable[str]
    ) -> tuple[bytes, str]:
        path_list = tuple(str(x) for x in paths)
        if not path_list:
            raise RuntimeError("PHASE10_EMPTY_STAGE_DENY")
        self.git("add", "--", *path_list, root=candidate.path)
        self.git("diff", "--cached", "--check", root=candidate.path)
        patch = self.git_bytes(
            "diff",
            "--cached",
            "--binary",
            "--full-index",
            "--no-ext-diff",
            root=candidate.path,
        )
        if not patch:
            raise RuntimeError("PHASE10_EMPTY_PATCH_DENY")
        return patch, hashlib.sha256(patch).hexdigest()

    def deterministic_replay(
        self,
        candidate: CandidateWorktree,
        patch: bytes,
        *,
        parent: Path | None = None,
    ) -> tuple[str, str]:
        root = Path(parent or tempfile.mkdtemp(prefix="phoenix-phase10-replay-")).resolve()
        created_parent = parent is None
        root.mkdir(parents=True, exist_ok=True)
        trees: list[str] = []
        replay_paths: list[Path] = []
        try:
            for index in (1, 2):
                replay = root / f"replay-{index}"
                replay_paths.append(replay)
                self.git("worktree", "add", "--detach", str(replay), candidate.baseline)
                self.git_bytes(
                    "apply",
                    "--binary",
                    "--index",
                    "-",
                    root=replay,
                    input_bytes=patch,
                )
                tree = self.git("write-tree", root=replay)
                trees.append(tree)
            if trees[0] != trees[1]:
                raise RuntimeError("PHASE10_DETERMINISTIC_PATCH_REPLAY_FAILED")
            return trees[0], trees[1]
        finally:
            for replay in replay_paths:
                if replay.exists():
                    self.git("worktree", "remove", "--force", str(replay), check=False)
            if created_parent and root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def commit_candidate(
        self,
        candidate: CandidateWorktree,
        lane: str,
        patch_sha256: str,
    ) -> str:
        subject = (
            f"chore(autonomy): phase10 {lane.lower()} candidate "
            f"{patch_sha256[:12]}"
        )
        self.git(
            "-c",
            "user.name=PROJECT PHOENIX",
            "-c",
            "user.email=phoenix@local.invalid",
            "commit",
            "-m",
            subject,
            root=candidate.path,
        )
        commit = self.git("rev-parse", "HEAD", root=candidate.path)
        parent = self.git("rev-parse", "HEAD^", root=candidate.path)
        if parent != candidate.baseline:
            raise RuntimeError("PHASE10_CANDIDATE_NOT_ONE_DIRECT_COMMIT")
        return commit

    def local_fast_forward_proof(
        self, candidate: CandidateWorktree, candidate_commit: str
    ) -> str:
        snap = self.snapshot(fetch=False)
        if snap.head != candidate.baseline or not snap.clean:
            raise RuntimeError("PHASE10_MAIN_CHANGED_BEFORE_PROMOTION")
        if self.git("merge-base", candidate.baseline, candidate_commit) != candidate.baseline:
            raise RuntimeError("PHASE10_NON_FAST_FORWARD_DENY")
        self.git("merge", "--ff-only", candidate.branch)
        promoted = self.git("rev-parse", "HEAD")
        if promoted != candidate_commit:
            raise RuntimeError("PHASE10_FAST_FORWARD_VERIFICATION_FAILED")
        return promoted

    def cleanup(self, candidate: CandidateWorktree, *, delete_branch: bool = True) -> None:
        if candidate.path.exists():
            self.git("worktree", "remove", "--force", str(candidate.path), check=False)
        if delete_branch:
            self.git("branch", "-D", candidate.branch, check=False)


def initialize_fixture_repository(path: Path, branch: str = "project-phoenix") -> str:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=False)
    subprocess.run(
        ["git", "init", "-b", branch, str(root)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    (root / "README.md").write_text("fixture baseline\n", encoding="utf-8", newline="\n")
    subprocess.run(
        ["git", "-C", str(root), "add", "README.md"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    subprocess.run(
        [
            "git", "-C", str(root),
            "-c", "user.name=PROJECT PHOENIX",
            "-c", "user.email=phoenix@local.invalid",
            "commit", "-m", "fixture baseline",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
