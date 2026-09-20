from __future__ import annotations

from pathlib import Path
from typing import Any
import base64
import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid

from .approval_resume import LocalIntegrityKey
from .change_classifier import ChangeClassification, RepositoryChangeClassifier
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway
from .worktree_guard import GuardedWorktreeManager, initialize_fixture_repository


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def build_patch_probe_source(patch: bytes, lane: str) -> str:
    encoded = base64.b64encode(patch).decode("ascii")
    expected = hashlib.sha256(patch).hexdigest()
    return f'''from __future__ import annotations
import base64
import hashlib
from phoenix.autonomy.executor_adapters import AdapterExecutionResult

PATCH = base64.b64decode({encoded!r})
EXPECTED = {expected!r}
LANE = {lane!r}

class Phase10RepositoryPatchProbe:
    def __init__(self, _policy):
        pass

    def execute(self, context):
        actual = hashlib.sha256(PATCH).hexdigest()
        if actual != EXPECTED:
            return AdapterExecutionResult(status="FAILED", reason="PATCH_SHA256_MISMATCH")
        return AdapterExecutionResult(
            status="COMPLETE",
            result={{
                "patch_sha256": actual,
                "patch_bytes": len(PATCH),
                "lane": LANE,
                "mode": "PHASE10_READ_ONLY_PATCH_PROBE_V1",
            }},
        )
'''


