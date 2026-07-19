# Phoenix Updater v1.1

## Dagelijks gebruik

```powershell
python -m phoenix update
```

Dit commando:

1. selecteert het eerstvolgende pakket uit `updates/incoming`;
2. valideert het manifest en alle SHA-256-checksums;
3. maakt een rollback-backup;
4. past de bestanden toe;
5. draait de tests;
6. commit de gewijzigde bronbestanden;
7. pusht naar de actieve branch;
8. verplaatst het pakket naar `updates/installed`.

Wanneer geen pakket aanwezig is, eindigt de opdracht succesvol zonder wijzigingen.

## Pakketten tonen

```powershell
python -m phoenix update-list
```

## Pakket bouwen

```powershell
python -m phoenix.updater build `
  --id phoenix-example-v1 `
  --version 1.0 `
  --description "Voorbeeldupdate" `
  --file phoenix/example.py `
  --test "python -m compileall -q phoenix" `
  --commit-message "feat: add example"
```
