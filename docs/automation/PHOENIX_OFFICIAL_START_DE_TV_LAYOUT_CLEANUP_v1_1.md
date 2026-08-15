# Project Phoenix Official Start — DE TV Layout Cleanup v1.1

## Doel

Deze update ruimt het officiële Phoenix-startscherm op zonder de bestaande DE-TV,
runtime-, solver- of releasefunctionaliteit te wijzigen.

## Wijzigingen

### GECERTIFICEERD + POWERSHELL

De materiaalmodus en PowerShell-knop zijn niet langer als `position:fixed` boven
andere schermdelen geplaatst. Er is nu een normale in-flow actiezone in het
projecttype-paneel. Op desktop beslaat die zone de kolommen boven **CIVIEL** en **INFRA**.

### Geen overlappende subschermen / tekstvakken

De belangrijkste grids gebruiken `minmax(0,1fr)` en hun kinderen krijgen een expliciete
`min-width:0`. Lange sectiekoppen kunnen afbreken en badges hebben geen kunstmatige vaste
breedte meer. Form controls zijn begrensd op 100% van hun ouderpaneel.

De DE-TV-bedieningsknoppen gebruiken op desktop maximaal drie kolommen per rij en kunnen
tekst afbreken, zodat de rechterkolom niet meer dichtloopt.

### PHOENIX MODULES

`PHOENIX MODULES` is verplaatst naar de onderzijde van de rechterkolom, na het
projectenblok. De modulelijst staat in een `<details>`-paneel en is standaard **ingeklapt**.
De bestaande `moduleGrid`-ID blijft behouden zodat de bestaande frontend de modules nog
steeds dynamisch kan vullen.

## Compatibiliteit

- Phoenix Local App: `1.8.7`
- Official Start: `3.0.2`
- DE TV: `1.0.2`
- Layout Cleanup: `1.1.0`

De bestaande versie-gates worden niet gewijzigd.

## Veiligheid

- geen live solveruitvoering tijdens installatie;
- geen verandering aan professionele approval;
- geen automatische code-compliance claim;
- Production blijft `LOCKED`;
- FOR-CONSTRUCTION blijft `LOCKED`.


## FIXED R1 — regressiecontractmigratie

De eerste v1.1-installatie passeerde alle 20 dedicated layout-tests, maar de volledige
regressiesuite bevatte nog een oudere DE-TV-test die expliciet de voorgaande vaste CSS-positie
`left:238px;right:auto` verwachtte.

Dat contract is nu onjuist omdat de geldige nieuwe layout juist vereist dat
`GECERTIFICEERD` en `POWERSHELL` **niet fixed** zijn, maar in de normale projecttype-flow
boven `CIVIEL` en `INFRA` staan.

R1 wijzigt daarom alleen dit historische testcontract. De v1.1 UI-layout zelf wordt
niet opnieuw gewijzigd. De legacy DE-TV-test verifieert nu:

- geen vaste viewport-toolbar meer;
- aanwezigheid van `phoenixProjectTypeActions`;
- in-flow toolbar;
- positie vóór CIVIEL en INFRA;
- behoud van GECERTIFICEERD- en POWERSHELL-functionaliteit;
- PHOENIX MODULES blijft onderaan en ingeklapt.

Production en FOR-CONSTRUCTION blijven LOCKED.


## FIXED R2 — dedicated policy-version test

R1 wijzigde terecht `policy_version` naar `1.1.1`, maar de bestaande dedicated
layout-test `test_16_policy_layout_version` verwachtte nog `1.1.0`.

R2 corrigeert uitsluitend die testverwachting naar `1.1.1`.

Er zijn geen verdere UI-, layout-, DE-TV-, solver-, approval- of releasewijzigingen.
