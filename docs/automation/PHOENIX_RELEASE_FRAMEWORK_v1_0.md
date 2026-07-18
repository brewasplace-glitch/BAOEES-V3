# Phoenix Release Framework v1.0

## Doel

Het Phoenix Release Framework standaardiseert het testen, valideren,
stagen, committen, pushen en afsluiten van Project Phoenix-releases.

## Runtimebeleid

Elke runtime-map krijgt in het releasemanifest één expliciet beleid:

- `track`: artefacten worden onderdeel van de releasecommit;
- `ignore`: artefacten worden via `.gitignore` uitgesloten;
- `clean`: tijdelijke artefacten worden vóór validatie verwijderd.

## Veiligheidsregels

- branchcontrole;
- staging wordt eerst hersteld;
- vereiste bestanden moeten bestaan;
- validaties en tests moeten volledig slagen;
- alleen manifestpaden mogen gewijzigd of gestaged zijn;
- commit en push vinden pas na volledige PASS plaats;
- iedere release eindigt met `working tree clean`.

## Gebruik

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  ".\runners\PROJECT_PHOENIX_release.ps1" `
  -Manifest ".\configs\release\<manifest>.json" `
  -RunTests
```
