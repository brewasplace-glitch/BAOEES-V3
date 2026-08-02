# Phoenix Autonomous Architectural Bootstrap & PAT Continuation Masterpack v1.0

## Doel
Verwijdert de PAT-root blocker `DIMENSIONED_ARCHITECTURAL_MODEL_REQUIRED` voor een voldoende duidelijke autonome BOUW-projectomschrijving, zonder projectfeiten stilzwijgend te verzinnen.

## Nieuwe keten
Projectomschrijving → ruimteprogramma → aannamesregister → maatvoerend conceptmodel → gedetailleerde elementen → Architectural Session Adapter → Digital Twin.

## Veiligheidsgrenzen
Het gegenereerde model is `CONCEPT_CANDIDATE`. Phoenix registreert alle automatische defaults, verzint geen perceelgrenzen/orientatie/jurisdictie en genereert geen stilzwijgend constructief belasting- of materiaalprofiel. Productievrijgave blijft `LOCKED`.

## Gewenste output
Architectuur als capability mag downstream `PASSED` worden zodat Digital Twin en latere engines kunnen starten. Definitieve tekeningen worden niet valselijk als gereed gemarkeerd: output-level coverage kan `BLOCKED` blijven tot tekening-/CAD-export en review echt zijn uitgevoerd.

## PAT-DEFECT-004
Het open venster `AUTONOME PRODUCTIERUN GESTART` wordt tijdens de reeds bestaande actieve-job-monitor bijgewerkt van `BEZIG` naar de terminale backendstatus. Er is geen extra idle-polling toegevoegd.

## Runtime
Runtime v1.8.1 voorkomt hergebruik van een nog draaiende v1.8.0-server na installatie.

## FIXED R1 — regressiecontract gecorrigeerd

De eerste v1.0-installatie bereikte de volledige regressiesuite en stopte op
één verouderde test uit Generic Session Adapter Masterpack v1.0.

Die oude test eiste dat iedere text-only architectuursessie exitcode 10 gaf.
Dat botst met de nieuwe bedoelde werking: een voldoende duidelijke
woningomschrijving in **Autonome projectmodus** mag nu een maatvoerend
**concept-kandidaatmodel** genereren met expliciete aannames en vrijgave-lock.

FIXED R1 wijzigt **geen productiegedrag**. Alleen het regressiecontract wordt
bijgewerkt:

- autonoom + duidelijke woningomschrijving -> adapter `PASSED` als
  `AUTONOMOUS_TEXT_CONCEPT`, met aannamesregister en `production_release=LOCKED`;
- handmatig/begeleid + alleen tekst -> gecontroleerd `BLOCKED_INPUT`;
- onduidelijk/niet-ondersteund gebouwgebruik -> gecontroleerd `BLOCKED`;
- professionele goedkeuring blijft uitgeschakeld.
