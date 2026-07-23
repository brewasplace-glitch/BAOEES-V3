"""Governed execution engine for Phoenix AI workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .models import DecisionRecord, WorkflowContext, WorkflowDefinition
from .planner import WorkflowPlanner
from .policy import WorkflowPolicy


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIWorkflowEngine:
    """Executes dependency-aware workflows with traceable decisions."""

    def __init__(
        self,
        *,
        policy: Optional[WorkflowPolicy] = None,
        planner: Optional[WorkflowPlanner] = None,
    ) -> None:
        self.policy = policy or WorkflowPolicy()
        self.planner = planner or WorkflowPlanner()

    def execute(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
    ) -> list[DecisionRecord]:
        self.policy.validate_step_count(len(workflow.steps))
        for step in workflow.steps:
            self.policy.validate_retry_limit(step.retry_limit)

        ordered_steps = self.planner.plan(workflow)
        decisions: list[DecisionRecord] = []
        status_by_name: dict[str, str] = {}

        for step in ordered_steps:
            blocked = [
                dependency
                for dependency in step.depends_on
                if status_by_name.get(dependency) != "succeeded"
            ]
            if blocked:
                record = DecisionRecord(
                    step_id=step.step_id,
                    step_name=step.name,
                    status="blocked",
                    started_at=utc_now_iso(),
                    finished_at=utc_now_iso(),
                    attempts=0,
                    rationale="Blocked by unsuccessful dependencies: "
                    + ", ".join(blocked),
                )
                decisions.append(record)
                status_by_name[step.name] = "blocked"
                continue

            if step.condition is not None and not step.condition(context):
                record = DecisionRecord(
                    step_id=step.step_id,
                    step_name=step.name,
                    status="skipped",
                    started_at=utc_now_iso(),
                    finished_at=utc_now_iso(),
                    attempts=0,
                    rationale="Step condition evaluated to false.",
                )
                decisions.append(record)
                status_by_name[step.name] = "skipped"
                continue

            attempts = 0
            started = utc_now_iso()
            result = None
            error = None
            status = "failed"

            while attempts <= step.retry_limit:
                attempts += 1
                try:
                    result = step.action(context)
                    status = "succeeded"
                    error = None
                    break
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"

            evidence_refs = [
                str(item.get("id"))
                for item in context.evidence
                if item.get("id") is not None
            ]
            record = DecisionRecord(
                step_id=step.step_id,
                step_name=step.name,
                status=status,
                started_at=started,
                finished_at=utc_now_iso(),
                attempts=attempts,
                result=result,
                error=error,
                rationale=(
                    "Step completed successfully."
                    if status == "succeeded"
                    else "Step failed after permitted attempts."
                ),
                evidence_refs=evidence_refs,
            )
            decisions.append(record)
            status_by_name[step.name] = status

            if status == "failed" and step.required and self.policy.fail_fast:
                break

        return decisions
