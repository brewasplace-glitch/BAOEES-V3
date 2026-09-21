# PROJECT PHOENIX 4.41 — Phase 12 Open-Source Review

Date: 2026-09-20

Primary selection primitive: Python `heapq` (PSF-2.0)
Documentation: https://docs.python.org/3/library/heapq.html

Future transactional fallback: Python `sqlite3` with SQLite
Documentation: https://docs.python.org/3/library/sqlite3.html

Repository transaction: native Git worktrees and fast-forward merge
Documentation: https://git-scm.com/docs/git-worktree

`heapq` is selected because the Phase-12 contract admits one immutable,
committed backlog and exactly one task. A stable tuple of negative priority and
task ID makes the selection deterministic without an external service. SQLite
is retained only as the inspected fallback for a later Level-4 design with
multiple producers and transactional task claims.
