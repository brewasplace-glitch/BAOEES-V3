# Phoenix Release Manager v2.3 – Sprint 3

Sprint 3 voegt een permanente release- en pakketbouwlaag toe.

## Componenten

```text
phoenix/updater/package_builder.py
phoenix/updater/release_manager.py
phoenix/release/__main__.py
```

## Release maken

Volledige Git-tracked repository:

```powershell
python -m phoenix.release --version 2.3.0
```

Geselecteerde bestanden:

```powershell
python -m phoenix.release `
  --version 2.3.0 `
  --file phoenix/updater/api.py `
  --file phoenix/updater/release_manager.py `
  --changelog "Phoenix Release Manager v2.3"
```

## Output

Releasebestanden worden geschreven naar:

```text
runtime/releases/<naam>/<versie>/
```

Per release worden aangemaakt:

- deterministisch ZIP-archief;
- `manifest.json`;
- `SHA256SUMS.txt`;
- runtime release-rapport.

## Veiligheidsregels

- alleen bestaande bestanden worden verpakt;
- runtimebestanden worden uitgesloten;
- absolute paden en `..` zijn verboden;
- bestandschecksums worden in het manifest opgenomen;
- het releasearchief krijgt een afzonderlijke SHA-256;
- ZIP-timestamps zijn vastgezet voor reproduceerbare output.

## Publieke Python-API

```python
from phoenix.updater.api import ReleaseManager

result = ReleaseManager(repository_root).create_release(
    name="project-phoenix",
    version="2.3.0",
)
```

## Volgende sprint

Sprint 4 bouwt de autonome update-uitvoering:

```text
Check → Validate → Backup → Install → Test → Git Verify → Commit → Push → Clean
```