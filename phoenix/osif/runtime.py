"""Restricted CLI runtime for Phoenix OSIF."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

from .contracts import ExecutionRequest, ExecutionResult


class RuntimeErrorOSIF(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimePolicy:
    timeout_seconds: int = 300
    allowed_executables: tuple[str, ...] = ()
    allow_shell: bool = False
    max_output_chars: int = 1_000_000

    def validate(self) -> None:
        if self.timeout_seconds <= 0:
            raise RuntimeErrorOSIF("timeout_seconds must be positive.")
        if self.max_output_chars <= 0:
            raise RuntimeErrorOSIF("max_output_chars must be positive.")
        if self.allow_shell:
            raise RuntimeErrorOSIF("Shell execution is disabled.")


class RuntimeManager:
    def __init__(self, policy: RuntimePolicy | None = None) -> None:
        self.policy = policy or RuntimePolicy()
        self.policy.validate()

    @staticmethod
    def _digest(value: object) -> str:
        return sha256(
            json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def execute_cli(
        self,
        *,
        executable: str,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        request.validate()
        allowed = self.policy.allowed_executables
        if allowed and executable not in allowed and Path(executable).name not in allowed:
            raise RuntimeErrorOSIF(f"Executable is not allowed: {executable}")
        completed = subprocess.run(
            [executable, *request.arguments],
            env={**os.environ, **dict(request.environment)},
            capture_output=True,
            text=True,
            timeout=self.policy.timeout_seconds,
            shell=False,
            check=False,
        )
        status = "completed" if completed.returncode == 0 else "failed"
        stdout = completed.stdout[: self.policy.max_output_chars]
        stderr = completed.stderr[: self.policy.max_output_chars]
        return ExecutionResult(
            request_id=request.request_id,
            application_id=request.application_id,
            status=status,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            evidence_sha256=self._digest(
                {
                    "request_id": request.request_id,
                    "status": status,
                    "exit_code": completed.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            ),
            metadata={"shell": False},
        )
