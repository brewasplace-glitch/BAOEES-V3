# Phoenix PDK Test Discovery v1.0a

## Probleem

Het commando:

```powershell
python -m unittest discover -s tests -p "test*.py"
```

vond in de bestaande repositorystructuur geen tests en eindigde met:

```text
Ran 0 tests
NO TESTS RAN
```

De afzonderlijke testsuites onder `tests/updater` en `tests/pdk` werden wel
correct ontdekt.

## Oplossing

`python -m pdk test` voert voortaan expliciet beide suites uit:

```text
tests/updater
tests/pdk
```

De opdracht slaagt alleen wanneer beide suites exitcode 0 teruggeven.

## Resultaat

De PDK-testpipeline is onafhankelijk van impliciete recursive discovery en
werkt betrouwbaar met de huidige PROJECT-PHOENIX teststructuur.