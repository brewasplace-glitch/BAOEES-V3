# Project Phoenix Official Start — DE TV + Presentation Output Viewer v1.0

## Doel

Deze update vervangt het voormalige visuele statusvak rechtsboven in het officiële Phoenix-startscherm
door **DE TV**: een lokale outputviewer voor bestaand Phoenix-projectbewijs en gegenereerde output.

## Functionele wijzigingen

- DE TV rechtsboven in het officiële startscherm.
- Volledig scherm via browser Fullscreen API.
- Vorige / volgende output.
- `AANGEVINKT`: toont bestaande artifacts die corresponderen met de huidige GEWENSTE OUTPUT-selectie.
- `PRESENTATIE`: maakt uitsluitend uit de aangevinkte PRESENTATIE-items een afspeellijst.
- Tekstcommando's zoals `toon plattegronden`, `toon rapporten`, `toon PDF`,
  `toon alle aangevinkte output`, `volgende`, `vorige`, `start presentatie`,
  `stop presentatie` en `volledig scherm`.
- Spraakcommando via Web Speech API (`nl-NL`) wanneer de browser dit ondersteunt.
- Veilige tekstinvoer blijft beschikbaar als fallback.
- Onder `TEKENINGEN / MODELLEN` is een nieuw vinkvak `PDF` aanwezig.
- `GECERTIFICEERD` en `POWERSHELL` zijn op desktop naar links verplaatst.

## Output- en evidencebeleid

DE TV verzint geen resultaat. Alleen bestaande artifacts onder gecontroleerde Phoenix-outputroots
worden geregistreerd. Native browserpreviews zijn beschikbaar voor PDF, afbeeldingen, video, HTML
en tekst/JSON/CSV/log/Markdown. Andere bestanden worden als artifactkaart getoond met een lokale
`OPEN BESTAND`-actie.

## PDF-vinkvak

`drawing_pdf` is een format preference, geen afzonderlijke engineering capability.
De expliciete UI-keuze wordt opgeslagen in `desired_output_ui_selection` en
`output_format_preferences.drawing_pdf`, terwijl capability gating het format-ID niet als aparte
engine-output behandelt.

## Veiligheid

Deze UI-update verandert geen professionele approval, code-compliance claim,
onafhankelijke verificatieclaim, SCIA-gap of releasegate.

Production en FOR-CONSTRUCTION blijven `LOCKED`.
De installer start geen CalculiX, OpenSees of SCIA.

## Versies

- Phoenix Local App: `1.8.8`
- Official Start: `3.1.0`
- DE TV: `1.0.0`


## FIXED R1 — Windows 8.3 path alias + installer recovery

De eerste v1.0-installatie bereikte de dedicated tests maar test 12 en 13 faalden op
Windows tijdelijke paden. Dezelfde fysieke map werd tegelijk gezien als:

- `C:\Users\BREWAS~1\...`
- `C:\Users\brewasplace\...`

`Path.relative_to()` vergelijkt deze paden lexicaal en concludeerde daardoor ten onrechte
dat het artifact buiten de repository lag.

R1 centraliseert alle DE-TV repository-relatieve artifactpaden via `_tv_repo_relative()`
en canonicaliseert zowel repository als artifact eerst met `os.path.realpath()`.
Repository-containment blijft daarna verplicht.

De v1.0-rollback had daarnaast een pathspec-fout doordat `git restore --staged` werd
uitgevoerd op nieuwe, nog untracked DE-TV-bestanden. De R1-installer gebruikt voor nieuwe
bestanden geen onvoorwaardelijke `git restore`. Hij kan exact de bekende v1.0-residuen
herkennen, veilig verwijderen en daarna alleen vanaf een schone baseline installeren.
Andere repositorywijzigingen blijven blokkerend.

Dedicated DE-TV tests in R1: 20.


## FIXED R2 — behoud bestaande Phoenix runtime/startscreen compatibility identity

R1 loste de Windows 8.3/long-path fout op, maar de volledige regressiesuite blokkeerde
omdat meerdere bestaande Phoenix-contracttests en launcher-gates expliciet de actuele
Local App-versie `1.8.7` verwachten. De DE-TV-wijziging vereist geen protocolbreuk en
hoeft die runtime-identiteit niet te verhogen.

R2 behoudt daarom:

- `PhoenixLocalApplication.VERSION = "1.8.7"`
- `PhoenixLocalApplication.START_SCREEN_VERSION = "3.0.2"`
- de zichtbare Official Start-identiteit `3.0.2`

DE TV wordt onafhankelijk geversioneerd als `1.0.2`.

R2 wijzigt geen bestaande legacy-version-gates en voorkomt daarmee dat een UI-feature
onnodig doorwerkt naar launcher-, orchestrator-, cost-, material- en structural-contracten.

De Windows 8.3/long-path canonicalisatie uit R1 blijft behouden.
