# DASHBOARD ENGINE FIXES

Status: lessons learned voor Project Phoenix / BAOEES V3.

## 1. Context

Tijdens de ontwikkeling van Project Phoenix v1.6 is de Project HTML Dashboard Export Engine herbouwd.

De fout ontstond doordat BAOEES Core extra engine-resultaten doorgaf aan de dashboard engine, terwijl de dashboard engine deze parameters nog niet accepteerde.

## 2. Gevonden fouten

Belangrijke fouten:

* unexpected keyword argument audit_result;
* storage_result zonder lokale waarde;
* missing run method;
* object has no attribute run;
* grote ongewenste codeverwijdering in main.py;
* verwarring tussen GitKraken Terminal en Kladblok;
* PowerShell continuation prompt `>>`.

## 3. Belangrijkste oplossing

De HTML Dashboard Export Engine moet robuust zijn en minimaal accepteren:

* project_result;
* report_result;
* drawing_result;
* cad_result;
* calculation_result;
* source_result;
* digital_twin_result;
* qa_qc_result;
* export_result;
* zip_result;
* storage_result;
* audit_result;
* checksum_result;
* git_evidence_result;
* index_result;
* extra future keyword arguments via `**extra_results`.

## 4. Run compatibility

Elke engine die door BAOEES Core kan worden aangeroepen, moet een `run()` methode hebben.

Dit voorkomt:

`AttributeError: object has no attribute run`

## 5. Veilig werken met main.py

Bij grote wijzigingen in codebestanden:

1. nooit direct Stage All Changes gebruiken;
2. eerst `git diff` bekijken;
3. verdachte grote deletions controleren;
4. indien nodig bestand herstellen met `git restore`;
5. pas committen na succesvolle test.

## 6. Testregel

Geen commit zonder:

* `python -m py_compile`;
* `python run_baoees_v3.py`;
* visuele controle van `outputs/projects/index.html`;
* `git status`.

## 7. Belangrijke les

Project Phoenix moet fouttolerante engines krijgen.
Een engine mag niet crashen doordat een andere engine extra informatie meestuurt.

Daarom moeten toekomstige engines bij voorkeur werken met:

* expliciete kernparameters;
* optionele parameters;
* `**kwargs` of `**extra_results`;
* duidelijke status-output;
* warnings;
* recommendation;
* evidence output.

## 8. Status

De HTML Dashboard Export Engine is herbouwd en werkend vastgelegd in Project Phoenix v1.6.
