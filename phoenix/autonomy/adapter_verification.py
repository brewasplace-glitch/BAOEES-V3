from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import hashlib

from .adapter_implementation import AdapterImplementationValidation


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class IsolatedVerificationProvider(Protocol):
    provider_id: str
    version: str
    security_boundary: bool

    def describe(self) -> dict[str, Any]: ...

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]: ...


class DisabledIsolationProvider:
    """Fail-closed provider used until an accepted OS security boundary exists."""

    provider_id = "disabled.no_security_boundary"
    version = "1.0.0"
    security_boundary = False

    def __init__(self, reason: str):
        self.reason = str(reason)

    def describe(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "version": self.version,
            "available": False,
            "security_boundary": False,
            "candidate_execution_enabled": False,
            "reason": self.reason,
        }

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]:
        raise PermissionError("CANDIDATE_EXECUTION_DENY:NO_ACCEPTED_SECURITY_BOUNDARY")


@dataclass(frozen=True)
class StaticVerificationReport:
    status: str
    errors: tuple[str, ...]
    source_sha256: str
    expected_source_sha256: str
    deterministic_replay: bool
    phase7_contract_pass: bool
    candidate_code_executed: bool
    provider: dict[str, Any]

    @property
    def static_pass(self) -> bool:
        return self.status == "STATIC_PASS_EXECUTION_BLOCKED" and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": list(self.errors),
            "source_sha256": self.source_sha256,
            "expected_source_sha256": self.expected_source_sha256,
            "deterministic_replay": self.deterministic_replay,
            "phase7_contract_pass": self.phase7_contract_pass,
            "candidate_code_executed": self.candidate_code_executed,
            "provider": self.provider,
        }


class AdapterStaticVerifier:
    def __init__(self, provider: IsolatedVerificationProvider):
        self.provider = provider

    def verify(
        self,
        source: str,
        expected_source: str,
        phase7_validation: AdapterImplementationValidation,
    ) -> StaticVerificationReport:
        errors = []
        source_sha = _sha_bytes(source.encode("utf-8"))
        expected_sha = _sha_bytes(expected_source.encode("utf-8"))
        deterministic = source == expected_source and source_sha == expected_sha
        if not deterministic:
            errors.append("DETERMINISTIC_SOURCE_REPLAY_MISMATCH")
        if not phase7_validation.activation_ready:
            errors.extend(
                "PHASE7_CONTRACT:" + item for item in phase7_validation.errors
            )
        provider = self.provider.describe()
        if provider.get("candidate_execution_enabled") is not False:
            errors.append("PROVIDER_MUST_REMAIN_EXECUTION_DISABLED")
        if provider.get("security_boundary") is not False:
            errors.append("UNREVIEWED_SECURITY_BOUNDARY_CLAIM")
        errors = tuple(sorted(set(errors)))
        return StaticVerificationReport(
            "STATIC_PASS_EXECUTION_BLOCKED" if not errors else "STATIC_FAIL",
            errors,
            source_sha,
            expected_sha,
            deterministic,
            phase7_validation.activation_ready,
            False,
            provider,
        )
