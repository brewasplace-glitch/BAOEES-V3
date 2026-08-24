# Project Phoenix Autonomous Build Orchestrator + Self-Healing Build Loop v1.0

## Status

Capability: `PHX.AUTONOMOUS_BUILD_ORCHESTRATOR_SELF_HEALING`

Classification: **EXTEND**

Phoenix already had strong individual build-governance mechanisms: clean-worktree
preflight, baseline locks, reuse gates, tests, exact-scope checks, secret scans,
BIB precommit synchronization, rollback patterns, remote race guards and
commit/push verification. What was missing was one reusable coordinator that
executes these mechanisms as one stateful build lifecycle.

## Open-source-first assessment

### Primary candidate — Prefect

License: Apache-2.0.

Strengths: mature Python workflow orchestration, retries, state handling,
scheduling and observability.

Decision for v1.0: evaluated but **not made a mandatory dependency**. Phoenix's
build lifecycle is strongly git/repository-specific and already owns exact-scope,
BIB, rollback and release-governance behavior. A Prefect dependency would add a
large runtime surface without replacing those Phoenix-specific controls.

### Fallback candidate — Dagster

License: Apache-2.0.

Strengths: mature orchestration, observability, lineage and multi-tool execution.

Decision for v1.0: evaluated but **not made a mandatory dependency** for the same
reason. Dagster remains a suitable future backend if Phoenix later needs
distributed workers or cross-machine orchestration.

### v1.0 implementation decision

Use Python standard library plus existing Phoenix governance capabilities. This
keeps installation deterministic and makes the later Autonomous Development
Queue independent of a third-party scheduler.

## Lifecycle

`DISCOVER -> CLASSIFY -> PREFLIGHT -> EXECUTE -> HEAL -> VERIFY -> SCOPE ->
STAGE -> SECRET_SCAN -> REMOTE_RACE_GUARD -> COMMIT -> PUSH -> FINAL`

## Deterministic self-healing

A build step may declare:

- `max_attempts`;
- one or more `repair_actions`.

When the main command fails, Phoenix may execute the declared repair actions and
retry the same step. No undeclared command is invented or executed.

This is intentionally different from unconstrained autonomous code mutation.
Arbitrary repair code generation is outside this v1.0 engine.

## Safety

Manifest commands are argument arrays and execute with `shell=False`.

The orchestrator blocks high-risk commands such as force-push and destructive
git reset/clean commands inside build manifests. Inline PowerShell `-Command` is
also blocked; repository-contained `.ps1` files must be used.

Before commit:

- `git diff --check`;
- exact worktree scope;
- exact staged scope;
- secret scan;
- live remote race guard.

Before push failures, rollback returns the repository to the locked baseline and
cleans only the declared expected scope.

Professional engineering approval, legal/code approval, construction release
and production-release claims remain outside this automation.

## Runtime evidence

Each run writes a JSON evidence record outside the repository, normally under:

`%LOCALAPPDATA%\ProjectPhoenix\autonomous_build_orchestrator\<BUILD_ID>\run_evidence.json`

This avoids contaminating the git worktree.

## Future Autonomous Development Queue

The future queue should output one validated
`phoenix.autonomous-build-manifest/1.0` item per development task.

The queue will own prioritization/strategy. This orchestrator will own execution,
deterministic recovery, verification and git finalization.

That means the queue can later drive:

`QUEUE ITEM -> BUILD MANIFEST -> ORCHESTRATOR -> PASS/REUSE/BLOCKED -> NEXT ITEM`

without duplicating build safety logic.
