# BIB EXPORT PLAN

Status: exportplan voor Project Phoenix BIB.

## 1. Doel

De BIB moet niet alleen in losse Markdown-bestanden bestaan, maar ook kunnen worden geëxporteerd naar professionele eindproducten.

Doelproducten:

* DOCX;
* PDF;
* ZIP;
* HTML knowledge dashboard;
* koppeling met Project Phoenix Master Specification.

## 2. Exportvormen

## 2.1 DOCX

De BIB moet kunnen worden samengevoegd tot één Word-document:

```text
PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx
```

Inhoud:

* titelpagina;
* inhoudsopgave;
* masterkennis;
* projectkennis;
* enginekennis;
* standaarden;
* aannames;
* workflows;
* templates;
* lessons learned;
* source evidence;
* exportplan.

## 2.2 PDF

De BIB moet kunnen worden geëxporteerd naar:

```text
PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf
```

Doel:

* archivering;
* delen met derden;
* projectverantwoording;
* naslagwerk.

## 2.3 ZIP

De volledige BIB moet kunnen worden verpakt als:

```text
PROJECT_PHOENIX_BIB_EXPORT.zip
```

Inhoud:

* alle Markdown-bestanden;
* alle README-bestanden;
* export DOCX;
* export PDF;
* exportlog;
* manifest;
* Git Evidence.

## 2.4 HTML Knowledge Dashboard

De BIB moet later een eigen HTML-dashboard krijgen:

```text
bib/10_EXPORTS/bib_dashboard.html
```

Het dashboard moet tonen:

* hoofdindex;
* projectkennis;
* enginekennis;
* aannames;
* standaarden;
* workflows;
* templates;
* lessons learned;
* evidence;
* zoekbare structuur;
* links naar bestanden.

## 3. Relatie met Master Specification

De BIB moet kunnen worden gebruikt om de Master Specification automatisch bij te werken.

Belangrijke koppelingen:

* BIB Core Knowledge → Master Specification hoofdstuk systeemdefinitie;
* Project Knowledge → referentieprojecten;
* Engine Knowledge → technische architectuur;
* Standards → systeemeisen;
* Assumptions → AAIE-regels;
* Workflows → proceshoofdstukken;
* Source Evidence → STEE en Git Evidence;
* Lessons Learned → QA/QC en ontwikkelregels.

## 4. Relatie met BAOEES V3

De BIB moet later door BAOEES V3 kunnen worden ingelezen als kennisbron.

Mogelijke toepassingen:

* automatische prompts;
* projectanalyse;
* engine-aansturing;
* standaarduitgangspunten;
* rapporttemplates;
* kwaliteitscontrole;
* aannameslog;
* bronvermelding;
* dashboardteksten.

## 5. Export-engine

Een toekomstige engine kan worden toegevoegd:

```text
baoees/bib_export_engine/
```

Mogelijke bestanden:

```text
baoees/bib_export_engine/__init__.py
baoees/bib_export_engine/main.py
```

Taken van de engine:

* BIB-map scannen;
* Markdown-bestanden verzamelen;
* inhoud sorteren;
* DOCX genereren;
* PDF genereren;
* ZIP genereren;
* HTML-dashboard genereren;
* manifest maken;
* Git Evidence koppelen.

## 6. Verplichte exportmetadata

Elke BIB-export moet bevatten:

* exportdatum;
* repository;
* branch;
* laatste commit;
* working tree status;
* aantal bestanden;
* lijst met bestanden;
* exportformaat;
* exportpad;
* checksums indien beschikbaar.

## 7. QA/QC voor BIB

Voor export moet worden gecontroleerd:

* bestaat `00_BIB_INDEX.md`;
* bestaan alle hoofdmap-README’s;
* zijn projectkennisbestanden aanwezig;
* is engine-register aanwezig;
* zijn assumptions aanwezig;
* zijn source evidence rules aanwezig;
* zijn workflows aanwezig;
* is exportplan aanwezig;
* is Git-status clean.

## 8. Roadmap

```text
v2.5 = BIB Index & Export Plan
v2.6 = BIB Project Phoenix Master Knowledge uitbreiden
v2.7 = BIB export engine ontwerpen
v2.8 = BIB export engine bouwen
v2.9 = BIB DOCX/PDF/ZIP export testen
v3.0 = BIB koppelen aan Project Phoenix Launcher
```

## 9. Belangrijk principe

De BIB is geen losse documentmap.

De BIB is de centrale kennisbank van Project Phoenix en moet later automatisch door de software kunnen worden gelezen, gebruikt, gecontroleerd en geëxporteerd.
