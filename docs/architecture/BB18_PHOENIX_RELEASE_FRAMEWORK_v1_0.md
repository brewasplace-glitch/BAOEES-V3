# BB18 — Phoenix Release Framework v1.0.0

Reusable manifest-driven release planning for PROJECT-PHOENIX.

Each release declares exact artifacts, branch, commit message and validation
gates. Runtime output is classified as `track`, `ignore` or `clean`.
The framework validates safe paths, duplicate artifacts, optional hashes,
deterministic release fingerprints and rollback journals.
