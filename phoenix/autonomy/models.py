from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
import json
import time
import uuid

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CycleMode(str, Enum):
    DRY_RUN = "dry-run"
    LOW_RISK_AUTO = "low-risk-auto"

@dataclass(frozen=True)
class Capability:
    capability_id: str
    name: str
    domain: str
    status: str = "planned"
    priority: int = 50
    source: str = "phoenix"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    capability_id: str
    action: str
    paths: tuple[str, ...] = ()
    requested_risk: RiskLevel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Decision:
    task_id: str
    risk: RiskLevel
    allowed: bool
    mode: CycleMode
    reason: str
    evidence: tuple[str, ...] = ()

@dataclass(frozen=True)
class LearningEvent:
    event_id: str
    timestamp: int
    cycle_id: str
    event_type: str
    payload: dict[str, Any]

    @classmethod
    def create(cls, cycle_id: str, event_type: str, payload: dict[str, Any]) -> "LearningEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=int(time.time()),
            cycle_id=cycle_id,
            event_type=event_type,
            payload=payload,
        )

def as_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: as_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): as_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [as_jsonable(v) for v in value]
    return value

def dumps(value: Any) -> str:
    return json.dumps(as_jsonable(value), ensure_ascii=False, sort_keys=True, indent=2)
