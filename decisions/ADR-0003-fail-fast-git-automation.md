# ADR-0003 — Fail-fast Git automation

## Status

Accepted.

## Decision

A package may stage, commit and push automatically only after all validations pass.
At the first failure it must stop without a new commit or push.

## Consequences

- Clean, synchronized branches
- Lower risk of committing incomplete Build Blocks
- Installers must distinguish tracked source files from ignored runtime output
