# ADR-0002 — External PowerShell as command standard

## Status

Accepted.

## Decision

Repository commands and installers run in external Windows PowerShell.
GitKraken is used for graph and history inspection.

## Consequences

- Reproducible command execution
- Clear separation between graphical inspection and automation
- Fewer terminal-context errors
