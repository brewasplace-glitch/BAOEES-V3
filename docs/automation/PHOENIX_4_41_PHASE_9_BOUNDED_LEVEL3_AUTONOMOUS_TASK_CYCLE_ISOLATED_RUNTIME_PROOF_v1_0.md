# PROJECT PHOENIX 4.41 — Phase 9 v1.0

## Bounded Level-3 Autonomous Task Cycle + Isolated Runtime Proof

Phase 9 connects the existing policy, planner, onboarding, deterministic adapter
synthesis, static validation, gateway, evidence and learning foundations into one
bounded LOW-risk proof cycle.

## Proof chain

`observe -> classify LOW -> open-source review -> plan -> synthesize -> static
verify -> isolated execute -> deterministic replay -> evidence -> learn ->
governed Phase-7 handoff ready`

## Runtime admission

Provider order is:

1. Podman Machine using a rootless connection and an already local,
   digest-bound image.
2. Hardened Windows Sandbox when the Windows component and a mappable Python
   runtime are already available.

Phoenix does not install a provider, enable Windows features, download a runtime
or pull a container image during the cycle. If neither provider passes its exact
probe, candidate execution is denied before repository mutation.

## Hard boundaries

- LOW-risk, read-only synthesized candidates only.
- Phase-7 AST/contract validation remains mandatory.
- Phase-8 deterministic source replay remains mandatory.
- Network access is denied.
- The repository is not mounted into the isolated execution environment.
- The runtime proof writes no repository files and creates no commit or push.
- Two executions must return byte-equivalent structured results.
- Maximum future repair attempts remain three; repeating the same failed patch
  is forbidden.
- MEDIUM escalates; HIGH and CRITICAL are denied.
- Professional approval and for-construction release remain denied.
- Successful proof creates signed evidence and handoff eligibility only.
- Phase-7 approval, verified backup and SHA binding remain required for any
  governed repository activation.
- Automatic engine activation remains forbidden.

## Honest Level-3 boundary

This phase proves autonomous completion of one read-only LOW-risk task. It does
not yet authorize autonomous Phoenix source changes. Future LOW-risk repository
mutation must continue through the existing isolated-worktree, verified-backup,
test, fast-forward and remote-race gates.
