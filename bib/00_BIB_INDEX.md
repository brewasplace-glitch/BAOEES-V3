# PROJECT PHOENIX BIB

BIB = Brewster Integrated Bibliotheek.

Status: centrale kennisbibliotheek voor Project Phoenix / BAOEES V3 / Brewster Engineering Wizard.

## 1. Doel

De BIB bewaart alle vaste kennis van Project Phoenix zodat deze niet verloren gaat.

De BIB bevat:

* masterkennis;
* projectkennis;
* enginekennis;
* standaarden;
* aannames;
* workflows;
* templates;
* lessons learned;
* source evidence;
* exportplannen.

## 2. Hoofdindeling

```text
bib/
  00_BIB_INDEX.md
  01_MASTER_KNOWLEDGE/
  02_PROJECTS/
  03_ENGINES/
  04_STANDARDS_AND_RULES/
  05_TEMPLATES/
  06_WORKFLOWS/
  07_LESSONS_LEARNED/
  08_SOURCE_EVIDENCE/
  09_ASSUMPTIONS/
  10_EXPORTS/
```

## 3. Master Knowledge

Map:

```text
bib/01_MASTER_KNOWLEDGE/
```

Bestanden:

```text
PROJECT_PHOENIX_CORE_KNOWLEDGE.md
README.md
```

Inhoud:

* Project Phoenix hoofdkennis;
* Digital Twin First;
* AAIE;
* STEE;
* Project Launcher;
* HTML Dashboard;
* Git Evidence;
* QA/QC;
* softwarebaseline v1.3 t/m v1.8.

## 4. Projects

Map:

```text
bib/02_PROJECTS/
```

Bestanden:

```text
PLUTOSTRAAT_PROJECT_KNOWLEDGE.md
MOSKEE_BUNSCHOTEN_PROJECT_KNOWLEDGE.md
BRUYNZEEL_WATERFRONT_PROJECT_KNOWLEDGE.md
README.md
```

Projecten:

* Plutostraat, Paramaribo;
* Moskee Bunschoten, Bikkersweg 88;
* Bruynzeel Waterfront District, Paramaribo.

## 5. Engines

Map:

```text
bib/03_ENGINES/
```

Bestanden:

```text
BAOEES_V3_ENGINE_REGISTER.md
AUTOMATIC_GROUNDWATER_FOUNDATION_ENGINE.md
AAIE_ENGINE_KNOWLEDGE.md
STEE_ENGINE_KNOWLEDGE.md
README.md
```

Belangrijke engines:

* Project Analyzer;
* AAIE;
* STEE;
* Digital Twin;
* Geo Engine;
* Structural Engine;
* Automatic Groundwater & Foundation Variant Engine;
* Permit Engine;
* Traffic and Parking Engine;
* AERIUS Engine;
* Reporting Engine;
* Dashboard Engine;
* ZIP Engine;
* Git Evidence Engine;
* QA/QC Engine.

## 6. Standards and Rules

Map:

```text
bib/04_STANDARDS_AND_RULES/
```

Bestanden:

```text
PROJECT_PHOENIX_STANDARDS.md
README.md
```

Vaste regels:

* Digital Twin First;
* automatische grondwaterstand;
* fallback grondwaterstand P = -0,50 m;
* automatisch geo-profiel;
* funderingsvarianten F1 stroken en F2 palen;
* standaard strokenfundering 150–200 cm;
* funderingsbalk 50 x 60 cm;
* vijf ontwerpvarianten A t/m E;
* bronvermelding via STEE;
* aannames via AAIE;
* outputformaten;
* Git-werkwijze.

## 7. Templates

Map:

```text
bib/05_TEMPLATES/
```

Bestanden:

```text
PROJECT_INPUT_TEMPLATE.md
REPORT_OUTPUT_TEMPLATE.md
README.md
```

Templates:

* projectinvoer;
* gewenste output;
* geotechniek;
* vergunning;
* parkeren;
* aannames;
* projectmodus;
* rapportstructuur.

## 8. Workflows

Map:

```text
bib/06_WORKFLOWS/
```

Bestanden:

```text
AUTONOMOUS_PROJECT_WORKFLOW.md
GITKRAKEN_WORKFLOW.md
README.md
```

Workflows:

* autonome projectverwerking;
* AAIE-aanvulling;
* STEE-bronvermelding;
* Digital Twin First;
* varianten;
* engineering engines;
* projectoutput;
* QA/QC;
* Git Evidence;
* GitKraken werkwijze.

## 9. Lessons Learned

Map:

```text
bib/07_LESSONS_LEARNED/
```

Bestanden:

```text
DASHBOARD_ENGINE_FIXES.md
README.md
```

Lessen:

* HTML Dashboard Export Engine v1.6;
* audit_result fout;
* storage_result fout;
* ontbrekende run-methode;
* PowerShell continuation prompt;
* veilig herstellen met git restore;
* geen Stage All Changes bij verdachte codewijzigingen.

## 10. Source Evidence

Map:

```text
bib/08_SOURCE_EVIDENCE/
```

Bestanden:

```text
GIT_EVIDENCE_BASELINE.md
SOURCE_EVIDENCE_RULES.md
README.md
```

Evidence-regels:

* Git Evidence;
* source register;
* STEE;
* runtime logs;
* audit trail;
* checksum;
* clean working tree;
* geen projectexport zonder evidence.

## 11. Assumptions

Map:

```text
bib/09_ASSUMPTIONS/
```

Bestanden:

```text
PROJECT_PHOENIX_ASSUMPTIONS.md
README.md
```

Aannames:

* grondwaterstand P = -0,50 m;
* automatische bepaling grondwaterstand;
* automatisch geo-profiel;
* F1 strokenfundering;
* F2 paalfundering;
* automatische funderingsvergelijking;
* aannameslog;
* bronkoppeling;
* gebruiker kan aannames aanpassen.

## 12. Exports

Map:

```text
bib/10_EXPORTS/
```

Bestanden:

```text
BIB_EXPORT_PLAN.md
README.md
```

Exportdoelen:

* DOCX;
* PDF;
* ZIP;
* HTML knowledge dashboard;
* projectkoppeling met Master Specification.

## 13. BIB-mijlpalen

```text
v1.8 = BIB structuur
v1.9 = Core Knowledge
v2.0 = Project Knowledge
v2.1 = Standards & Assumptions
v2.2 = Engine Knowledge
v2.3 = Workflows & Templates
v2.4 = Lessons Learned & Source Evidence
v2.5 = BIB Index & Export Plan
```

## 14. Belangrijk principe

De BIB is de centrale kennislaag van Project Phoenix.

Kennis die in de BIB staat, moet later kunnen worden gebruikt voor:

* automatische projectanalyse;
* rapportgeneratie;
* engine-aansturing;
* aannames;
* bronvermelding;
* QA/QC;
* dashboards;
* Master Specification updates;
* toekomstige softwareontwikkeling.
