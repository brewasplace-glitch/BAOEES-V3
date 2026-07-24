# BB12 — Phoenix QGIS Integration Engine

## Test command

```powershell
python -m unittest tests.qgis.test_phoenix_qgis_integration -v
```

## Self-test command

```powershell
powershell -ExecutionPolicy Bypass -File .\runners\PROJECT_PHOENIX_BB12_qgis.ps1
```

The self-test writes ignored runtime evidence under `outputs/runtime/bb12`.
