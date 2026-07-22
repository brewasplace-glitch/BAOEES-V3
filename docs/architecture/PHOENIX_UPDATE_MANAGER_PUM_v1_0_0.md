# Phoenix Update Manager (PUM) v1.0.0

PUM is the central manifest-driven update orchestrator for Project Phoenix.

It separates installation, validation, commit and push state. A transient push
failure leaves a valid local commit with `push_pending=true`; only the push must
be retried. Runtime state remains under `outputs/runtime/pum/` and is not committed.

Future updates must require a clean worktree, install only declared paths, run
syntax checks, tests, PVE and `git diff --check`, then commit and push.
