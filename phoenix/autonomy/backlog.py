from __future__ import annotations
import hashlib
from .models import Task
from .capability_registry import CapabilityRegistry

class BacklogGenerator:
    def generate(self, registry: CapabilityRegistry) -> tuple[Task,...]:
        tasks=[]
        for cap in registry.gaps():
            raw=f"{cap.capability_id}:{cap.status}"
            suffix=hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
            tasks.append(Task(
                task_id=f"TASK-{suffix.upper()}",
                title=f"Advance {cap.name}",
                capability_id=cap.capability_id,
                action="plan" if cap.status=="locked" else "analyze",
                paths=(),
                metadata={"capability_status":cap.status,"priority":cap.priority},
            ))
        return tuple(tasks)
