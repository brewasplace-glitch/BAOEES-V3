from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import time
import uuid

from .models import Capability, Task, RiskLevel, LearningEvent
from .policy import AutonomyPolicy, RiskClassifier
from .capability_registry import CapabilityRegistry
from .backlog import BacklogGenerator
from .planner import TaskPlanner
from .opensource_scout import OpenSourceScout
from .learning import LearningStore
from .executor import LowRiskExecutor, LowRiskExecutionPolicy, TextMutation
from .promoter import LowRiskMainlinePromoter, LowRiskMainlinePromotionPolicy
from .worktree import SafeWorktreeManager


@dataclass(frozen=True)
class LowRiskSelfImprovementPolicy:
    enabled: bool
    mode: str
    max_cycles_per_invocation: int
    max_candidates_per_cycle: int
    stop_on_first_failure: bool
    require_clean_synced_baseline: bool
    require_verified_backup_before_promotion: bool
    require_open_source_review: bool
    require_low_risk_classification: bool
    target_root: str
    target_extension: str
    mainline_promotion: str
    source_self_modification: str
    medium_high_critical: str
    central_decision_engine_required: bool = False

    @classmethod
    def from_json(cls, path: Path) -> "LowRiskSelfImprovementPolicy":
        d=json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return cls(
            bool(d["enabled"]),
            str(d["mode"]),
            int(d["max_cycles_per_invocation"]),
            int(d["max_candidates_per_cycle"]),
            bool(d["stop_on_first_failure"]),
            bool(d["require_clean_synced_baseline"]),
            bool(d["require_verified_backup_before_promotion"]),
            bool(d["require_open_source_review"]),
            bool(d["require_low_risk_classification"]),
            str(d["target_root"]),
            str(d["target_extension"]),
            str(d["mainline_promotion"]),
            str(d["source_self_modification"]),
            str(d["medium_high_critical"]),
            bool(d.get("central_decision_engine_required",False)),
        )


def _slug(value: str) -> str:
    clean="".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in clean:
        clean=clean.replace("--","-")
    return clean.strip("-") or "autonomy"


