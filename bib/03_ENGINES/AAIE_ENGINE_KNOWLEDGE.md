AAIE ENGINE KNOWLEDGE

AAIE = Autonomous Assumption and Inference Engine.

Status: officiële engine-kennis voor Project Phoenix / BAOEES V3.

1. Doel

AAIE vult ontbrekende projectgegevens automatisch aan wanneer de gebruiker of brondata niet volledig is.

AAIE mag gegevens genereren, maar nooit verborgen toepassen.

Alle automatisch gegenereerde waarden moeten zichtbaar worden opgeslagen in het aannameslog.

2. Wat AAIE mag aanvullen

AAIE mag conceptueel aanvullen:

projecttype;
locatiegegevens;
maaiveldniveau;
grondwaterstand;
bodemprofiel;
funderingskeuze;
constructieve uitgangspunten;
parkeeruitgangspunten;
vergunninguitgangspunten;
kostenkengetallen;
planning;
risico’s;
ontbrekende rapportonderdelen.
3. Verplichte registratie per aanname

Elke aanname moet minimaal bevatten:

naam;
waarde;
discipline;
reden;
bron;
methode;
betrouwbaarheid;
datum/tijd;
status;
gebruiker kan wijzigen: ja/nee.
4. Betrouwbaarheid

AAIE moet betrouwbaarheid aangeven als:

hoog;
middel;
laag;
onbekend.

Wanneer betrouwbaarheid laag of onbekend is, moet het systeem een waarschuwing geven.

5. Fallbacks

Vaste fallback voor grondwaterstand:

P = -0,50 m

Vaste fallback voor funderingsonderzoek:

altijd strokenfundering en paalfundering als varianten genereren;
automatisch vergelijken;
geen definitieve funderingskeuze zonder toetsing.
6. Koppeling met Digital Twin

AAIE-resultaten moeten naar de Digital Twin worden geschreven.

Elk automatisch gegenereerd gegeven moet herkenbaar blijven als:

AAIE-generated

7. Koppeling met rapporten

Rapporten moeten onderscheid maken tussen:

bekende gegevens;
brongegevens;
aannames;
automatische inferenties;
nog te controleren punten.
8. Gebruikerscontrole

De gebruiker moet aannames kunnen:

accepteren;
aanpassen;
verwijderen;
vervangen door handmatige waarde;
markeren als definitief;
markeren als voorlopig.
9. Belangrijk principe

AAIE is bedoeld om Project Phoenix autonoom te laten werken, maar altijd controleerbaar en transparant.