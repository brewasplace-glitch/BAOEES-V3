# Phoenix Updater v1.0

## Doel

De Phoenix Updater past toekomstige broncode-updates lokaal en controleerbaar toe.

## Updatepakket

Plaats iedere update als map in:

`updates/incoming/<update-id>/`

De map bevat:

- `manifest.json`;
- de bronbestanden waarnaar het manifest verwijst.

## Manifestvelden

- `update_id`
- `version`
- `description`
- `files`
- `test_commands`
- `commit_message`
- `auto_push`

Iedere bestandsvermelding bevat:

- `source`
- `target`
- `sha256`

## Gebruik

```powershell
python -m phoenix.updater list
python -m phoenix.updater inspect updates/incoming/<update-id>
python -m phoenix.updater apply updates/incoming/<update-id>
python -m phoenix.updater apply updates/incoming/<update-id> --commit --push
```

## Veiligheid

- vereist een schone working tree;
- controleert SHA-256-checksums;
- blokkeert absolute paden en `..`;
- maakt vóór iedere update een rollback-backup;
- draait manifesttests;
- herstelt gewijzigde bestanden wanneer een test faalt;
- commit en push zijn expliciete opties.