class LowRiskSelfImprovementLoop:
    """Bounded autonomous LOW-risk improvement cycle.

    v1 deliberately cannot self-modify Phoenix source code. It can convert a
    capability gap into planning/evidence under the LOW-risk generated-doc root,
    execute that change in an isolated worktree, then promote it only through
    the verified backup-gated fast-forward promoter.
    """

    def __init__(
        self,
        repo_root: Path,
        autonomy_policy: AutonomyPolicy,
        execution_policy: LowRiskExecutionPolicy,
        promotion_policy: LowRiskMainlinePromotionPolicy,
        self_policy: LowRiskSelfImprovementPolicy,
        scout: OpenSourceScout,
        learning: LearningStore,
        registry: CapabilityRegistry | None = None,
        runtime_root: Path | None = None,
        decision_engine=None,
    ):
        self.repo_root=Path(repo_root).resolve()
        self.autonomy_policy=autonomy_policy
        self.execution_policy=execution_policy
        self.promotion_policy=promotion_policy
        self.self_policy=self_policy
        self.scout=scout
        self.learning=learning
        self.registry=registry or CapabilityRegistry()
        self.runtime_root=Path(runtime_root) if runtime_root else learning.path.parent/"self_improvement"
        self.worktree=SafeWorktreeManager(self.repo_root,promotion_policy.main_branch)
        self.risk=RiskClassifier(autonomy_policy)
        self.planner=TaskPlanner()
        self.backlog=BacklogGenerator()
        self.decision_engine=decision_engine

    def _select_gap(self) -> tuple[Capability, Task]:
        gaps=self.registry.gaps()
        if gaps:
            cap=gaps[0]
            source_task=self.backlog.generate(self.registry)[0]
        else:
            cap=Capability(
                "AUTO-MAINT-001",
                "Autonomy Health Evidence",
                "observability",
                "ready",
                50,
            )
            source_task=Task(
                task_id="TASK-AUTONOMY-HEALTH",
                title="Refresh autonomy health evidence",
                capability_id=cap.capability_id,
                action="report",
                paths=(),
                metadata={"maintenance":True},
            )
        return cap,source_task

    def _target_path(self, capability: Capability) -> str:
        root=self.self_policy.target_root.replace("\\","/").rstrip("/")+"/"
        return root+_slug(capability.capability_id)+self.self_policy.target_extension

    def _open_source_review(self) -> dict:
        review=self.scout.select("orchestration")
        if self.self_policy.require_open_source_review:
            if not review.get("primary") or not review.get("fallback"):
                raise RuntimeError("open-source primary/fallback orchestration review missing")
        return review

    def _render_document(
        self,
        cycle_id: str,
        baseline: str,
        capability: Capability,
        source_task: Task,
        target_path: str,
        review: dict,
        plan: dict,
    ) -> str:
        primary=(review.get("primary") or {}).get("name","NONE")
        fallback=(review.get("fallback") or {}).get("name","NONE")
        phases=", ".join(x["phase"] for x in plan.get("phases",[]))
        return (
            "# PHOENIX LOW-risk Self-Improvement Evidence\n\n"
            f"- Cycle: `{cycle_id}`\n"
            f"- Baseline before cycle: `{baseline}`\n"
            f"- Capability gap: `{capability.capability_id}` — {capability.name}\n"
            f"- Capability status: `{capability.status}`\n"
            f"- Backlog task: `{source_task.task_id}` — {source_task.title}\n"
            f"- LOW-risk target: `{target_path}`\n"
            f"- Open-source primary candidate: `{primary}`\n"
            f"- Open-source fallback candidate: `{fallback}`\n"
            f"- Plan phases: `{phases}`\n\n"
            "## Safety boundary\n\n"
            "- Only generated documentation/evidence is changed automatically.\n"
            "- Phoenix source-code self-modification is blocked in v1.\n"
            "- MEDIUM, HIGH and CRITICAL execution remain blocked.\n"
            "- Promotion requires a verified backup and `git merge --ff-only`.\n"
            "- Force push is forbidden.\n\n"
            "## Improvement outcome\n\n"
            "This cycle converts the highest-priority capability gap into current, "
            "versioned planning/evidence so the next engineering step is explicit, "
            "traceable and available to the BIB governance layer.\n"
        )

    def run_once(self, expected_head: str, backup_receipt: Path) -> dict:
        if not self.self_policy.enabled:
            raise RuntimeError("self-improvement policy disabled")
        if self.self_policy.mode!="bounded_single_cycle":
            raise RuntimeError("unsupported self-improvement mode")
        if self.self_policy.max_cycles_per_invocation!=1:
            raise RuntimeError("v1 requires exactly one bounded cycle")
        if self.self_policy.max_candidates_per_cycle!=1:
            raise RuntimeError("v1 requires exactly one candidate per cycle")
        if self.self_policy.mainline_promotion!="ENABLED_FF_ONLY_BACKUP_GATED":
            raise RuntimeError("self-improvement mainline gate invalid")
        if self.self_policy.source_self_modification!="BLOCKED":
            raise RuntimeError("source self-modification must remain blocked")
        if self.self_policy.medium_high_critical!="BLOCKED":
            raise RuntimeError("MEDIUM/HIGH/CRITICAL must remain blocked")

        snap=self.worktree.assert_safe_baseline(
            expected_head,
            require_remote_sync=self.self_policy.require_clean_synced_baseline,
        )
        if not Path(backup_receipt).is_file():
            raise RuntimeError("verified backup receipt required before self-improvement")

        cycle_id="SELF-"+uuid.uuid4().hex[:12].upper()
        capability,source_task=self._select_gap()
        target=self._target_path(capability)
        review=self._open_source_review()

        task=Task(
            task_id=cycle_id,
            title=f"Advance {capability.name} with LOW-risk planning evidence",
            capability_id=capability.capability_id,
            action="update",
            paths=(target,),
            requested_risk=RiskLevel.LOW,
            metadata={
                "source_backlog_task_id":source_task.task_id,
                "bounded_self_improvement":True,
            },
        )
        risk,evidence=self.risk.classify(task)
        if self.self_policy.require_low_risk_classification and risk!=RiskLevel.LOW:
            raise RuntimeError(f"self-improvement task must classify LOW, got {risk.value}")

        plan=self.planner.plan(task)

        if self.self_policy.central_decision_engine_required and self.decision_engine is None:
            raise RuntimeError("central autonomy decision engine required")

        policy_decision=None
        if self.decision_engine is not None:
            from .decision_engine import ActionRequest
            policy_request=ActionRequest(
                action="autonomy.self_improvement.low_risk_evidence",
                risk="LOW",
                mutating=True,
                domain="orchestration",
                paths=(target,),
                external_effect=False,
                gates=(
                    "clean_synced","verified_backup","open_source_review",
                    "risk_low","allowlisted_path","audit_log",
                ),
                metadata={"cycle_id":cycle_id,"capability_id":capability.capability_id},
            )
            policy_decision=self.decision_engine.require_authorized(policy_request)
        content=self._render_document(
            cycle_id,snap.head,capability,source_task,target,review,plan
        )
        mutation=TextMutation(target,content,"replace")

        executor=LowRiskExecutor(
            self.repo_root,
            self.autonomy_policy,
            self.execution_policy,
            self.learning,
            branch=self.promotion_policy.main_branch,
        )
        execution=executor.execute(
            task,
            (mutation,),
            expected_head=snap.head,
            allowed_main_dirty_paths=(),
            keep_candidate=True,
            publish_candidate=False,
        )

        promoter=LowRiskMainlinePromoter(
            self.repo_root,
            self.promotion_policy,
            runtime_root=self.runtime_root/"promotion",
        )
        promotion=promoter.promote(
            execution["candidate_branch"],
            snap.head,
            Path(backup_receipt),
        )

        final=self.worktree.snapshot(fetch=True)
        if final.branch!=self.promotion_policy.main_branch:
            raise RuntimeError("final branch mismatch")
        if not final.clean:
            raise RuntimeError("final main worktree dirty")
        if final.head!=promotion["promoted_commit"]:
            raise RuntimeError("final HEAD does not equal promoted commit")
        if final.origin_head!=final.head:
            raise RuntimeError("final origin/main mismatch")

        report={
            "schema":"PHOENIX_LOW_RISK_SELF_IMPROVEMENT_REPORT_V1",
            "status":"PASS",
            "cycle_id":cycle_id,
            "baseline_before":snap.head,
            "baseline_after":final.head,
            "capability_gap":{
                "id":capability.capability_id,
                "name":capability.name,
                "status":capability.status,
            },
            "risk":risk.value,
            "risk_evidence":list(evidence),
            "policy_decision":policy_decision.to_dict() if policy_decision is not None else None,
            "target_path":target,
            "open_source_review":review,
            "plan":plan,
            "candidate_branch":execution["candidate_branch"],
            "candidate_commit":execution["candidate_commit"],
            "promotion":promotion,
            "backup_receipt":str(Path(backup_receipt)),
            "mainline_promotion":"PASS_FF_ONLY_BACKUP_GATED",
            "source_self_modification":"BLOCKED",
            "medium_high_critical":"BLOCKED",
            "repository_end_state":"CLEAN_SYNCED",
        }

        report_dir=self.runtime_root/cycle_id
        report_dir.mkdir(parents=True,exist_ok=True)
        (report_dir/"self_improvement_report.json").write_text(
            json.dumps(report,indent=2,ensure_ascii=False),
            encoding="utf-8",
            newline="\n",
        )
        self.learning.append(
            LearningEvent.create(cycle_id,"low_risk_self_improvement",report)
        )
        return report
