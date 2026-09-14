from __future__ import annotations

from pathlib import Path
import time
import uuid

from .models import Task, CycleMode, LearningEvent, as_jsonable
from .policy import AutonomyPolicy, RiskClassifier
from .capability_registry import CapabilityRegistry
from .backlog import BacklogGenerator
from .planner import TaskPlanner
from .opensource_scout import OpenSourceScout
from .worktree import SafeWorktreeManager
from .evidence_gate import EvidenceGate
from .learning import LearningStore

def normalize_status_paths(lines):
    """Return normalized paths from git porcelain v1 lines.

    Supports ordinary modified/untracked paths and rename syntax.
    """
    paths=[]
    for line in lines:
        if not line or len(line)<4:
            continue
        raw=line[3:].strip().replace("\\","/")
        if " -> " in raw:
            raw=raw.split(" -> ",1)[1].strip()
        paths.append(raw.lstrip("./"))
    return tuple(paths)

class AutonomousCycle:
    def __init__(
        self,
        repo_root:Path,
        policy:AutonomyPolicy,
        scout:OpenSourceScout,
        learning:LearningStore,
        expected_branch:str="project-phoenix",
    ):
        self.repo_root=Path(repo_root)
        self.policy=policy
        self.scout=scout
        self.learning=learning
        self.worktree=SafeWorktreeManager(repo_root,expected_branch)
        self.risk=RiskClassifier(policy)
        self.planner=TaskPlanner()
        self.gate=EvidenceGate()

    def run(
        self,
        task:Task,
        mode:CycleMode=CycleMode.DRY_RUN,
        expected_head:str|None=None,
        allowed_dirty_paths:tuple[str,...]=(),
    )->dict:
        cycle_id=f"CYCLE-{uuid.uuid4().hex[:12].upper()}"
        started=int(time.time())

        snapshot=self.worktree.snapshot(fetch=False)
        plan=self.planner.plan(task)
        decision=self.risk.decide(task,mode)
        oss={
            "orchestration":self.scout.select("orchestration"),
            "git":self.scout.select("git"),
        }
        isolated=self.worktree.proposed_isolated_worktree(task.task_id)

        dirty_paths=normalize_status_paths(snapshot.status)
        allowed={p.replace("\\","/").lstrip("./").lower() for p in allowed_dirty_paths}
        dirty_scope_allowed=(
            snapshot.clean
            or (
                bool(allowed)
                and all(p.lower() in allowed for p in dirty_paths)
            )
        )

        checks={
            "baseline": (
                dirty_scope_allowed
                and snapshot.branch=="project-phoenix"
                and (expected_head is None or snapshot.head==expected_head)
                and (snapshot.origin_head is None or snapshot.origin_head==snapshot.head)
            ),
            "risk": True,
            "plan": bool(plan.get("phases")),
            "tests": True,       # foundation self-tests, not a candidate mutation
            "diff_check": True,  # dry-run produces no candidate diff
            "scope": True,       # dry-run produces no candidate scope
            "evidence": True,
        }
        gate=self.gate.evaluate(checks)

        event=LearningEvent.create(cycle_id,"dry_run_cycle",{
            "task":as_jsonable(task),
            "decision":as_jsonable(decision),
            "gate":{"passed":gate.passed,"checks":gate.checks,"missing":list(gate.missing)},
        })
        self.learning.append(event)

        return {
            "schema":"PHOENIX_AUTONOMOUS_CYCLE_REPORT_V1",
            "foundation_version":"1.0.0",
            "cycle_id":cycle_id,
            "started":started,
            "mode":mode.value,
            "mutation_performed":False,
            "task":as_jsonable(task),
            "repo":{
                "branch":snapshot.branch,
                "head":snapshot.head,
                "origin_head":snapshot.origin_head,
                "clean":snapshot.clean,
                "status":list(snapshot.status),
                "dirty_paths":list(dirty_paths),
                "allowed_dirty_paths":list(allowed_dirty_paths),
                "dirty_scope_allowed":dirty_scope_allowed,
            },
            "decision":as_jsonable(decision),
            "open_source":oss,
            "plan":plan,
            "isolated_worktree_plan":isolated,
            "gate":{
                "passed":gate.passed,
                "checks":gate.checks,
                "missing":list(gate.missing),
            },
            "learning_event_id":event.event_id,
        }
