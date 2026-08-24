# PHOENIX AUTO SYNC — Orchestrator Scope Parser Repair v1.0 R1

The Autonomous Build Orchestrator scope parser now preserves the two porcelain
status columns and separator on the first git status --porcelain=v1 line.

Root cause: _git_text().strip() removed a meaningful leading status-space.
Repair is deliberately local to _changed_scope().

Regression tests cover modified, staged, untracked, rename and multi-line scope.