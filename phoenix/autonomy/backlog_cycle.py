from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import uuid

from .approval_resume import LocalIntegrityKey
from .backlog_selector import (
    BacklogSelection,
    DeterministicBacklogSelector,
    canonical_bytes,
    object_sha256,
)
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .multi_agent_orchestrator import BoundedMultiAgentDagService
from .promoter import LowRiskMainlinePromoter, LowRiskMainlinePromotionPolicy
from .repository_cycle import BoundedRepositoryImprovementCycleService
from .specialized_agents import AgentTaskSpec
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway
from .worktree_guard import CandidateWorktree, GuardedWorktreeManager


class _TestOnlyGateway:
    def authorize(self, _intent: MutationIntent) -> object:
        return object()

    def consume(self, _permit: object, **_bindings: Any) -> None:
        return None


def phase12_review_tasks(selection: BacklogSelection) -> tuple[AgentTaskSpec, ...]:
    common = {
        "backlog_task_id": selection.task.task_id,
        "backlog_task_sha256": selection.task.sha256,
        "output_path": selection.task.output_path,
    }
    return (
        AgentTaskSpec("observe", "agent.context.observer", "research.inspect", payload={**common, "scope": "repository"}),
        AgentTaskSpec("plan", "agent.planning.specialist", "planning.analyze", ("observe",), payload={**common, "mode": "single-task"}),
        AgentTaskSpec("qa", "agent.qa.specialist", "qa.inspect", ("observe",), payload={**common, "gate": "lane-a"}),
        AgentTaskSpec("research", "agent.research.specialist", "research.inspect", ("observe",), payload={**common, "source": "committed-backlog"}),
        AgentTaskSpec("merge", "agent.evidence.merger", "evidence.merge", ("plan", "qa", "research"), payload={**common, "format": "canonical"}),
    )


