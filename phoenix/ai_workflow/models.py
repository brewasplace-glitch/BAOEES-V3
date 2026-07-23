"""Models for Phoenix AI-driven workflow execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowContext:
    project_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowStep:
    name: str
    capability: str
    action: Callable[[WorkflowContext], Any]
    depends_on: list[str] = field(default_factory=list)
    condition: Optional[Callable[[WorkflowContext], bool]] = None
    step_id: str = field(default_factory=lambda: str(uuid4()))
    retry_limit: int = 0
    required: bool = True


@dataclass
class WorkflowDefinition:
    name: str
    version: str
    steps: list[WorkflowStep]
    workflow_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class DecisionRecord:
    step_id: str
    step_name: str
    status: str
    started_at: str
    finished_at: str
    attempts: int
    result: Any = None
    error: Optional[str] = None
    rationale: str = ""
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
