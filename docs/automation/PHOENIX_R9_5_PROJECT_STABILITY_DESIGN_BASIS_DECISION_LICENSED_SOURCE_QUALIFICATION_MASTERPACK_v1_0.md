# PROJECT PHOENIX R9.5 — Project Stability Design-Basis Decision & Licensed-Source Qualification

Baseline: `ecc1e3b5f1a951f06d51344225a00bc94187e250`

## Doel
R9.5 vormt de beslis- en bronkwalificatielaag tussen R9.4 en de bestaande v8.6-verifier.

De technische stabiliteitsevidence blijft afkomstig uit R9/R9.1/R9.2/R9.3. R9.5:
- kwalificeert expliciete projectbesluiten;
- controleert de bronklasse en traceerbaarheid;
- valideert lokale bestandschecksums voor `LICENSED_STANDARD_SOURCE`;
- kan primaire Suriname-BIB-bronnen als authority/supporting evidence gebruiken;
- weigert de achtergrond-AI-bron als normatieve primaire bron;
- genereert alleen via de bestaande R9.4-engine een v8.6-input;
- wijzigt de v8.6-verifier niet.

## Suriname BIB
De baseline bevat de permanente Suriname BIB op commit `ecc1e3b`. Bouwbesluit no. 1 artikel 27 kan de noodzaak van een knikcontrole ondersteunen. De BIB stelt nadrukkelijk dat dit geen specifieke R9/v8.6 eigenwaardegrens oplevert.

## Fail-closed
Geen default acceptatiegrenzen, geen automatische Eurocode-rechtsstatus, geen automatische seismische vrijstelling, geen automatische code-compliance of productievrijgave.

## Alternate path
R9.3 screening is onvoldoende voor R9.5-eindkwalificatie. Een werkelijk onafhankelijk beoordeeld engineering-evidencebestand met checksum is vereist.

## Weak storey
R8/R9.3 capaciteit blijft kandidaat-screening. Gebruik voor de kandidaat-gate vereist expliciete acceptatie en reviewreferentie.

## Verwachte commit
`feat(structural): add project stability design-basis decision R9.5`
