# Project Phoenix Core v15.0 — Autonomous Execution Engine

Functies:

- validated plan loader;
- execution queue;
- dependency gates;
- dry-run;
- checkpoints;
- resume;
- runtime events;
- execution evidence;
- expliciete GO-autorisatie;
- geen automatische commit of push.

```powershell
.\runners\PROJECT_PHOENIX_v15_0_autonomous_execution.ps1 -Mode dry-run
```

Echte uitvoering vereist opnieuw expliciete GO:

```powershell
.\runners\PROJECT_PHOENIX_v15_0_autonomous_execution.ps1 -Mode execute -ApprovalToken GO
```
