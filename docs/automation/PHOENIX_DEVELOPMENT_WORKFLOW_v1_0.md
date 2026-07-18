# Phoenix Development Workflow v1.0

## Centrale CLI

```powershell
python -m phoenix doctor
python -m phoenix cleanup
python -m phoenix test
python -m phoenix status
python -m phoenix validate-manifest <manifest.json>
```

## Nieuwe ontwikkelstandaard

- productcode staat rechtstreeks in de repository;
- PowerShell-runners blijven dun;
- kleine gerichte broncodewijzigingen;
- Repository Doctor vóór iedere release;
- pre-commit-controles vóór commit;
- GitHub Actions na push en bij pull requests;
- runtime-output gescheiden van broncode;
- releasebewijs in `artifacts/releases/`.

## Veiligheidsbeleid

Cleanup verwijdert uitsluitend Python-cache en `.runtime`.
Onbekende bronbestanden worden nooit automatisch verwijderd.
Commit en push vinden alleen plaats nadat tests volledig slagen.
