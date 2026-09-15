from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess

@dataclass(frozen=True)
class RepoSnapshot:
    branch: str
    head: str
    origin_head: str | None
    clean: bool
    status: tuple[str,...]

class SafeWorktreeManager:
    def __init__(self, repo_root: Path, branch: str="project-phoenix"):
        self.repo_root=Path(repo_root)
        self.branch=branch

    def git(self,*args:str,check:bool=True)->str:
        cp=subprocess.run(
            ["git","-c","core.longpaths=true","-C",str(self.repo_root),*args],
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check and cp.returncode:
            raise RuntimeError(f"git {' '.join(args)} failed: {cp.stdout.strip()}")
        # IMPORTANT: preserve leading whitespace. Git porcelain v1 uses the
        # first two columns as XY status; e.g. " M path". Calling strip()
        # corrupts the first status record by removing its leading status byte.
        return cp.stdout.rstrip("\r\n")

    def snapshot(self, fetch: bool=False)->RepoSnapshot:
        if fetch:
            self.git("fetch","origin",self.branch)
        branch=self.git("branch","--show-current")
        head=self.git("rev-parse","HEAD")
        origin=None
        cp=subprocess.run(
            ["git","-c","core.longpaths=true","-C",str(self.repo_root),"rev-parse",f"origin/{self.branch}"],
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if cp.returncode==0:
            origin=cp.stdout.strip()
        status_lines=tuple(x for x in self.git("status","--porcelain=v1","--untracked-files=all").splitlines() if x)
        return RepoSnapshot(branch,head,origin,not status_lines,status_lines)

    def assert_safe_baseline(self, expected_head: str|None=None, require_remote_sync: bool=True):
        snap=self.snapshot(fetch=False)
        errors=[]
        if snap.branch != self.branch:
            errors.append(f"branch={snap.branch}, expected={self.branch}")
        if not snap.clean:
            errors.append("worktree_dirty")
        if expected_head and snap.head != expected_head:
            errors.append(f"head={snap.head}, expected={expected_head}")
        if require_remote_sync and snap.origin_head and snap.origin_head != snap.head:
            errors.append("local_remote_not_synced")
        if errors:
            raise RuntimeError("; ".join(errors))
        return snap

    def proposed_isolated_worktree(self, task_id: str)->dict:
        safe="".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in task_id)
        return {
            "strategy":"git_worktree",
            "path":str(self.repo_root.parent / f"PROJECT-PHOENIX-AUTO-{safe}"),
            "branch":f"auto/{safe.lower()}",
            "created":False,
            "reason":"v1 dry-run plans isolation but does not mutate repository",
        }
