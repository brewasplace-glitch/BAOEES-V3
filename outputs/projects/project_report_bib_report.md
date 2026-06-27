# PROJECT PHOENIX / BAOEES PROJECTRAPPORT

Automatisch gegenereerd: 2026-06-27T18:35:06

> Concept startpakket. Definitieve engineering vereist projectdata, controle en goedkeuring.

## 1. Managementsamenvatting

- Dit rapport is automatisch voorbereid vanuit Project Phoenix / BAOEES.
- De rapportage gebruikt BIB-kennis, AAIE-aannames en de Geo/Foundation BIB Engine.
- De fundering wordt voorlopig beoordeeld met minimaal F1 strokenfundering en F2 paalfundering.
- Definitieve engineering vereist projectlasten, bodemonderzoek, berekening en QA/QC.

## 2. Projectgegevens

- project_name: Default Project Phoenix Report
- project_type: bouw
- purpose: Automatisch projectrapport-startpakket vanuit BIB.
- location: nog niet opgegeven
- phase: concept

## 3. BIB, AAIE en STEE uitgangspunten

- Digital Twin First: alle projectoutputs moeten uit dezelfde centrale projectdata komen.
- AAIE: ontbrekende gegevens worden automatisch aangevuld en geregistreerd als aanname.
- STEE: bronnen, fallbacks en aannames moeten herleidbaar worden vastgelegd.
- QA/QC: geen volledige projectexport zonder controle.
- Groundwater fallback: P = -0,50 m als projectgegevens ontbreken.

## 4. Geo-profiel startwaarden

- Status: GEREED
- Grondwaterstand: P = -0,50 m
- Bron grondwaterstand: AAIE-BIB fallback
- Fallback grondwaterstand: P = -0,50 m
- Automatische grondwaterdetectie: True
- Automatisch geo-profiel: True
- maaiveldniveau: P = 0,00 m — bron: project_context of AAIE fallback
- grondwaterstand: P = -0,50 m — bron: AAIE-BIB fallback
- globale bodemopbouw: automatisch genereren op basis van locatie/kaart/bodemdata of handmatige invoer — bron: AAIE + STEE
- grondsoort per laag: voorlopig onbekend totdat bodemdata/sondering beschikbaar zijn — bron: AAIE assumption
- draagkrachtindicatie: voorlopige indicatie; definitief na grondonderzoek — bron: engineering rule
- zettingsgevoeligheid: voorlopige risico-inschatting — bron: engineering rule
- advies vervolgonderzoek: sondering/grondonderzoek vereist voor definitief funderingsadvies — bron: QA/QC rule

## 5. Funderingsvarianten

- F1 — Strokenfundering
- Type: fundering_op_staal
- Omschrijving: Fundering op staal met stroken onder dragende wanden en kolommen.
- Standaard dimensies: {"strookbreedte": "150 cm tot 200 cm", "strookhoogte": "40 cm", "funderingsbalk": "50 cm x 60 cm", "ligging_balk": "hart van strook"}
- Checks: draagkracht, zetting, grondwaterinvloed, uitvoerbaarheid, kosten, bouwrisico
- 
- F2 — Paalfundering
- Type: diepe_fundering
- Omschrijving: Diepe fundering op palen bij slappe bodem, onvoldoende draagkracht of verhoogd zettingsrisico.
- Checks: paallengte, paaltype, draagkracht per paal, paalbelasting, paalafstand, kosten, uitvoerbaarheid
- 

## 6. Funderingsvergelijking

- F2 — Paalfundering: totaalscore 36
- - draagkracht: 5/5 — Voorlopige BIB/AAIE-score.
- - zetting: 5/5 — Voorlopige BIB/AAIE-score.
- - kosten: 2/5 — Voorlopige BIB/AAIE-score.
- - bouwtijd: 3/5 — Voorlopige BIB/AAIE-score.
- - risico: 4/5 — Voorlopige BIB/AAIE-score.
- - bodemgeschiktheid: 4/5 — Voorlopige BIB/AAIE-score.
- - grondwaterinvloed: 4/5 — Voorlopige BIB/AAIE-score.
- - constructieve haalbaarheid: 5/5 — Voorlopige BIB/AAIE-score.
- - vergunning / acceptatie: 4/5 — Voorlopige BIB/AAIE-score.
- Opmerking: Paalfundering is robuuster bij slappe bodem en zettingsrisico.
- Opmerking: Duurder en vraagt meer geotechnisch detailonderzoek.
- Opmerking: Grondwaterstand voorlopig: P = -0,50 m.
- Opmerking: Paaltype en paallengte pas definitief na sondering/grondonderzoek.
- 
- F1 — Strokenfundering: totaalscore 33
- - draagkracht: 3/5 — Voorlopige BIB/AAIE-score.
- - zetting: 3/5 — Voorlopige BIB/AAIE-score.
- - kosten: 5/5 — Voorlopige BIB/AAIE-score.
- - bouwtijd: 5/5 — Voorlopige BIB/AAIE-score.
- - risico: 3/5 — Voorlopige BIB/AAIE-score.
- - bodemgeschiktheid: 3/5 — Voorlopige BIB/AAIE-score.
- - grondwaterinvloed: 3/5 — Voorlopige BIB/AAIE-score.
- - constructieve haalbaarheid: 4/5 — Voorlopige BIB/AAIE-score.
- - vergunning / acceptatie: 4/5 — Voorlopige BIB/AAIE-score.
- Opmerking: Strokenfundering is standaard goedkoop en snel uitvoerbaar.
- Opmerking: Definitieve keuze afhankelijk van draagkracht en zettingsberekening.
- Opmerking: Grondwaterstand voorlopig: P = -0,50 m.
- Opmerking: Bij slappe bodem of hoge zettingsgevoeligheid F2 serieus onderzoeken.
- 

## 7. Voorlopige funderingsaanbeveling

- Status: VOORLOPIG
- Voorlopige voorkeursvariant: F2 — Paalfundering
- Totaalscore: 36
- Dit is een automatische voorlopige BIB/AAIE-beoordeling. Definitieve funderingskeuze vereist projectlasten, bodemonderzoek en constructieve berekening.

## 8. AAIE-aannames gekoppeld aan rapport

- AAIE-BIB-005 — Automatische grondwaterdetectie — discipline: geotechniek
- AAIE-BIB-006 — Fallback grondwaterstand — discipline: geotechniek
- AAIE-BIB-007 — Status fallback grondwaterstand — discipline: geotechniek
- AAIE-BIB-008 — Automatisch geo-profiel — discipline: geotechniek
- AAIE-BIB-009 — Funderingsvarianten verplicht — discipline: fundering
- AAIE-BIB-F01 — Funderingsvariant F1 - Strokenfundering — discipline: fundering
- AAIE-BIB-F02 — Funderingsvariant F2 - Paalfundering — discipline: fundering
- AAIE-BIB-010 — Standaard projectoutputs — discipline: output

## 9. Benodigd voor definitieve rapportage

- projectlocatie bevestigen
- maaiveldpeil bepalen
- grondwaterstand verifiëren
- bodemopbouw/sondering invoeren
- belastingen bepalen
- zettingscontrole uitvoeren
- draagkrachtcontrole uitvoeren
- QA/QC uitvoeren

## 10. Standaard outputpakket

- Projectrapport PDF.
- Projectrapport DOCX.
- HTML dashboard.
- Digital Twin JSON.
- AAIE aannameslog.
- STEE bronregister.
- Geo/Foundation analyse.
- Funderingsvarianten F1/F2.
- QA/QC rapport.
- Project-ZIP.
- Git Evidence.
