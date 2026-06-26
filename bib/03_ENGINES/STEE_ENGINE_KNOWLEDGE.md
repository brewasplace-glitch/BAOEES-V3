# STEE ENGINE KNOWLEDGE

STEE = Source Traceability and Evidence Engine.

Status: officiële engine-kennis voor Project Phoenix / BAOEES V3.

## 1. Doel

STEE registreert alle bronnen, bewijsstukken en herleidbaarheid binnen Project Phoenix.

Elke projectoutput moet kunnen worden teruggeleid naar:

* projectinput;
* brondata;
* aannames;
* berekeningen;
* Digital Twin-data;
* runtime logs;
* Git evidence.

## 2. Bronregistratie

Per bron moet minimaal worden vastgelegd:

* bronnaam;
* bronbestand of URL;
* type bron;
* discipline;
* projectonderdeel;
* datum/tijd;
* betrouwbaarheid;
* gebruikte waarde;
* relatie met rapport, tekening of berekening.

## 3. Bronmap

Elke projectrun moet een bronmap hebben:

**Bronvermelding_van_dit_project**

of binnen BAOEES-output:

**06_sources/source_register.json**

## 4. Relatie met AAIE

Als AAIE een aanname maakt op basis van een bron, moet STEE die bron koppelen aan de aanname.

Als geen bron beschikbaar is, moet de aanname worden gemarkeerd als:

**AAIE fallback assumption**

## 5. Relatie met Git Evidence

STEE moet samenwerken met Git Evidence zodat zichtbaar is:

* welke commit bij een projectrun hoort;
* welke bestanden zijn gegenereerd;
* welke output bij welke codeversie hoort;
* of de working tree clean was.

## 6. Relatie met QA/QC

QA/QC moet controleren of belangrijke rapportonderdelen een bron of aanname hebben.

Ontbrekende bronvermelding moet als waarschuwing worden opgenomen.

## 7. Output

STEE moet kunnen exporteren naar:

* JSON;
* CSV;
* XLSX;
* PDF;
* DOCX;
* HTML dashboard;
* project-ZIP.

## 8. Belangrijk principe

Geen eindrapport zonder bronvermelding.

Geen automatische aanname zonder aannameslog.

Geen projectexport zonder evidence.
