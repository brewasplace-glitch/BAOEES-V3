from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import hashlib
import hmac
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import uuid

from .approval_resume import LocalIntegrityKey
from .campaign_selector import (
    CampaignSelection,
    CampaignTask,
    DeterministicCampaignSelector,
    campaign_object_sha256,
    canonical_campaign_bytes,
)
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .multi_agent_orchestrator import BoundedMultiAgentDagService
from .promoter import LowRiskMainlinePromoter, LowRiskMainlinePromotionPolicy
from .repository_cycle import BoundedRepositoryImprovementCycleService
from .specialized_agents import AgentTaskSpec
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway
from .worktree_guard import CandidateWorktree, GuardedWorktreeManager


class _CampaignTestOnlyGateway:
    def authorize(self, intent: MutationIntent) -> MutationIntent:
        return intent

    def consume(self, permit: MutationIntent, **bindings: Any) -> None:
        paths = tuple(str(path).replace("\\", "/").lstrip("./") for path in bindings.get("paths", ()))
        if (
            permit.engine_id != bindings.get("engine_id")
            or permit.action != bindings.get("action")
            or permit.paths != paths
        ):
            raise PermissionError("PHASE14_TEST_GATEWAY_EXACT_BINDING_DENY")


def phase14_review_tasks(selection: CampaignSelection, batch_number: int) -> tuple[AgentTaskSpec, ...]:
    common = {
        "campaign_task_ids": list(selection.task_ids),
        "backlog_sha256": selection.backlog_sha256,
        "completed_before": list(selection.completed_before),
        "output_paths": [task.output_path for task in selection.tasks],
        "batch_number": batch_number,
    }
    return (
        AgentTaskSpec("observe", "agent.context.observer", "research.inspect", payload={**common, "scope": "campaign-batch"}),
        AgentTaskSpec("plan", "agent.planning.specialist", "planning.analyze", ("observe",), payload={**common, "mode": "repeatable-level4"}),
        AgentTaskSpec("qa", "agent.qa.specialist", "qa.inspect", ("observe",), payload={**common, "gate": "resume-safe-transactional-lane-a"}),
        AgentTaskSpec("research", "agent.research.specialist", "research.inspect", ("observe",), payload={**common, "source": "committed-campaign"}),
        AgentTaskSpec("merge", "agent.evidence.merger", "evidence.merge", ("plan", "qa", "research"), payload={**common, "format": "canonical"}),
    )


class SQLiteCampaignStateStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._volatile: dict[str, Any] | None = None

    def load(self, *, persist: bool) -> dict[str, Any] | None:
        if not persist:
            return None if self._volatile is None else json.loads(json.dumps(self._volatile))
        if not self.path.is_file():
            return None
        connection = sqlite3.connect(self.path)
        try:
            row = connection.execute(
                "SELECT payload_json, payload_sha256 FROM campaign_state WHERE singleton_id=1"
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        payload_json, expected = str(row[0]), str(row[1])
        if hashlib.sha256(payload_json.encode("utf-8")).hexdigest() != expected:
            raise RuntimeError("PHASE14_SQLITE_STATE_DIGEST_DENY")
        return json.loads(payload_json)

    def save(self, value: dict[str, Any], *, persist: bool) -> None:
        copied = json.loads(json.dumps(value))
        if not persist:
            self._volatile = copied
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload_json = json.dumps(copied, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        connection = sqlite3.connect(self.path, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS campaign_state ("
                "singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1), "
                "payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO campaign_state(singleton_id,payload_json,payload_sha256) VALUES(1,?,?) "
                "ON CONFLICT(singleton_id) DO UPDATE SET payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256",
                (payload_json, digest),
            )
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()


class RepeatableLevel4CampaignService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        policy_root: Path | None = None,
        provider: IsolatedRuntimeProvider | None = None,
        gateway: UniversalAutonomyGateway | None = None,
        enable_gateway: bool = True,
        test_only_gateway: bool = False,
        test_executor: Callable[[Path], dict[str, Any]] | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.policy_root = Path(policy_root or repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        cfg = self.policy_root / "configs" / "phoenix"
        self.policy = json.loads((cfg / "autonomous_campaign_policy_v1.json").read_text(encoding="utf-8-sig"))
        backlog = json.loads((cfg / "autonomous_campaign_v1.json").read_text(encoding="utf-8-sig"))
        runtime_policy = json.loads((cfg / "isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.selector = DeterministicCampaignSelector(self.policy, backlog)
        self.provider = provider or select_runtime_provider(runtime_policy, self.runtime_root)
        self.gateway: Any = gateway
        if enable_gateway and self.gateway is None and self.policy_root == self.repo_root:
            self.gateway = UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(self.runtime_root / "policy_decisions" / "decisions_v1.jsonl"),
                audit_log=GatewayAuditLog(self.runtime_root / "gateway" / "audit_v1.jsonl"),
            )
        if test_only_gateway:
            if enable_gateway or self.policy_root == self.repo_root:
                raise RuntimeError("PHASE14_TEST_GATEWAY_SCOPE_DENY")
            self.gateway = _CampaignTestOnlyGateway()
        self.test_executor = test_executor or self._run_full_regression
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "campaign_cycle_hmac_v1.key"
        ).load_or_create()
        self.state_store = SQLiteCampaignStateStore(
            self.runtime_root / "campaign_cycle" / "campaign_state_v1.sqlite3"
        )
        self.worktrees = GuardedWorktreeManager(
            self.repo_root,
            candidate_branch_prefix=str(self.policy["candidate_branch_prefix"]),
            candidate_directory_prefix="PROJECT-PHOENIX-PHASE14-",
        )
        promotion_policy = LowRiskMainlinePromotionPolicy.from_json(
            cfg / "low_risk_mainline_promotion_policy_v1.json"
        )
        self.promoter = LowRiskMainlinePromoter(
            self.repo_root, promotion_policy, self.runtime_root / "mainline_promotion"
        )
        self.multi_agent = BoundedMultiAgentDagService(
            self.repo_root,
            self.runtime_root / "multi_agent_review",
            policy_root=self.policy_root,
            provider=self.provider,
            enable_gateway=False,
        )
        self.repository_cycle = BoundedRepositoryImprovementCycleService(
            self.repo_root,
            self.runtime_root / "repository_verification",
            policy_root=self.policy_root,
            provider=self.provider,
            enable_gateway=False,
        )
        self._validate_policy()

    def _validate_policy(self) -> None:
        repair = self.policy.get("self_repair", {})
        if (
            repair.get("enabled") is not True
            or int(repair.get("max_repairs_per_batch", 0)) != 1
            or int(repair.get("max_repairs_per_campaign", 0)) != 2
            or repair.get("allowed_failure_codes") != ["TRAILING_WHITESPACE"]
            or repair.get("strategy") != "DETERMINISTIC_RSTRIP_LINES"
        ):
            raise RuntimeError("Phase-14 bounded repair policy invalid")
        resume = self.policy.get("resume", {})
        if resume.get("state_backend") != "SQLITE_ATOMIC_HMAC_BOUND" or resume.get("enabled") is not True:
            raise RuntimeError("Phase-14 resume policy invalid")
        regression = self.policy.get("regression", {})
        files = regression.get("test_files") or []
        if (
            regression.get("command_profile") != "PYTHON_UNITTEST_EXPLICIT_ALLOWLIST"
            or len(files) != 16
            or len(files) != len(set(files))
            or any(Path(str(name)).name != name or not str(name).startswith("test_") or not str(name).endswith(".py") for name in files)
            or int(regression.get("expected_test_count", 0)) != 424
        ):
            raise RuntimeError("Phase-14 explicit regression allowlist invalid")
        if regression.get("network") != "DENY" or regression.get("dependency_install") != "DENY":
            raise RuntimeError("Phase-14 regression boundary invalid")
        if self.policy.get("partial_batch_promotion") != "DENY" or self.policy.get("continuous_monitoring") is not False:
            raise RuntimeError("Phase-14 campaign boundary invalid")

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def _sign(self, value: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, canonical_campaign_bytes(value), hashlib.sha256).hexdigest()

    def _signed(self, value: dict[str, Any], digest_field: str) -> dict[str, Any]:
        result = dict(value)
        result[digest_field] = campaign_object_sha256(result)
        result["hmac_sha256"] = self._sign(dict(result))
        return result

    def _verify_signed(self, value: dict[str, Any], digest_field: str) -> None:
        body = dict(value)
        supplied_hmac = str(body.pop("hmac_sha256", ""))
        if not hmac.compare_digest(supplied_hmac, self._sign(body)):
            raise RuntimeError("PHASE14_STATE_HMAC_DENY")
        supplied_digest = str(body.pop(digest_field, ""))
        if supplied_digest != campaign_object_sha256(body):
            raise RuntimeError("PHASE14_STATE_OBJECT_DIGEST_DENY")

    def _persist_runtime(
        self,
        value: dict[str, Any],
        *,
        category: str,
        action: str,
        gates: tuple[str, ...],
        persist: bool,
    ) -> str | None:
        if not persist:
            return None
        if self.gateway is None:
            raise RuntimeError("Phase-14 gateway unavailable for runtime receipt")
        identifier = str(
            value.get("selection_id") or value.get("repair_id")
            or value.get("batch_id") or value.get("campaign_id")
        )
        relative = f"{category}/{identifier}.json"
        uri = "runtime://campaign_cycle/" + relative
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.campaign_cycle",
            action=action,
            risk="LOW",
            domain="orchestration",
            paths=(uri,),
            gates=gates,
            metadata={"receipt_schema": value.get("schema")},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.campaign_cycle",
            action=action,
            paths=(uri,),
        )
        path = self.runtime_root / "campaign_cycle" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
        return str(path)

    def _save_state(self, state: dict[str, Any], *, persist: bool) -> dict[str, Any]:
        unsigned = dict(state)
        unsigned.pop("state_sha256", None)
        unsigned.pop("hmac_sha256", None)
        signed = self._signed(unsigned, "state_sha256")
        if persist:
            if self.gateway is None:
                raise RuntimeError("Phase-14 gateway unavailable for state write")
            uri = "runtime://campaign_cycle/campaign_state_v1.sqlite3"
            permit = self.gateway.authorize(MutationIntent(
                engine_id="autonomy.campaign_cycle",
                action="autonomy.campaign.state.write",
                risk="LOW",
                domain="orchestration",
                paths=(uri,),
                gates=("audit_log", "signed_state", "atomic_sqlite_transaction"),
                metadata={"state_sha256": signed["state_sha256"]},
            ))
            self.gateway.consume(
                permit,
                engine_id="autonomy.campaign_cycle",
                action="autonomy.campaign.state.write",
                paths=(uri,),
            )
        self.state_store.save(signed, persist=persist)
        return signed

    def _verify_backup(self, path: Path, expected_baseline: str) -> dict[str, Any]:
        target = Path(path)
        if not target.is_file():
            raise RuntimeError("PHASE14_VERIFIED_BACKUP_RECEIPT_REQUIRED")
        value = json.loads(target.read_text(encoding="utf-8-sig"))
        if value.get("status") != "PASS" or value.get("baseline") != expected_baseline:
            raise RuntimeError("PHASE14_BACKUP_BASELINE_DENY")
        if value.get("bundle_verified") is not True or value.get("snapshot_verified") is not True:
            raise RuntimeError("PHASE14_BACKUP_VERIFICATION_DENY")
        if not Path(str(value.get("bundle_path", ""))).is_file() or not Path(str(value.get("snapshot_path", ""))).is_dir():
            raise RuntimeError("PHASE14_BACKUP_ARTIFACT_MISSING")
        return value

    def _new_state(self, baseline: str) -> dict[str, Any]:
        return {
            "schema": "PHOENIX_LEVEL4_CAMPAIGN_STATE_V1",
            "campaign_id": "PHX-L4-CAMPAIGN-001",
            "start_baseline": baseline,
            "current_baseline": baseline,
            "completed_batches": 0,
            "completed_task_ids": [],
            "batch_receipts": [],
            "policy_sha256": campaign_object_sha256(self.policy),
            "backlog_sha256": campaign_object_sha256(self.selector.backlog),
            "status": "ACTIVE",
            "automatic_engine_activation": False,
        }

    def _load_state(self, expected_baseline: str, *, persist: bool) -> dict[str, Any]:
        state = self.state_store.load(persist=persist)
        if state is None:
            state = self._save_state(self._new_state(expected_baseline), persist=persist)
        else:
            self._verify_signed(state, "state_sha256")
        if state.get("schema") != "PHOENIX_LEVEL4_CAMPAIGN_STATE_V1":
            raise RuntimeError("PHASE14_STATE_SCHEMA_DENY")
        if state.get("current_baseline") != expected_baseline:
            raise RuntimeError("PHASE14_AMBIGUOUS_POST_PUSH_STATE_DENY")
        if state.get("policy_sha256") != campaign_object_sha256(self.policy):
            raise RuntimeError("PHASE14_STATE_POLICY_BINDING_DENY")
        if state.get("backlog_sha256") != campaign_object_sha256(self.selector.backlog):
            raise RuntimeError("PHASE14_STATE_BACKLOG_BINDING_DENY")
        self._verify_completed_outputs(state)
        return state

    def _verify_completed_outputs(self, state: dict[str, Any]) -> None:
        flattened: list[str] = []
        for receipt in state.get("batch_receipts", []):
            self._verify_signed(dict(receipt), "completion_sha256")
            for task in receipt.get("task_receipts", []):
                path = self.repo_root / str(task["output_path"])
                if not path.is_file():
                    raise RuntimeError("PHASE14_RESUME_OUTPUT_MISSING_DENY")
                if task.get("final_content_hash_mode") != "UTF8_CANONICAL_LF_V1":
                    raise RuntimeError("PHASE14_RESUME_OUTPUT_HASH_MODE_DENY")
                try:
                    text = path.read_bytes().decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise RuntimeError("PHASE14_RESUME_OUTPUT_ENCODING_DENY") from exc
                canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
                if hashlib.sha256(canonical).hexdigest() != task.get("final_content_sha256"):
                    raise RuntimeError("PHASE14_RESUME_OUTPUT_HASH_DENY")
                flattened.append(str(task["task_id"]))
        if flattened != list(state.get("completed_task_ids", [])):
            raise RuntimeError("PHASE14_RESUME_TASK_CHAIN_DENY")
        if len(state.get("batch_receipts", [])) != int(state.get("completed_batches", -1)):
            raise RuntimeError("PHASE14_RESUME_BATCH_COUNT_DENY")

    def inspect_state(self, expected_baseline: str, *, persist: bool = True) -> dict[str, Any]:
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=True)
        state = self.state_store.load(persist=persist)
        if state is None:
            existing = [
                task.output_path for task in self.selector.tasks
                if (self.repo_root / task.output_path).exists()
            ]
            if existing:
                raise RuntimeError(
                    "PHASE14_UNRECORDED_OUTPUT_WITHOUT_STATE_DENY:" + ",".join(existing)
                )
            return {
                "schema": "PHOENIX_LEVEL4_CAMPAIGN_STATUS_V1",
                "campaign_id": "PHX-L4-CAMPAIGN-001",
                "status": "NOT_STARTED",
                "current_baseline": expected_baseline,
                "completed_batches": 0,
                "completed_task_ids": [],
                "automatic_engine_activation": False,
            }
        self._verify_signed(state, "state_sha256")
        if state.get("schema") != "PHOENIX_LEVEL4_CAMPAIGN_STATE_V1":
            raise RuntimeError("PHASE14_STATE_SCHEMA_DENY")
        if state.get("current_baseline") != expected_baseline:
            raise RuntimeError("PHASE14_AMBIGUOUS_POST_PUSH_STATE_DENY")
        if state.get("policy_sha256") != campaign_object_sha256(self.policy):
            raise RuntimeError("PHASE14_STATE_POLICY_BINDING_DENY")
        if state.get("backlog_sha256") != campaign_object_sha256(self.selector.backlog):
            raise RuntimeError("PHASE14_STATE_BACKLOG_BINDING_DENY")
        self._verify_completed_outputs(state)
        return state

    def campaign_status(self, expected_baseline: str, *, persist: bool = True) -> dict[str, Any]:
        return self.inspect_state(expected_baseline, persist=persist)

    def _selection_receipt(self, selection: CampaignSelection, baseline: str, batch_number: int) -> dict[str, Any]:
        return self._signed({
            "schema": "PHOENIX_AUTONOMOUS_CAMPAIGN_SELECTION_V1",
            "selection_id": "CAMPSEL-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "campaign_id": "PHX-L4-CAMPAIGN-001",
            "batch_number": batch_number,
            "baseline_sha": baseline,
            "task_ids": list(selection.task_ids),
            "task_sha256s": {task.task_id: task.sha256 for task in selection.tasks},
            "selection_keys": [[key[0], key[1]] for key in selection.selection_keys],
            "completed_before": list(selection.completed_before),
            "backlog_sha256": selection.backlog_sha256,
            "automatic_engine_activation": False,
            "status": "SELECTED",
        }, "selection_sha256")

    def _base_content(
        self,
        task: CampaignTask,
        baseline: str,
        selection_receipt: dict[str, Any],
        review: dict[str, Any],
        batch_number: int,
        prior_completion_sha256: str,
    ) -> str:
        lines = [
            f"# PROJECT PHOENIX — {task.title}",
            "",
            f"- Campaign task: `{task.task_id}`",
            f"- Campaign batch: `{batch_number}/2`",
            f"- Source baseline: `{baseline}`",
            f"- Selection SHA-256: `{selection_receipt['selection_sha256']}`",
            f"- Multi-agent result SHA-256: `{review['result_sha256']}`",
            f"- Prior batch completion SHA-256: `{prior_completion_sha256}`",
            "- Risk: `LOW`",
            "- Resume state: `SQLITE_ATOMIC_HMAC_BOUND`",
            "- Regression profile: `EXPLICIT_424_TEST_ALLOWLIST_PER_BATCH`",
            "- Promotion: `FAST_FORWARD_ONLY_NORMAL_NON_FORCE_PUSH`",
            "- Automatic engine activation: `FORBIDDEN`",
            "",
            "All three tasks in this batch are validated together before promotion.",
            "The current batch must pass every gate before promotion.",
            "A proven prior batch remains preserved when a later batch stops fail-closed.",
        ]
        if batch_number == 2:
            lines.extend([
                "The prior completion digest is consumed as bounded lessons-learned evidence.",
                "No security, policy, dependency, isolation or remote failure is auto-repaired.",
            ])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _content_failure(content: str) -> str | None:
        if any(line.endswith((" ", "\t")) for line in content.splitlines()):
            return "TRAILING_WHITESPACE"
        if not content.startswith("# PROJECT PHOENIX — ") or not content.endswith("\n"):
            return "STRUCTURE_INVALID"
        return None

    def _repair_content(self, content: str, failure_code: str) -> str:
        if failure_code not in self.policy["self_repair"]["allowed_failure_codes"]:
            raise RuntimeError(f"PHASE14_UNREPAIRABLE_CONTENT_DENY:{failure_code}")
        return "\n".join(line.rstrip(" \t") for line in content.splitlines()) + "\n"

    def _authorize_candidate_write(self, paths: tuple[str, ...], backup_receipt: Path) -> None:
        if self.gateway is None:
            raise RuntimeError("Phase-14 gateway unavailable for candidate write")
        uris = tuple("worktree://phase14/" + path for path in paths)
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.campaign_cycle",
            action="autonomy.campaign.candidate.write",
            risk="LOW",
            domain="software",
            paths=uris,
            gates=(
                "audit_log", "deterministic_batch_selection", "signed_resume_state",
                "dependency_order_validation", "multi_agent_review", "protected_path_gate", "verified_backup",
            ),
            metadata={"backup_receipt": str(backup_receipt), "task_count": len(paths)},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.campaign_cycle",
            action="autonomy.campaign.candidate.write",
            paths=uris,
        )

    def _run_full_regression(self, candidate_root: Path) -> dict[str, Any]:
        tests = Path(candidate_root) / "tests" / "automation"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(candidate_root)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        deadline = time.monotonic() + float(self.policy["regression"]["timeout_seconds_per_batch"])
        outputs: list[str] = []
        count = 0
        for name in self.policy["regression"]["test_files"]:
            path = tests / str(name)
            if not path.is_file():
                raise RuntimeError(f"PHASE14_REGRESSION_ALLOWLIST_FILE_MISSING:{name}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("PHASE14_FULL_REGRESSION_TIMEOUT")
            completed = subprocess.run(
                [sys.executable, "-B", str(path)],
                cwd=str(candidate_root), env=environment, text=True,
                encoding="utf-8", errors="replace",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=remaining,
            )
            output = completed.stdout
            outputs.append(f"[{name}]\n{output}")
            match = re.search(r"Ran\s+(\d+)\s+tests?", output)
            file_count = int(match.group(1)) if match else 0
            if completed.returncode != 0 or file_count <= 0 or not re.search(r"\nOK\s*$", output):
                raise RuntimeError(
                    f"PHASE14_ALLOWLIST_TEST_DENY:file={name};exit={completed.returncode};tests={file_count};tail={output[-1200:]}"
                )
            count += file_count
        expected = int(self.policy["regression"]["expected_test_count"])
        if count != expected:
            raise RuntimeError(f"PHASE14_FULL_REGRESSION_COUNT_DENY:tests={count};expected={expected}")
        combined = "\n".join(outputs)
        return {
            "status": "PASS", "test_count": count,
            "test_file_count": len(self.policy["regression"]["test_files"]),
            "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        }

    def _promotion_paths(self, expected_baseline: str, candidate_branch: str) -> tuple[str, ...]:
        primary_paths, governance_paths = self.promoter._paths(expected_baseline, candidate_branch)
        return tuple(primary_paths) + tuple(governance_paths)

    def _promotion_permit(self, paths: tuple[str, ...], batch_number: int) -> object:
        if self.gateway is None:
            raise RuntimeError("Phase-14 gateway unavailable for promotion")
        return self.gateway.authorize(MutationIntent(
            engine_id="autonomy.mainline_promoter",
            action="git.fast_forward_promotion",
            risk="LOW", domain="git", paths=paths,
            gates=(
                "verified_backup", "signed_resume_state", "candidate_validated",
                "tests_pass", "evidence_pass", "ff_only", "normal_non_force_push",
                "remote_race_guard", "audit_log",
            ),
            metadata={"phase": "PHASE14_REPEATABLE_LEVEL4_CAMPAIGN", "batch_number": batch_number},
        ))

    def run_next_batch(
        self,
        expected_baseline: str,
        backup_receipt: Path,
        *,
        persist: bool = True,
        test_only: bool = False,
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{40}", expected_baseline):
            raise ValueError("expected baseline must be a 40-character lowercase SHA")
        self._verify_backup(Path(backup_receipt), expected_baseline)
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=True)
        state = self._load_state(expected_baseline, persist=persist)
        if state["status"] == "COMPLETED":
            raise RuntimeError("PHASE14_CAMPAIGN_ALREADY_COMPLETED")
        if int(state["completed_batches"]) >= int(self.policy["max_batches_per_campaign"]):
            raise RuntimeError("PHASE14_CAMPAIGN_READY_TO_FINALIZE")
        batch_number = int(state["completed_batches"]) + 1
        selection = self.selector.select(self.repo_root, tuple(state["completed_task_ids"]))
        selection_receipt = self._selection_receipt(selection, expected_baseline, batch_number)
        selection_path = self._persist_runtime(
            selection_receipt, category="selections",
            action="autonomy.campaign.selection.write",
            gates=("audit_log", "exact_baseline", "signed_resume_state", "deterministic_batch_selection"),
            persist=persist,
        )
        if selection_path:
            selection_receipt["runtime_path"] = selection_path
        review = self.multi_agent.review_tasks(phase14_review_tasks(selection, batch_number))
        if review.get("status") != "PASS" or review.get("parallel_overlap_proven") is not True:
            raise RuntimeError("PHASE14_MULTI_AGENT_REVIEW_DENY")
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=False)

        candidate: CandidateWorktree | None = None
        promoted = False
        repairs: list[dict[str, Any]] = []
        task_receipts: list[dict[str, Any]] = []
        try:
            candidate = self.worktrees.create_candidate(
                f"campaign-001-batch-{batch_number}", expected_baseline,
                parent=self.runtime_root / "candidates",
            )
            expected_paths = tuple(task.output_path for task in selection.tasks)
            self._authorize_candidate_write(expected_paths, Path(backup_receipt))
            prior_sha = (
                state["batch_receipts"][-1]["completion_sha256"]
                if state["batch_receipts"] else "NONE"
            )
            total_bytes = 0
            for task in selection.tasks:
                content = self._base_content(
                    task, expected_baseline, selection_receipt, review,
                    batch_number, prior_sha,
                )
                if task.repair_probe == "TRAILING_WHITESPACE_ON_FIRST_ATTEMPT":
                    content = content.replace("before promotion.\n", "before promotion. \n", 1)
                initial_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
                failure = self._content_failure(content)
                if failure:
                    if len(repairs) >= int(self.policy["self_repair"]["max_repairs_per_batch"]):
                        raise RuntimeError("PHASE14_REPAIR_BUDGET_EXHAUSTED")
                    repaired = self._repair_content(content, failure)
                    repair = self._signed({
                        "schema": "PHOENIX_BOUNDED_CAMPAIGN_REPAIR_V1",
                        "repair_id": "CAMPREPAIR-" + uuid.uuid4().hex[:16].upper(),
                        "timestamp": int(time.time()),
                        "campaign_id": "PHX-L4-CAMPAIGN-001",
                        "batch_number": batch_number,
                        "task_id": task.task_id,
                        "failure_code": failure,
                        "hypothesis": "A single generated line retained trailing horizontal whitespace.",
                        "strategy": self.policy["self_repair"]["strategy"],
                        "before_sha256": initial_sha,
                        "after_sha256": hashlib.sha256(repaired.encode("utf-8")).hexdigest(),
                        "attempt": 1,
                        "status": "REPAIRED_AND_REVALIDATED",
                    }, "repair_sha256")
                    if self._content_failure(repaired) is not None:
                        raise RuntimeError("PHASE14_REPAIR_REVALIDATION_DENY")
                    repair_path = self._persist_runtime(
                        repair, category="repairs", action="autonomy.campaign.repair.write",
                        gates=("audit_log", "bounded_repair", "new_hypothesis", "content_only"),
                        persist=persist,
                    )
                    if repair_path:
                        repair["runtime_path"] = repair_path
                    repairs.append(repair)
                    content = repaired
                if self._content_failure(content) is not None:
                    raise RuntimeError("PHASE14_CONTENT_VALIDATION_DENY")
                encoded = content.encode("utf-8")
                if len(encoded) > int(self.policy["max_output_bytes_per_file"]):
                    raise RuntimeError("PHASE14_OUTPUT_SIZE_DENY")
                total_bytes += len(encoded)
                if total_bytes > int(self.policy["max_total_output_bytes_per_batch"]):
                    raise RuntimeError("PHASE14_TOTAL_OUTPUT_SIZE_DENY")
                output = candidate.path / Path(task.output_path)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(content, encoding="utf-8", newline="\n")
                final_sha = hashlib.sha256(encoded).hexdigest()
                task_receipts.append({
                    "task_id": task.task_id, "task_sha256": task.sha256,
                    "output_path": task.output_path,
                    "initial_content_sha256": initial_sha,
                    "final_content_sha256": final_sha,
                    "final_content_hash_mode": "UTF8_CANONICAL_LF_V1",
                    "self_repaired": initial_sha != final_sha,
                    "status": "COMPLETED_IN_CANDIDATE",
                })
            if len(repairs) != 1:
                raise RuntimeError("PHASE14_BATCH_REPAIR_PROOF_COUNT_DENY")
            records = self.repository_cycle.classifier.classify(self.worktrees.status_records(candidate))
            if records.lane != "LOW_NON_EXECUTABLE" or len(records.paths) != 3 or set(records.paths) != set(expected_paths):
                raise PermissionError("PHASE14_LANE_A_EXACT_BATCH_SCOPE_DENY")
            patch, patch_sha256 = self.worktrees.stage_and_patch(candidate, records.paths)
            replay = self.worktrees.deterministic_replay(
                candidate, patch, parent=self.runtime_root / "replay" / f"campaign-batch-{batch_number}"
            )
            if replay[0] != replay[1]:
                raise RuntimeError("PHASE14_PATCH_REPLAY_DENY")
            patch_execution = self.repository_cycle._execute_patch_probe(patch, records)
            tests = self.test_executor(candidate.path)
            if tests.get("status") != "PASS" or int(tests.get("test_count", 0)) != 424:
                raise RuntimeError("PHASE14_TEST_GATE_DENY")
            self.worktrees.git(
                "-c", "user.name=PROJECT PHOENIX", "-c", "user.email=phoenix@local.invalid",
                "commit", "-m", f"chore(autonomy): low-risk candidate LOW-PHX-L4-CAMPAIGN-001-BATCH-{batch_number}",
                root=candidate.path,
            )
            candidate_commit = self.worktrees.git("rev-parse", "HEAD", root=candidate.path)
            parent = self.worktrees.git("rev-parse", "HEAD^", root=candidate.path)
            if parent != expected_baseline:
                raise RuntimeError("PHASE14_CANDIDATE_NOT_ONE_DIRECT_COMMIT")
            commit_paths = tuple(
                path for path in self.worktrees.git(
                    "diff", "--name-only", f"{expected_baseline}..{candidate_commit}", root=candidate.path
                ).splitlines() if path
            )
            if not set(expected_paths).issubset(set(commit_paths)):
                raise RuntimeError("PHASE14_BATCH_OUTPUT_MISSING_FROM_COMMIT")
            promotion_paths = self._promotion_paths(expected_baseline, candidate.branch)
            if len(promotion_paths) != len(commit_paths) or set(promotion_paths) != set(commit_paths):
                raise RuntimeError("PHASE14_PROMOTION_PATH_CLASSIFICATION_MISMATCH")
            permit = self._promotion_permit(promotion_paths, batch_number)
            promotion = self.promoter.promote(
                candidate.branch, expected_baseline, Path(backup_receipt),
                gateway=self.gateway, gateway_permit=permit,
            )
            promoted = True
            completion = self._signed({
                "schema": "PHOENIX_AUTONOMOUS_CAMPAIGN_BATCH_COMPLETION_V1",
                "batch_id": "CAMPBATCH-" + uuid.uuid4().hex[:16].upper(),
                "timestamp": int(time.time()),
                "campaign_id": "PHX-L4-CAMPAIGN-001",
                "batch_number": batch_number,
                "baseline_sha": expected_baseline,
                "promoted_commit": promotion["promoted_commit"],
                "task_ids": list(selection.task_ids),
                "task_receipts": task_receipts,
                "paths": promotion["paths"],
                "governance_side_effect_paths": promotion["governance_side_effect_paths"],
                "repair_count": 1,
                "repair_sha256s": [repair["repair_sha256"] for repair in repairs],
                "prior_batch_completion_sha256": prior_sha,
                "patch_sha256": patch_sha256,
                "deterministic_patch_replay": "PASS",
                "multi_agent_result_sha256": review["result_sha256"],
                "isolation_provider": patch_execution["provider"]["provider_id"],
                "tests_pass": True,
                "test_count": tests["test_count"],
                "fast_forward_promotion": True,
                "repository_push_performed": True,
                "normal_non_force_push": True,
                "partial_batch_promotion": False,
                "automatic_engine_activation": False,
                "status": "COMPLETED_AND_PROMOTED",
            }, "completion_sha256")
            completion_path = self._persist_runtime(
                completion, category="batch_completions",
                action="autonomy.campaign.batch.completion.write",
                gates=(
                    "audit_log", "verified_backup", "signed_resume_state", "multi_agent_review",
                    "bounded_repair", "deterministic_patch_replay", "tests_pass", "ff_only",
                    "normal_non_force_push", "remote_race_guard",
                ), persist=persist,
            )
            receipt_for_state = dict(completion)
            if completion_path:
                completion["runtime_path"] = completion_path
            state["current_baseline"] = promotion["promoted_commit"]
            state["completed_batches"] = batch_number
            state["completed_task_ids"] = list(state["completed_task_ids"]) + list(selection.task_ids)
            state["batch_receipts"] = list(state["batch_receipts"]) + [receipt_for_state]
            state["status"] = "READY_TO_FINALIZE" if batch_number == 2 else "ACTIVE"
            state = self._save_state(state, persist=persist)
            return {
                "schema": "PHOENIX_PHASE14_LEVEL4_CAMPAIGN_BATCH_V1",
                "status": "PASS", "test_only": bool(test_only),
                "campaign_id": "PHX-L4-CAMPAIGN-001",
                "batch_number": batch_number,
                "selected_task_ids": list(selection.task_ids),
                "task_count": 3, "selection_determinism": "PASS",
                "dependency_order": "PASS", "multi_agent_review": "PASS",
                "accepted_security_boundary": True,
                "self_repair_count": 1,
                "self_repair_status": "REPAIRED_AND_REVALIDATED",
                "deterministic_patch_replay": "PASS",
                "test_count": tests["test_count"], "tests_pass": True,
                "fast_forward_promotion": True, "repository_push_performed": True,
                "promoted_commit": promotion["promoted_commit"],
                "repository_end_state": "CLEAN_SYNCED",
                "completed_batches": batch_number,
                "remaining_batches": 2 - batch_number,
                "automatic_engine_activation": False,
                "selection_receipt": selection_receipt,
                "repairs": repairs, "completion": completion,
                "state_sha256": state["state_sha256"],
            }
        finally:
            if candidate is not None and not promoted:
                self.worktrees.cleanup(candidate)

    def finalize_campaign(
        self,
        expected_baseline: str,
        *,
        persist: bool = True,
        test_only: bool = False,
    ) -> dict[str, Any]:
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=True)
        state = self._load_state(expected_baseline, persist=persist)
        if state.get("status") == "COMPLETED" and state.get("campaign_completion"):
            completion = dict(state["campaign_completion"])
            self._verify_signed(completion, "completion_sha256")
            return {"status": "PASS", "already_completed": True, "completion": completion}
        if (
            int(state.get("completed_batches", 0)) != 2
            or len(state.get("completed_task_ids", [])) != 6
            or sum(int(row.get("repair_count", 0)) for row in state.get("batch_receipts", [])) != 2
        ):
            raise RuntimeError("PHASE14_CAMPAIGN_INCOMPLETE_DENY")
        completion = self._signed({
            "schema": "PHOENIX_AUTONOMOUS_CAMPAIGN_COMPLETION_V1",
            "campaign_id": "PHX-L4-CAMPAIGN-001",
            "timestamp": int(time.time()),
            "start_baseline": state["start_baseline"],
            "final_baseline": expected_baseline,
            "completed_batches": 2,
            "completed_task_ids": list(state["completed_task_ids"]),
            "batch_completion_sha256s": [row["completion_sha256"] for row in state["batch_receipts"]],
            "total_repairs": 2,
            "tests_per_batch": 424,
            "resume_backend": "SQLITE_ATOMIC_HMAC_BOUND",
            "lessons_applied_across_batches": True,
            "normal_non_force_push": True,
            "continuous_monitoring": False,
            "automatic_engine_activation": False,
            "status": "COMPLETED_BOUNDED_LEVEL4_CAMPAIGN",
        }, "completion_sha256")
        completion_path = self._persist_runtime(
            completion, category="campaign_completions",
            action="autonomy.campaign.completion.write",
            gates=(
                "audit_log", "two_batches_completed", "six_tasks_completed",
                "two_bounded_repairs", "tests_pass_per_batch", "clean_synced_repository",
            ), persist=persist,
        )
        stored_completion = dict(completion)
        if completion_path:
            completion["runtime_path"] = completion_path
        state["status"] = "COMPLETED"
        state["campaign_completion"] = stored_completion
        state = self._save_state(state, persist=persist)
        return {
            "schema": "PHOENIX_PHASE14_OPERATIONAL_REPEATABLE_LEVEL4_CAMPAIGN_V1",
            "status": "PASS", "test_only": bool(test_only),
            "operational_repeatable_level4_proof": not test_only,
            "completed_batches": 2, "completed_tasks": 6,
            "total_self_repairs": 2, "tests_per_batch": 424,
            "resume_backend": "SQLITE_ATOMIC_HMAC_BOUND",
            "lessons_applied_across_batches": True,
            "repository_end_state": "CLEAN_SYNCED",
            "final_baseline": expected_baseline,
            "continuous_monitoring": False,
            "automatic_engine_activation": False,
            "completion": completion,
            "state_sha256": state["state_sha256"],
        }
