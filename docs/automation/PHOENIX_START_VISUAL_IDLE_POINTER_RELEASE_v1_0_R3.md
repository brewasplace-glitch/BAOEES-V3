# PROJECT PHOENIX — STARTSCREEN VISUAL IDLE + POINTER RELEASE v1.0 R3

## Baseline
`project-phoenix` at `91421bda612759da48c1dfeec1bdb7b6704dec83`.

## Problem
After R2, the requested output layout is correct, but a visible refresh still occurs every
few seconds. The same open start page can also behave as if the pointer is trapped.

## Repair
1. The existing official start-screen status poll is changed from the 6-second visual
   heartbeat to a visual-idle interval of 10 minutes. Initial load, user-triggered actions,
   and visibility-driven refresh behavior remain available from the existing shell.
2. A start-shell pointer-release guard exits any unexpected Pointer Lock. Explicit future
   components can opt in with `data-phoenix-allow-pointer-lock="true"`.
3. No `mousemove`, `pointermove`, `MutationObserver`, or continuous timer is added by the guard.
4. DE TV core files are immutable and hash-checked.

This is a repair of the already-authorized start-screen stability build; no new external
runtime dependency is introduced.

Release remains `CONCEPT ONLY / NOT FOR CONSTRUCTION`.
