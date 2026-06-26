PROJECT PHOENIX ASSUMPTIONS

Status: vaste aannames en automatische inferentieregels voor Project Phoenix / BAOEES V3.

1. Doel

Dit bestand legt vast welke aannames Project Phoenix automatisch mag gebruiken wanneer projectspecifieke gegevens ontbreken.

Alle aannames moeten zichtbaar blijven voor de gebruiker en mogen nooit verborgen worden toegepast.

2. Grondwaterstand

Standaard fallback:

P = -0,50 m

Deze waarde wordt gebruikt wanneer geen projectspecifieke grondwaterstand beschikbaar is.

Status:

type: automatische aanname;
discipline: geotechniek;
bron: Brewster / BAOEES standaard;
betrouwbaarheid: middel;
gebruiker mag overschrijven: ja.
3. Automatische bepaling grondwaterstand

Project Phoenix moet eerst proberen de grondwaterstand automatisch te bepalen op basis van:

locatie;
kaartuitsnede;
satellietbeeld;
maaiveldinformatie;
bodemdata;
omgevingstype;
oppervlaktewater in de nabijheid;
eerdere projectgegevens;
open data;
gebruikersinput.

Wanneer de automatische bepaling onvoldoende betrouwbaar is, gebruikt het systeem P = -0,50 m als fallback.

4. Geo-informatie

Wanneer geen volledig grondonderzoek beschikbaar is, mag AAIE een concept-bodemprofiel genereren.

Het gegenereerde profiel moet altijd als concept worden gemarkeerd.

Minimale output:

laagopbouw;
grondsoort per laag;
indicatieve draagkracht;
indicatieve zettingsgevoeligheid;
risico-inschatting;
advies vervolgonderzoek.
5. Fundering

Project Phoenix moet standaard twee funderingsvarianten genereren:

F1 Strokenfundering

Conceptuitgangspunt:

strookbreedte: 150 cm tot 200 cm;
strookhoogte: 40 cm;
funderingsbalk: 50 cm x 60 cm;
funderingsbalk in hart strook;
toepassen onder dragende wanden en kolommen.

Te toetsen op:

draagkracht;
zetting;
grondwater;
uitvoerbaarheid;
kosten;
bouwrisico.
F2 Paalfundering

Conceptuitgangspunt:

toepassen bij onvoldoende draagkracht;
toepassen bij slappe lagen;
toepassen bij verhoogd zettingsrisico;
toepassen bij hogere belastingen;
toepassen wanneer fundering op staal niet verantwoord is.

Te toetsen op:

paallengte;
draagkracht per paal;
paaltype;
paalafstand;
paalbelasting;
paalkop / funderingsbalk;
kosten;
uitvoerbaarheid.
6. Automatische funderingsvergelijking

Project Phoenix moet F1 en F2 automatisch vergelijken op:

Aspect	F1 Strokenfundering	F2 Paalfundering
Draagkracht	toetsen	toetsen
Zetting	toetsen	toetsen
Kosten	vergelijken	vergelijken
Risico	vergelijken	vergelijken
Bouwtijd	vergelijken	vergelijken
Bodemgeschiktheid	beoordelen	beoordelen
Vergunning / constructie	beoordelen	beoordelen

De beste variant mag automatisch worden geadviseerd, maar beide varianten moeten rapportabel blijven.

7. Gebruikerskeuze

De gebruiker moet kunnen kiezen uit:

automatisch beste fundering kiezen;
alleen strokenfundering uitwerken;
alleen paalfundering uitwerken;
beide varianten volledig rapporteren;
handmatig aangepaste funderingsvariant gebruiken.
8. Aannameslog

Elke automatische aanname moet worden opgenomen in het aannameslog.

Per aanname:

naam;
waarde;
discipline;
reden;
bron;
betrouwbaarheid;
status;
datum/tijd;
gebruiker-goedkeuring.
9. Bronkoppeling

Elke aanname moet worden gekoppeld aan STEE-bronvermelding wanneer er een bron beschikbaar is.

Wanneer er geen bron beschikbaar is, moet de aanname worden gemarkeerd als:

AAIE fallback assumption

10. Belangrijk principe

Automatisch genereren is toegestaan, maar Project Phoenix moet altijd duidelijk tonen:

wat zeker is;
wat aangenomen is;
wat automatisch is gegenereerd;
wat nog handmatig gecontroleerd moet worden;
wat projectspecifiek berekend moet worden.