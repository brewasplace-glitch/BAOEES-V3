"""PROJECT PHOENIX Autonomous Development Foundation v1.0.0."""

__version__ = "1.0.0"

from .models import RiskLevel, CycleMode, Task, Decision, Capability, LearningEvent
from .policy import AutonomyPolicy, RiskClassifier
from .capability_registry import CapabilityRegistry
from .backlog import BacklogGenerator
from .planner import TaskPlanner
from .opensource_scout import OpenSourceScout
from .worktree import SafeWorktreeManager
from .evidence_gate import EvidenceGate
from .repair_fsm import AutoRepairFSM, RepairState
from .learning import LearningStore
from .cycle import AutonomousCycle
from .executor import LowRiskExecutor, LowRiskExecutionPolicy, TextMutation
from .request_io import load_json_request

__all__ = [
    "RiskLevel","CycleMode","Task","Decision","Capability","LearningEvent",
    "AutonomyPolicy","RiskClassifier","CapabilityRegistry","BacklogGenerator",
    "TaskPlanner","OpenSourceScout","SafeWorktreeManager","EvidenceGate",
    "AutoRepairFSM","RepairState","LearningStore","AutonomousCycle",
    "LowRiskExecutor","LowRiskExecutionPolicy","TextMutation","load_json_request",
]
