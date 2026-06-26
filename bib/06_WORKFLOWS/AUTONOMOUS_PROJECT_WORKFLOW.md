AUTONOMOUS PROJECT WORKFLOW

Status: standaard workflow voor Project Phoenix / BAOEES V3.

1. Doel

Deze workflow beschrijft hoe Project Phoenix autonoom een project moet verwerken vanaf eerste opdracht tot volledig projectpakket.

De workflow geldt voor:

bouwprojecten;
civiele projecten;
infraprojecten;
vergunningprojecten;
gebiedsontwikkeling;
constructieve en geotechnische analyses.
2. Start

Een project mag starten met minimale invoer, bijvoorbeeld:

tekstuele projectopdracht;
gesproken opdracht;
PDF;
foto;
tekening;
kaartuitsnede;
Google Maps- of satellietbeeld;
bestaande projectmap;
projectconfiguratie JSON.
3. Projectanalyse

Project Phoenix bepaalt automatisch:

projecttype;
locatie;
discipline;
benodigde engines;
ontbrekende gegevens;
benodigde bronnen;
benodigde aannames;
gewenste output;
risico’s;
vervolgacties.
4. AAIE-aanvulling

AAIE vult ontbrekende gegevens aan, maar markeert alles als aanname.

Voorbeelden:

grondwaterstand;
bodemprofiel;
funderingstype;
parkeerbehoefte;
vergunningstrategie;
kostenkengetallen;
planning;
constructieve uitgangspunten.
5. STEE-bronvermelding

STEE registreert alle gebruikte bronnen.

Elke bron moet gekoppeld worden aan:

rapporttekst;
berekening;
tekening;
aanname;
Digital Twin-object;
dashboard;
projectexport.
6. Digital Twin First

Alle projectdata worden opgeslagen in de Living Digital Twin.

Rapporten, tekeningen, berekeningen, kosten, planning, vergunningstukken en dashboards moeten uit dezelfde projectdata voortkomen.

7. Varianten

Project Phoenix genereert standaard vijf ontwerpvarianten:

A: laagste kosten;
B: hoogste vergunningkans;
C: meest duurzaam;
D: hoogste opbrengst;
E: beste ruimtelijke kwaliteit.

Voor funderingen worden aanvullend minimaal twee technische varianten gegenereerd:

F1: strokenfundering;
F2: paalfundering.
8. Engineering

De relevante engines worden automatisch aangeroepen:

Geo Engine;
Structural Engine;
Drainage and Sewerage Engine;
Traffic and Parking Engine;
Permit Engine;
AERIUS Engine;
Cost Engine;
Planning Engine;
QA/QC Engine.
9. Output

Per project moet minimaal kunnen worden gegenereerd:

projectrapport;
tekeningen;
CAD/DXF;
berekeningen;
Digital Twin JSON;
bronregister;
aannameslog;
QA/QC-rapport;
HTML-dashboard;
project-ZIP.
10. Controle

Voor elke projectrun moet Project Phoenix controleren:

zijn verplichte bronnen aanwezig;
zijn aannames zichtbaar;
zijn rapport en tekeningen consistent;
is de Digital Twin bijgewerkt;
zijn exports aangemaakt;
is QA/QC uitgevoerd;
is Git Evidence aanwezig.
11. Git-evidence

Na een geldige projectrun moet worden vastgelegd:

branch;
commit;
status working tree;
gegenereerde bestanden;
runtime log;
audit trail;
checksum;
Git evidence JSON.
12. Eindstatus

Een projectrun is pas volledig wanneer:

rapporten zijn aangemaakt;
tekeningen zijn aangemaakt;
dashboard werkt;
project-ZIP bestaat;
bronregister bestaat;
aannameslog bestaat;
QA/QC is uitgevoerd;
Git-status clean is.