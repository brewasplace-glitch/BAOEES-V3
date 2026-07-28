# Phoenix Architectural Suite v4.0.2 — Runner import recovery

## Root cause
The unit tests imported the `phoenix` package from the repository root and passed.
The production runner was executed by file path from the `runners` directory.
Python therefore placed `runners` rather than the repository root on `sys.path`,
causing `ModuleNotFoundError: No module named 'phoenix'`.

## Recovery
The runner now derives the repository root from its own location and inserts that
absolute path into `sys.path` before importing Phoenix modules.

A direct-execution regression test now runs the exact production command and
requires successful generation of `05_artifact_manifest.json`.
