# Brewster Engineering Wizard Knowledge Base v6.6

Systematische migratie van opgebouwde Brewster Engineering Wizard kennis naar Project Phoenix / BAOEES BIB.

## Domeinen

### BEOS / BREWAS / BAOEES visie
Autonoom engineeringplatform van locatiekeuze tot beheer, met Digital Twin, Knowledge Graph en AI Engine als centrale kern.
Belang: kern

### Digital Twin centraal
Alle disciplines lezen en schrijven naar dezelfde Digital Twin: terrein, BIM, constructie, fundering, riolering, verkeer, vergunning, kosten en assetbeheer.
Belang: kern

### AAIE
Autonomous Assumption and Inference Engine vult ontbrekende gegevens aan met aannameslog, bron, datum, betrouwbaarheid en projectcontext.
Belang: kern

### STEE
Source Traceability and Evidence Engine maakt per project een bronvermelding, evidence-log en projectpakket.
Belang: kern

### Open engineering stack
SCIA/Viktor worden vervangen door open engines zoals FreeCAD BIM, OpenSees, CalculiX, BREWAS Geo Engine, rapportage-engine en viewers.
Belang: hoog

## Projecten

### Moskee Bunschoten
Locatie: Bikkersweg 88, Bunschoten
Uitbreiding circa 20 m² inclusief vergunning, parkeren, AERIUS, constructie, situatietekening, plattegronden, gevels, doorsneden en 3D-impressies.

Bekende outputs:
- situatietekening
- plattegronden bestaand en nieuw
- geveltekeningen
- doorsneden
- 3D-impressies
- ruimtelijke onderbouwing / BOPA
- parkeeronderzoek
- participatie
- AERIUS

### Plutostraat Paramaribo
Locatie: Paramaribo, Suriname
Testproject voor geotechniek, fundering, constructie, grondwaterstand, strokenfundering en automatische rapportage.

Bekende outputs:
- funderingsplan
- geotechnische uitgangspunten
- constructieschema
- rapportage

### Bruynzeel Waterfront District
Locatie: Paramaribo, Suriname
Masterplanontwikkeling met GLIS-percelen, waterfront, kantoorprogramma, multifunctionele functies, GREX, investeerdersmemo en professioneel masterplanrapport.

Bekende outputs:
- masterplan
- GLIS kaarten
- perceelanalyse
- GREX
- SWOT
- ontwikkelscenario's
- investeerdersmemorandum

## Modules

### Geotechniek
Automatisch grondwater en geo-informatie genereren op basis van kaartuitsnede of Google Maps/satellietfoto, met handmatige optie.

Default regels:
- Standaard grondwaterstand P = -0,50 m tenzij projectspecifiek anders.
- Onderzoek strokenfundering en palenfundering als varianten.

### Fundering
Standaard funderingsconcepten, waaronder strokenfundering met funderingsbalk en variantenonderzoek.

Default regels:
- Standaard strook 150 cm breed en 40 cm hoog onder muren en kolommen.
- Funderingsbalk 50 cm breed en 60 cm hoog in hart strook.
- Later projectspecifiek ook strook 200 cm toepasbaar.

### Constructie
Constructiemodellen, belastingen, materiaaloptimalisatie, FreeCAD/OpenSees/CalculiX en constructierapportage.

Default regels:
- Open engines krijgen voorkeur boven gesloten SCIA/Viktor flow.
- Constructie-output moet reproduceerbaar en traceerbaar zijn.

### Riolering en afwatering
Ontwerp HWA, DWA, infiltratie, berging, leidingen, kolken, putten, hoeveelheden en kosten.

Default regels:
- Afwateringsplan koppelen aan Digital Twin.
- Hoeveelheden en kosten automatisch genereren.

### Verkeer en parkeren
Verkeersgeneratie, parkeerbalans, parkeerdruk, CROW-toets, advies parkeerregime en fysieke parkeerinformatie.

Default regels:
- Vink advies parkeerregime opnemen.
- Vink fysieke parkeerinfo opnemen.
- Automatische analyse via kaartgebied of gesproken projectopdracht.

### Vergunningen
Ruimtelijke onderbouwing, BOPA, omgevingsvergunning, participatieplan, AERIUS en milieukundige paragrafen.

Default regels:
- Omgevingswet en Regels op de kaart als bron opnemen.
- AERIUS/stikstof als automatische stap opnemen.

### Rapportage en export
PDF, DOCX, dashboards, evidence, bronvermelding, manifest en ZIP-pakket.

Default regels:
- PDF en DOCX standaard.
- Project-ZIP standaard.
- Bronvermelding_van_dit_project standaard.

### Live Digital Twin Viewer
Interactieve 3D viewer met vogelvlucht, walkthrough, drivethrough en videopresentatie.

Default regels:
- Project moet rondom en van boven bekeken kunnen worden.

## Standaardregels

- **Outputstandaard**: Rapporten standaard PDF en DOCX; tekeningen standaard SKP, DWG en DXF.
- **Autonomous Project Mode**: Volledig autonoom is default, met mogelijkheid tot assistent of semi-autonoom.
- **Ontwerpvarianten**: Automatisch vijf varianten A t/m E genereren: kosten, vergunningkans, duurzaamheid, opbrengst en ruimtelijke kwaliteit.
- **Bronvermelding**: Elke projectanalyse krijgt automatisch map Bronvermelding_van_dit_project.
- **Geen handmatig plakken**: Project Phoenix updates gebeuren voortaan via downloadbare updatebestanden en scripts, niet via handmatig Python knip- en plakwerk.

## Outputformaten

- PDF
- DOCX
- SKP
- DWG
- DXF
- IFC
- STEP
- FreeCAD
- OpenSees
- CalculiX
- Excel
- CSV
- JSON
- HTML dashboard
- ZIP projectpakket
