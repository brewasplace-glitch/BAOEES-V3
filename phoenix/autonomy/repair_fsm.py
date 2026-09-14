from __future__ import annotations
from enum import Enum

class RepairState(str,Enum):
    IDLE="IDLE"
    DETECTED="DETECTED"
    DIAGNOSED="DIAGNOSED"
    PATCH_PLANNED="PATCH_PLANNED"
    PATCHED="PATCHED"
    TESTING="TESTING"
    PASS="PASS"
    RETRY="RETRY"
    BLOCKED="BLOCKED"

_ALLOWED={
    RepairState.IDLE:{RepairState.DETECTED},
    RepairState.DETECTED:{RepairState.DIAGNOSED,RepairState.BLOCKED},
    RepairState.DIAGNOSED:{RepairState.PATCH_PLANNED,RepairState.BLOCKED},
    RepairState.PATCH_PLANNED:{RepairState.PATCHED,RepairState.BLOCKED},
    RepairState.PATCHED:{RepairState.TESTING},
    RepairState.TESTING:{RepairState.PASS,RepairState.RETRY,RepairState.BLOCKED},
    RepairState.RETRY:{RepairState.DIAGNOSED,RepairState.BLOCKED},
    RepairState.PASS:set(),
    RepairState.BLOCKED:set(),
}

class AutoRepairFSM:
    def __init__(self,max_attempts:int=3):
        self.state=RepairState.IDLE
        self.attempts=0
        self.max_attempts=max_attempts
        self.history=[self.state.value]

    def transition(self,new_state:RepairState):
        if new_state not in _ALLOWED[self.state]:
            raise ValueError(f"illegal transition {self.state.value}->{new_state.value}")
        if new_state==RepairState.RETRY:
            self.attempts+=1
            if self.attempts>=self.max_attempts:
                new_state=RepairState.BLOCKED
        self.state=new_state
        self.history.append(self.state.value)
        return self.state
