# Phoenix Updater v2.0 – Repository Runtime Policy

## Doel

De Repository Runtime Policy maakt een expliciet onderscheid tussen:

- broncode;
- documentatie;
- tests;
- configuratie;
- bewust gevolgde release-artifacts;
- gegenereerde runtimegegevens.

Hierdoor kan Phoenix gegenereerde gegevens gebruiken zonder dat de Git working
tree onbedoeld vervuild raakt.

## Python-module

```text
phoenix/updater/runtime_policy.py
```

De module bevat:

- `PathClass`;
- `RuntimePolicy`;
- `DEFAULT_RUNTIME_POLICY`;
- `classify_path()`.

## Runtimepaden

De standaard runtimepaden zijn:

```text
updates/
runtime/
runtime_reports/
.phoenix/runtime/
artifacts/runtime/
```

Deze paden zijn niet bedoeld als permanente bronbestanden.

## Gebruik

```python
from phoenix.updater.runtime_policy import DEFAULT_RUNTIME_POLICY

classification = DEFAULT_RUNTIME_POLICY.classify(
    "runtime_reports/update-result.json"
)
```

## Integratiepad

Deze fase legt de beleidslaag vast. De volgende fase koppelt dit beleid aan:

- updater package discovery;
- updater reports;
- rollback;
- repository verification;
- Git-clean checks.