from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import time
import uuid

from .adapter_implementation import AdapterImplementationValidator
from .adapter_verification import AdapterStaticVerifier, DisabledIsolationProvider
from .approval_resume import LocalIntegrityKey
from .decision_engine import PolicyDecisionLog
from .engine_onboarding import EngineOnboardingService
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_obj(obj: Any) -> str:
    return _sha_bytes(_canonical(obj))


def _json_text(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _norm(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./")


class DeterministicReadOnlyAdapterSynthesizer:
    generator_id = "PHOENIX_DETERMINISTIC_READ_ONLY_ADAPTER_V1"
    generator_version = "1.0.0"

    def specification(
        self, *, engine_id: str, descriptor: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "schema": "PHOENIX_ADAPTER_SYNTHESIS_SPEC_V1",
            "generator": self.generator_id,
            "generator_version": self.generator_version,
            "behavior": "READ_ONLY_DECLARED_ACTION_EVIDENCE_V1",
            "engine_id": str(engine_id),
            "adapter_id": str(descriptor["adapter_id"]),
            "class_name": str(descriptor["implementation"]).partition(":")[2],
            "actions": [str(x) for x in descriptor.get("actions", ())],
            "mutation_capable": bool(descriptor.get("mutation_capable")),
            "gateway_required": bool(descriptor.get("gateway_required")),
            "unknown_action": "FAILED_ACTION_SCOPE_DENY",
            "repository_write": False,
            "network_access": False,
        }

    def synthesize(
        self, *, engine_id: str, descriptor: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        spec = self.specification(engine_id=engine_id, descriptor=descriptor)
        if spec["mutation_capable"] or spec["gateway_required"]:
            raise PermissionError("MUTATION_CAPABLE_SYNTHESIS_DENY")
        if not spec["class_name"]:
            raise ValueError("generated adapter class name missing")
        if not spec["actions"]:
            raise ValueError("generated adapter action scope missing")

        source = (
            "from __future__ import annotations\n"
            "from phoenix.autonomy.executor_adapters import AdapterExecutionResult\n\n"
            f"class {spec['class_name']}:\n"
            f"    adapter_id = {spec['adapter_id']!r}\n"
            f"    engine_id = {spec['engine_id']!r}\n"
            f"    actions = {tuple(spec['actions'])!r}\n"
            "    mutation_capable = False\n"
            "    gateway_required = False\n\n"
            "    def __init__(self, host):\n"
            "        self.host = host\n\n"
            "    def execute(self, ctx):\n"
            "        if ctx.step.action not in self.actions:\n"
            "            return AdapterExecutionResult(\"FAILED\", reason=\"ACTION_SCOPE_DENY\")\n"
            "        return AdapterExecutionResult(\"COMPLETE\", result={\n"
            "            \"adapter_id\": self.adapter_id,\n"
            "            \"engine_id\": self.engine_id,\n"
            "            \"action\": ctx.step.action,\n"
            "            \"mode\": \"READ_ONLY_SYNTHESIZED_V1\",\n"
            "        })\n"
        )
        return spec, source


class AdapterSynthesisService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        gateway: UniversalAutonomyGateway | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        cfg = self.repo_root / "configs/phoenix"
        self.policy = json.loads(
            (cfg / "adapter_synthesis_policy_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.profile = json.loads(
            (cfg / "adapter_verification_profile_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        activation_policy = json.loads(
            (cfg / "engine_activation_policy_v1.json").read_text(
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
        self.onboarding = EngineOnboardingService(
            self.repo_root, self.runtime_root, gateway=gateway
        )
        self.phase7_validator = AdapterImplementationValidator(activation_policy)
        self.synthesizer = DeterministicReadOnlyAdapterSynthesizer()
        provider_data = self.profile["active_provider"]
        self.provider = DisabledIsolationProvider(provider_data["reason"])
        self.static_verifier = AdapterStaticVerifier(self.provider)
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "adapter_synthesis_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self) -> None:
        if self.policy.get("schema") != "PHOENIX_ADAPTER_SYNTHESIS_POLICY_V1":
            raise RuntimeError("adapter synthesis policy schema invalid")
        if self.policy.get("status") != "ACTIVE" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("adapter synthesis policy must be active and fail closed")
        if self.policy["synthesis"].get("mutation_capable_adapter_synthesis") != "DENY":
            raise RuntimeError("mutation-capable synthesis must remain denied")
        if self.policy["synthesis"].get("repository_write_during_synthesis") is not False:
            raise RuntimeError("repository write during synthesis must remain disabled")
        if self.profile.get("candidate_execution_enabled") is not False:
            raise RuntimeError("candidate execution must remain disabled")
        if self.profile["active_provider"].get("security_boundary") is not False:
            raise RuntimeError("unreviewed provider security-boundary claim")

    def _sign(self, obj: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, _canonical(obj), hashlib.sha256).hexdigest()

    def _verify_signed(self, obj: dict[str, Any]) -> bool:
        supplied = str(obj.get("hmac_sha256", ""))
        unsigned = dict(obj)
        unsigned.pop("hmac_sha256", None)
        return bool(supplied) and hmac.compare_digest(supplied, self._sign(unsigned))

    def _runtime_path(self, rel: str) -> Path:
        rel = _norm(rel)
        path = (self.runtime_root / "adapter_synthesis" / Path(rel)).resolve()
        allowed = (self.runtime_root / "adapter_synthesis").resolve()
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("adapter synthesis runtime path escape") from exc
        return path

    def _runtime_write_json(
        self,
        rel: str,
        obj: dict[str, Any],
        *,
        action: str,
        gates: tuple[str, ...],
    ) -> Path:
        rel = _norm(rel)
        uri = f"runtime://adapter_synthesis/{rel}"
        permit = self.gateway.authorize(
            MutationIntent(
                engine_id="autonomy.adapter_synthesis",
                action=action,
                risk="LOW",
                domain="synthesis",
                paths=(uri,),
                gates=gates,
                metadata={"artifact": rel, "sha256": _sha_obj(obj)},
            )
        )
        self.gateway.consume(
            permit,
            engine_id="autonomy.adapter_synthesis",
            action=action,
            paths=(uri,),
        )
        path = self._runtime_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(_json_text(obj), encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        return path

    def _runtime_write_text(
        self,
        rel: str,
        text: str,
        *,
        action: str,
        gates: tuple[str, ...],
    ) -> Path:
        rel = _norm(rel)
        uri = f"runtime://adapter_synthesis/{rel}"
        permit = self.gateway.authorize(
            MutationIntent(
                engine_id="autonomy.adapter_synthesis",
                action=action,
                risk="LOW",
                domain="synthesis",
                paths=(uri,),
                gates=gates,
                metadata={
                    "artifact": rel,
                    "sha256": _sha_bytes(text.encode("utf-8")),
                },
            )
        )
        self.gateway.consume(
            permit,
            engine_id="autonomy.adapter_synthesis",
            action=action,
            paths=(uri,),
        )
        path = self._runtime_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        return path

    def load_phase6_proposal(self, proposal_path: Path) -> dict[str, Any]:
        path = Path(proposal_path).resolve()
        allowed = (self.runtime_root / "engine_onboarding" / "proposals").resolve()
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("Phase-6 proposal path outside governed runtime") from exc
        proposal = json.loads(path.read_text(encoding="utf-8-sig"))
        if proposal.get("schema") != "PHOENIX_ENGINE_ONBOARDING_PROPOSAL_V1":
            raise PermissionError("Phase-6 proposal schema invalid")
        if not self.onboarding.verify_signed_artifact(proposal):
            raise PermissionError("Phase-6 proposal HMAC verification failed")
        if proposal.get("admission", {}).get("status") != "PASS":
            raise PermissionError("Phase-6 proposal admission did not pass")
        if proposal.get("activation", {}).get("automatic_activation") is not False:
            raise PermissionError("Phase-6 automatic activation boundary invalid")
        if proposal.get("activation", {}).get("policy_denied_actions"):
            raise PermissionError("Phase-6 proposal contains policy-denied actions")
        return proposal

    def _descriptor(
        self, proposal: dict[str, Any], adapter_id: str
    ) -> dict[str, Any]:
        descriptors = [
            x
            for x in proposal.get("executor_registry_patch", ())
            if x.get("adapter_id") == adapter_id
        ]
        generated = {
            x.get("adapter_id") for x in proposal.get("generated_scaffolds", ())
        }
        if len(descriptors) != 1 or adapter_id not in generated:
            raise PermissionError("generated Phase-6 adapter descriptor required")
        descriptor = json.loads(json.dumps(descriptors[0]))
        if descriptor.get("plan_dispatchable") is not True:
            raise PermissionError("adapter must be plan-dispatchable")
        return descriptor

    def build_candidate(
        self,
        proposal_path: Path,
        adapter_id: str,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        proposal = self.load_phase6_proposal(proposal_path)
        descriptor = self._descriptor(proposal, adapter_id)
        spec, source = self.synthesizer.synthesize(
            engine_id=proposal["engine_id"], descriptor=descriptor
        )
        validation = self.phase7_validator.validate(
            source, engine_id=proposal["engine_id"], descriptor=descriptor
        )
        if not validation.activation_ready:
            raise PermissionError(
                "synthesized source failed Phase-7 contract: "
                + ",".join(validation.errors)
            )

        candidate_id = "ADPCAND-" + uuid.uuid4().hex[:16].upper()
        source_rel = f"candidates/{candidate_id}/{validation.target_path.rsplit('/', 1)[-1]}"
        record = {
            "schema": "PHOENIX_ADAPTER_SYNTHESIS_CANDIDATE_V1",
            "candidate_id": candidate_id,
            "timestamp": int(time.time()),
            "proposal_id": proposal["proposal_id"],
            "proposal_path": str(Path(proposal_path).resolve()),
            "engine_id": proposal["engine_id"],
            "adapter_id": adapter_id,
            "descriptor": descriptor,
            "synthesis_spec": spec,
            "prompt_spec_sha256": _sha_obj(spec),
            "source_sha256": validation.source_sha256,
            "source_relative_path": source_rel,
            "target_path": validation.target_path,
            "static_validation": validation.contract(),
            "candidate_code_executed": False,
            "repository_write_performed": False,
            "automatic_activation": False,
            "status": "SYNTHESIZED_STATIC_VALIDATION_PASS",
        }
        record["hmac_sha256"] = self._sign(dict(record))
        if persist:
            gates = ("audit_log", "synthesis_integrity", "static_validation")
            self._runtime_write_text(
                source_rel,
                source,
                action="adapter.synthesis.candidate.write",
                gates=gates,
            )
            record_path = self._runtime_write_json(
                f"candidates/{candidate_id}/candidate.json",
                record,
                action="adapter.synthesis.candidate.write",
                gates=gates,
            )
            record["runtime_path"] = str(record_path)
            record["source_path"] = str(self._runtime_path(source_rel))
        else:
            record["source"] = source
        return record

    def load_candidate(self, candidate_path: Path) -> tuple[dict[str, Any], str]:
        path = Path(candidate_path).resolve()
        allowed = self._runtime_path("candidates")
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("candidate path outside governed runtime") from exc
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        if record.get("schema") != "PHOENIX_ADAPTER_SYNTHESIS_CANDIDATE_V1":
            raise PermissionError("candidate schema invalid")
        if not self._verify_signed(record):
            raise PermissionError("candidate HMAC verification failed")
        source_path = self._runtime_path(record["source_relative_path"])
        source = source_path.read_text(encoding="utf-8-sig")
        if _sha_bytes(source.encode("utf-8")) != record.get("source_sha256"):
            raise PermissionError("candidate source integrity failed")
        return record, source

    def verify_candidate(
        self, candidate_path: Path, *, persist: bool = True
    ) -> dict[str, Any]:
        record, source = self.load_candidate(candidate_path)
        spec, expected_source = self.synthesizer.synthesize(
            engine_id=record["engine_id"], descriptor=record["descriptor"]
        )
        if _sha_obj(spec) != record.get("prompt_spec_sha256"):
            raise PermissionError("synthesis specification digest mismatch")
        validation = self.phase7_validator.validate(
            source,
            engine_id=record["engine_id"],
            descriptor=record["descriptor"],
        )
        report = self.static_verifier.verify(source, expected_source, validation)
        if not report.static_pass:
            raise PermissionError("candidate static verification failed")

        empty_sha = _sha_bytes(b"")
        attestation = {
            "schema": "PHOENIX_ADAPTER_RUNTIME_ATTESTATION_V1",
            "attestation_id": "ADPATT-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "candidate_id": record["candidate_id"],
            "candidate_path": str(Path(candidate_path).resolve()),
            "proposal_id": record["proposal_id"],
            "engine_id": record["engine_id"],
            "adapter_id": record["adapter_id"],
            "source_sha256": record["source_sha256"],
            "prompt_spec_sha256": record["prompt_spec_sha256"],
            "static_validation": report.to_dict(),
            "isolation": {
                **self.provider.describe(),
                "network_policy": "DENY",
                "filesystem_policy": "NO_REPOSITORY_WRITE",
                "process_policy": "DENY",
                "timeout_seconds": self.profile["execution_policy"]["timeout_seconds"],
                "memory_megabytes": self.profile["execution_policy"]["memory_megabytes"],
            },
            "stdout_sha256": empty_sha,
            "stderr_sha256": empty_sha,
            "timeout_outcome": "NOT_RUN",
            "memory_outcome": "NOT_RUN",
            "gateway_simulation": {
                "status": "NOT_REQUIRED_READ_ONLY",
                "mutation_capable": False,
                "gateway_required": False,
            },
            "deterministic_replay": {
                "status": "PASS",
                "source_sha256": report.source_sha256,
                "replay_source_sha256": report.expected_source_sha256,
            },
            "restrictedpython": {
                "reviewed_version": self.profile["defense_in_depth"]["restrictedpython_reviewed_version"],
                "used": False,
                "security_boundary": False,
            },
            "candidate_code_executed": False,
            "repository_write_performed": False,
            "automatic_activation": False,
            "governed_promotion_eligible": True,
            "phase7_activation_transaction_eligible": False,
            "status": "STATIC_VERIFIED_EXECUTION_BLOCKED",
        }
        attestation["attestation_sha256"] = _sha_obj(attestation)
        attestation["hmac_sha256"] = self._sign(dict(attestation))
        if persist:
            path = self._runtime_write_json(
                f"attestations/{attestation['attestation_id']}.json",
                attestation,
                action="adapter.verification.attestation.write",
                gates=(
                    "audit_log",
                    "synthesis_integrity",
                    "static_validation",
                    "non_executing_verification",
                ),
            )
            attestation["runtime_path"] = str(path)
        return attestation

    def load_attestation(self, attestation_path: Path) -> dict[str, Any]:
        path = Path(attestation_path).resolve()
        allowed = self._runtime_path("attestations")
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("attestation path outside governed runtime") from exc
        attestation = json.loads(path.read_text(encoding="utf-8-sig"))
        if attestation.get("schema") != "PHOENIX_ADAPTER_RUNTIME_ATTESTATION_V1":
            raise PermissionError("attestation schema invalid")
        if not self._verify_signed(attestation):
            raise PermissionError("attestation HMAC verification failed")
        material = dict(attestation)
        material.pop("hmac_sha256", None)
        supplied = str(material.pop("attestation_sha256", ""))
        if not supplied or not hmac.compare_digest(supplied, _sha_obj(material)):
            raise PermissionError("attestation digest verification failed")
        if attestation.get("candidate_code_executed") is not False:
            raise PermissionError("attestation execution boundary invalid")
        if attestation.get("repository_write_performed") is not False:
            raise PermissionError("attestation repository boundary invalid")
        return attestation

    def promote_candidate(
        self,
        attestation_path: Path,
        approved_source_sha256: str,
        *,
        explicit_approval: bool,
        persist: bool = True,
    ) -> dict[str, Any]:
        if explicit_approval is not True:
            raise PermissionError("explicit governed promotion approval required")
        attestation = self.load_attestation(attestation_path)
        if attestation.get("status") != "STATIC_VERIFIED_EXECUTION_BLOCKED":
            raise PermissionError("attestation is not statically verified")
        if not hmac.compare_digest(
            str(approved_source_sha256).lower(),
            str(attestation["source_sha256"]).lower(),
        ):
            raise PermissionError("approved source SHA256 mismatch")
        candidate, source = self.load_candidate(Path(attestation["candidate_path"]))
        if candidate["candidate_id"] != attestation["candidate_id"]:
            raise PermissionError("attestation candidate binding mismatch")

        handoff_id = "ADPHANDOFF-" + uuid.uuid4().hex[:16].upper()
        source_rel = f"handoffs/{handoff_id}/{Path(candidate['target_path']).name}"
        handoff = {
            "schema": "PHOENIX_ADAPTER_GOVERNED_HANDOFF_V1",
            "handoff_id": handoff_id,
            "timestamp": int(time.time()),
            "candidate_id": candidate["candidate_id"],
            "attestation_id": attestation["attestation_id"],
            "engine_id": candidate["engine_id"],
            "adapter_id": candidate["adapter_id"],
            "source_sha256": candidate["source_sha256"],
            "source_relative_path": source_rel,
            "target_path": candidate["target_path"],
            "explicit_approval": True,
            "sha_bound": True,
            "repository_write_performed": False,
            "activation_transaction_created": False,
            "automatic_activation": False,
            "phase7_activation_transaction_eligible": False,
            "status": "PHASE7_REVIEW_CANDIDATE",
            "blocked_reason": "ISOLATED_EXECUTION_SECURITY_BOUNDARY_UNAVAILABLE",
        }
        handoff["hmac_sha256"] = self._sign(dict(handoff))
        if persist:
            gates = (
                "audit_log",
                "synthesis_integrity",
                "explicit_approval",
                "sha_binding",
                "no_repository_write",
            )
            self._runtime_write_text(
                source_rel,
                source,
                action="adapter.promotion.handoff.write",
                gates=gates,
            )
            path = self._runtime_write_json(
                f"handoffs/{handoff_id}/handoff.json",
                handoff,
                action="adapter.promotion.handoff.write",
                gates=gates,
            )
            handoff["runtime_path"] = str(path)
            handoff["source_path"] = str(self._runtime_path(source_rel))
        return handoff
