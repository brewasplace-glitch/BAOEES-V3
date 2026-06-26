AUTOMATIC GROUNDWATER & FOUNDATION VARIANT ENGINE

Status: officiële engine-kennis voor Project Phoenix / BAOEES V3.

1. Doel

Deze engine bepaalt automatisch de geotechnische uitgangspunten voor een project en genereert minimaal twee funderingsvarianten:

F1: strokenfundering;
F2: paalfundering.

De engine werkt samen met:

AAIE: Autonomous Assumption and Inference Engine;
STEE: Source Traceability and Evidence Engine;
Geo Engine;
Structural Engine;
Digital Twin;
QA/QC Engine.
2. Automatische grondwaterstand

De engine moet automatisch proberen de grondwaterstand te bepalen op basis van:

projectlocatie;
kaartuitsnede;
Google Maps- of satellietbeeld;
maaiveldinformatie;
bodemgegevens;
nabijheid van oppervlaktewater;
eerdere projectdata;
open data;
handmatige gebruikersinput;
AAIE-inferentie.

Wanneer geen betrouwbare projectinformatie beschikbaar is, gebruikt de engine de fallback:

Grondwaterstand: P = -0,50 m

Deze fallback moet altijd worden opgeslagen als aanname.

3. Automatisch geo-profiel

De engine moet een concept-geo-profiel kunnen genereren met:

maaiveldniveau;
grondwaterstand;
globale bodemopbouw;
grondsoort per laag;
draagkrachtindicatie;
zettingsgevoeligheid;
risico-indicatie;
advies vervolgonderzoek;
betrouwbaarheid per onderdeel.
4. Funderingsvariant F1: strokenfundering

Conceptuitgangspunt:

fundering op staal;
aaneengesloten strokenfundering;
breedte: 150 cm tot 200 cm;
hoogte: 40 cm;
funderingsbalk: 50 cm breed en 60 cm hoog;
balk in hart van strook;
toepassen onder dragende wanden en kolommen.

Te toetsen:

draagkracht;
zetting;
grondwaterinvloed;
strookbreedte;
uitvoerbaarheid;
kosten;
bouwrisico;
constructieve haalbaarheid.
5. Funderingsvariant F2: paalfundering

Conceptuitgangspunt:

diepe fundering op palen;
toepassen bij slappe bodem;
toepassen bij onvoldoende draagkracht;
toepassen bij verhoogd zettingsrisico;
toepassen bij hogere belasting;
toepassen wanneer strokenfundering niet verantwoord is.

Te toetsen:

paallengte;
paaltype;
draagkracht per paal;
paalbelasting;
paalafstand;
paalkop;
funderingsbalk;
uitvoerbaarheid;
kosten;
risico.
6. Automatische vergelijking

De engine moet F1 en F2 vergelijken op:

Aspect	F1 Strokenfundering	F2 Paalfundering
Draagkracht	toetsen	toetsen
Zetting	toetsen	toetsen
Kosten	vergelijken	vergelijken
Bouwtijd	vergelijken	vergelijken
Risico	vergelijken	vergelijken
Bodemgeschiktheid	beoordelen	beoordelen
Grondwaterinvloed	beoordelen	beoordelen
Constructieve haalbaarheid	beoordelen	beoordelen
Vergunning / acceptatie	beoordelen	beoordelen
7. Output

De engine moet minimaal leveren:

geotechnische uitgangspunten;
grondwaterstand;
bodemprofiel;
funderingsvariant F1;
funderingsvariant F2;
vergelijkingstabel;
aanbevolen fundering;
aannameslog;
bronvermelding;
QA/QC-status;
export naar rapport, dashboard en Digital Twin.
8. Gebruikerskeuze

De gebruiker moet kunnen kiezen:

automatisch beste fundering kiezen;
strokenfundering vastzetten;
paalfundering vastzetten;
beide varianten volledig rapporteren;
handmatig funderingstype aanpassen.
9. Belangrijk principe

Automatisch genereren mag, maar Project Phoenix moet altijd zichtbaar maken:

wat uit brondata komt;
wat door AAIE is aangenomen;
wat projectspecifiek berekend is;
wat nog handmatig gecontroleerd moet worden.