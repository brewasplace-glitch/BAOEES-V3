# BIB EXPORT ENGINE KNOWLEDGE

Status: enginekennis voor de toekomstige Project Phoenix BIB Export Engine.

## 1. Doel

De BIB Export Engine is verantwoordelijk voor het omzetten van de Brewster Integrated Bibliotheek naar professionele exports.

De engine vormt de brug tussen:

* BIB Markdown-bestanden;
* Master Specification;
* DOCX/PDF-rapportage;
* HTML knowledge dashboard;
* ZIP-archief;
* Git Evidence.

## 2. Rol binnen Project Phoenix

De engine hoort bij de Output and Evidence Layer van Project Phoenix.

Relaties:

* leest BIB Knowledge Layer;
* gebruikt STEE voor bron- en evidenceprincipes;
* gebruikt Git Evidence voor versieherleidbaarheid;
* gebruikt QA/QC voor exportcontrole;
* levert output aan Master Specification Sync.

## 3. Engine-input

Input:

* `bib/` hoofdmap;
* Markdown-bestanden;
* README-bestanden;
* projectkennis;
* enginekennis;
* standaarden;
* aannames;
* workflows;
* templates;
* lessons learned;
* source evidence.

## 4. Engine-output

Output:

* Word-document;
* PDF-document;
* ZIP-bestand;
* HTML-dashboard;
* JSON-manifest;
* exportlog;
* Git Evidence-bestand.

## 5. Verplichte methode

De engine moet een `run()` methode hebben.

Dit voorkomt dezelfde fout als eerder bij de HTML Dashboard Export Engine:

`AttributeError: object has no attribute run`

## 6. Robuuste parameters

De engine moet toekomstige extra parameters kunnen accepteren via:

`**extra_results`

Daarmee blijft de engine compatibel met BAOEES Core wanneer later extra resultaten worden meegegeven.

## 7. Standaard result-structuur

Elke run moet teruggeven:

* status;
* engine;
* engine_version;
* output_paths;
* file_count;
* warnings;
* recommendation;
* generated_at;
* git_evidence.

## 8. Warnings

De engine moet waarschuwingen geven wanneer:

* BIB-index ontbreekt;
* categorie leeg is;
* README ontbreekt;
* projectkennis ontbreekt;
* assumptions ontbreken;
* source evidence ontbreekt;
* Git-status niet clean is.

## 9. Recommendation

De engine moet aanbevelingen geven voor:

* ontbrekende kennis;
* verouderde hoofdstukken;
* ontbrekende exports;
* QA/QC-aandachtspunten;
* volgende BIB-versie.

## 10. Toekomstige koppeling

De BIB Export Engine moet later gekoppeld worden aan:

* Project Phoenix Launcher;
* Master Specification Sync;
* HTML dashboard;
* Project ZIP Engine;
* Document Export Engine;
* QA/QC Engine.

## 11. Belangrijk principe

De BIB Export Engine mag geen kennis verzinnen.

De engine mag alleen bestaande BIB-inhoud verzamelen, structureren, exporteren en controleren.
