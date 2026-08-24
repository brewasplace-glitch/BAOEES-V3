"""Project Phoenix Autonomous Build Orchestrator + Self-Healing Build Loop v1.0.

Purpose
-------
Execute a manifest-driven Phoenix software-build cycle end-to-end while reusing
the repository's existing governance model:

DISCOVER -> CLASSIFY -> PREFLIGHT -> EXECUTE -> HEAL -> VERIFY ->
SCOPE -> STAGE -> SECRET SCAN -> REMOTE RACE GUARD -> COMMIT -> PUSH -> FINAL.

The self-healing loop is deliberately deterministic. It only executes repair
actions explicitly registered in the build manifest. It does not invent source
code, professional review, engineering approval, or release authority.

This module uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Callable, Iterable, Sequence


ALLOWED_CLASSIFICATIONS = {"REUSE", "REPAIR", "EXTEND", "BUILD"}
ALLOWED_STEP_KINDS = {"build", "repair", "test", "smoke", "verify"}
FORBIDDEN_COMMAND_FRAGMENTS = (
    "git push --force",
    "git push -f",
    "git reset --hard",
    "git clean -fdx",
    "git clean -xdf",
    "git checkout -- .",
    "git restore .",
    "rm -rf /",
    "format c:",
    "diskpart",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"""(?ix)
        \b(api[_-]?key|access[_-]?token|client[_-]?secret|password)\b
        \s*[:=]\s*["'][^"']{8,}["']
        """
    ),
)


class BuildOrchestratorError(RuntimeError):
    """Fail-closed orchestration error."""


class ManifestValidationError(BuildOrchestratorError):
    """Invalid build manifest."""


class CommandSafetyError(BuildOrchestratorError):
    """Unsafe command rejected before execution."""


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: str = "."
    timeout_seconds: int = 900
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommandSpec":
        argv = data.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise ManifestValidationError("command.argv must be a non-empty list of strings")
        timeout = int(data.get("timeout_seconds", 900))
        if timeout < 1 or timeout > 86400:
            raise ManifestValidationError("command.timeout_seconds must be in range 1..86400")
        cwd = str(data.get("cwd", "."))
        env = data.get("env") or {}
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            raise ManifestValidationError("command.env must be a string-to-string object")
        return cls(tuple(argv), cwd=cwd, timeout_seconds=timeout, env=dict(env))


@dataclass(frozen=True)
class BuildStep:
    step_id: str
    kind: str
    command: CommandSpec
    max_attempts: int = 1
    repair_actions: tuple[CommandSpec, ...] = ()
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildStep":
        step_id = str(data.get("id") or "").strip()
        if not step_id:
            raise ManifestValidationError("step.id is required")
        kind = str(data.get("kind") or "build").lower()
        if kind not in ALLOWED_STEP_KINDS:
            raise ManifestValidationError(f"step.kind not allowed: {kind}")
        max_attempts = int(data.get("max_attempts", 1))
        if max_attempts < 1 or max_attempts > 5:
            raise ManifestValidationError("step.max_attempts must be in range 1..5")
        repairs = tuple(CommandSpec.from_dict(x) for x in (data.get("repair_actions") or []))
        return cls(
            step_id=step_id,
            kind=kind,
            command=CommandSpec.from_dict(data["command"]),
            max_attempts=max_attempts,
            repair_actions=repairs,
            description=str(data.get("description") or ""),
        )


@dataclass(frozen=True)
class BuildManifest:
    schema_version: str
    build_id: str
    title: str
    branch: str
    baseline: str
    classification: str
    commit_message: str
    expected_scope: tuple[str, ...]
    existing_markers: tuple[str, ...]
    required_contracts: tuple[str, ...]
    health_checks: tuple[CommandSpec, ...]
    steps: tuple[BuildStep, ...]
    impact_tests: tuple[BuildStep, ...]
    smoke_tests: tuple[BuildStep, ...]
    auto_commit: bool = True
    auto_push: bool = True
    rollback_on_failure: bool = True
    allow_reuse_noop: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildManifest":
        required = ("schema_version", "build_id", "title", "branch", "baseline", "classification")
        missing = [key for key in required if not str(data.get(key) or "").strip()]
        if missing:
            raise ManifestValidationError(f"manifest missing required fields: {', '.join(missing)}")

        classification = str(data["classification"]).upper()
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ManifestValidationError(f"classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}")

        expected_scope = tuple(str(x).replace("\\", "/") for x in (data.get("expected_scope") or []))
        if classification != "REUSE" and not expected_scope:
            raise ManifestValidationError("non-REUSE manifest requires expected_scope")

        steps = tuple(BuildStep.from_dict(x) for x in (data.get("steps") or []))
        impact_tests = tuple(BuildStep.from_dict({**x, "kind": x.get("kind", "test")}) for x in (data.get("impact_tests") or []))
        smoke_tests = tuple(BuildStep.from_dict({**x, "kind": x.get("kind", "smoke")}) for x in (data.get("smoke_tests") or []))

        if classification != "REUSE" and not steps:
            raise ManifestValidationError("non-REUSE manifest requires at least one build step")

        return cls(
            schema_version=str(data["schema_version"]),
            build_id=str(data["build_id"]),
            title=str(data["title"]),
            branch=str(data["branch"]),
            baseline=str(data["baseline"]).lower(),
            classification=classification,
            commit_message=str(data.get("commit_message") or f"build: {data['build_id']}"),
            expected_scope=expected_scope,
            existing_markers=tuple(str(x).replace("\\", "/") for x in (data.get("existing_markers") or [])),
            required_contracts=tuple(str(x).replace("\\", "/") for x in (data.get("required_contracts") or [])),
            health_checks=tuple(CommandSpec.from_dict(x) for x in (data.get("health_checks") or [])),
            steps=steps,
            impact_tests=impact_tests,
            smoke_tests=smoke_tests,
            auto_commit=bool(data.get("auto_commit", True)),
            auto_push=bool(data.get("auto_push", True)),
            rollback_on_failure=bool(data.get("rollback_on_failure", True)),
            allow_reuse_noop=bool(data.get("allow_reuse_noop", True)),
        )


@dataclass
class CommandResult:
    argv: list[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class RunEvidence:
    build_id: str
    started_at: str
    manifest_classification: str
    observed_classification: str | None = None
    phases: list[dict[str, Any]] = field(default_factory=list)
    repairs: list[dict[str, Any]] = field(default_factory=list)
    final_status: str = "RUNNING"
    final_head: str | None = None
    error: str | None = None

    def add_phase(self, phase: str, status: str, **extra: Any) -> None:
        self.phases.append(
            {
                "phase": phase,
                "status": status,
                "at": datetime.now(timezone.utc).isoformat(),
                **extra,
            }
        )


Executor = Callable[[CommandSpec, Path], CommandResult]


def load_manifest(path: str | Path) -> BuildManifest:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be an object")
    return BuildManifest.from_dict(data)


def _normalize_relpath(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _is_safe_command(command: CommandSpec) -> None:
    joined = " ".join(command.argv).strip().lower()
    for fragment in FORBIDDEN_COMMAND_FRAGMENTS:
        if fragment in joined:
            raise CommandSafetyError(f"forbidden command fragment: {fragment}")
    if command.argv[0].lower() in {"cmd", "cmd.exe"} and any("/c" == x.lower() for x in command.argv[1:]):
        raise CommandSafetyError("cmd /c is not allowed in autonomous build manifests")
    if command.argv[0].lower() in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
        lowered = [x.lower() for x in command.argv[1:]]
        if "-command" in lowered or "-encodedcommand" in lowered:
            raise CommandSafetyError("inline PowerShell command execution is not allowed; use -File")


def _default_executor(command: CommandSpec, repository: Path) -> CommandResult:
    _is_safe_command(command)
    cwd = (repository / command.cwd).resolve()
    try:
        cwd.relative_to(repository.resolve())
    except ValueError as exc:
        raise CommandSafetyError(f"command cwd escapes repository: {cwd}") from exc

    env = os.environ.copy()
    env.update(command.env)
    started = time.monotonic()
    completed = subprocess.run(
        list(command.argv),
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=command.timeout_seconds,
        shell=False,
        check=False,
    )
    return CommandResult(
        argv=list(command.argv),
        cwd=str(cwd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )


def _evidence_root(build_id: str) -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base) / "ProjectPhoenix" / "autonomous_build_orchestrator"
    else:
        root = Path(tempfile.gettempdir()) / "ProjectPhoenix" / "autonomous_build_orchestrator"
    return root / build_id


class AutonomousBuildOrchestrator:
    def __init__(
        self,
        repository: str | Path,
        *,
        executor: Executor | None = None,
        evidence_dir: str | Path | None = None,
    ) -> None:
        self.repository = Path(repository).resolve()
        self.executor = executor or _default_executor
        self.evidence_dir = Path(evidence_dir).resolve() if evidence_dir else None

    def _git(self, *args: str, timeout: int = 120) -> CommandResult:
        return self.executor(
            CommandSpec(("git", *args), ".", timeout),
            self.repository,
        )

    def _git_text(self, *args: str) -> str:
        result = self._git(*args)
        if not result.ok:
            raise BuildOrchestratorError(
                f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}"
            )
        return result.stdout.strip()

    def inspect_capability(self, manifest: BuildManifest) -> dict[str, Any]:
        marker_results = {
            marker: (self.repository / marker).exists()
            for marker in manifest.existing_markers
        }
        contract_results = {
            contract: (self.repository / contract).exists()
            for contract in manifest.required_contracts
        }

        health_results: list[dict[str, Any]] = []
        for command in manifest.health_checks:
            result = self.executor(command, self.repository)
            health_results.append(
                {
                    "argv": result.argv,
                    "ok": result.ok,
                    "returncode": result.returncode,
                }
            )

        all_contracts = bool(contract_results) and all(contract_results.values())
        any_presence = any(marker_results.values()) or any(contract_results.values())
        health_failed = any(not item["ok"] for item in health_results)

        if all_contracts and not health_failed:
            classification = "REUSE"
        elif any_presence and health_failed:
            classification = "REPAIR"
        elif any_presence:
            classification = "EXTEND"
        else:
            classification = "BUILD"

        return {
            "classification": classification,
            "markers": marker_results,
            "contracts": contract_results,
            "health_checks": health_results,
        }

    def preflight(self, manifest: BuildManifest) -> dict[str, str]:
        if not self.repository.is_dir():
            raise BuildOrchestratorError(f"repository not found: {self.repository}")

        branch = self._git_text("branch", "--show-current")
        head = self._git_text("rev-parse", "HEAD").lower()
        remote = self._git_text("rev-parse", f"origin/{manifest.branch}").lower()
        live = self._git_text("ls-remote", "origin", f"refs/heads/{manifest.branch}")
        live_head = live.split()[0].lower() if live.strip() else ""
        status = self._git_text("status", "--porcelain=v1", "--untracked-files=all")

        if branch != manifest.branch:
            raise BuildOrchestratorError(f"wrong branch: {branch}")
        if status.strip():
            raise BuildOrchestratorError("worktree must be clean")
        if head != manifest.baseline:
            raise BuildOrchestratorError(
                f"baseline mismatch: expected {manifest.baseline}, got {head}"
            )
        if remote != head or live_head != head:
            raise BuildOrchestratorError("local/remote/live remote are not synchronized")

        return {
            "branch": branch,
            "head": head,
            "remote": remote,
            "live_remote": live_head,
        }

    def _run_step_with_healing(
        self,
        step: BuildStep,
        evidence: RunEvidence,
    ) -> CommandResult:
        last_result: CommandResult | None = None

        for attempt in range(1, step.max_attempts + 1):
            result = self.executor(step.command, self.repository)
            last_result = result
            evidence.add_phase(
                f"STEP:{step.step_id}",
                "PASS" if result.ok else "FAIL",
                kind=step.kind,
                attempt=attempt,
                returncode=result.returncode,
                elapsed_seconds=result.elapsed_seconds,
            )
            if result.ok:
                return result

            if attempt >= step.max_attempts:
                break

            if not step.repair_actions:
                continue

            for repair_index, repair in enumerate(step.repair_actions, start=1):
                repair_result = self.executor(repair, self.repository)
                evidence.repairs.append(
                    {
                        "step_id": step.step_id,
                        "attempt": attempt,
                        "repair_index": repair_index,
                        "argv": repair_result.argv,
                        "returncode": repair_result.returncode,
                        "ok": repair_result.ok,
                        "elapsed_seconds": repair_result.elapsed_seconds,
                    }
                )
                if not repair_result.ok:
                    raise BuildOrchestratorError(
                        f"repair action failed for {step.step_id}: "
                        f"{(repair_result.stderr or repair_result.stdout).strip()}"
                    )

        assert last_result is not None
        raise BuildOrchestratorError(
            f"step failed after {step.max_attempts} attempt(s): {step.step_id}; "
            f"{(last_result.stderr or last_result.stdout).strip()}"
        )

    def _changed_scope(self) -> list[str]:
        result = self._git("status", "--porcelain=v1", "--untracked-files=all")
        if not result.ok:
            raise BuildOrchestratorError(
                "git status --porcelain=v1 failed: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        # Do not use _git_text() here. Its .strip() is correct for scalar git
        # values but would remove the first porcelain status column when the
        # first line begins with a space, e.g. " M path".
        status = result.stdout
        changed: list[str] = []
        for raw in status.splitlines():
            if len(raw) < 4:
                continue
            path = raw[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.append(_normalize_relpath(path))
        return sorted(set(changed))

    def _assert_exact_scope(self, expected_scope: Sequence[str]) -> None:
        expected = sorted({_normalize_relpath(x) for x in expected_scope})
        actual = self._changed_scope()
        if actual != expected:
            raise BuildOrchestratorError(
                "exact scope mismatch; "
                f"expected={expected!r}; actual={actual!r}"
            )

    def _stage_exact_scope(self, expected_scope: Sequence[str]) -> None:
        for rel in expected_scope:
            result = self._git("add", "--", _normalize_relpath(rel))
            if not result.ok:
                raise BuildOrchestratorError(f"git add failed: {rel}")

        staged_text = self._git_text("diff", "--cached", "--name-only")
        staged = sorted(
            {
                _normalize_relpath(line.strip())
                for line in staged_text.splitlines()
                if line.strip()
            }
        )
        expected = sorted({_normalize_relpath(x) for x in expected_scope})
        if staged != expected:
            raise BuildOrchestratorError(
                f"exact staged scope mismatch; expected={expected!r}; actual={staged!r}"
            )

    def _secret_scan(self) -> None:
        patch = self._git_text("diff", "--cached", "--no-ext-diff", "--unified=0")
        for pattern in SECRET_PATTERNS:
            if pattern.search(patch):
                raise BuildOrchestratorError(
                    f"secret scan failed: pattern {pattern.pattern!r}"
                )

    def _remote_race_guard(self, manifest: BuildManifest) -> None:
        live = self._git_text("ls-remote", "origin", f"refs/heads/{manifest.branch}")
        live_head = live.split()[0].lower() if live.strip() else ""
        if live_head != manifest.baseline:
            raise BuildOrchestratorError(
                f"remote race guard failed: expected {manifest.baseline}, got {live_head}"
            )

    def _rollback(self, manifest: BuildManifest) -> None:
        reset = subprocess.run(
            ["git", "reset", "--hard", manifest.baseline],
            cwd=str(self.repository),
            capture_output=True,
            text=True,
            check=False,
        )
        if reset.returncode != 0:
            raise BuildOrchestratorError(
                f"rollback reset failed: {(reset.stderr or reset.stdout).strip()}"
            )
        for rel in manifest.expected_scope:
            subprocess.run(
                ["git", "clean", "-fd", "--", _normalize_relpath(rel)],
                cwd=str(self.repository),
                capture_output=True,
                text=True,
                check=False,
            )

    def _write_evidence(self, evidence: RunEvidence) -> Path:
        root = self.evidence_dir or _evidence_root(evidence.build_id)
        root.mkdir(parents=True, exist_ok=True)
        target = root / "run_evidence.json"
        target.write_text(
            json.dumps(
                {
                    "build_id": evidence.build_id,
                    "started_at": evidence.started_at,
                    "manifest_classification": evidence.manifest_classification,
                    "observed_classification": evidence.observed_classification,
                    "phases": evidence.phases,
                    "repairs": evidence.repairs,
                    "final_status": evidence.final_status,
                    "final_head": evidence.final_head,
                    "error": evidence.error,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return target

    def run(self, manifest: BuildManifest, *, dry_run: bool = False) -> dict[str, Any]:
        evidence = RunEvidence(
            build_id=manifest.build_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            manifest_classification=manifest.classification,
        )
        committed = False
        pushed = False

        try:
            preflight = self.preflight(manifest)
            evidence.add_phase("PREFLIGHT", "PASS", **preflight)

            inspection = self.inspect_capability(manifest)
            observed = inspection["classification"]
            evidence.observed_classification = observed
            evidence.add_phase(
                "CAPABILITY_RECONCILIATION",
                "PASS",
                observed_classification=observed,
                requested_classification=manifest.classification,
            )

            if observed == "REUSE" and manifest.allow_reuse_noop:
                evidence.final_status = "REUSE_NO_BUILD_REQUIRED"
                evidence.final_head = preflight["head"]
                path = self._write_evidence(evidence)
                return {
                    "status": evidence.final_status,
                    "classification": "REUSE",
                    "head": evidence.final_head,
                    "evidence": str(path),
                }

            if dry_run:
                evidence.final_status = "DRY_RUN_PASS"
                evidence.final_head = preflight["head"]
                evidence.add_phase("DRY_RUN", "PASS")
                path = self._write_evidence(evidence)
                return {
                    "status": evidence.final_status,
                    "classification": observed,
                    "head": evidence.final_head,
                    "evidence": str(path),
                }

            for step in manifest.steps:
                self._run_step_with_healing(step, evidence)

            for step in manifest.impact_tests:
                self._run_step_with_healing(step, evidence)

            for step in manifest.smoke_tests:
                self._run_step_with_healing(step, evidence)

            diff = self._git("diff", "--check")
            if not diff.ok:
                raise BuildOrchestratorError(
                    f"git diff --check failed: {(diff.stderr or diff.stdout).strip()}"
                )
            evidence.add_phase("GIT_DIFF_CHECK", "PASS")

            self._assert_exact_scope(manifest.expected_scope)
            evidence.add_phase("EXACT_SCOPE", "PASS")

            self._stage_exact_scope(manifest.expected_scope)
            evidence.add_phase("EXACT_STAGED_SCOPE", "PASS")

            self._secret_scan()
            evidence.add_phase("SECRET_SCAN", "PASS")

            self._remote_race_guard(manifest)
            evidence.add_phase("REMOTE_RACE_GUARD", "PASS")

            if manifest.auto_commit:
                result = self._git("commit", "-m", manifest.commit_message, timeout=900)
                if not result.ok:
                    raise BuildOrchestratorError(
                        f"git commit failed: {(result.stderr or result.stdout).strip()}"
                    )
                committed = True
                evidence.add_phase("COMMIT", "PASS")

            if manifest.auto_push:
                if not manifest.auto_commit:
                    raise ManifestValidationError("auto_push requires auto_commit")
                result = self._git("push", "origin", f"HEAD:{manifest.branch}", timeout=900)
                if not result.ok:
                    raise BuildOrchestratorError(
                        f"git push failed: {(result.stderr or result.stdout).strip()}"
                    )
                pushed = True
                evidence.add_phase("PUSH", "PASS")

            final_head = self._git_text("rev-parse", "HEAD").lower()
            final_remote = self._git_text("rev-parse", f"origin/{manifest.branch}").lower()
            live = self._git_text("ls-remote", "origin", f"refs/heads/{manifest.branch}")
            final_live = live.split()[0].lower() if live.strip() else ""
            final_status = self._git_text("status", "--porcelain=v1", "--untracked-files=all")

            if manifest.auto_push and not (final_head == final_remote == final_live):
                raise BuildOrchestratorError("final local/remote/live remote mismatch")
            if final_status.strip():
                raise BuildOrchestratorError("final worktree is not clean")

            evidence.final_status = "PASS"
            evidence.final_head = final_head
            evidence.add_phase("FINAL_VERIFICATION", "PASS", head=final_head)
            path = self._write_evidence(evidence)

            return {
                "status": "PASS",
                "classification": observed,
                "head": final_head,
                "repairs_applied": len(evidence.repairs),
                "evidence": str(path),
            }

        except Exception as exc:
            evidence.final_status = "FAILED"
            evidence.error = str(exc)
            evidence.add_phase("FAILURE", "FAIL", error=str(exc))

            if manifest.rollback_on_failure and not pushed:
                try:
                    self._rollback(manifest)
                    evidence.add_phase("ROLLBACK", "PASS")
                except Exception as rollback_exc:
                    evidence.add_phase("ROLLBACK", "FAIL", error=str(rollback_exc))
                    evidence.error = f"{exc}; rollback_error={rollback_exc}"

            path = self._write_evidence(evidence)
            raise BuildOrchestratorError(
                f"{evidence.error}; evidence={path}"
            ) from exc


def manifest_sha256(path: str | Path) -> str:
    source = Path(path)
    return sha256(source.read_bytes()).hexdigest()
