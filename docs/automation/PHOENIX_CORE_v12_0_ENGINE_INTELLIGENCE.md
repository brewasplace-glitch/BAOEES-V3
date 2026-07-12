# Project Phoenix Core v12.0 â€” Engine Intelligence

## Onderdelen

- Engine Discovery Service
- Capability Registry
- Intelligent Module Selection

## Zelftest

```powershell
.\runners\PROJECT_PHOENIX_v12_0_engine_intelligence.ps1 -Mode self-test
```

## Discovery

```powershell
.\runners\PROJECT_PHOENIX_v12_0_engine_intelligence.ps1 -Mode discover
```

## Registry-validatie

```powershell
.\runners\PROJECT_PHOENIX_v12_0_engine_intelligence.ps1 -Mode validate-registry
```

## Dry-run module-selectie

```powershell
.\runners\PROJECT_PHOENIX_v12_0_engine_intelligence.ps1 `
  -Mode select `
  -Capability @("workflow.orchestration","engine.discovery","capability.registry")
```

v12.0 voert geen geselecteerde engine automatisch uit.
