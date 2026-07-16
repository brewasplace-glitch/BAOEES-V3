# Project Phoenix Core v20.0 — Full Autonomous Project Engine

## Functies

- Planner, Reasoning, Multi-Agent, Execution, Supervisor en Learning samenbrengen;
- vaste stagevolgorde en dependency-gates;
- planmodus als standaard;
- expliciete GO voor echte uitvoering;
- automatische Git-finalisatie na volledig geslaagde installatie en tests;
- stop zonder commit of push bij iedere fout.

## Plan

```powershell
.\runners\PROJECT_PHOENIX_v20_0_full_autonomous_project.ps1 -Mode plan
```

## Echte uitvoering

```powershell
.\runners\PROJECT_PHOENIX_v20_0_full_autonomous_project.ps1 `
  -Mode execute `
  -ApprovalToken GO
```
