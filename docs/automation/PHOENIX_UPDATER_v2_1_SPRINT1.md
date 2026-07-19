# Phoenix Updater v2.1 – Sprint 1

Sprint 1 integreert drie permanente updatercomponenten.

## Package Discovery

Module:

```text
phoenix/updater/package_discovery.py
```

Updatepakketten worden uitsluitend gezocht in:

```text
updates/incoming/
```

Ondersteunde extensies:

- `.zip`
- `.phx`
- `.json`

## Runtime Reports

Module:

```text
phoenix/updater/report_writer.py
```

Updater-rapporten worden als JSON geschreven naar:

```text
runtime_reports/updater/
```

Deze locatie valt onder de Repository Runtime Policy.

## Rollback Manager

Module:

```text
phoenix/updater/rollback_manager.py
```

Rollback-snapshots worden geschreven naar:

```text
runtime/rollback/<snapshot-id>/
```

Iedere snapshot bevat:

- kopieën van bestaande bestanden;
- registratie van ontbrekende bestanden;
- SHA-256 per back-upbestand;
- `rollback_manifest.json`.

## Volgende sprint

Sprint 2 koppelt deze componenten aan de centrale Updater Engine en maakt één
geïntegreerde update-uitvoering mogelijk.