# Phoenix Autonomous Engineering Input & Real-World Data Acquisition Masterpack v1.0

## Doel

Deze masterpack verbindt de autonome projectketen met echte projectspecifieke
engineering- en locatie-evidence zonder gegevens te verzinnen.

De drie nieuwe kernonderdelen zijn:

1. **Autonomous Real-World Data Acquisition Engine**
2. **Site Drawing & Parcel Intelligence Engine**
3. **Structural Action & Load Basis Engine**

## Real-World Data Acquisition

Phoenix accepteert:
- machine-readable uploads;
- expliciet geregistreerde lokale/autoritatieve HTTPS feeds;
- een uploadbaar `phoenix.real-world-source-manifest/1.0`.

Ondersteunde categorieën:
- `market_prices`
- `material_supply`
- `structural_action_load`
- `site_context`

Iedere acquisitie krijgt:
- bron/provider;
- URL of uploadreferentie;
- projectgeografie;
- tijdstip;
- SHA256;
- doelbestand;
- status.

Phoenix voert **geen impliciete websearch** uit en levert geen fictieve
leverancier-, prijs- of normbron mee.

## Site Drawing & Parcel Intelligence

Direct ondersteund:
- GeoJSON / JSON;
- DXF met expliciete `$INSUNITS`;
- PDF-tekstextractie wanneer `pypdf` of `PyPDF2` lokaal beschikbaar is.

DWG vereist eerst betrouwbare DXF-conversie. Rasterafbeeldingen worden niet via
OCR gegokt.

Uit valide site-evidence kunnen o.a. volgen:
- perceelbreedte/-diepte;
- polygon/boundary candidate;
- noordrichting indien expliciet aanwezig;
- bronreferentie.

De geometrie blijft **niet-kadastraal** totdat echte kadastrale validatie is
geleverd.

## Structural Action & Load Basis

Na v8.1 zoekt Phoenix automatisch naar een actuele, jurisdiction-matching
belastings-/combinatiebron onder:
- `inputs/structural_action_load/**`
- `data/structural_action_load/**`
- `configs/phoenix/structural_action_load_catalog/**`

Een bron moet minimaal bevatten:
- country/jurisdiction;
- source name;
- effective date;
- actuele status of valid-until;
- volledige `action_load_input`;
- actions;
- combinations;
- expliciete self-weight action.

Phoenix verzint geen:
- gebruiksbelasting;
- windbelasting;
- normbasis;
- combinatiefactor;
- code-status.

Wanneer geen actuele bron bestaat stopt v8.2 met
`CURRENT_STRUCTURAL_ACTION_LOAD_BASIS_REQUIRED`.

## Koppeling met bestaande engines

Real-world acquisition draait vóór:
- Local Material/Product/Supply Intelligence;
- Local Cost Intelligence;
- Structural v8.2.

Daarmee kunnen aangeleverde of geconfigureerde echte bronnen automatisch
doorstromen naar:
- lokaal beschikbare materialen;
- actuele lokale prijzen;
- constructieve belastingen/combinaties;
- situatietekening;
- Digital Twin;
- QA/QC.

## Release

Alle output blijft `CONCEPT / TER CONTROLE` waar professionele of wettelijke
validatie ontbreekt. Productievrijgave blijft `LOCKED` tot een succesvolle
real-project PAT en de bestaande review/release gates.
