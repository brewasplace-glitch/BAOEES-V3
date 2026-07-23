"""Execution and governance policy for AI workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowPolicy:
    fail_fast: bool = True
    allow_assumptions: bool = True
    require_assumption_source: bool = True
    require_evidence_for_success: bool = False
    max_total_steps: int = 100
    max_retry_limit: int = 3

    def validate_step_count(self, count: int) -> None:
        if count <= 0:
            raise ValueError("workflow must contain at least one step")
        if count > self.max_total_steps:
            raise ValueError("workflow exceeds maximum allowed steps")

    def validate_retry_limit(self, retry_limit: int) -> None:
        if retry_limit < 0:
            raise ValueError("retry_limit must be zero or greater")
        if retry_limit > self.max_retry_limit:
            raise ValueError("retry_limit exceeds policy maximum")
