"""Deterministic decision-log persistence."""

from __future__ import annotations

from pathlib import Path

from phoenix.database.persistence import save_json

from .models import DecisionRecord, WorkflowContext, WorkflowDefinition


def save_workflow_evidence(
    path: Path | str,
    *,
    workflow: WorkflowDefinition,
    context: WorkflowContext,
    decisions: list[DecisionRecord],
) -> str:
    payload = {
        "schema_version": "1.0",
        "workflow": {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "version": workflow.version,
        },
        "project_id": context.project_id,
        "state": context.state,
        "assumptions": context.assumptions,
        "evidence": context.evidence,
        "decisions": [decision.to_dict() for decision in decisions],
    }
    return save_json(Path(path), payload)
