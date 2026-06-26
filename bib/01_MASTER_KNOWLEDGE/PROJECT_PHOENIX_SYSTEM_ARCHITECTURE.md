# PROJECT PHOENIX SYSTEM ARCHITECTURE

Status: systeemarchitectuur voor Project Phoenix / BAOEES V3.

## 1. Hoofdarchitectuur

Project Phoenix bestaat uit vijf hoofdlagen:

1. Phoenix Core
2. Project Input Layer
3. Engineering Engine Layer
4. Output and Evidence Layer
5. BIB Knowledge Layer

## 2. Phoenix Core

Phoenix Core bestaat uit:

- Living Digital Twin;
- Knowledge Graph;
- AI Orchestrator;
- AAIE;
- STEE;
- Workflow Engine;
- Runtime Engine;
- QA/QC Engine;
- Export Engine.

## 3. Project Input Layer

De inputlaag accepteert:

- tekst;
- spraak;
- PDF;
- foto;
- tekening;
- kaartuitsnede;
- satellietbeeld;
- DXF;
- DWG;
- SKP;
- IFC;
- JSON;
- bestaande projectmap.

## 4. Engineering Engine Layer

De engine-laag bevat:

- Project Analyzer;
- Geo Engine;
- Automatic Groundwater and Foundation Variant Engine;
- Structural Engine;
- Drainage and Sewerage Engine;
- Traffic and Parking Engine;
- Permit Engine;
- AERIUS Engine;
- GIS Map Engine;
- Cost Engine;
- Planning Engine;
- Reporting Engine;
- Drawing Engine;
- CAD/DXF Engine;
- Dashboard Engine;
- ZIP Engine;
- Git Evidence Engine.

## 5. Output and Evidence Layer

De outputlaag genereert:

- projectrapporten;
- tekeningen;
- CAD/DXF;
- Digital Twin JSON;
- source register;
- assumptions log;
- QA/QC rapport;
- runtime log;
- audit trail;
- checksum;
- git evidence;
- dashboard;
- project-ZIP.

## 6. BIB Knowledge Layer

De BIB bevat:

- masterkennis;
- projectkennis;
- enginekennis;
- standaarden;
- aannames;
- workflows;
- templates;
- lessons learned;
- source evidence;
- exportplannen.

## 7. Dataflow

Standaard dataflow:

1. projectopdracht komt binnen;
2. Project Analyzer bepaalt projecttype en scope;
3. AAIE vult ontbrekende gegevens aan;
4. STEE registreert bronnen;
5. Digital Twin wordt opgebouwd;
6. engines voeren analyses uit;
7. varianten worden gegenereerd;
8. rapporten en tekeningen worden gemaakt;
9. QA/QC controleert output;
10. dashboard en ZIP worden gemaakt;
11. Git Evidence wordt vastgelegd;
12. BIB kan kennis bijwerken.

## 8. Belangrijk architectuurprincipe

Geen losse documenten zonder centrale projectdata.

Geen automatische aannames zonder aannameslog.

Geen eindrapport zonder bronvermelding.

Geen projectexport zonder QA/QC en Git Evidence.