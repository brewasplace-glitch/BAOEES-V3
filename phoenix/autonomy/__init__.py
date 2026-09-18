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
    "LowRiskMainlinePromotionPolicy","LowRiskMainlinePromoter",
    "LowRiskSelfImprovementPolicy","LowRiskSelfImprovementLoop",
    "ActionRequest","PolicyDecision","PolicyDecisionLog","AutonomyDecisionEngine",
    "MutationIntent","GatewayPermit","GatewayAuditLog","UniversalAutonomyGateway",
    "LocalIntegrityKey","ApprovalResumeEngine","OrchestrationStore","ReadOnlyStepExecutor","AutonomousExecutionOrchestrator",
    "IsolatedVerificationProvider","DisabledIsolationProvider","StaticVerificationReport","AdapterStaticVerifier",
    "DeterministicReadOnlyAdapterSynthesizer","AdapterSynthesisService",
]

from .promoter import LowRiskMainlinePromotionPolicy, LowRiskMainlinePromoter

from .self_improvement import LowRiskSelfImprovementPolicy, LowRiskSelfImprovementLoop

from .decision_engine import ActionRequest, PolicyDecision, PolicyDecisionLog, AutonomyDecisionEngine

from .universal_gateway import MutationIntent, GatewayPermit, GatewayAuditLog, UniversalAutonomyGateway

from .execution_planner import GoalSpec, PlanStep, ExecutionPlan, DagAdapter, AutonomousExecutionPlanner, ExecutionCoordinator

from .approval_resume import LocalIntegrityKey, ApprovalResumeEngine

from .execution_orchestrator import OrchestrationStore, ReadOnlyStepExecutor, AutonomousExecutionOrchestrator

from .executor_adapter_registry import ExecutorAdapterDescriptor, UniversalCapabilityExecutorRegistry

from .executor_adapters import AdapterExecutionContext, AdapterExecutionResult, ReadOnlyPlannerAdapter, LowRiskMutationAdapter, MainlinePromotionAdapter

from .engine_onboarding import DiscoveryRecord, EngineManifestDiscovery, EngineOnboardingService

from .adapter_implementation import AdapterImplementationValidation, AdapterImplementationValidator

from .engine_activation import EngineActivationService

from .adapter_verification import IsolatedVerificationProvider, DisabledIsolationProvider, StaticVerificationReport, AdapterStaticVerifier

from .adapter_synthesis import DeterministicReadOnlyAdapterSynthesizer, AdapterSynthesisService
