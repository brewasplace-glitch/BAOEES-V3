# SOURCE EVIDENCE RULES

Status: bron- en bewijsregels voor Project Phoenix / BAOEES V3.

## 1. Doel

Project Phoenix moet alle bronnen, aannames en bewijsstukken systematisch vastleggen.

Elke output moet herleidbaar zijn naar:

* projectinput;
* brondata;
* aannames;
* berekeningen;
* Digital Twin;
* runtime logs;
* Git Evidence.

## 2. STEE

STEE betekent:

Source Traceability and Evidence Engine.

STEE registreert:

* documenten;
* kaarten;
* normen;
* websites;
* gebruikersinput;
* projectbestanden;
* AI-aannames;
* berekeningen;
* gegenereerde outputs.

## 3. Bronregister

Elk project krijgt minimaal:

`06_sources/source_register.json`

Daarnaast kan worden geëxporteerd naar:

* CSV;
* XLSX;
* PDF;
* DOCX;
* HTML dashboard;
* project ZIP.

## 4. Verplichte velden per bron

Per bron moet minimaal worden vastgelegd:

* bron-ID;
* bronnaam;
* brontype;
* bestandsnaam of URL;
* datum/tijd;
* discipline;
* gebruikt projectonderdeel;
* betrouwbaarheid;
* gebruikte waarde;
* koppeling met aanname;
* koppeling met rapport;
* koppeling met Digital Twin.

## 5. Relatie met AAIE

Als AAIE automatisch gegevens genereert, moet duidelijk worden vastgelegd:

* welke waarde is gegenereerd;
* waarom deze waarde is gekozen;
* welke bron of fallback is gebruikt;
* hoe betrouwbaar de waarde is;
* of gebruiker de waarde heeft goedgekeurd.

## 6. Fallback zonder bron

Als geen bron beschikbaar is, wordt de waarde gemarkeerd als:

`AAIE fallback assumption`

Voorbeeld:

`Grondwaterstand P = -0,50 m`

## 7. Relatie met rapportage

Rapporten moeten onderscheid maken tussen:

* bekende gegevens;
* brongegevens;
* automatische aannames;
* handmatige aannames;
* nog te controleren gegevens.

## 8. Relatie met QA/QC

QA/QC moet controleren of belangrijke onderdelen bronvermelding of aannameslog hebben.

Ontbrekende bronvermelding moet als waarschuwing worden opgenomen.

## 9. Belangrijk principe

Geen eindrapport zonder bronvermelding.

Geen automatische aanname zonder aannameslog.

Geen project-ZIP zonder evidence.