class BoundedRepositoryImprovementCycleService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        policy_root: Path | None = None,
        provider: IsolatedRuntimeProvider | None = None,
        gateway: UniversalAutonomyGateway | None = None,
        enable_gateway: bool = True,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.policy_root = Path(policy_root or repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        cfg = self.policy_root / "configs" / "phoenix"
        self.policy = json.loads(
            (cfg / "repository_improvement_cycle_policy_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        protected = json.loads(
            (cfg / "protected_repository_paths_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        runtime_policy = json.loads(
            (cfg / "isolated_runtime_policy_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.classifier = RepositoryChangeClassifier(self.policy, protected)
        self.provider = provider or select_runtime_provider(runtime_policy, self.runtime_root)
        self.gateway = gateway
        if enable_gateway and self.gateway is None and self.policy_root == self.repo_root:
            self.gateway = UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(
                    self.runtime_root / "policy_decisions" / "decisions_v1.jsonl"
                ),
                audit_log=GatewayAuditLog(
                    self.runtime_root / "gateway" / "audit_v1.jsonl"
                ),
            )
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "repository_cycle_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != "PHOENIX_REPOSITORY_IMPROVEMENT_CYCLE_POLICY_V1":
            raise RuntimeError("Phase-10 policy schema invalid")
        if self.policy.get("fail_closed") is not True:
            raise RuntimeError("Phase-10 policy must fail closed")
        if self.policy.get("allowed_risk") != ["LOW"]:
            raise RuntimeError("Phase-10 permits LOW risk only")
        if int(self.policy.get("max_cycles_per_invocation", 0)) != 1:
            raise RuntimeError("Phase-10 permits one cycle per invocation")
        if int(self.policy.get("max_repair_attempts", 0)) != 3:
            raise RuntimeError("Phase-10 requires exactly three repair attempts")
        if self.policy.get("automatic_engine_activation") is not False:
            raise RuntimeError("automatic engine activation must remain disabled")
        promotion = self.policy.get("promotion", {})
        if promotion.get("fast_forward_only") is not True:
            raise RuntimeError("Phase-10 requires fast-forward-only promotion")
        if promotion.get("normal_non_force_push_only") is not True:
            raise RuntimeError("Phase-10 requires normal non-force push")

    def _sign(self, obj: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, _canonical(obj), hashlib.sha256).hexdigest()

    def _verify_signed(self, obj: dict[str, Any]) -> bool:
        supplied = str(obj.get("hmac_sha256", ""))
        unsigned = dict(obj)
        unsigned.pop("hmac_sha256", None)
        return bool(supplied) and hmac.compare_digest(supplied, self._sign(unsigned))

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def _execute_patch_probe(
        self, patch: bytes, classification: ChangeClassification
    ) -> dict[str, Any]:
        probe = self.provider.probe()
        if not (probe.available and probe.security_boundary and probe.execution_enabled):
            raise PermissionError(
                "PHASE10_ACCEPTED_SECURITY_BOUNDARY_REQUIRED:" + ",".join(probe.reasons)
            )
        source = build_patch_probe_source(patch, classification.lane)
        nonce = uuid.uuid4().hex
        request = {
            "action": "qa.execute",
            "class_name": "Phase10RepositoryPatchProbe",
            "engine_id": "autonomy.repository_cycle",
            "adapter_id": "builtin.repository.cycle.internal",
            "nonce": nonce,
            "repetitions": 2,
        }
        execution = self.provider.execute(source, request)
        boundary = execution.get("boundary_result", {})
        if boundary.get("schema") != "PHOENIX_PHASE9_BOUNDARY_RESULT_V1":
            raise PermissionError("PHASE10_BOUNDARY_RESULT_SCHEMA_INVALID")
        if not hmac.compare_digest(str(boundary.get("nonce", "")), nonce):
            raise PermissionError("PHASE10_BOUNDARY_NONCE_MISMATCH")
        expected_source = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(str(boundary.get("source_sha256", "")), expected_source):
            raise PermissionError("PHASE10_BOUNDARY_SOURCE_SHA256_MISMATCH")
        if boundary.get("candidate_code_executed") is not True:
            raise PermissionError("PHASE10_PATCH_PROBE_EXECUTION_NOT_PROVEN")
        results = boundary.get("results") or []
        if len(results) != 2 or results[0] != results[1]:
            raise PermissionError("PHASE10_BOUNDARY_DETERMINISTIC_REPLAY_FAILED")
        value = results[0]
        expected_patch = hashlib.sha256(patch).hexdigest()
        result = value.get("result") or {}
        if value.get("status") != "COMPLETE":
            raise PermissionError("PHASE10_PATCH_PROBE_FAILED")
        if result.get("patch_sha256") != expected_patch:
            raise PermissionError("PHASE10_PATCH_PROBE_SHA256_MISMATCH")
        if result.get("lane") != classification.lane:
            raise PermissionError("PHASE10_PATCH_PROBE_LANE_MISMATCH")
        return execution

    def _write_attestation(self, attestation: dict[str, Any]) -> Path:
        if self.gateway is None:
            raise RuntimeError("Phase-10 gateway unavailable for attestation write")
        rel = f"attestations/{attestation['attestation_id']}.json"
        uri = "runtime://repository_cycle/" + rel
        gates = (
            "audit_log",
            "accepted_security_boundary",
            "protected_path_gate",
            "deterministic_patch_replay",
            "main_worktree_unchanged",
        )
        permit = self.gateway.authorize(
            MutationIntent(
                engine_id="autonomy.repository_cycle",
                action="autonomy.repository.cycle.attestation.write",
                risk="LOW",
                domain="orchestration",
                paths=(uri,),
                gates=gates,
                metadata={"attestation_sha256": attestation["attestation_sha256"]},
            )
        )
        self.gateway.consume(
            permit,
            engine_id="autonomy.repository_cycle",
            action="autonomy.repository.cycle.attestation.write",
            paths=(uri,),
        )
        path = self.runtime_root / "repository_cycle" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(attestation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(tmp, path)
        return path

    def _attestation(
        self,
        *,
        baseline_sha: str,
        classification: ChangeClassification,
        patch_sha256: str,
        provider: dict[str, Any],
        candidate_commit: str | None,
        promoted: bool,
        persist: bool,
    ) -> dict[str, Any]:
        if promoted:
            status = "PROMOTED"
        elif classification.approval_required:
            status = "LANE_B_APPROVAL_REQUIRED"
        else:
            status = "LANE_A_PROMOTION_ELIGIBLE"
        obj: dict[str, Any] = {
            "schema": "PHOENIX_REPOSITORY_CYCLE_ATTESTATION_V1",
            "attestation_id": "RCA-" + uuid.uuid4().hex[:16].upper(),
            "cycle_id": "RCYCLE-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "baseline_sha": baseline_sha,
            "lane": classification.lane,
            "paths": list(classification.paths),
            "total_bytes": classification.total_bytes,
            "change_manifest_sha256": classification.manifest_sha256,
            "patch_sha256": patch_sha256,
            "candidate_commit": candidate_commit,
            "deterministic_patch_replay": "PASS",
            "accepted_security_boundary": True,
            "provider": provider,
            "main_worktree_unchanged_during_verification": True,
            "approval_required": classification.approval_required,
            "automatic_fast_forward_promotion": (
                classification.automatic_fast_forward_promotion
            ),
            "repository_push_performed": False,
            "automatic_engine_activation": False,
            "status": status,
        }
        obj["attestation_sha256"] = _sha_obj(obj)
        obj["hmac_sha256"] = self._sign(dict(obj))
        if persist:
            path = self._write_attestation(obj)
            obj["runtime_path"] = str(path)
        return obj

    def load_attestation(self, path: Path) -> dict[str, Any]:
        target = Path(path).resolve()
        allowed = (self.runtime_root / "repository_cycle" / "attestations").resolve()
        try:
            target.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("Phase-10 attestation outside runtime") from exc
        obj = json.loads(target.read_text(encoding="utf-8-sig"))
        if obj.get("schema") != "PHOENIX_REPOSITORY_CYCLE_ATTESTATION_V1":
            raise PermissionError("Phase-10 attestation schema invalid")
        if not self._verify_signed(obj):
            raise PermissionError("Phase-10 attestation HMAC verification failed")
        material = dict(obj)
        material.pop("hmac_sha256", None)
        supplied = str(material.pop("attestation_sha256", ""))
        if not supplied or not hmac.compare_digest(supplied, _sha_obj(material)):
            raise PermissionError("Phase-10 attestation digest verification failed")
        if obj.get("automatic_engine_activation") is not False:
            raise PermissionError("Phase-10 automatic activation boundary invalid")
        return obj

    def run_synthetic_proof(
        self,
        expected_phoenix_baseline: str,
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        if len(expected_phoenix_baseline) != 40:
            raise ValueError("expected Phoenix baseline must be a 40-character SHA")
        with tempfile.TemporaryDirectory(prefix="phoenix-phase10-proof-") as td:
            fixture = Path(td) / "repo"
            baseline = initialize_fixture_repository(fixture)
            manager = GuardedWorktreeManager(fixture)

            lane_a_candidate = manager.create_candidate(
                "lane-a-proof", baseline, parent=Path(td) / "worktrees"
            )
            lane_a_file = (
                lane_a_candidate.path
                / "docs"
                / "automation"
                / "autonomous_generated"
                / "phase10-proof.md"
            )
            lane_a_file.parent.mkdir(parents=True, exist_ok=True)
            lane_a_file.write_text("phase10 deterministic fixture\n", encoding="utf-8")
            lane_a_records = manager.status_records(lane_a_candidate)
            lane_a = self.classifier.classify(lane_a_records)
            patch_a, patch_a_sha = manager.stage_and_patch(
                lane_a_candidate, lane_a.paths
            )
            replay_a = manager.deterministic_replay(
                lane_a_candidate, patch_a, parent=Path(td) / "replay-a"
            )
            if replay_a[0] != replay_a[1]:
                raise RuntimeError("PHASE10_LANE_A_REPLAY_FAILED")
            main_before = manager.snapshot(fetch=False)
            execution = self._execute_patch_probe(patch_a, lane_a)
            main_after_boundary = manager.snapshot(fetch=False)
            if main_after_boundary.head != main_before.head or not main_after_boundary.clean:
                raise RuntimeError("PHASE10_MAIN_WORKTREE_CHANGED_DURING_BOUNDARY")
            commit_a = manager.commit_candidate(lane_a_candidate, lane_a.lane, patch_a_sha)
            promoted_a = manager.local_fast_forward_proof(lane_a_candidate, commit_a)
            manager.cleanup(lane_a_candidate)

            lane_b_baseline = promoted_a
            lane_b_candidate = manager.create_candidate(
                "lane-b-proof", lane_b_baseline, parent=Path(td) / "worktrees"
            )
            source = (
                lane_b_candidate.path
                / "phoenix"
                / "autonomy"
                / "generated_adapters"
                / "phase10_fixture.py"
            )
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("VALUE = 'phase10'\n", encoding="utf-8")
            lane_b_records = manager.status_records(lane_b_candidate)
            lane_b = self.classifier.classify(lane_b_records)
            patch_b, patch_b_sha = manager.stage_and_patch(
                lane_b_candidate, lane_b.paths
            )
            replay_b = manager.deterministic_replay(
                lane_b_candidate, patch_b, parent=Path(td) / "replay-b"
            )
            if replay_b[0] != replay_b[1]:
                raise RuntimeError("PHASE10_LANE_B_REPLAY_FAILED")
            if not lane_b.approval_required or lane_b.automatic_fast_forward_promotion:
                raise RuntimeError("PHASE10_LANE_B_APPROVAL_BOUNDARY_FAILED")
            if manager.snapshot(fetch=False).head != lane_b_baseline:
                raise RuntimeError("PHASE10_LANE_B_CHANGED_MAIN_WITHOUT_APPROVAL")
            manager.cleanup(lane_b_candidate)

            att = self._attestation(
                baseline_sha=expected_phoenix_baseline,
                classification=lane_a,
                patch_sha256=patch_a_sha,
                provider=execution["provider"],
                candidate_commit=commit_a,
                promoted=True,
                persist=persist,
            )
            return {
                "schema": "PHOENIX_PHASE10_SYNTHETIC_REPOSITORY_PROOF_V1",
                "status": "PASS",
                "test_only": False,
                "live_runtime_proof": True,
                "provider_id": execution["provider"]["provider_id"],
                "lane_a_fast_forward_proof": "PASS",
                "lane_a_patch_sha256": patch_a_sha,
                "lane_b_approval_pause_proof": "PASS",
                "lane_b_patch_sha256": patch_b_sha,
                "deterministic_patch_replay": "PASS",
                "protected_path_gate": "PASS",
                "main_phoenix_repository_write_performed": False,
                "main_phoenix_repository_commit_created": False,
                "main_phoenix_repository_push_performed": False,
                "automatic_engine_activation": False,
                "attestation": att,
            }
