# Project Phoenix Material Engineering Continuation v1.1

## Doel
Phoenix voltooit ontwerpengineering ook wanneer materiaalcertificatie of materiaalbeschikbaarheid nog niet volledig is opgelost, zonder eigenschappen, beschikbaarheid of prijzen te fabriceren.

## Dashboard
- `GECERTIFICEERD` standaard aan: strikte certificatie voor daadwerkelijk geselecteerde beschikbare producten.
- uit: beschikbare ongecertificeerde producten mogen worden doorgerekend met de vereiste ontwerp-/sterkteklasse als expliciete niet-productgeverifieerde aanname.
- `↩ POWERSHELL`: activeert de geregistreerde Phoenix-console; fallback opent een nieuwe PowerShell in de repository.

## Onbekende of ontbrekende beschikbaarheid
1. Beschikbaarheid blokkeert ontwerpengineering niet.
2. Phoenix zoekt eerst in verworven project-evidence naar een beschikbaar alternatief uit dezelfde materiaalfamilie.
3. In gecertificeerde modus wordt alleen een gekwalificeerd/certified alternatief automatisch geselecteerd.
4. In ongecertificeerde modus mag een beschikbaar alternatief met expliciete ontwerpklasse-aanname worden geselecteerd.
5. Elke substitutie triggert herberekening/QA-QC.
6. Als geen alternatief aantoonbaar beschikbaar is, blijft het voorgeschreven materiaal als design placeholder in het ontwerp en de constructieberekening staan.
7. Deze materialen komen in `unavailable_materials_register.json/.csv` met status procurement unresolved.
8. Phoenix verzint geen prijs. De kostenraming blijft draaien; ontbrekende actuele prijzen worden expliciet als onopgelost gemarkeerd.
9. Procurement/for-construction/production release blijft LOCKED zolang materiaalbeschikbaarheid of materiaalverificatie niet is opgelost.

## Registers
- uncertified_materials_register.json/.csv
- material_availability_resolution_register.json
- unavailable_materials_register.json/.csv
- available_alternative_materials_register.json/.csv

## Veiligheid
Engineering continuation is geen bewijs dat een product leverbaar is of de aangenomen eigenschappen bezit. Professionele/material verification blijft vereist vóór uitvoering.


## FIXED R3 packaging/staging correction
The console-return bridge is source code and is stored under `phoenix/local_app/console_return_bridge.py`, not the repository-ignored `phoenix/runtime/` tree. The installer verifies new source paths are not ignored before installation and only restores v34 graph fixtures when tracked.


## FIXED R4 test-artifact cleanup correction
- Full regression tests may generate v34 graph artifacts under `outputs/graph/v34_0` as well as `outputs/runtime/v34_0`.
- The installer now restores tracked fixtures and removes only Git-untracked files within those two exact test-artifact roots before scope validation.
- No unrelated project/runtime files are deleted.
