from __future__ import annotations

from pathlib import Path
import json
from .models import Capability

DEFAULT_CAPABILITIES = (
    Capability("AUTO-POLICY-001","Autonomy Policy","governance","ready",100),
    Capability("AUTO-RISK-001","Risk Classifier","governance","ready",100),
    Capability("AUTO-CAP-001","Capability Registry","knowledge","ready",95),
    Capability("AUTO-BACKLOG-001","Backlog Generator","planning","ready",90),
    Capability("AUTO-PLAN-001","Task Planner","planning","ready",90),
    Capability("AUTO-WORKTREE-001","Safe Worktree Manager","git","ready",100),
    Capability("AUTO-OSS-001","Open-Source Scout","research","ready",90),
    Capability("AUTO-GATE-001","Test/Evidence Gate","qa","ready",100),
    Capability("AUTO-REPAIR-001","Auto-Repair FSM","repair","ready",85),
    Capability("AUTO-LEARN-001","Learning Event Store","learning","ready",85),
    Capability("AUTO-CYCLE-001","Autonomous Cycle Runner","orchestration","ready",100),
    Capability("AUTO-DASH-001","Autonomy Runtime Dashboard","observability","ready",75),
    Capability("AUTO-LOWRISK-002","LOW-risk autonomous mutation executor","orchestration","ready",100),
    Capability("AUTO-PROMOTE-003","LOW-risk autonomous mainline promotion","orchestration","ready",100),
    Capability("AUTO-BACKUP-004","Backup-gated autonomous promotion backup","governance","ready",100),
    Capability("AUTO-SELF-IMPROVE-005","Bounded LOW-risk self-improvement loop","orchestration","ready",100),
    Capability("AUTO-BIB-002","BIB learning-event ingestion","knowledge","planned",70),
)

class CapabilityRegistry:
    def __init__(self, capabilities=None):
        self._items={c.capability_id:c for c in (capabilities or DEFAULT_CAPABILITIES)}

    def all(self):
        return tuple(sorted(self._items.values(), key=lambda c:(-c.priority,c.capability_id)))

    def gaps(self):
        return tuple(c for c in self.all() if c.status not in {"ready","complete"})

    def get(self, capability_id: str):
        return self._items[capability_id]

    def to_dict(self):
        return {
            "schema":"PHOENIX_AUTONOMY_CAPABILITY_REGISTRY_V1",
            "capabilities":[{
                "id":c.capability_id,
                "name":c.name,
                "domain":c.domain,
                "status":c.status,
                "priority":c.priority,
                "source":c.source,
                "metadata":c.metadata,
            } for c in self.all()]
        }

    def save(self, path: Path):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.to_dict(),indent=2,ensure_ascii=False),encoding="utf-8")
