# Project Phoenix Core v21.0 — Autonomous Release & Git Finalization Engine

## Functies

- repository-audit;
- staged- en untracked-bestandscontrole;
- `git diff --check`;
- releaseplan in dry-run;
- expected-files-only-validatie;
- automatische commit en push na succesvolle tests;
- eindcontrole op `working tree clean`.

## Gebruik

```powershell
.\runners\PROJECT_PHOENIX_v21_0_release_finalize.ps1 -Mode self-test
.\runners\PROJECT_PHOENIX_v21_0_release_finalize.ps1 -Mode audit
.\runners\PROJECT_PHOENIX_v21_0_release_finalize.ps1 -Mode plan
```
