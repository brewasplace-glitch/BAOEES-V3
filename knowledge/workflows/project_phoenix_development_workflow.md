# Project Phoenix Development Workflow

1. Confirm repository is clean.
2. Install one signed or checksummed Build Block package.
3. Run syntax and compile checks.
4. Run unit tests and self-tests.
5. Run `git diff --check`.
6. Stage only intended, non-ignored files.
7. Commit and push only after every check succeeds.
8. Confirm `nothing to commit, working tree clean`.

At the first failure, automation stops without a new commit or push.
