# PROJECT PHOENIX BIB AUTO-SYNC + KNOWLEDGE INGESTION v1.0

Baseline before installation: `e98d5ef688010789898a0e47e5451efd134779e5`.

## Goal
Make the Phoenix BIB current immediately through a full backfill and keep it current automatically before every future commit.

## Open-source-first assessment
Primary: SQLite FTS5, integrated through Python `sqlite3`. SQLite is public domain and FTS5 is its built-in full-text-search module.
Operational fallback: `git grep` over the tracked plaintext JSONL BIB store. Git is GPL-2.0 and is already a required Phoenix tool.
Alternative evaluated: Tantivy/tantivy-py, MIT and actively maintained in 2026. It is not added as a hard dependency because Phoenix does not need another Rust/Python binary dependency at the present repository scale.

## Architecture
`authoritative repository knowledge -> Git index snapshot -> BIB manifest/fingerprints -> tracked JSONL knowledge store -> local SQLite FTS5 index`

The pre-commit hook indexes the Git **index**, not arbitrary unstaged worktree edits. Therefore the BIB corresponds to what will actually be committed.

Full text is stored for docs, configs and existing BIB/knowledge roots. Source code, runners and tests are fingerprinted by Git object id without duplicating the whole codebase. Runtime-heavy generated directories are excluded. High-signal secrets are redacted before searchable BIB content is written.

Managed root: `BIB/PHOENIX_AUTO_SYNC`.

## Required gates
- `BIB_FULL_BACKFILL=PASS`
- `BIB_CURRENT_BASELINE=PASS`
- `BIB_KNOWLEDGE_INDEX=PASS`
- `BIB_AUTO_SYNC=ENABLED`
- `BIB_UP_TO_DATE=YES`

A tracked BIB cannot embed the hash of the same commit that contains it without circularity. Currentness is therefore validated by a deterministic source digest against the actual Git index/HEAD snapshot.

## Installer repair R1
The initial v1.0 installer stopped safely before commit because the unittest helper
was named `run()`, unintentionally overriding `unittest.TestCase.run(result)`.
R1 renames that helper to `invoke_engine()` and adds an installer guard that forbids
overriding `TestCase.run`. The BIB engine, indexing architecture, hook model,
source-digest model, release gates, and open-source choices are unchanged.

## Installer repair R2 — exact Git path preservation
R1 reached the real initial full backfill and exposed a path-normalization defect:
`normalize()` used `lstrip("./")`. Python's `str.lstrip()` treats the argument as a
set of characters, so `.pre-commit-config.yaml` became `pre-commit-config.yaml`.

R2 replaces this with literal `./` prefix removal only. Root dotfiles and dotdirectories
therefore preserve their exact Git identity, including `.pre-commit-config.yaml`,
`.gitattributes`, `.gitignore`, `.githooks/...`, and `.github/...`.

Regression tests now stage both `.pre-commit-config.yaml` and `.github/workflows/ci.yml`
and require those exact paths to appear in the BIB manifest.

## Installer repair R3 — secret-scan-safe test fixture
R2 completed the real full backfill, BIB index validation and all mandatory BIB gates,
then correctly stopped at the staged-diff secret scan. The blocking match came from the
unit test itself, which stored a synthetic AWS access-key-shaped string literally.

R3 keeps the secret scan strict and changes only the test fixture: the synthetic value is
constructed from separate string fragments at runtime. The redaction engine still receives
the same secret-shaped value in the temporary test repository, but tracked Phoenix source
contains no literal credential-shaped token.

An additional regression asserts that the tracked BIB test source contains no literal
`AKIA` + 16 uppercase/digit key shape.
