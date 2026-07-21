# Phoenix Release Builder (PRB) v1.0.0

PRB is the deterministic release packaging engine for Project Phoenix.

## Core behavior

PRB reads an explicit JSON manifest, validates every path, copies only declared
files, generates SHA-256 evidence, creates a deterministic ZIP archive and
writes a machine-readable release manifest.

## Safety rules

- No implicit file discovery.
- No parent-directory traversal.
- Missing files stop the build.
- Build errors stop before Git actions.
- Installation commits and pushes only after syntax checks, unit tests,
  regression tests and `git diff --check` succeed.

## Current recovery behavior

The installer recognizes the known interrupted Wave 15.1 installation state.
It permits only the expected Wave 15.1 changed files. Any unrelated change
still stops installation.

## Usage

Create a release manifest based on:

`configs/phoenix/release_manifest_example_v1_0.json`

Run:

`runners/PROJECT_PHOENIX_release_builder.ps1`

PRB creates:

- `<release>_v<version>.zip`
- `<release>_v<version>.manifest.json`
- `<release>_v<version>.sha256`
