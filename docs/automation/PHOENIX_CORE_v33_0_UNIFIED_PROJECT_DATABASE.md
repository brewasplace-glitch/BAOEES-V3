# Phoenix Core v33.0 — Unified Project Database

## Purpose

BB9 introduces the Phoenix Digital Twin Core Engine and a unified project
database for objects, relationships, persistence, snapshots and audit evidence.

## Core capabilities

- Globally unique Digital Twin objects
- Versioned object updates
- Typed relationships
- Deterministic JSON persistence
- SHA-256 checksums
- Snapshot creation, verification and restore
- Snapshot comparison
- Audit trail for all mutations
- Validation of object references
- Protection against unsafe deletion

## Runtime entry point

```powershell
powershell -ExecutionPolicy Bypass -File .\runners\PROJECT_PHOENIX_v33_0_database.ps1
```

## Test entry point

```powershell
python -m unittest tests.automation.test_phoenix_unified_project_database_v33_0 -v
```
