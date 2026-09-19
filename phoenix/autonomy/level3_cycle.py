from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import time
import uuid

from .adapter_synthesis import AdapterSynthesisService
from .approval_resume import LocalIntegrityKey
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


class BoundedLevel3CycleService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        provider: IsolatedRuntimeProvider | None = None,
        gateway: UniversalAutonomyGateway | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        cfg = self.repo_root / "configs/phoenix"
        self.runtime_policy = json.loads(
            (cfg / "isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig")
        )
        self.cycle_policy = json.loads(
            (cfg / "level3_autonomous_cycle_policy_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        if gateway is None:
            gateway = UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(
                    self.runtime_root / "policy_decisions" / "decisions_v1.jsonl"
                ),
                audit_log=GatewayAuditLog(
                    self.runtime_root / "gateway" / "audit_v1.jsonl"
                ),
            )
        self.gateway = gateway
        self.synthesis = AdapterSynthesisService(
            self.repo_root, self.runtime_root, gateway=gateway
        )
        self.provider = provider or select_runtime_provider(
            self.runtime_policy, self.runtime_root
        )
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "level3_cycle_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self) -> None:
        if self.runtime_policy.get("schema") != "PHOENIX_ISOLATED_RUNTIME_POLICY_V1":
            raise RuntimeError("isolated runtime policy schema invalid")
        if self.runtime_policy.get("fail_closed") is not True:
            raise RuntimeError("isolated runtime policy must fail closed")
        if self.runtime_policy.get("automatic_provider_install") is not False:
            raise RuntimeError("automatic provider installation must remain disabled")
        if self.runtime_policy.get("automatic_image_pull") is not False:
            raise RuntimeError("automatic image pulls must remain disabled")
        if self.cycle_policy.get("schema") != "PHOENIX_LEVEL3_AUTONOMOUS_CYCLE_POLICY_V1":
            raise RuntimeError("Level-3 cycle policy schema invalid")
        if self.cycle_policy.get("allowed_risk") != ["LOW"]:
            raise RuntimeError("only LOW risk may execute in Phase 9")
        if int(self.cycle_policy.get("max_repair_attempts", 0)) != 3:
            raise RuntimeError("Phase 9 requires exactly three bounded repair attempts")
        if self.cycle_policy.get("automatic_activation") is not False:
            raise RuntimeError("automatic activation must remain disabled")

    def _sign(self, obj: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, _canonical(obj), hashlib.sha256).hexdigest()

    def _verify_signed(self, obj: dict[str, Any]) -> bool:
        supplied = str(obj.get("hmac_sha256", ""))
        unsigned = dict(obj)
        unsigned.pop("hmac_sha256", None)
        return bool(supplied) and hmac.compare_digest(supplied, self._sign(unsigned))

    def _write_attestation(self, obj: dict[str, Any]) -> Path:
        rel = f"attestations/{obj['attestation_id']}.json"
        uri = "runtime://level3_cycle/" + rel
        gates = (
            "audit_log",
            "accepted_security_boundary",
            "static_validation",
            "deterministic_replay",
            "no_repository_write",
        )
        permit = self.gateway.authorize(
            MutationIntent(
                engine_id="autonomy.level3_cycle",
                action="autonomy.level3.cycle.attestation.write",
                risk="LOW",
                domain="orchestration",
                paths=(uri,),
                gates=gates,
                metadata={"attestation_sha256": obj["attestation_sha256"]},
            )
        )
        self.gateway.consume(
            permit,
            engine_id="autonomy.level3_cycle",
            action="autonomy.level3.cycle.attestation.write",
            paths=(uri,),
        )
        path = self.runtime_root / "level3_cycle" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def execute_candidate(
        self,
        candidate_path: Path,
        action: str,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        candidate, source = self.synthesis.load_candidate(candidate_path)
        if candidate["descriptor"].get("mutation_capable") is not False:
            raise PermissionError("PHASE9_MUTATION_CAPABLE_CANDIDATE_DENY")
        if action not in candidate["descriptor"].get("actions", []):
            raise PermissionError("PHASE9_ACTION_SCOPE_DENY")
        static_attestation = self.synthesis.verify_candidate(candidate_path, persist=persist)
        probe = self.provider.probe()
        if not (probe.available and probe.security_boundary and probe.execution_enabled):
            raise PermissionError(
                "PHASE9_ACCEPTED_SECURITY_BOUNDARY_REQUIRED:" + ",".join(probe.reasons)
            )
        class_name = str(candidate["descriptor"]["implementation"]).partition(":")[2]
        nonce = uuid.uuid4().hex
        request = {
            "action": action,
            "class_name": class_name,
            "engine_id": candidate["engine_id"],
            "adapter_id": candidate["adapter_id"],
            "nonce": nonce,
            "repetitions": 2,
        }
        execution = self.provider.execute(source, request)
        boundary = execution.get("boundary_result", {})
        if boundary.get("schema") != "PHOENIX_PHASE9_BOUNDARY_RESULT_V1":
            raise PermissionError("PHASE9_BOUNDARY_RESULT_SCHEMA_INVALID")
        if not hmac.compare_digest(str(boundary.get("nonce", "")), nonce):
            raise PermissionError("PHASE9_BOUNDARY_NONCE_MISMATCH")
        if not hmac.compare_digest(
            str(boundary.get("source_sha256", "")), candidate["source_sha256"]
        ):
            raise PermissionError("PHASE9_BOUNDARY_SOURCE_SHA256_MISMATCH")
        if boundary.get("candidate_code_executed") is not True:
            raise PermissionError("PHASE9_CANDIDATE_EXECUTION_NOT_PROVEN")
        results = boundary.get("results") or []
        if len(results) != 2 or results[0] != results[1]:
            raise PermissionError("PHASE9_DETERMINISTIC_RUNTIME_REPLAY_FAILED")
        result = results[0]
        expected = {
            "adapter_id": candidate["adapter_id"],
            "engine_id": candidate["engine_id"],
            "action": action,
            "mode": "READ_ONLY_SYNTHESIZED_V1",
        }
        if result.get("status") != "COMPLETE" or result.get("result") != expected:
            raise PermissionError("PHASE9_RUNTIME_CONTRACT_FAILED")

        stages = [
            "OBSERVE", "CLASSIFY_LOW", "OPEN_SOURCE_REVIEW", "PLAN",
            "SYNTHESIZE", "STATIC_VERIFY", "ISOLATED_EXECUTE",
            "DETERMINISTIC_REPLAY", "EVIDENCE", "LEARN", "HANDOFF_READY",
        ]
        attestation = {
            "schema": "PHOENIX_LEVEL3_CYCLE_ATTESTATION_V1",
            "attestation_id": "L3ATT-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "cycle_id": "L3CYCLE-" + uuid.uuid4().hex[:16].upper(),
            "risk": "LOW",
            "candidate_id": candidate["candidate_id"],
            "candidate_path": str(Path(candidate_path).resolve()),
            "source_sha256": candidate["source_sha256"],
            "action": action,
            "provider": execution["provider"],
            "execution": {
                "candidate_code_executed": True,
                "exit_code": execution["exit_code"],
                "timed_out": execution["timed_out"],
                "elapsed_seconds": execution["elapsed_seconds"],
                "stdout_sha256": execution["stdout_sha256"],
                "stderr_sha256": execution["stderr_sha256"],
                "command_policy": execution["command_policy"],
                "result": result,
            },
            "static_attestation_id": static_attestation["attestation_id"],
            "deterministic_runtime_replay": "PASS",
            "repair_attempts": 0,
            "max_repair_attempts": 3,
            "stages": stages,
            "repository_write_performed": False,
            "repository_commit_created": False,
            "repository_push_performed": False,
            "automatic_activation": False,
            "phase7_activation_transaction_created": False,
            "governed_phase7_handoff_eligible": True,
            "status": "LEVEL3_LOW_RISK_RUNTIME_PROOF_PASS",
        }
        attestation["attestation_sha256"] = _sha_obj(attestation)
        attestation["hmac_sha256"] = self._sign(dict(attestation))
        if persist:
            path = self._write_attestation(attestation)
            attestation["runtime_path"] = str(path)
        return attestation

    def load_attestation(self, path: Path) -> dict[str, Any]:
        path = Path(path).resolve()
        allowed = (self.runtime_root / "level3_cycle" / "attestations").resolve()
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("Level-3 attestation path outside runtime") from exc
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        if obj.get("schema") != "PHOENIX_LEVEL3_CYCLE_ATTESTATION_V1":
            raise PermissionError("Level-3 attestation schema invalid")
        if not self._verify_signed(obj):
            raise PermissionError("Level-3 attestation HMAC verification failed")
        material = dict(obj)
        material.pop("hmac_sha256", None)
        supplied = str(material.pop("attestation_sha256", ""))
        if not supplied or not hmac.compare_digest(supplied, _sha_obj(material)):
            raise PermissionError("Level-3 attestation digest verification failed")
        if obj.get("repository_write_performed") is not False:
            raise PermissionError("Level-3 repository boundary invalid")
        if obj.get("automatic_activation") is not False:
            raise PermissionError("Level-3 activation boundary invalid")
        return obj