class BacklogDrivenLevel3CycleService:
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
        self.policy = json.loads((cfg / "autonomous_backlog_policy_v1.json").read_text(encoding="utf-8-sig"))
        backlog = json.loads((cfg / "autonomous_backlog_v1.json").read_text(encoding="utf-8-sig"))
        runtime_policy = json.loads((cfg / "isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.selector = DeterministicBacklogSelector(self.policy, backlog)
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
                raise RuntimeError("PHASE12_TEST_GATEWAY_SCOPE_DENY")
            self.gateway = _TestOnlyGateway()
        self.test_executor = test_executor or self._run_full_regression
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "backlog_cycle_hmac_v1.key"
        ).load_or_create()
        self.worktrees = GuardedWorktreeManager(
            self.repo_root,
            candidate_branch_prefix=str(self.policy["candidate_branch_prefix"]),
            candidate_directory_prefix="PROJECT-PHOENIX-PHASE12-",
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
        regression = self.policy.get("regression", {})
        if regression.get("command_profile") != "PYTHON_UNITTEST_EXPLICIT_ALLOWLIST":
            raise RuntimeError("Phase-12 regression profile invalid")
        test_files = regression.get("test_files") or []
        if (
            len(test_files) != 14
            or len(test_files) != len(set(test_files))
            or any(Path(str(name)).name != name or not str(name).startswith("test_") or not str(name).endswith(".py") for name in test_files)
        ):
            raise RuntimeError("Phase-12 explicit regression allowlist invalid")
        if int(regression.get("expected_test_count", 0)) < 300:
            raise RuntimeError("Phase-12 regression test floor invalid")
        if regression.get("network") != "DENY" or regression.get("dependency_install") != "DENY":
            raise RuntimeError("Phase-12 regression boundary invalid")
        if self.policy.get("automatic_engine_activation") is not False:
            raise RuntimeError("automatic engine activation must remain disabled")

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def _sign(self, value: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, canonical_bytes(value), hashlib.sha256).hexdigest()

    def _signed(self, value: dict[str, Any], digest_field: str) -> dict[str, Any]:
        result = dict(value)
        result[digest_field] = object_sha256(result)
        result["hmac_sha256"] = self._sign(dict(result))
        return result

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
            raise RuntimeError("Phase-12 gateway unavailable for runtime receipt")
        identifier = str(value.get("selection_id") or value.get("completion_id"))
        relative = f"{category}/{identifier}.json"
        uri = "runtime://backlog_cycle/" + relative
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.backlog_cycle",
            action=action,
            risk="LOW",
            domain="orchestration",
            paths=(uri,),
            gates=gates,
            metadata={"receipt_sha256": value.get("selection_sha256") or value.get("completion_sha256")},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.backlog_cycle",
            action=action,
            paths=(uri,),
        )
        path = self.runtime_root / "backlog_cycle" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
        return str(path)

    def _verify_backup(self, path: Path, expected_baseline: str) -> dict[str, Any]:
        target = Path(path)
        if not target.is_file():
            raise RuntimeError("PHASE12_VERIFIED_BACKUP_RECEIPT_REQUIRED")
        value = json.loads(target.read_text(encoding="utf-8-sig"))
        if value.get("status") != "PASS" or value.get("baseline") != expected_baseline:
            raise RuntimeError("PHASE12_BACKUP_BASELINE_DENY")
        if value.get("bundle_verified") is not True or value.get("snapshot_verified") is not True:
            raise RuntimeError("PHASE12_BACKUP_VERIFICATION_DENY")
        if not Path(str(value.get("bundle_path", ""))).is_file():
            raise RuntimeError("PHASE12_BACKUP_BUNDLE_MISSING")
        if not Path(str(value.get("snapshot_path", ""))).is_dir():
            raise RuntimeError("PHASE12_BACKUP_SNAPSHOT_MISSING")
        return value

    def _selection_receipt(self, selection: BacklogSelection, baseline: str) -> dict[str, Any]:
        return self._signed({
            "schema": "PHOENIX_BACKLOG_TASK_SELECTION_V1",
            "selection_id": "BSEL-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "baseline_sha": baseline,
            "task_id": selection.task.task_id,
            "task_sha256": selection.task.sha256,
            "eligible_task_count": selection.eligible_task_count,
            "eligible_task_ids": list(selection.eligible_task_ids),
            "selection_key": list(selection.selection_key),
            "backlog_sha256": selection.backlog_sha256,
            "deterministic_repetitions": 2,
            "automatic_engine_activation": False,
            "status": "SELECTED",
        }, "selection_sha256")

    def _report_content(
        self,
        selection: BacklogSelection,
        baseline: str,
        selection_receipt: dict[str, Any],
        review: dict[str, Any],
    ) -> str:
        return (
            "# PROJECT PHOENIX — Operational Level-3 Capability Evidence\n\n"
            f"- Backlog task: `{selection.task.task_id}`\n"
            f"- Source baseline: `{baseline}`\n"
            f"- Task SHA-256: `{selection.task.sha256}`\n"
            f"- Selection SHA-256: `{selection_receipt['selection_sha256']}`\n"
            f"- Multi-agent DAG SHA-256: `{review['dag_sha256']}`\n"
            f"- Multi-agent result SHA-256: `{review['result_sha256']}`\n"
            "- Risk: `LOW`\n"
            "- Mutation lane: `LOW_NON_EXECUTABLE`\n"
            "- Candidate worktree: isolated outside the main repository\n"
            "- Deterministic patch replay: `PASS`\n"
            "- Promotion: backup-gated fast-forward only\n"
            "- Push: normal non-force only\n"
            "- Automatic engine activation: `FORBIDDEN`\n\n"
            "This file was selected from the committed Phase-12 backlog and generated by the governed single-task autonomous cycle.\n"
        )

    def _authorize_candidate_write(self, output_path: str, backup_receipt: Path) -> None:
        if self.gateway is None:
            raise RuntimeError("Phase-12 gateway unavailable for candidate write")
        uri = "worktree://phase12/" + output_path
        gates = (
            "audit_log", "deterministic_selection", "selection_integrity",
            "multi_agent_review", "protected_path_gate", "verified_backup",
        )
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.backlog_cycle",
            action="autonomy.backlog.task.candidate.write",
            risk="LOW",
            domain="software",
            paths=(uri,),
            gates=gates,
            metadata={"backup_receipt": str(backup_receipt)},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.backlog_cycle",
            action="autonomy.backlog.task.candidate.write",
            paths=(uri,),
        )

    def _run_full_regression(self, candidate_root: Path) -> dict[str, Any]:
        tests = Path(candidate_root) / "tests" / "automation"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(candidate_root)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        timeout = float(self.policy["regression"]["timeout_seconds"])
        deadline = time.monotonic() + timeout
        outputs: list[str] = []
        count = 0
        for name in self.policy["regression"]["test_files"]:
            path = tests / str(name)
            if not path.is_file():
                raise RuntimeError(f"PHASE12_REGRESSION_ALLOWLIST_FILE_MISSING:{name}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("PHASE12_FULL_REGRESSION_TIMEOUT")
            completed = subprocess.run(
                [sys.executable, "-B", str(path)],
                cwd=str(candidate_root),
                env=environment,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=remaining,
            )
            output = completed.stdout
            outputs.append(f"[{name}]\n{output}")
            match = re.search(r"Ran\s+(\d+)\s+tests?", output)
            file_count = int(match.group(1)) if match else 0
            if completed.returncode != 0 or file_count <= 0 or not re.search(r"\nOK\s*$", output):
                raise RuntimeError(
                    f"PHASE12_ALLOWLIST_TEST_DENY:file={name};exit={completed.returncode};tests={file_count};tail={output[-1200:]}"
                )
            count += file_count
        expected = int(self.policy["regression"]["expected_test_count"])
        combined = "\n".join(outputs)
        if count != expected:
            raise RuntimeError(
                f"PHASE12_FULL_REGRESSION_COUNT_DENY:tests={count};expected={expected}"
            )
        return {
            "status": "PASS",
            "test_count": count,
            "test_file_count": len(self.policy["regression"]["test_files"]),
            "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        }

    def _promotion_permit(self, commit_paths: tuple[str, ...]) -> object:
        if self.gateway is None:
            raise RuntimeError("Phase-12 gateway unavailable for promotion")
        gates = (
            "verified_backup", "candidate_validated", "tests_pass", "evidence_pass",
            "ff_only", "normal_non_force_push", "remote_race_guard", "audit_log",
        )
        return self.gateway.authorize(MutationIntent(
            engine_id="autonomy.mainline_promoter",
            action="git.fast_forward_promotion",
            risk="LOW",
            domain="git",
            paths=commit_paths,
            gates=gates,
            metadata={"phase": "PHASE12_REAL_BACKLOG_LEVEL3"},
        ))

    def run_cycle(
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
        selection = self.selector.select(self.repo_root)
        selection_receipt = self._selection_receipt(selection, expected_baseline)
        selection_path = self._persist_runtime(
            selection_receipt,
            category="selections",
            action="autonomy.backlog.selection.write",
            gates=("audit_log", "exact_baseline", "backlog_integrity", "deterministic_selection"),
            persist=persist,
        )
        if selection_path:
            selection_receipt["runtime_path"] = selection_path

        review = self.multi_agent.review_tasks(phase12_review_tasks(selection))
        if review.get("status") != "PASS" or review.get("parallel_overlap_proven") is not True:
            raise RuntimeError("PHASE12_MULTI_AGENT_REVIEW_DENY")
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=False)

        cycle_id = selection.task.task_id.lower()
        candidate: CandidateWorktree | None = None
        promoted = False
        try:
            candidate = self.worktrees.create_candidate(
                cycle_id,
                expected_baseline,
                parent=self.runtime_root / "candidates",
            )
            self._authorize_candidate_write(selection.task.output_path, Path(backup_receipt))
            output = candidate.path / Path(selection.task.output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            content = self._report_content(selection, expected_baseline, selection_receipt, review)
            encoded = content.encode("utf-8")
            if len(encoded) > int(self.policy["max_output_bytes"]):
                raise RuntimeError("PHASE12_OUTPUT_SIZE_DENY")
            output.write_text(content, encoding="utf-8", newline="\n")

            records = self.repository_cycle.classifier.classify(
                self.worktrees.status_records(candidate)
            )
            if records.lane != "LOW_NON_EXECUTABLE" or records.paths != (selection.task.output_path,):
                raise PermissionError("PHASE12_LANE_A_EXACT_SCOPE_DENY")
            patch, patch_sha256 = self.worktrees.stage_and_patch(candidate, records.paths)
            replay = self.worktrees.deterministic_replay(
                candidate, patch, parent=self.runtime_root / "replay" / selection.task.task_id
            )
            if replay[0] != replay[1]:
                raise RuntimeError("PHASE12_PATCH_REPLAY_DENY")
            patch_execution = self.repository_cycle._execute_patch_probe(patch, records)
            tests = self.test_executor(candidate.path)
            expected_tests = int(self.policy["regression"]["expected_test_count"])
            if tests.get("status") != "PASS" or int(tests.get("test_count", 0)) != expected_tests:
                raise RuntimeError("PHASE12_TEST_GATE_DENY")

            self.worktrees.git(
                "-c", "user.name=PROJECT PHOENIX",
                "-c", "user.email=phoenix@local.invalid",
                "commit", "-m",
                f"chore(autonomy): low-risk candidate LOW-{selection.task.task_id}",
                root=candidate.path,
            )
            candidate_commit = self.worktrees.git("rev-parse", "HEAD", root=candidate.path)
            parent = self.worktrees.git("rev-parse", "HEAD^", root=candidate.path)
            if parent != expected_baseline:
                raise RuntimeError("PHASE12_CANDIDATE_NOT_ONE_DIRECT_COMMIT")
            commit_paths = tuple(
                x for x in self.worktrees.git(
                    "diff", "--name-only", f"{expected_baseline}..{candidate_commit}", root=candidate.path
                ).splitlines() if x
            )
            if selection.task.output_path not in commit_paths:
                raise RuntimeError("PHASE12_PRIMARY_OUTPUT_MISSING_FROM_COMMIT")
            permit = self._promotion_permit(commit_paths)
            promotion = self.promoter.promote(
                candidate.branch,
                expected_baseline,
                Path(backup_receipt),
                gateway=self.gateway,
                gateway_permit=permit,
            )
            promoted = True

            completion = self._signed({
                "schema": "PHOENIX_LEVEL3_TASK_COMPLETION_V1",
                "completion_id": "L3DONE-" + uuid.uuid4().hex[:16].upper(),
                "timestamp": int(time.time()),
                "task_id": selection.task.task_id,
                "task_sha256": selection.task.sha256,
                "baseline_sha": expected_baseline,
                "promoted_commit": promotion["promoted_commit"],
                "paths": promotion["paths"],
                "governance_side_effect_paths": promotion["governance_side_effect_paths"],
                "patch_sha256": patch_sha256,
                "deterministic_patch_replay": "PASS",
                "multi_agent_result_sha256": review["result_sha256"],
                "isolation_provider": patch_execution["provider"]["provider_id"],
                "tests_pass": True,
                "test_count": tests["test_count"],
                "fast_forward_promotion": True,
                "repository_push_performed": True,
                "normal_non_force_push": True,
                "automatic_source_change": False,
                "automatic_dependency_change": False,
                "automatic_policy_change": False,
                "automatic_registry_change": False,
                "automatic_engine_activation": False,
                "status": "COMPLETED_AND_PROMOTED",
            }, "completion_sha256")
            completion_path = self._persist_runtime(
                completion,
                category="completions",
                action="autonomy.backlog.completion.write",
                gates=(
                    "audit_log", "verified_backup", "multi_agent_review",
                    "deterministic_patch_replay", "tests_pass", "ff_only",
                    "normal_non_force_push", "remote_race_guard",
                ),
                persist=persist,
            )
            if completion_path:
                completion["runtime_path"] = completion_path
            return {
                "schema": "PHOENIX_PHASE12_OPERATIONAL_LEVEL3_CYCLE_V1",
                "status": "PASS",
                "test_only": bool(test_only),
                "operational_level3_proof": not test_only,
                "selected_task_id": selection.task.task_id,
                "eligible_task_count": selection.eligible_task_count,
                "selection_determinism": "PASS",
                "multi_agent_review": "PASS",
                "accepted_security_boundary": True,
                "candidate_worktree_outside_main": True,
                "protected_path_gate": "PASS",
                "deterministic_patch_replay": "PASS",
                "test_count": tests["test_count"],
                "tests_pass": True,
                "fast_forward_promotion": True,
                "repository_push_performed": True,
                "promoted_commit": promotion["promoted_commit"],
                "repository_end_state": "CLEAN_SYNCED",
                "automatic_engine_activation": False,
                "selection_receipt": selection_receipt,
                "completion": completion,
            }
        finally:
            if candidate is not None and not promoted:
                self.worktrees.cleanup(candidate)
