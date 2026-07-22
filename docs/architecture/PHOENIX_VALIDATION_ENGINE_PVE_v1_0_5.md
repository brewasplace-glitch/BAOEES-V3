# Phoenix Validation Engine (PVE) v1.0.5

PVE v1.0.5 is the consolidation recovery release.

It resolves partially staged PVE v1.0.0-v1.0.4 states by validating that only
authorized PVE paths are changed, resetting the index for those paths only,
preserving the working tree, reinstalling the canonical v1.0.5 payload,
removing obsolete PVE metadata, rerunning all tests and regressions, staging
the exact Git-reported paths, then committing and pushing only after success.

Runtime evidence remains local under `outputs/runtime/pve/`.
