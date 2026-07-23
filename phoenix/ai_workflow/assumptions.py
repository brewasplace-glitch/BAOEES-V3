"""Assumption handling for incomplete project information."""

from __future__ import annotations

from typing import Any

from .models import WorkflowContext


def add_assumption(
    context: WorkflowContext,
    *,
    key: str,
    value: Any,
    source: str,
    confidence: float,
    status: str = "provisional",
) -> dict:
    if not key.strip():
        raise ValueError("assumption key must not be empty")
    if not source.strip():
        raise ValueError("assumption source must not be empty")
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    record = {
        "key": key,
        "value": value,
        "source": source,
        "confidence": confidence,
        "status": status,
    }
    context.assumptions.append(record)
    context.state[key] = value
    return record
