"""PROJECT PHOENIX Autonomous Development Foundation v1.0.0."""

__version__ = "1.6.0"

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
    "RuntimeProviderProbe","IsolatedRuntimeProvider","DisabledRuntimeProvider",
    "PodmanMachineRuntimeProvider","WindowsSandboxRuntimeProvider",
    "select_runtime_provider","BoundedLevel3CycleService",
    "ChangeRecord","ChangeClassification","RepositoryChangeClassifier",
    "normalize_repository_path","GuardedRepositorySnapshot","CandidateWorktree",
    "GuardedWorktreeManager","initialize_fixture_repository",
    "BoundedRepositoryImprovementCycleService","build_patch_probe_source",
    "AgentTaskSpec","AgentTaskResult","SpecializedAgentRegistry",
    "DagExecutionResult","BoundedDagScheduler",
    "BoundedMultiAgentDagService","build_parallel_dag_probe_source","phase11_fixture_tasks",
    "BacklogTask","BacklogSelection","DeterministicBacklogSelector",
    "BacklogDrivenLevel3CycleService","phase12_review_tasks",
    "BatchTask","BatchSelection","DeterministicBatchSelector",
    "BoundedLevel4BatchService","phase13_review_tasks",
    "CampaignTask","CampaignSelection","DeterministicCampaignSelector",
    "SQLiteCampaignStateStore","RepeatableLevel4CampaignService","phase14_review_tasks",
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

from .isolated_runtime import RuntimeProviderProbe, IsolatedRuntimeProvider, DisabledRuntimeProvider, PodmanMachineRuntimeProvider, WindowsSandboxRuntimeProvider, select_runtime_provider

from .level3_cycle import BoundedLevel3CycleService

from .change_classifier import ChangeRecord, ChangeClassification, RepositoryChangeClassifier, normalize_repository_path

from .worktree_guard import GuardedRepositorySnapshot, CandidateWorktree, GuardedWorktreeManager, initialize_fixture_repository

from .repository_cycle import BoundedRepositoryImprovementCycleService, build_patch_probe_source

from .specialized_agents import AgentTaskSpec, AgentTaskResult, SpecializedAgentRegistry

from .dag_scheduler import DagExecutionResult, BoundedDagScheduler

from .multi_agent_orchestrator import BoundedMultiAgentDagService, build_parallel_dag_probe_source, phase11_fixture_tasks

from .backlog_selector import BacklogTask, BacklogSelection, DeterministicBacklogSelector

from .backlog_cycle import BacklogDrivenLevel3CycleService, phase12_review_tasks

from .batch_selector import BatchTask, BatchSelection, DeterministicBatchSelector

from .batch_cycle import BoundedLevel4BatchService, phase13_review_tasks

from .campaign_selector import CampaignTask, CampaignSelection, DeterministicCampaignSelector

from .campaign_cycle import SQLiteCampaignStateStore, RepeatableLevel4CampaignService, phase14_review_tasks
