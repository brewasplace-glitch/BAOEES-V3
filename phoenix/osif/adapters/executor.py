"""Managed adapter execution and audit envelope."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .base import OSIFAdapter
from .contracts import AdapterContext, AdapterExecutionRequest


class AdapterExecutor:
    @staticmethod
    def _digest(value: Any) -> str:
        return sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()

    def run(
        self,
        *,
        adapter: OSIFAdapter,
        context: AdapterContext,
        request: AdapterExecutionRequest,
    ) -> dict[str, Any]:
        adapter.initialize(context)
        try:
            health = adapter.health_check()
            result = adapter.execute(request)
            writeback = adapter.digital_twin_writeback(
                project_id=request.project_id,
                result=result,
            )
            envelope = {
                "schema_version": "1.0",
                "adapter_state": adapter.state.value,
                "health": asdict(health),
                "result": asdict(result),
                "digital_twin_writeback": writeback,
            }
            envelope["audit_sha256"] = self._digest(envelope)
            return envelope
        finally:
            adapter.shutdown()

    def write_envelope(
        self,
        envelope: Mapping[str, Any],
        destination: str | Path,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path
