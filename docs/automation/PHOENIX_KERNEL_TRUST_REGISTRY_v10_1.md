# Project Phoenix v10.1 — Kernel Trust & Registry Update

## Doel

v10.1 registreert Phoenix Kernel v10.0 formeel binnen de Main Runner Orchestrator.

## Wijzigingen

- `phoenix_kernel.py` toegevoegd aan de vertrouwde untracked paden;
- `kernel_self_test` toegevoegd aan de Main Runner Registry;
- `platform_foundation` uitgebreid met Kernel Self-Test;
- registry- en policyversie verhoogd naar v10.1;
- geen automatische commit of push.

## Controle

```powershell
.\runners\PROJECT_PHOENIX_v9_1_main_runner_orchestrator.ps1 `
  -Mode plan `
  -Workflow platform_foundation
```

Werkelijke uitvoering blijft alleen toegestaan na expliciete GO.
