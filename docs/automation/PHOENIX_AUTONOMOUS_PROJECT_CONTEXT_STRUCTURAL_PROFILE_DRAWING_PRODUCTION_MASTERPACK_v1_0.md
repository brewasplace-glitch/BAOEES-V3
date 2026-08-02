# Phoenix Autonomous Project Context, Structural Profile & Drawing Production Masterpack v1.0

## Doel

Deze masterpack sluit de volgende downstream gaten uit PHOENIX-PAT-001:

- automatisch centraal projectcontextbestand;
- projectspecifiek constructief kandidaatprofiel voor de v8.0-keten;
- echte concepttekeningproductie uit het maatvoerende architectuurmodel;
- overdracht van context, tekeningen en constructief profiel naar de Digitale Tweeling.

## Project Context Engine

De engine verwerkt alleen expliciete projectfeiten uit de projectomschrijving en
houdt die strikt gescheiden van ontwerp-aannames.

Ondersteund in vrije tekst:

- `Locatie: Amsterdam, Nederland`
- `Perceel 20 x 30 m`
- `Valuta: EUR`

Wanneer een land expliciet aanwezig is, mag Phoenix de valuta deterministisch
afleiden (bijvoorbeeld Nederland -> EUR, Suriname -> SRD). De Nederlandse
gebruikersinterface wordt **nooit** gebruikt om het projectland te raden.

Als perceelgegevens ontbreken, maakt Phoenix wel een schematische ontwerpcanvas
zodat ontwerpcoördinatie mogelijk blijft. Deze canvas is geen kadastrale of
juridische perceelgrens en kan een echte situatietekening niet vrijgeven.

## Structural Project Profile Generator

De generator maakt automatisch `structural_project_profile.json` met de acht
aannames die de bestaande v8.0 Architectural-to-Structural Model Derivation
Engine nodig heeft.

De aannames zijn expliciet als concept-hypothese geregistreerd. De generator
maakt nadrukkelijk **geen** normbasis, ontwerpbelastingen, grondgegevens,
definitieve materiaalkeuze, doorsneden of professionele goedkeuring.

De architectuurbootstrap v1.1 voegt tevens de traceerbaarheidsvelden toe die de
bestaande v8.0-runner verwacht voor wandkandidaten:
`element_id`, `storey_id`, `category`, `length_m`, `height_m`.

## Drawing Production Engine

Uit het architectuurmodel worden echte bestanden geproduceerd:

- maatgevoerde plattegronden per bouwlaag — SVG + DXF;
- vier gevelaanzichten — SVG + DXF;
- twee doorsneden — SVG + DXF;
- situatie/terreincontext — SVG + DXF;
- `architectural_drawing_register.json`.

Alle bladen dragen de status **CONCEPT / TER CONTROLE**. De output kan door de
orchestrator als geproduceerd worden aangemerkt zonder dat professionele
vrijgave wordt verleend.

Een schematische situatietekening blijft outputtechnisch geblokkeerd met
`SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN` totdat echte perceel-/locatiegegevens
zijn opgegeven.

## Projectcontext naar Permit en Cost & Planning

De architectuuradapter schrijft expliciete locatie/country/currency-context terug
naar `project_manifest.json`. Hierdoor kunnen de bestaande Permit- en
Cost & Planning-adapters dezelfde centrale context gebruiken.

Zonder echte locatie blijft Permit terecht geblokkeerd. Zonder expliciete of uit
een expliciet land afleidbare valuta blijft de kostenraming terecht geblokkeerd.

## Verwachte PAT-continuatie

Voor dezelfde PHOENIX-PAT-001-omschrijving zonder locatie behoren deze blockers
te verdwijnen:

- `STRUCTURAL_PROJECT_PROFILE_REQUIRED`
- `FINAL_DRAWING_EXPORT_REQUIRED` voor plattegronden
- `FINAL_DRAWING_EXPORT_REQUIRED` voor gevels
- `FINAL_DRAWING_EXPORT_REQUIRED` voor doorsneden

Daarna kan de constructieketen v8.0 werkelijk starten. De eerstvolgende
constructieve blocker kan dan `V8_1_TO_V8_12_VALIDATED_INPUT_MAPPING_REQUIRED`
worden. Dit is een downstream-koppelvraag en geen terugval van de architectuur.

## Safety / release

- automatische professionele goedkeuring: uit;
- productievrijgave: LOCKED;
- juridisch/kadastraal sitefeit wordt niet verzonnen;
- normbasis en belastingen worden niet verzonnen;
- zero-idle-polling blijft behouden.
