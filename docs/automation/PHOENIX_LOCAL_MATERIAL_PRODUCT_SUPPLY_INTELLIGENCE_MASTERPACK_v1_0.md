# Phoenix Local Material, Product & Supply Intelligence Masterpack v1.0

## Doel

Project Phoenix gebruikt lokale materiaal- en productbeschikbaarheid voortaan
als een expliciete ontwerp-, engineering-, kosten-, planning- en releasevoorwaarde.

De voorkeursvolgorde is:

`PROJECTLOCATIE -> STAD -> REGIO -> LAND -> REGIONALE IMPORT -> INTERNATIONALE IMPORT`

Alleen **STAD / REGIO / LAND** telt standaard als lokaal.

## Harde regel

Een definitief gebouw, constructie of infra-object mag niet als release-ready
worden beschouwd wanneer vereiste materialen/producten niet aantoonbaar lokaal
verkrijgbaar zijn.

Conceptgeometrie mag wel worden gegenereerd met generieke materiaalfamilies,
maar die blijven kandidaten totdat de Local Material Supply Gate is geslaagd.

## Beschikbaarheidsstatussen

- `LOCAL_AVAILABILITY_CONFIRMED`
- `LOCAL_AVAILABILITY_PROBABLE`
- `REGIONAL_IMPORT_REQUIRED`
- `INTERNATIONAL_IMPORT_REQUIRED`
- `AVAILABILITY_UNKNOWN`
- `UNAVAILABLE`

Alleen `LOCAL_AVAILABILITY_CONFIRMED` telt zonder aanvullende goedkeuring als
voldoende voor de lokale-materialengate.

## Bron- en actualiteitsregels

Een lokale bevestiging vereist minimaal:
- projectgeografie;
- leverancier/bron;
- product;
- materiaalcategorie;
- beschikbaarheidsstatus;
- verificatiedatum;
- geldige actualiteit;
- voor constructieve producten: `engineering_material_id` en technische eigenschappen.

Stale voorraad-/beschikbaarheidsevidence is geen bevestiging.

## Constructieve koppeling

De v8.x-keten mag v8.0/v8.1 als geometrische conceptfasen doorlopen.
Voor solvermateriaalgebruik in v8.3 geldt vervolgens:
1. alle constructieve materiaalvereisten moeten lokaal bevestigd zijn;
2. solver `material_id` moet voorkomen in de lokaal geselecteerde
   `engineering_material_id`-set.

Zo kan Phoenix geen theoretisch materiaal/staalprofiel berekenen dat niet aan
de lokale productselectie gekoppeld is.

## Productsubstitutie

Een vervanging is nooit een naamwissel. Elke substitutie activeert:
- Digital Twin-update;
- structurele herberekening indien constructief;
- kostencalculatie opnieuw;
- planning opnieuw indien levertijd verandert;
- tekeningen/bestek bijwerken;
- QA/QC opnieuw;
- menselijke review.

Automatische stille substitutie is uitgeschakeld.

## Kosten & planning

Supplier unit price en lead time worden in het productregister vastgelegd als
evidence. De bestaande **Local Cost Intelligence** blijft de formele actuele
kostenmarkt-gate; een supplier price alleen vervangt die gate niet.

## Prijs-/productbronnen

Phoenix scant standaard:
- `inputs/material_supply/**/*.json`
- `data/material_supply/**/*.json`
- `configs/phoenix/material_supply_catalog/**/*.json`

Autoritatieve HTTPS supplier/distributor feeds kunnen expliciet worden
geregistreerd. Deze masterpack levert bewust geen verzonnen leverancier of
live-stock API mee.

## Release

QA/QC / Release Control controleert de materiaal-supply gate. Wanneer niet alle
vereiste materialen lokaal bevestigd zijn blijft productievrijgave `LOCKED`.

## FIXED R1 — Cost Planning regression contract

The first v1.0 installation reached the full Phoenix regression suite and
stopped on one older Project Context/Cost regression.

That regression correctly checked the Local Cost Intelligence rule first:
current local price evidence is required. It then still expected Cost Planning
to pass immediately after price evidence was added.

After this masterpack that expectation is obsolete. Cost Planning now has two
independent evidence gates:

1. current local market **price evidence**;
2. current local **material/product availability evidence** for the actual
   project material requirements.

FIXED R1 changes no production behavior. It updates the regression so that
price evidence without local material supply evidence remains `BLOCKED_INPUT`,
and it passes only after a current locally confirmed supplier catalog covers
all required material families.

Automatic product substitution remains disabled and production release remains
`LOCKED`.
