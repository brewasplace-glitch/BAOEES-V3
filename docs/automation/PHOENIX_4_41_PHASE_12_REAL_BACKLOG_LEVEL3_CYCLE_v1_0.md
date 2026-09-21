# PROJECT PHOENIX 4.41 — Phase 12 v1.0

## Real Backlog-Driven Level-3 Autonomous Task Cycle

Phase 12 converts the bounded Level-3 proofs into one operational repository
task. Phoenix deterministically chooses exactly one eligible LOW-risk task from
the committed backlog, obtains a Phase-11 specialized-agent review, constructs
the change in an external Phase-10 worktree, runs the full regression suite,
verifies deterministic patch replay, and promotes only a Lane-A
non-executable change through the existing backup-gated fast-forward promoter.

Hard boundaries:

- exactly one task per invocation;
- LOW-risk non-executable documentation/evidence only;
- output restricted to `docs/automation/autonomous_generated/`;
- exact clean local/remote baseline and verified backup required;
- accepted isolation boundary and deterministic multi-agent review required;
- full regression before the candidate commit;
- exactly one direct candidate commit;
- remote race guard, fast-forward-only merge and normal non-force push;
- signed selection and completion receipts;
- source, dependency, policy, registry and engine-activation changes denied.

The first operational backlog task publishes a baseline-bound capability report
at `docs/automation/autonomous_generated/phase12-level3-operational-capability.md`.
Its content is deterministic and its completion creates the second, autonomous
commit of the Phase-12 launcher run.
