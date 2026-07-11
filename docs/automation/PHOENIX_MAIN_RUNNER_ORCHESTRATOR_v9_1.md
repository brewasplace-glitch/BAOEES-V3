# Project Phoenix Main Runner Orchestrator v9.1

De centrale regisseur voor Phoenix-runners en workflows.

## Functies

- module- en workflowregistry;
- dependency-resolutie;
- detectie van circulaire afhankelijkheden;
- standaard dry-run planning;
- modulebeschikbaarheid;
- expliciete GO-autorisatie voor uitvoering;
- stop bij falende verplichte module;
- runtime-rapportage;
- geen automatische commit of push.

## Zelftest

```powershell
.\runners\PROJECT_PHOENIX_v9_1_main_runner_orchestrator.ps1 -Mode self-test
```

## Plan

```powershell
.\runners\PROJECT_PHOENIX_v9_1_main_runner_orchestrator.ps1 -Mode plan -Workflow platform_foundation
```

## Uitvoering

Alleen na een nieuwe expliciete GO:

```powershell
.\runners\PROJECT_PHOENIX_v9_1_main_runner_orchestrator.ps1 -Mode execute -Workflow platform_foundation -ApprovalToken GO
```
