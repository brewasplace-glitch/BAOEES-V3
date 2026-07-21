# Phoenix Recovery Manager (PRM) v1.0.0

PRM safely resumes known interrupted Project Phoenix installations.

## Recovery strategy

1. Enumerate all modified and untracked files individually with
   `git status --porcelain=v1 -uall`.
2. Compare every changed path with an explicit allow-list.
3. Stop without modifying Git history when an unrelated path is present.
4. Reapply the known Wave 15.1 and PRB payloads.
5. Run syntax checks, unit tests and Wave 13/14 regressions.
6. Run `git diff --check`.
7. Stage only declared files.
8. Commit and push only after every validation succeeds.
9. Require an empty final working tree.

PRM does not automatically delete or reset user files.
