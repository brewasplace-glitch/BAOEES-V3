# BB16 — Building Model Engine v1.0.2

BB16 is the central canonical building model for PROJECT-PHOENIX 2.0.

It provides:
- SI-based levels, spaces, elements and relationships.
- Stable Phoenix IDs and validation.
- Deterministic SHA-256 model fingerprints.
- JSON building-model snapshots.
- Local SketchUp detection and controlled manifest handoff.
- Local SCIA Engineer detection and controlled manifest handoff.

The v1.0.0 stabilization boundary deliberately excludes direct UI automation
and native-model mutation. Those follow after the canonical BB16 contract is stable.

Quality gates: compile, unit tests, self-test, `git diff --check`, commit and push.

## Installer correction v1.0.1

The ignored `outputs/runtime` tree is no longer staged. Runtime output remains generated locally and outside version control.

## Installer correction v1.0.2

The installer derives the exact Git staging list from the payload itself.
It performs a preflight `git check-ignore` on every payload file and stops
before copying files when any payload path is ignored.
