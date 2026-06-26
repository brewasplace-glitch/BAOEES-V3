PROJECT PHOENIX STANDARDS

Status: vaste standaarden en systeemregels voor Project Phoenix / BAOEES V3.

1. Digital Twin First

Alle projectinformatie moet worden vastgelegd in de Living Digital Twin.

Rapporten, tekeningen, berekeningen, kostenramingen, vergunningstukken, dashboards en exports moeten voortkomen uit dezelfde centrale projectdata.

2. Automatische grondwaterstand

Project Phoenix moet de grondwaterstand automatisch kunnen bepalen of schatten.

De geotechnische module moet hiervoor gebruik kunnen maken van:

projectlocatie;
kaartuitsnede;
Google Maps- of satellietbeeld;
beschikbare geo-informatie;
open data;
eerdere projecten;
bodemtype;
maaiveldniveau;
AAIE-inferentie;
handmatige invoer van de gebruiker.

Wanneer geen betrouwbare projectspecifieke grondwaterstand beschikbaar is, geldt als fallback:

Grondwaterstand: P = -0,50 m

Deze waarde moet altijd als aanname worden geregistreerd in het aannameslog.

3. Automatisch genereren geo-informatie

Project Phoenix moet geo-informatie automatisch kunnen genereren op basis van locatie en beschikbare gegevens.

Minimaal te genereren gegevens:

maaiveldniveau;
grondwaterstand;
globale bodemopbouw;
bodemrisico’s;
draagkrachtindicatie;
zettingsgevoeligheid;
grondsoortindicatie;
funderingsadvies;
betrouwbaarheid per aanname;
bronvermelding per gebruikt gegeven.
4. Automatische funderingsvarianten

Voor elk bouwproject moet Project Phoenix standaard minimaal twee funderingsvarianten genereren:

Variant	Naam	Omschrijving
F1	Strokenfundering	Fundering op staal met stroken onder wanden/kolommen
F2	Paalfundering	Diepe fundering op palen bij onvoldoende draagkracht of zettingsrisico

Beide varianten moeten automatisch worden getoetst op:

draagkracht;
zetting;
bodemgeschiktheid;
grondwaterinvloed;
uitvoerbaarheid;
kosten;
risico;
bouwtijd;
constructieve haalbaarheid;
vergunningstechnische haalbaarheid.
5. Standaard strokenfundering

Voor conceptontwerp geldt als standaard Brewster-uitgangspunt:

aaneengesloten strokenfundering;
breedte: 150 cm tot 200 cm;
hoogte: 40 cm;
funderingsbalk: 50 cm breed en 60 cm hoog;
funderingsbalk in het hart van de strook.

Deze standaard is een conceptbasis en moet projectspecifiek worden gecontroleerd.

6. Paalfundering als tweede variant

Paalfundering moet automatisch worden toegevoegd als tweede funderingsvariant wanneer:

slappe bodemlagen aanwezig zijn;
zettingsrisico verhoogd is;
draagkracht van fundering op staal onzeker is;
grondwaterstand invloedrijk is;
projectbelasting hoog is;
fundering op staal economisch of technisch ongunstig lijkt.
7. Keuzeopties voor gebruiker

De gebruiker moet kunnen kiezen uit:

strokenfundering gebruiken;
paalfundering gebruiken;
automatisch beste fundering kiezen;
beide varianten rapporteren;
handmatig funderingstype vastzetten.
8. Ontwerpvarianten

Project Phoenix moet standaard vijf ontwerpvarianten genereren:

Variant	Doel
A	Laagste kosten
B	Hoogste vergunningkans
C	Meest duurzaam
D	Hoogste opbrengst
E	Beste ruimtelijke kwaliteit

Funderingsvarianten F1 en F2 worden aanvullend binnen de technische/geotechnische module gegenereerd.

9. Bronvermelding

Alle bronnen moeten worden geregistreerd via STEE: Source Traceability and Evidence Engine.

Per bron moet minimaal worden vastgelegd:

bronnaam;
type bron;
datum/tijd;
gebruikt projectonderdeel;
betrouwbaarheid;
relatie met rapport, tekening, berekening of aanname.
10. Aannames

Alle automatisch gegenereerde gegevens moeten worden vastgelegd via AAIE: Autonomous Assumption and Inference Engine.

Per aanname moet minimaal worden vastgelegd:

waarde;
discipline;
reden;
bron;
betrouwbaarheid;
status;
gebruiker kan goedkeuren of aanpassen.
11. Outputformaten

Project Phoenix moet standaard kunnen exporteren naar:

PDF;
DOCX;
MD;
TXT;
XLSX;
CSV;
DXF;
DWG indien beschikbaar;
SKP indien beschikbaar;
IFC indien beschikbaar;
FreeCAD-bestand indien beschikbaar;
JSON;
HTML dashboard;
ZIP projectpakket.
12. Git-werkwijze

Geen commit zonder test.

Standaardvolgorde:

git status
bestand aanpassen
test uitvoeren
output controleren
git status
git add
git commit
git push
git status

Bij verdachte grote verwijderingen in codebestanden: nooit Stage All Changes gebruiken, maar eerst diff controleren of bestand herstellen.