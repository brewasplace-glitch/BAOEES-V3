from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ENGINE_ID = "PHX-SESSION-RESULT-INTEGRITY-R8.2.1"
ENGINE_VERSION = "1.0.0"


class SessionResultIntegrityError(RuntimeError):
    """Raised when a session-adapter result cannot be trusted for this run."""


def prepare_adapter_result_path(path: Path) -> None:
    """Remove only the mutable adapter-result summary before a new adapter run.

    Detailed historical evidence remains in the project workspace. Removing the
    single mutable summary guarantees that a crashed adapter cannot accidentally
    leave a previous session's result available for the current orchestrator run.
    """

    target = Path(path)
    if target.is_file():
        target.unlink()


def validate_adapter_result_session(
    path: Path,
    current_session_id: str,
    capability_id: str,
) -> dict[str, Any]:
    """Load an adapter result and require exact current-session identity."""

    target = Path(path)
    if not target.is_file():
        raise SessionResultIntegrityError(
            f"SESSION_ADAPTER_RESULT_REQUIRED: {capability_id}: {target}"
        )

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact decoder varies
        raise SessionResultIntegrityError(
            f"SESSION_ADAPTER_RESULT_INVALID_JSON: {capability_id}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise SessionResultIntegrityError(
            f"SESSION_ADAPTER_RESULT_INVALID_SHAPE: {capability_id}"
        )

    expected = str(current_session_id or "")
    actual = str(data.get("session_id") or "")
    result_capability = str(data.get("capability_id") or "")

    if not expected:
        raise SessionResultIntegrityError(
            f"CURRENT_SESSION_ID_REQUIRED: {capability_id}"
        )

    if actual != expected:
        raise SessionResultIntegrityError(
            "STALE_SESSION_ADAPTER_RESULT_REJECTED: "
            f"{capability_id}: expected={expected!r}, actual={actual!r}"
        )

    if result_capability and result_capability != str(capability_id):
        raise SessionResultIntegrityError(
            "SESSION_ADAPTER_CAPABILITY_MISMATCH: "
            f"expected={capability_id!r}, actual={result_capability!r}"
        )

    return data
