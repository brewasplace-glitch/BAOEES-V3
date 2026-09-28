from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .isolated_runtime import RuntimeProviderProbe, select_runtime_provider


@dataclass(frozen=True)
class ContinuousObservation:
    baseline: str
    branch: str
    origin_head: str
    clean: bool
    signals: tuple[str, ...]
    signal_sha256: str


class AtomicHmacStateStore:
    def __init__(self, runtime_root: Path):
        self.root = Path(runtime_root)
        self.state_path = self.root / "continuous_state_v1.json"
        self.key_path = self.root / "continuous_state_v1.key"

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _key(self) -> bytes:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            self.key_path.write_bytes(secrets.token_bytes(32))
        return self.key_path.read_bytes()

    def save(self, value: dict[str, Any]) -> dict[str, Any]:
        unsigned = dict(value)
        unsigned.pop("state_sha256", None)
        unsigned.pop("hmac_sha256", None)
        digest = hashlib.sha256(self._canonical(unsigned)).hexdigest()
        signed = {**unsigned, "state_sha256": digest}
        signed["hmac_sha256"] = hmac.new(
            self._key(), self._canonical(signed), hashlib.sha256
        ).hexdigest()
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(signed, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, self.state_path)
        return signed

    def load(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        signature = value.pop("hmac_sha256", "")
        expected = hmac.new(self._key(), self._canonical(value), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RuntimeError("PHASE15_STATE_HMAC_DENY")
        digest = value.pop("state_sha256", "")
        if digest != hashlib.sha256(self._canonical(value)).hexdigest():
            raise RuntimeError("PHASE15_STATE_DIGEST_DENY")
        return {**value, "state_sha256": digest, "hmac_sha256": signature}


class ContinuousDevelopmentPilotService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        policy_root: Path | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        self.policy_root = Path(policy_root or repo_root).resolve()
        self.clock = clock
        self.policy = json.loads(
            (self.policy_root / "configs/phoenix/continuous_development_policy_v1.json").read_text(encoding="utf-8")
        )
        self.pilot = json.loads(
            (self.policy_root / "configs/phoenix/monitored_level5_pilot_v1.json").read_text(encoding="utf-8")
        )
        self.store = AtomicHmacStateStore(self.runtime_root)
        self._validate_policy()

    def _validate_policy(self) -> None:
        p = self.policy
        if p.get("mode") != "MONITORED_LEVEL5_PILOT" or p.get("monitoring_enabled") is not True:
            raise RuntimeError("PHASE15_POLICY_MODE_DENY")
        if p.get("continuous_daemon_activation") is not False or p.get("automatic_engine_activation") is not False:
            raise RuntimeError("PHASE15_UNBOUNDED_ACTIVATION_DENY")
        if p.get("max_cycles_per_window") != 1 or p.get("max_tasks_per_cycle") != 1:
            raise RuntimeError("PHASE15_BOUNDS_DENY")
        if p["promotion"].get("pilot_automatic_promotion") is not False:
            raise RuntimeError("PHASE15_PILOT_PROMOTION_DENY")
        if self.pilot.get("maximum_live_cycles") != 0 or self.pilot.get("promotion_enabled") is not False:
            raise RuntimeError("PHASE15_LIVE_CYCLE_DENY")

    def _git(self, *args: str, check: bool = True) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.longpaths=true", "-c", "core.quotepath=false", "-C", str(self.repo_root), *args],
            text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if check and completed.returncode:
            raise RuntimeError("PHASE15_GIT_DENY:" + completed.stdout[-500:])
        return completed.stdout.strip()

    def probe(self) -> dict[str, Any]:
        runtime_policy = json.loads(
            (self.policy_root / "configs/phoenix/isolated_runtime_policy_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        provider = select_runtime_provider(runtime_policy, self.runtime_root)
        result: RuntimeProviderProbe = provider.probe()
        return result.to_dict()

    def observe(self, expected_baseline: str, *, require_remote: bool = True) -> ContinuousObservation:
        if len(expected_baseline) != 40 or any(c not in "0123456789abcdef" for c in expected_baseline):
            raise ValueError("expected baseline must be a lowercase 40-character SHA")
        branch = self._git("branch", "--show-current")
        head = self._git("rev-parse", "HEAD")
        origin = self._git("rev-parse", "origin/project-phoenix") if require_remote else head
        clean = not bool(self._git("status", "--porcelain=v1", "--untracked-files=all"))
        if branch != "project-phoenix" or head != expected_baseline or not clean:
            raise RuntimeError("PHASE15_BASELINE_DENY")
        if require_remote and origin != expected_baseline:
            raise RuntimeError("PHASE15_ORIGIN_DENY")
        signals = tuple(self.policy["signals"])
        material = json.dumps({"baseline": head, "branch": branch, "origin": origin, "signals": signals}, sort_keys=True).encode()
        return ContinuousObservation(head, branch, origin, clean, signals, hashlib.sha256(material).hexdigest())

    def _kill_switch(self) -> Path:
        return self.runtime_root / self.policy["kill_switch_filename"]

    def monitored_tick(self, expected_baseline: str, *, persist: bool = True) -> dict[str, Any]:
        observation = self.observe(expected_baseline)
        prior = self.store.load() if persist else None
        if self._kill_switch().exists():
            result = {
                "schema": "PHOENIX_PHASE15_MONITORED_TICK_V1", "status": "PAUSED_KILL_SWITCH",
                "baseline": expected_baseline, "repository_mutation": False, "push_performed": False,
                "automatic_engine_activation": False,
            }
        else:
            selected = "PHX-L5-PILOT-OBSERVATION-EVIDENCE-001"
            result = {
                "schema": "PHOENIX_PHASE15_MONITORED_TICK_V1", "status": "DRY_RUN_PASS",
                "baseline": expected_baseline, "signal_sha256": observation.signal_sha256,
                "selected_task_id": selected, "selected_task_risk": "LOW", "task_count": 1,
                "tests_required": int(self.policy["regression"]["expected_test_count"]),
                "benchmark_gate": "REQUIRED", "accepted_isolation_gate": "REQUIRED",
                "repository_mutation": False, "push_performed": False,
                "pilot_automatic_promotion": False, "automatic_engine_activation": False,
            }
        if persist:
            count = int(prior["cycle_count"]) + 1 if prior else 1
            state = self.store.save({
                "schema": "PHOENIX_CONTINUOUS_DEVELOPMENT_STATE_V1",
                "baseline": expected_baseline, "cycle_count": count,
                "last_status": result["status"], "timestamp": int(self.clock()),
                "signal_sha256": observation.signal_sha256,
            })
            result["state_sha256"] = state["state_sha256"]
        return result

    def status(self) -> dict[str, Any]:
        state = self.store.load()
        return {
            "schema": "PHOENIX_PHASE15_CONTINUOUS_STATUS_V1",
            "mode": self.policy["mode"], "monitoring_enabled": True,
            "continuous_daemon_activation": False, "automatic_promotion": False,
            "kill_switch_active": self._kill_switch().exists(), "state": state,
        }
