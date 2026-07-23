"""Uniform adapter lifecycle for Phoenix OSIF."""

from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
import json
from typing import Any, Mapping

from phoenix.osif.contracts import ApplicationDescriptor
from .contracts import (
    AdapterContext,
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterHealth,
    AdapterLifecycleState,
)


class AdapterError(RuntimeError):
    """Raised when an adapter cannot complete its lifecycle safely."""


class OSIFAdapter(ABC):
    def __init__(self) -> None:
        self._state = AdapterLifecycleState.CREATED
        self._context: AdapterContext | None = None

    @property
    def state(self) -> AdapterLifecycleState:
        return self._state

    @staticmethod
    def evidence_digest(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    @abstractmethod
    def descriptor(self) -> ApplicationDescriptor:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> AdapterHealth:
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: AdapterExecutionRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def _execute(self, request: AdapterExecutionRequest) -> AdapterExecutionResult:
        raise NotImplementedError

    def initialize(self, context: AdapterContext) -> None:
        context.validate()
        if self._state not in {
            AdapterLifecycleState.CREATED,
            AdapterLifecycleState.STOPPED,
        }:
            raise AdapterError(f"Cannot initialize from state {self._state.value}.")
        self._context = context
        self._state = AdapterLifecycleState.INITIALIZED
        health = self.health_check()
        health.validate()
        self._state = (
            AdapterLifecycleState.READY
            if health.status in {"available", "degraded"}
            else AdapterLifecycleState.FAILED
        )
        if self._state is AdapterLifecycleState.FAILED:
            raise AdapterError(
                f"Adapter health check failed: {health.status} {health.message}".strip()
            )

    def execute(self, request: AdapterExecutionRequest) -> AdapterExecutionResult:
        if self._state is not AdapterLifecycleState.READY:
            raise AdapterError(
                f"Adapter is not ready; current state is {self._state.value}."
            )
        request.validate()
        self.validate_request(request)
        self._state = AdapterLifecycleState.RUNNING
        try:
            result = self._execute(request)
            result.validate()
            self._state = AdapterLifecycleState.READY
            return result
        except Exception:
            self._state = AdapterLifecycleState.FAILED
            raise

    def shutdown(self) -> None:
        self._context = None
        self._state = AdapterLifecycleState.STOPPED

    def digital_twin_writeback(
        self,
        *,
        project_id: str,
        result: AdapterExecutionResult,
    ) -> Mapping[str, Any]:
        result.validate()
        payload = {
            "schema_version": "1.0",
            "project_id": project_id,
            "adapter_id": result.adapter_id,
            "application_id": result.application_id,
            "request_id": result.request_id,
            "status": result.status,
            "outputs": dict(result.outputs),
            "warnings": list(result.warnings),
            "errors": list(result.errors),
            "source_evidence_sha256": result.evidence_sha256,
        }
        payload["writeback_sha256"] = self.evidence_digest(payload)
        return payload
