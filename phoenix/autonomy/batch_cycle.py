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
from .batch_selector import (
    BatchSelection,
    BatchTask,
    DeterministicBatchSelector,
    batch_object_sha256,
    canonical_batch_bytes,
)
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .multi_agent_orchestrator import BoundedMultiAgentDagService
from .promoter import LowRiskMainlinePromoter, LowRiskMainlinePromotionPolicy
from .repository_cycle import BoundedRepositoryImprovementCycleService
from .specialized_agents import AgentTaskSpec
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway
from .worktree_guard import CandidateWorktree, GuardedWorktreeManager


class _BatchTestOnlyGateway:
    def authorize(self, intent: MutationIntent) -> MutationIntent:
        return intent

    def consume(self, permit: MutationIntent, **bindings: Any) -> None:
        paths = tuple(str(path).replace("\\", "/").lstrip("./") for path in bindings.get("paths", ()))
        if (
            permit.engine_id != bindings.get("engine_id")
            or permit.action != bindings.get("action")
            or permit.paths != paths
        ):
            raise PermissionError("PHASE13_TEST_GATEWAY_EXACT_BINDING_DENY")


def phase13_review_tasks(selection: BatchSelection) -> tuple[AgentTaskSpec, ...]:
    common = {
        "batch_task_ids": list(selection.task_ids),
        "backlog_sha256": selection.backlog_sha256,
        "output_paths": [task.output_path for task in selection.tasks],
    }
    return (
        AgentTaskSpec("observe", "agent.context.observer", "research.inspect", payload={**common, "scope": "batch"}),
        AgentTaskSpec("plan", "agent.planning.specialist", "planning.analyze", ("observe",), payload={**common, "mode": "bounded-level4"}),
        AgentTaskSpec("qa", "agent.qa.specialist", "qa.inspect", ("observe",), payload={**common, "gate": "transactional-lane-a"}),
        AgentTaskSpec("research", "agent.research.specialist", "research.inspect", ("observe",), payload={**common, "source": "committed-batch"}),
        AgentTaskSpec("merge", "agent.evidence.merger", "evidence.merge", ("plan", "qa", "research"), payload={**common, "format": "canonical"}),
    )


