# Project Phoenix Core v19.0 — Autonomous Multi-Agent Orchestrator

## Functies

- agent-registry;
- rol- en capabilitytoewijzing;
- dependency-aware agentplanning;
- persistente message bus;
- status en state tracking;
- dry-run planning;
- expliciete GO voor uitvoering;
- geen automatische commit of push.

## Dry-run

```powershell
.\runners\PROJECT_PHOENIX_v19_0_multi_agent.ps1 -Mode plan
```

## Echte uitvoering

Alleen na expliciete GO:

```powershell
.\runners\PROJECT_PHOENIX_v19_0_multi_agent.ps1 `
  -Mode execute `
  -ApprovalToken GO
```
