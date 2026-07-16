# Project Phoenix Core v23.0 — Deterministic Runtime & Release Finalization

## Kernregel

Alle runtime-rapporten worden geschreven vóór staging, commit en push. Na de commit zijn geen nieuwe runtimewrites toegestaan.

## Functies

- gecontroleerde v22-runtimeherstelcommit;
- deterministische runtime-inventory;
- SHA-256-evidence;
- release-audit;
- expected-files-only-validatie;
- automatische commit en push;
- finale controle op `working tree clean`.

```powershell
.\runners\PROJECT_PHOENIX_v23_0_deterministic_release.ps1 -Mode plan
```
