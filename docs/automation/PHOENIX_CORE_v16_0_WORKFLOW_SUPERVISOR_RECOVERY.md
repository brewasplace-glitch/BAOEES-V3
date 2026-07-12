# Project Phoenix Core v16.0 â€” Workflow Supervisor & Recovery Manager

Functies:

- workflowstatus inspecteren;
- runtime health controleren;
- incidenten registreren;
- recoverystrategie bepalen;
- checkpoints herkennen;
- gecontroleerd hervatten via v15;
- expliciete GO-autorisatie;
- geen automatische commit of push.

```powershell
.\runners\PROJECT_PHOENIX_v16_0_supervisor.ps1 -Mode recovery-plan
```

Echte herstelactie vereist opnieuw expliciete GO:

```powershell
.\runners\PROJECT_PHOENIX_v16_0_supervisor.ps1 -Mode recover -ApprovalToken GO
```