class BoundedLevel4BatchService:
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
        self.policy = json.loads((cfg / "autonomous_batch_policy_v1.json").read_text(encoding="utf-8-sig"))
        backlog = json.loads((cfg / "autonomous_batch_v1.json").read_text(encoding="utf-8-sig"))
        runtime_policy = json.loads((cfg / "isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.selector = DeterministicBatchSelector(self.policy, backlog)
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
                raise RuntimeError("PHASE13_TEST_GATEWAY_SCOPE_DENY")
            self.gateway = _BatchTestOnlyGateway()
        self.test_executor = test_executor or self._run_full_regression
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "batch_cycle_hmac_v1.key"
        ).load_or_create()
        self.worktrees = GuardedWorktreeManager(
            self.repo_root,
            candidate_branch_prefix=str(self.policy["candidate_branch_prefix"]),
            candidate_directory_prefix="PROJECT-PHOENIX-PHASE13-",
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
            or repair.get("allowed_failure_codes") != ["TRAILING_WHITESPACE"]
            or repair.get("strategy") != "DETERMINISTIC_RSTRIP_LINES"
            or repair.get("new_hypothesis_required") is not True
        ):
            raise RuntimeError("Phase-13 bounded self-repair policy invalid")
        regression = self.policy.get("regression", {})
        files = regression.get("test_files") or []
        if (
            regression.get("command_profile") != "PYTHON_UNITTEST_EXPLICIT_ALLOWLIST"
            or len(files) != 15
            or len(files) != len(set(files))
            or any(Path(str(name)).name != name or not str(name).startswith("test_") or not str(name).endswith(".py") for name in files)
            or int(regression.get("expected_test_count", 0)) != 380
        ):
            raise RuntimeError("Phase-13 explicit regression allowlist invalid")
        if regression.get("network") != "DENY" or regression.get("dependency_install") != "DENY":
            raise RuntimeError("Phase-13 regression boundary invalid")
        if self.policy.get("partial_batch_promotion") != "DENY":
            raise RuntimeError("Phase-13 partial promotion must remain denied")

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def _sign(self, value: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, canonical_batch_bytes(value), hashlib.sha256).hexdigest()

    def _signed(self, value: dict[str, Any], digest_field: str) -> dict[str, Any]:
        result = dict(value)
        result[digest_field] = batch_object_sha256(result)
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
            raise RuntimeError("Phase-13 gateway unavailable for runtime receipt")
        identifier = str(value.get("selection_id") or value.get("repair_id") or value.get("batch_id"))
        relative = f"{category}/{identifier}.json"
        uri = "runtime://batch_cycle/" + relative
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.batch_cycle",
            action=action,
            risk="LOW",
            domain="orchestration",
            paths=(uri,),
            gates=gates,
            metadata={"receipt_sha256": value.get("selection_sha256") or value.get("repair_sha256") or value.get("completion_sha256")},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.batch_cycle",
            action=action,
            paths=(uri,),
        )
        path = self.runtime_root / "batch_cycle" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
        return str(path)

    def _verify_backup(self, path: Path, expected_baseline: str) -> dict[str, Any]:
        target = Path(path)
        if not target.is_file():
            raise RuntimeError("PHASE13_VERIFIED_BACKUP_RECEIPT_REQUIRED")
        value = json.loads(target.read_text(encoding="utf-8-sig"))
        if value.get("status") != "PASS" or value.get("baseline") != expected_baseline:
            raise RuntimeError("PHASE13_BACKUP_BASELINE_DENY")
        if value.get("bundle_verified") is not True or value.get("snapshot_verified") is not True:
            raise RuntimeError("PHASE13_BACKUP_VERIFICATION_DENY")
        if not Path(str(value.get("bundle_path", ""))).is_file():
            raise RuntimeError("PHASE13_BACKUP_BUNDLE_MISSING")
        if not Path(str(value.get("snapshot_path", ""))).is_dir():
            raise RuntimeError("PHASE13_BACKUP_SNAPSHOT_MISSING")
        return value

    def _selection_receipt(self, selection: BatchSelection, baseline: str) -> dict[str, Any]:
        return self._signed({
            "schema": "PHOENIX_AUTONOMOUS_BATCH_SELECTION_V1",
            "selection_id": "BATCHSEL-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "baseline_sha": baseline,
            "task_ids": list(selection.task_ids),
            "task_sha256s": {task.task_id: task.sha256 for task in selection.tasks},
            "selection_keys": [[key[0], key[1]] for key in selection.selection_keys],
            "backlog_sha256": selection.backlog_sha256,
            "deterministic_repetitions": 2,
            "max_tasks_per_batch": 3,
            "automatic_engine_activation": False,
            "status": "SELECTED",
        }, "selection_sha256")

    def _base_content(
        self,
        task: BatchTask,
        baseline: str,
        selection_receipt: dict[str, Any],
        review: dict[str, Any],
        repair_count: int,
    ) -> str:
        headings = {
            "PHX-L4-GOVERNANCE-SUMMARY-001": "Bounded Level-4 Governance Summary",
            "PHX-L4-REGRESSION-EVIDENCE-002": "Level-4 Batch Regression Evidence",
            "PHX-L4-LESSONS-LEARNED-003": "Level-4 Batch Lessons Learned",
        }
        title = headings[task.task_id]
        lines = [
            f"# PROJECT PHOENIX — {title}",
            "",
            f"- Batch task: `{task.task_id}`",
            f"- Source baseline: `{baseline}`",
            f"- Selection SHA-256: `{selection_receipt['selection_sha256']}`",
            f"- Multi-agent result SHA-256: `{review['result_sha256']}`",
            "- Risk: `LOW`",
            "- Transaction: `ALL_TASKS_OR_NO_BATCH_PROMOTION`",
            "- Candidate worktree: `ISOLATED_OUTSIDE_MAIN`",
            "- Regression profile: `EXPLICIT_380_TEST_ALLOWLIST`",
            "- Promotion: `FAST_FORWARD_ONLY_NORMAL_NON_FORCE_PUSH`",
            "- Automatic engine activation: `FORBIDDEN`",
            "",
        ]
        if task.task_id == "PHX-L4-GOVERNANCE-SUMMARY-001":
            lines.extend([
                "The batch is capped at three committed LOW-risk non-executable tasks and one bounded deterministic repair.",
                "Security, policy, isolation, test and remote-race failures are never auto-repaired.",
            ])
        elif task.task_id == "PHX-L4-REGRESSION-EVIDENCE-002":
            lines.extend([
                "The governed candidate must pass all 380 explicitly bound Phase-1-through-13 tests before promotion.",
                "An unrelated historical test cannot enter the gate through test discovery.",
            ])
        else:
            lines.extend([
                f"The batch recorded `{repair_count}` bounded repair before final verification.",
                "Lesson: authorize promotion paths in the exact classifier order consumed by the mainline promoter.",
                "Lesson: transient infrastructure failures stop safely and are not treated as repairable content defects.",
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
        repair = self.policy["self_repair"]
        if failure_code not in repair["allowed_failure_codes"]:
            raise RuntimeError(f"PHASE13_UNREPAIRABLE_CONTENT_DENY:{failure_code}")
        if repair["strategy"] != "DETERMINISTIC_RSTRIP_LINES":
            raise RuntimeError("PHASE13_REPAIR_STRATEGY_DENY")
        return "\n".join(line.rstrip(" \t") for line in content.splitlines()) + "\n"

    def _authorize_candidate_write(self, paths: tuple[str, ...], backup_receipt: Path) -> None:
        if self.gateway is None:
            raise RuntimeError("Phase-13 gateway unavailable for candidate write")
        uris = tuple("worktree://phase13/" + path for path in paths)
        gates = (
            "audit_log", "deterministic_batch_selection", "selection_integrity",
            "dependency_order_validation", "multi_agent_review", "protected_path_gate", "verified_backup",
        )
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.batch_cycle",
            action="autonomy.batch.candidate.write",
            risk="LOW",
            domain="software",
            paths=uris,
            gates=gates,
            metadata={"backup_receipt": str(backup_receipt), "task_count": len(paths)},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.batch_cycle",
            action="autonomy.batch.candidate.write",
            paths=uris,
        )

    def _run_full_regression(self, candidate_root: Path) -> dict[str, Any]:
        tests = Path(candidate_root) / "tests" / "automation"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(candidate_root)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        deadline = time.monotonic() + float(self.policy["regression"]["timeout_seconds"])
        outputs: list[str] = []
        count = 0
        for name in self.policy["regression"]["test_files"]:
            path = tests / str(name)
            if not path.is_file():
                raise RuntimeError(f"PHASE13_REGRESSION_ALLOWLIST_FILE_MISSING:{name}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("PHASE13_FULL_REGRESSION_TIMEOUT")
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
                    f"PHASE13_ALLOWLIST_TEST_DENY:file={name};exit={completed.returncode};tests={file_count};tail={output[-1200:]}"
                )
            count += file_count
        expected = int(self.policy["regression"]["expected_test_count"])
        if count != expected:
            raise RuntimeError(f"PHASE13_FULL_REGRESSION_COUNT_DENY:tests={count};expected={expected}")
        combined = "\n".join(outputs)
        return {
            "status": "PASS",
            "test_count": count,
            "test_file_count": len(self.policy["regression"]["test_files"]),
            "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        }

    def _promotion_paths(self, expected_baseline: str, candidate_branch: str) -> tuple[str, ...]:
        primary_paths, governance_paths = self.promoter._paths(expected_baseline, candidate_branch)
        return tuple(primary_paths) + tuple(governance_paths)

    def _promotion_permit(self, paths: tuple[str, ...]) -> object:
        if self.gateway is None:
            raise RuntimeError("Phase-13 gateway unavailable for promotion")
        return self.gateway.authorize(MutationIntent(
            engine_id="autonomy.mainline_promoter",
            action="git.fast_forward_promotion",
            risk="LOW",
            domain="git",
            paths=paths,
            gates=(
                "verified_backup", "candidate_validated", "tests_pass", "evidence_pass",
                "ff_only", "normal_non_force_push", "remote_race_guard", "audit_log",
            ),
            metadata={"phase": "PHASE13_BOUNDED_LEVEL4_BATCH"},
        ))

    def run_batch(
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
            action="autonomy.batch.selection.write",
            gates=("audit_log", "exact_baseline", "backlog_integrity", "deterministic_batch_selection"),
            persist=persist,
        )
        if selection_path:
            selection_receipt["runtime_path"] = selection_path

        review = self.multi_agent.review_tasks(phase13_review_tasks(selection))
        if review.get("status") != "PASS" or review.get("parallel_overlap_proven") is not True:
            raise RuntimeError("PHASE13_MULTI_AGENT_REVIEW_DENY")
        self.worktrees.assert_exact_baseline(expected_baseline, require_remote=True, fetch=False)

        candidate: CandidateWorktree | None = None
        promoted = False
        repairs: list[dict[str, Any]] = []
        task_receipts: list[dict[str, Any]] = []
        try:
            candidate = self.worktrees.create_candidate(
                "level4-batch-001", expected_baseline, parent=self.runtime_root / "candidates"
            )
            expected_paths = tuple(task.output_path for task in selection.tasks)
            self._authorize_candidate_write(expected_paths, Path(backup_receipt))
            total_bytes = 0
            for task in selection.tasks:
                content = self._base_content(
                    task, expected_baseline, selection_receipt, review, len(repairs)
                )
                if task.repair_probe == "TRAILING_WHITESPACE_ON_FIRST_ATTEMPT":
                    content = content.replace("before promotion.\n", "before promotion. \n", 1)
                initial_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
                failure = self._content_failure(content)
                if failure:
                    if len(repairs) >= int(self.policy["self_repair"]["max_repairs_per_batch"]):
                        raise RuntimeError("PHASE13_REPAIR_BUDGET_EXHAUSTED")
                    repaired = self._repair_content(content, failure)
                    repair = self._signed({
                        "schema": "PHOENIX_BOUNDED_BATCH_REPAIR_V1",
                        "repair_id": "L4REPAIR-" + uuid.uuid4().hex[:16].upper(),
                        "timestamp": int(time.time()),
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
                        raise RuntimeError("PHASE13_REPAIR_REVALIDATION_DENY")
                    repair_path = self._persist_runtime(
                        repair,
                        category="repairs",
                        action="autonomy.batch.repair.write",
                        gates=("audit_log", "bounded_repair", "new_hypothesis", "content_only"),
                        persist=persist,
                    )
                    if repair_path:
                        repair["runtime_path"] = repair_path
                    repairs.append(repair)
                    content = repaired
                final_failure = self._content_failure(content)
                if final_failure is not None:
                    raise RuntimeError(f"PHASE13_CONTENT_VALIDATION_DENY:{final_failure}")
                encoded = content.encode("utf-8")
                if len(encoded) > int(self.policy["max_output_bytes_per_file"]):
                    raise RuntimeError("PHASE13_OUTPUT_SIZE_DENY")
                total_bytes += len(encoded)
                if total_bytes > int(self.policy["max_total_output_bytes"]):
                    raise RuntimeError("PHASE13_TOTAL_OUTPUT_SIZE_DENY")
                output = candidate.path / Path(task.output_path)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(content, encoding="utf-8", newline="\n")
                task_receipts.append({
                    "task_id": task.task_id,
                    "task_sha256": task.sha256,
                    "output_path": task.output_path,
                    "initial_content_sha256": initial_sha,
                    "final_content_sha256": hashlib.sha256(encoded).hexdigest(),
                    "self_repaired": initial_sha != hashlib.sha256(encoded).hexdigest(),
                    "status": "COMPLETED_IN_CANDIDATE",
                })

            if len(repairs) != 1:
                raise RuntimeError("PHASE13_LIVE_REPAIR_PROOF_COUNT_DENY")
            records = self.repository_cycle.classifier.classify(self.worktrees.status_records(candidate))
            if (
                records.lane != "LOW_NON_EXECUTABLE"
                or len(records.paths) != len(expected_paths)
                or set(records.paths) != set(expected_paths)
            ):
                raise PermissionError("PHASE13_LANE_A_EXACT_BATCH_SCOPE_DENY")
            patch, patch_sha256 = self.worktrees.stage_and_patch(candidate, records.paths)
            replay = self.worktrees.deterministic_replay(
                candidate, patch, parent=self.runtime_root / "replay" / "level4-batch-001"
            )
            if replay[0] != replay[1]:
                raise RuntimeError("PHASE13_PATCH_REPLAY_DENY")
            patch_execution = self.repository_cycle._execute_patch_probe(patch, records)
            tests = self.test_executor(candidate.path)
            if tests.get("status") != "PASS" or int(tests.get("test_count", 0)) != 380:
                raise RuntimeError("PHASE13_TEST_GATE_DENY")

            self.worktrees.git(
                "-c", "user.name=PROJECT PHOENIX",
                "-c", "user.email=phoenix@local.invalid",
                "commit", "-m", "chore(autonomy): low-risk candidate LOW-PHX-L4-BATCH-001",
                root=candidate.path,
            )
            candidate_commit = self.worktrees.git("rev-parse", "HEAD", root=candidate.path)
            parent = self.worktrees.git("rev-parse", "HEAD^", root=candidate.path)
            if parent != expected_baseline:
                raise RuntimeError("PHASE13_CANDIDATE_NOT_ONE_DIRECT_COMMIT")
            commit_paths = tuple(
                path for path in self.worktrees.git(
                    "diff", "--name-only", f"{expected_baseline}..{candidate_commit}", root=candidate.path
                ).splitlines() if path
            )
            if not set(expected_paths).issubset(set(commit_paths)):
                raise RuntimeError("PHASE13_BATCH_OUTPUT_MISSING_FROM_COMMIT")
            promotion_paths = self._promotion_paths(expected_baseline, candidate.branch)
            if len(promotion_paths) != len(commit_paths) or set(promotion_paths) != set(commit_paths):
                raise RuntimeError("PHASE13_PROMOTION_PATH_CLASSIFICATION_MISMATCH")
            permit = self._promotion_permit(promotion_paths)
            promotion = self.promoter.promote(
                candidate.branch,
                expected_baseline,
                Path(backup_receipt),
                gateway=self.gateway,
                gateway_permit=permit,
            )
            promoted = True

            completion = self._signed({
                "schema": "PHOENIX_AUTONOMOUS_BATCH_COMPLETION_V1",
                "batch_id": "L4BATCH-" + uuid.uuid4().hex[:16].upper(),
                "timestamp": int(time.time()),
                "baseline_sha": expected_baseline,
                "promoted_commit": promotion["promoted_commit"],
                "task_ids": list(selection.task_ids),
                "task_receipts": task_receipts,
                "paths": promotion["paths"],
                "governance_side_effect_paths": promotion["governance_side_effect_paths"],
                "repair_count": len(repairs),
                "repair_sha256s": [repair["repair_sha256"] for repair in repairs],
                "lessons_learned": [
                    "Bind authorization and consumption to identical classified path order.",
                    "Repair only explicit content defects within a one-attempt budget.",
                    "Never repair security, policy, isolation, regression or remote-race failures.",
                ],
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
                action="autonomy.batch.completion.write",
                gates=(
                    "audit_log", "verified_backup", "multi_agent_review", "bounded_repair",
                    "deterministic_patch_replay", "tests_pass", "ff_only",
                    "normal_non_force_push", "remote_race_guard",
                ),
                persist=persist,
            )
            if completion_path:
                completion["runtime_path"] = completion_path
            return {
                "schema": "PHOENIX_PHASE13_OPERATIONAL_LEVEL4_BATCH_V1",
                "status": "PASS",
                "test_only": bool(test_only),
                "operational_level4_proof": not test_only,
                "selected_task_ids": list(selection.task_ids),
                "task_count": len(selection.tasks),
                "selection_determinism": "PASS",
                "dependency_order": "PASS",
                "multi_agent_review": "PASS",
                "accepted_security_boundary": True,
                "candidate_worktree_outside_main": True,
                "protected_path_gate": "PASS",
                "self_repair_count": len(repairs),
                "self_repair_status": "REPAIRED_AND_REVALIDATED",
                "deterministic_patch_replay": "PASS",
                "test_count": tests["test_count"],
                "tests_pass": True,
                "fast_forward_promotion": True,
                "repository_push_performed": True,
                "promoted_commit": promotion["promoted_commit"],
                "repository_end_state": "CLEAN_SYNCED",
                "automatic_engine_activation": False,
                "selection_receipt": selection_receipt,
                "repairs": repairs,
                "completion": completion,
            }
        finally:
            if candidate is not None and not promoted:
                self.worktrees.cleanup(candidate)
