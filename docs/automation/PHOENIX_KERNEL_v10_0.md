# Project Phoenix Kernel v10.0

## Doel

De Phoenix Kernel is de centrale startlaag van PROJECT-PHOENIX.

## Startcommando

```powershell
.\runners\START_PROJECT_PHOENIX_v10_0.ps1 -Mode plan -Workflow platform_foundation
```

## Status

```powershell
.\runners\START_PROJECT_PHOENIX_v10_0.ps1 -Mode status
```

## Zelftest

```powershell
.\runners\START_PROJECT_PHOENIX_v10_0.ps1 -Mode self-test
```

## Werkelijke uitvoering

Alleen na een afzonderlijke expliciete GO:

```powershell
.\runners\START_PROJECT_PHOENIX_v10_0.ps1 `
  -Mode execute `
  -Workflow platform_foundation `
  -ApprovalToken GO
```

## Veiligheidsregels

- standaard planmodus;
- geen automatische commit;
- geen automatische push;
- workflowuitvoering via Main Runner Orchestrator;
- runtime-rapportage bij elke start.
