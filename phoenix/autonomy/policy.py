from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .models import RiskLevel, CycleMode, Task, Decision

@dataclass(frozen=True)
class AutonomyPolicy:
    default_mode: CycleMode = CycleMode.DRY_RUN
    low_risk_auto_enabled: bool = False
    require_clean_worktree: bool = True
    require_remote_sync: bool = True
    max_repair_attempts: int = 3
    protected_paths: tuple[str, ...] = (
        ".git/",
        "bib/",
        "phoenix/local_app/static/official_start_v3_0/phoenix_detv_cad_bridge.js",
        "runners/",
    )
    critical_terms: tuple[str, ...] = (
        "production release",
        "for construction",
        "professional approval",
        "secret",
        "credential",
        "token",
        "password",
        "delete repository",
        "force push",
    )

    @classmethod
    def from_json(cls, path: Path) -> "AutonomyPolicy":
        data=json.loads(path.read_text(encoding="utf-8"))
        return cls(
            default_mode=CycleMode(data.get("default_mode","dry-run")),
            low_risk_auto_enabled=bool(data.get("low_risk_auto_enabled",False)),
            require_clean_worktree=bool(data.get("require_clean_worktree",True)),
            require_remote_sync=bool(data.get("require_remote_sync",True)),
            max_repair_attempts=int(data.get("max_repair_attempts",3)),
            protected_paths=tuple(data.get("protected_paths",cls.protected_paths)),
            critical_terms=tuple(data.get("critical_terms",cls.critical_terms)),
        )

class RiskClassifier:
    """Deterministic conservative classifier.

    v1.0 deliberately makes LOW narrow:
    documentation and generated evidence only. Source code is MEDIUM or higher.
    """

    def __init__(self, policy: AutonomyPolicy):
        self.policy=policy

    def classify(self, task: Task) -> tuple[RiskLevel, list[str]]:
        evidence=[]
        text=(task.title+" "+task.action+" "+" ".join(task.paths)).lower()

        if any(term.lower() in text for term in self.policy.critical_terms):
            return RiskLevel.CRITICAL, ["critical_term_match"]

        normalized=[p.replace("\\","/").lstrip("./") for p in task.paths]
        for p in normalized:
            low=p.lower()
            if any(low == protected.rstrip("/").lower() or low.startswith(protected.lower())
                   for protected in self.policy.protected_paths):
                return RiskLevel.HIGH, [f"protected_path:{p}"]

        if any(p.lower().endswith((".ps1",".bat",".cmd",".exe",".dll")) for p in normalized):
            return RiskLevel.HIGH, ["executable_or_installer_change"]

        if any(p.lower().endswith((".py",".js",".ts",".tsx",".html",".css")) for p in normalized):
            evidence.append("source_code_change")
            return RiskLevel.MEDIUM, evidence

        if normalized and all(
            p.lower().startswith(("docs/","outputs/","evidence/"))
            or p.lower().endswith((".md",".txt"))
            for p in normalized
        ):
            return RiskLevel.LOW, ["documentation_or_evidence_only"]

        if not normalized and task.action.lower() in {"analyze","inspect","plan","research","report"}:
            return RiskLevel.LOW, ["read_only_action"]

        return RiskLevel.MEDIUM, ["default_conservative"]

    def decide(self, task: Task, mode: CycleMode) -> Decision:
        risk,evidence=self.classify(task)
        if task.requested_risk and task.requested_risk.value != risk.value:
            evidence.append(f"requested_risk:{task.requested_risk.value}")

        if mode == CycleMode.DRY_RUN:
            return Decision(task.task_id,risk,False,mode,"dry-run never executes",tuple(evidence))

        if mode == CycleMode.LOW_RISK_AUTO:
            if not self.policy.low_risk_auto_enabled:
                return Decision(task.task_id,risk,False,mode,"LOW-risk auto locked by policy",tuple(evidence))
            if risk != RiskLevel.LOW:
                return Decision(task.task_id,risk,False,mode,"only LOW risk may auto-execute",tuple(evidence))
            return Decision(task.task_id,risk,True,mode,"LOW-risk policy permits execution",tuple(evidence))

        return Decision(task.task_id,risk,False,mode,"unsupported mode",tuple(evidence))
