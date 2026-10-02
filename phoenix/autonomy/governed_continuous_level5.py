from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from .continuous_development import AtomicHmacStateStore
from .isolated_runtime import select_runtime_provider


class GovernedContinuousLevel5Service:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        policy_root: Path | None = None,
        clock: Callable[[], float] = time.time,
        isolation_probe: Callable[[], dict[str, Any]] | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        self.policy_root = Path(policy_root or repo_root).resolve()
        self.clock = clock
        self.policy = json.loads(
            (self.policy_root / "configs/phoenix/governed_continuous_level5_policy_v1.json").read_text(encoding="utf-8")
        )
        self.store = AtomicHmacStateStore(self.runtime_root / "phase16")
        self.isolation_probe = isolation_probe or self._probe_isolation
        self._validate_policy()

    def _validate_policy(self) -> None:
        p = self.policy
        if p.get("mode") != "SCHEDULED_GOVERNED_HEALTH_WINDOWS" or p.get("monitoring_enabled") is not True:
            raise RuntimeError("PHASE16_POLICY_MODE_DENY")
        forbidden = ("persistent_daemon", "automatic_repository_mutation", "automatic_promotion", "automatic_engine_activation")
        if any(p.get(key) is not False for key in forbidden):
            raise RuntimeError("PHASE16_UNBOUNDED_AUTOMATION_DENY")
        if p.get("max_windows_per_invocation") != 1 or p.get("max_tasks_selected_per_window") != 1:
            raise RuntimeError("PHASE16_WINDOW_BOUND_DENY")
        if p["scheduler"].get("overlap") != "DENY" or p.get("human_kill_switch") != "REQUIRED":
            raise RuntimeError("PHASE16_SAFETY_CONTROL_DENY")

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.longpaths=true", "-c", "core.quotepath=false", "-C", str(self.repo_root), *args],
            text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if completed.returncode:
            raise RuntimeError("PHASE16_GIT_DENY:" + completed.stdout[-500:])
        return completed.stdout.strip()

    def _probe_isolation(self) -> dict[str, Any]:
        policy = json.loads((self.policy_root / "configs/phoenix/isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig"))
        return select_runtime_provider(policy, self.runtime_root / "isolation").probe().to_dict()

    def _observe_repository(self, expected_baseline: str) -> dict[str, Any]:
        if len(expected_baseline) != 40 or any(c not in "0123456789abcdef" for c in expected_baseline):
            raise ValueError("expected baseline must be a lowercase 40-character SHA")
        branch = self._git("branch", "--show-current")
        head = self._git("rev-parse", "HEAD")
        origin = self._git("rev-parse", "origin/project-phoenix")
        clean = not bool(self._git("status", "--porcelain=v1", "--untracked-files=all"))
        if branch != "project-phoenix" or head != expected_baseline or origin != expected_baseline or not clean:
            raise RuntimeError("PHASE16_BASELINE_DENY")
        return {"branch": branch, "head": head, "origin_head": origin, "clean": clean}

    def _kill_switch(self) -> Path:
        return self.runtime_root / self.policy["kill_switch_filename"]

    def _lock_path(self) -> Path:
        return self.runtime_root / self.policy["lock_filename"]

    def scheduler_spec(self) -> dict[str, Any]:
        s = self.policy["scheduler"]
        return {
            "task_name": s["task_name"], "frequency": s["frequency"], "local_time": s["local_time"],
            "timezone": s["timezone"], "multiple_instances": "IGNORE_NEW", "start_when_available": False,
            "persistent_daemon": False,
        }

    def _dependency_digest(self) -> str:
        path = self.repo_root / "pyproject.toml"
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _backlog_observation(self) -> dict[str, Any]:
        path = self.policy_root / "configs/phoenix/autonomous_backlog_v1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        ready = [x for x in data.get("tasks", []) if x.get("status") == "READY" and x.get("risk") == "LOW"]
        ready.sort(key=lambda x: (-int(x.get("priority", 0)), str(x.get("task_id", ""))))
        return {"ready_low_risk_count": len(ready), "selected_task_id": ready[0]["task_id"] if ready else None}

    def _persist_health(self, record: dict[str, Any]) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        latest = self.runtime_root / self.policy["health_record_filename"]
        temporary = latest.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, latest)
        audit = self.runtime_root / self.policy["audit_filename"]
        with audit.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def run_window(self, expected_baseline: str, *, persist: bool = True, enforce_interval: bool = True) -> dict[str, Any]:
        repository = self._observe_repository(expected_baseline)
        now = int(self.clock())
        common = {
            "schema": "PHOENIX_GOVERNED_LEVEL5_HEALTH_RECORD_V1", "baseline": expected_baseline,
            "timestamp": now, "repository_mutation": False, "push_performed": False,
            "automatic_promotion": False, "automatic_engine_activation": False,
        }
        if self._kill_switch().exists():
            result = {**common, "status": "PAUSED_KILL_SWITCH", "signals": {"kill_switch": "ACTIVE"}}
            if persist: self._persist_health(result)
            return result

        self.runtime_root.mkdir(parents=True, exist_ok=True)
        lock = self._lock_path()
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"pid={os.getpid()}\ntimestamp={now}\n".encode())
            os.close(descriptor)
        except FileExistsError:
            return {**common, "status": "SKIPPED_OVERLAP", "signals": {"overlap": "DENIED"}}

        try:
            prior = self.store.load() if persist else None
            if prior and enforce_interval:
                age = now - int(prior.get("last_window_epoch", 0))
                if age < int(self.policy["minimum_window_interval_seconds"]):
                    return {**common, "status": "SKIPPED_INTERVAL", "signals": {"seconds_since_prior": age}}
                if age > int(self.policy["missed_window_fail_closed_seconds"]):
                    result = {**common, "status": "MISSED_WINDOW_FAIL_CLOSED", "signals": {"seconds_since_prior": age}}
                    if persist: self._persist_health(result)
                    return result

            isolation = self.isolation_probe()
            isolation_ok = bool(isolation.get("available") and isolation.get("security_boundary") and isolation.get("execution_enabled"))
            if not isolation_ok:
                raise RuntimeError("PHASE16_ISOLATION_PROVIDER_DENY")
            bundle = self.repo_root / "configs/phoenix/policy_bundle_manifest_v1.json"
            backlog = self._backlog_observation()
            signals = {
                "repository_clean": "PASS" if repository["clean"] else "FAIL",
                "repository_remote_synchronized": "PASS" if repository["head"] == repository["origin_head"] else "FAIL",
                "accepted_isolation_provider": "PASS",
                "policy_bundle_present": "PASS" if bundle.is_file() else "FAIL",
                "dependency_manifest_digest": self._dependency_digest(),
                "low_risk_backlog_observation": backlog,
            }
            if any(signals[x] == "FAIL" for x in ("repository_clean", "repository_remote_synchronized", "policy_bundle_present")):
                raise RuntimeError("PHASE16_HEALTH_SIGNAL_DENY")
            result = {**common, "status": "HEALTHY_NO_MUTATION", "signals": signals, "selected_task_id": backlog["selected_task_id"], "task_count": min(1, backlog["ready_low_risk_count"]), "scheduled_action": self.policy["scheduled_action"]}
            if persist:
                signed = self.store.save({"schema": "PHOENIX_GOVERNED_LEVEL5_STATE_V1", "baseline": expected_baseline, "last_window_epoch": now, "last_status": result["status"], "window_count": int(prior.get("window_count", 0)) + 1 if prior else 1})
                result["state_sha256"] = signed["state_sha256"]
                self._persist_health(result)
            return result
        finally:
            lock.unlink(missing_ok=True)

    def status(self) -> dict[str, Any]:
        return {"schema": "PHOENIX_GOVERNED_LEVEL5_STATUS_V1", "policy": self.policy["mode"], "scheduler": self.scheduler_spec(), "kill_switch_active": self._kill_switch().exists(), "state": self.store.load(), "automatic_promotion": False}
