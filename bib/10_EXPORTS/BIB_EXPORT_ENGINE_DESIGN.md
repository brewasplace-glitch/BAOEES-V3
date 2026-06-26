# BIB EXPORT ENGINE DESIGN

Status: ontwerpdocument voor de toekomstige Project Phoenix BIB Export Engine.

## 1. Doel

De BIB Export Engine moet de volledige Brewster Integrated Bibliotheek automatisch kunnen exporteren naar professionele eindproducten.

De engine moet de map `bib/` scannen, alle kennisbestanden verzamelen, sorteren, combineren en exporteren.

## 2. Gewenste output

De engine moet minimaal kunnen genereren:

* DOCX kennisbibliotheek;
* PDF kennisbibliotheek;
* ZIP-export van de volledige BIB;
* HTML knowledge dashboard;
* exportmanifest;
* Git Evidence;
* checksum;
* QA/QC-controle.

## 3. Voorgestelde engine-map

```text
baoees/bib_export_engine/
  __init__.py
  main.py
```

## 4. Input

De engine leest:

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

## 5. Outputmap

Voorgestelde output:

```text
outputs/bib/
  PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx
  PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf
  PROJECT_PHOENIX_BIB_EXPORT.zip
  bib_dashboard.html
  bib_manifest.json
  bib_export_log.json
  bib_git_evidence.json
```

## 6. Basisfuncties

De BIB Export Engine moet minimaal bevatten:

* scan_bib_files;
* read_markdown_files;
* build_bib_manifest;
* build_docx_export;
* build_pdf_export;
* build_html_dashboard;
* build_zip_export;
* build_git_evidence;
* run_quality_check;
* export_all.

## 7. Sorteervolgorde

De engine moet bestanden sorteren volgens vaste BIB-volgorde:

1. 00_BIB_INDEX.md
2. 01_MASTER_KNOWLEDGE
3. 02_PROJECTS
4. 03_ENGINES
5. 04_STANDARDS_AND_RULES
6. 05_TEMPLATES
7. 06_WORKFLOWS
8. 07_LESSONS_LEARNED
9. 08_SOURCE_EVIDENCE
10. 09_ASSUMPTIONS
11. 10_EXPORTS

## 8. DOCX-export

De DOCX-export moet bevatten:

* titelpagina;
* versiegegevens;
* exportdatum;
* repositorygegevens;
* inhoudsopgave;
* alle BIB-hoofdstukken;
* duidelijke koppen;
* tabellen waar mogelijk;
* bijlagenoverzicht.

## 9. PDF-export

De PDF-export moet worden gemaakt vanuit de DOCX of rechtstreeks vanuit HTML/Markdown.

Doel:

* archivering;
* delen met derden;
* projectverantwoording;
* kennisborging.

## 10. ZIP-export

De ZIP-export moet bevatten:

* alle originele Markdown-bestanden;
* README-bestanden;
* DOCX-export;
* PDF-export;
* HTML-dashboard;
* manifest;
* exportlog;
* Git Evidence.

## 11. HTML Knowledge Dashboard

Het dashboard moet tonen:

* hoofdindex;
* projectkennis;
* enginekennis;
* standaarden;
* aannames;
* workflows;
* templates;
* lessons learned;
* source evidence;
* exportstatus;
* links naar alle bestanden.

## 12. Manifest

Het manifest moet per bestand vastleggen:

* bestandsnaam;
* relatief pad;
* categorie;
* grootte;
* extensie;
* datum/tijd export;
* checksum indien beschikbaar.

## 13. Git Evidence

De engine moet vastleggen:

* branch;
* laatste commit;
* commit message;
* remote status;
* working tree status;
* exportdatum;
* exportpad;
* aantal bestanden.

## 14. QA/QC

Voor export moet worden gecontroleerd:

* bestaat `bib/00_BIB_INDEX.md`;
* bestaan alle hoofdmap-README’s;
* bestaan projectkennisbestanden;
* bestaat engine-register;
* bestaan standards en assumptions;
* bestaan workflows en templates;
* bestaan lessons learned;
* bestaan source evidence rules;
* bestaat exportplan.

## 15. Belangrijk principe

De BIB Export Engine maakt van de BIB een officiële kennisbibliotheek die leesbaar, deelbaar, exporteerbaar en controleerbaar is.
