# PROJECT PHOENIX R9.5.2.2 — Runtime Policy Path Literal Repair Masterpack v1.2

Baseline: `218bcbf2ccbb27d5f73d9273c531b801e83b6534`

## Exact runtime failure

The first live PAT after R9.5.2.2 v1.1 failed in `structural_session_chain.py` with:

`NameError: name 'stability_ab_project_policy_r9_5_2_2' is not defined`

The policy path ended with an unquoted Python name:

`repository/"configs"/"phoenix"/"structural"/stability_ab_project_policy_r9_5_2_2.json`

## v1.2 repair

Both R9.5.2.2 runtime hooks are repaired to:

`repository/"configs"/"phoenix"/"structural"/"stability_ab_project_policy_r9_5_2_2.json"`

The installer requires exactly two malformed occurrences on baseline `218bcbf2ccbb27d5f73d9273c531b801e83b6534`, compiles the fully
repaired chain in memory before touching the worktree, then runs dedicated and impact-scoped tests.

No A+B policy semantics change. R9.5/R9.4/v8.6 gates remain preserved. Professional structural review
remains required. Production release remains `LOCKED`.
