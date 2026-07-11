# Project Phoenix Update Center v9.0

## Doel

Phoenix Update Center wordt de vaste en veilige installatiepoort voor toekomstige Project Phoenix-updates.

## Veiligheidsregels

- Een updatepakket wordt eerst buiten de repository uitgepakt.
- `manifest.json` en alle SHA-256-checksums worden gevalideerd.
- Alleen expliciet toegestane doelmappen kunnen worden gewijzigd.
- De working tree moet vóór toepassing clean zijn.
- Werkelijke toepassing vereist `--approval-token GO`.
- Bestaande bestanden worden vooraf geback-upt.
- Python-bestanden worden na installatie gecompileerd.
- `git diff --check` wordt uitgevoerd.
- Commit en push worden nooit automatisch uitgevoerd.

## Zelftest

```powershell
.\runners\PROJECT_PHOENIX_v9_0_update_center.ps1 -Mode self-test
```

## Updatepakket inspecteren

```powershell
.\runners\PROJECT_PHOENIX_v9_0_update_center.ps1 `
  -Mode inspect `
  -Package "C:\pad\naar\PROJECT_PHOENIX_update.zip"
```

## Update toepassen

Alleen na expliciete beoordeling en een nieuwe GO:

```powershell
.\runners\PROJECT_PHOENIX_v9_0_update_center.ps1 `
  -Mode apply `
  -Package "C:\pad\naar\PROJECT_PHOENIX_update.zip" `
  -ApprovalToken GO
```

## Package-formaat

```text
manifest.json
files/
  apps/...
  configs/...
  docs/...
  runners/...
```

Minimaal manifest:

```json
{
  "format_version": "1.0",
  "package_name": "PROJECT_PHOENIX_example",
  "package_version": "v9.1",
  "files": [
    {
      "path": "apps/example.py",
      "sha256": "<sha256>"
    }
  ]
}
```
