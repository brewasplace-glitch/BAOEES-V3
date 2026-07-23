# LL-0001 — Gitignore-safe staging

## Observation

A BB9 installer attempted to stage a runtime output path ignored by Git.
The engineering code and tests passed, but the installer stopped at `git add`.

## Permanent lesson

Installers must never assume every generated path is trackable.

## Required control

- Test candidate paths with `git check-ignore`.
- Stage only intended and non-ignored paths.
- Keep runtime output outside source-control commits unless explicitly required.
