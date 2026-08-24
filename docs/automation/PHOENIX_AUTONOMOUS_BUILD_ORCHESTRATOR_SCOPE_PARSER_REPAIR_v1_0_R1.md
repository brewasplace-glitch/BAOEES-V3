# Project Phoenix Autonomous Build Orchestrator Scope Parser Repair v1.0 R1

## Defect

_git_text() returns stdout.strip(). For porcelain-v1 status, the first
character can be a meaningful status-column space. Example:

 M phoenix/file.py

When _changed_scope() consumed _git_text(), the first line became
M phoenix/file.py. The existing aw[3:] then produced hoenix/file.py.

## Repair

Only _changed_scope() now consumes raw CommandResult.stdout from _git().
Scalar git consumers keep the existing _git_text() behavior.

No change to staging, secret scan, remote race guard, rollback, commit or push
semantics.

## Regression coverage

- unstaged modified:  M path
- staged modified: M  path
- untracked: ?? path
- rename destination
- multiple lines with a modified tracked file as the first line