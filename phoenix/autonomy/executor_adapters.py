from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .execution_planner import ExecutionPlan, PlanStep


@dataclass(frozen=True)
class AdapterExecutionContext:
    host: Any
    plan: ExecutionPlan
    step: PlanStep
    state: dict[str,Any]
    backup_receipt: Path|None
    execution_payloads: dict[str,Any]


@dataclass(frozen=True)
class AdapterExecutionResult:
    outcome: str
    result: dict[str,Any]|None=None
    reason: str|None=None


class ExecutorAdapter(Protocol):
    adapter_id: str
    def execute(self,ctx:AdapterExecutionContext) -> AdapterExecutionResult: ...


class ReadOnlyPlannerAdapter:
    adapter_id="builtin.planner.readonly"

    def __init__(self,host:Any):
        self.host=host

    def execute(self,ctx:AdapterExecutionContext) -> AdapterExecutionResult:
        if ctx.step.mutating:
            raise RuntimeError("read-only adapter received mutating step")
        result=self.host.read_only.execute(ctx.step,ctx.plan)
        return AdapterExecutionResult("COMPLETE",result=result)


class LowRiskMutationAdapter:
    adapter_id="builtin.lowrisk.plan"

    def __init__(self,host:Any):
        self.host=host

    def execute(self,ctx:AdapterExecutionContext) -> AdapterExecutionResult:
        if not ctx.step.mutating:
            raise RuntimeError("LOW-risk mutation adapter received read-only step")
        if ctx.backup_receipt is None:
            return AdapterExecutionResult("PAUSED_GATES",reason="BACKUP_RECEIPT_REQUIRED_FOR_MUTATION")
        self.host._execute_lowrisk(
            ctx.step,ctx.plan,ctx.state,Path(ctx.backup_receipt),ctx.execution_payloads
        )
        return AdapterExecutionResult("COMPLETE",result=ctx.state["step_states"][ctx.step.step_id]["result"])


class MainlinePromotionAdapter:
    adapter_id="builtin.mainline.promoter"

    def __init__(self,host:Any):
        self.host=host

    def execute(self,ctx:AdapterExecutionContext) -> AdapterExecutionResult:
        if ctx.backup_receipt is None:
            return AdapterExecutionResult("PAUSED_GATES",reason="BACKUP_RECEIPT_REQUIRED_FOR_PROMOTION")
        self.host._execute_promotion(
            ctx.step,ctx.plan,ctx.state,Path(ctx.backup_receipt)
        )
        return AdapterExecutionResult("COMPLETE",result=ctx.state["step_states"][ctx.step.step_id]["result"])
