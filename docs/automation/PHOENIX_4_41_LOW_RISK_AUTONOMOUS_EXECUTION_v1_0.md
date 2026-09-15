# PROJECT PHOENIX 4.41 — LOW-RISK AUTONOMOUS EXECUTION v1.0

Baseline: `f17e9dcb055487ce7d4edbc08e513ad4cd6896d4`

V1.0 enables autonomous execution only for tasks classified LOW and only inside an isolated linked Git worktree. The executor creates a temporary candidate branch and candidate commit. The main `project-phoenix` branch is not merged, cherry-picked, reset or autonomously modified by this executor.

Allowed roots are `docs/automation/autonomous_generated/` and `outputs/runtime/autonomy/`, with only Markdown, text and JSON files. Source code, runners, configs, tests, BIB, `.git` and GitHub workflow files are outside the LOW-risk surface.

Hard gates include branch/head/origin validation, LOW risk classification, exact path allowlist, content screening, isolated worktree, exact candidate scope, `git diff --check`, JSON validation, candidate commit, remote-race guard and cleanup evidence.

Open-source-first: native Git `worktree` is primary; GitPython is fallback; Dulwich remains the alternate Python Git implementation fallback.

`LOW_RISK_AUTO=ENABLED_CANDIDATE_BRANCH_ONLY`

`LOW_RISK_MAINLINE_PROMOTION=LOCKED`

## FIX R3 — Windows PowerShell UTF-8 BOM compatibility

Windows PowerShell 5.1 may write `Set-Content -Encoding UTF8` files with a BOM.
The LOW-risk request loader now uses `utf-8-sig`, accepting both BOM and
BOM-less UTF-8. The installer probe also writes UTF-8 explicitly without BOM.
Regression tests cover both forms.

## FIX R4 — Windows long-path-safe linked worktrees

The R3 real probe reached `git worktree add` but existing long tracked filenames exceeded the effective Windows path length under the previous nested runtime root.

FIX R4 uses `%LOCALAPPDATA%\PXW\<execution-id>` for linked worktrees and runs Git with per-call `-c core.longpaths=true`. Global and repository Git config are not changed. Failed LOW-risk probe worktrees/branches may be removed only when they are under known PHOENIX autonomy roots and still point exactly to the expected baseline. Mainline autonomous promotion remains locked.
