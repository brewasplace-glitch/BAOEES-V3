# Project Phoenix 4.41 — Phase 19 FIX R4

## Doel

FIX R4 koppelt geüploade locatiebestanden veilig aan de bestaande Phase-19-run en genereert exact vijf voorlopige woonhuisvarianten A–E. De startknop hervat een passende geblokkeerde run automatisch en voorkomt dubbele runs voor hetzelfde verzoek.

## Bewijsgrenzen

- De bestandsnaam, bestandsgrootte en SHA-256 van ieder uploadbestand worden gecontroleerd.
- De upload geldt uitsluitend als conceptbron met door de gebruiker opgegeven locatie.
- Landmeting, kadastrale grens, juridische toepasselijkheid, bodemgegevens en professionele vrijgave worden niet afgeleid of goedgekeurd.
- Alle varianten dragen de status `CONCEPT_ONLY_NOT_FOR_CONSTRUCTION`.

## Projectproef Perceel 314

De conceptgenerator bindt 300 m2, twee bouwlagen, drie slaapkamers, een tweewagengarage, master suite, zwembadreservering, plat dak met stalen buisvakwerken, rasters 3 × 6 m en 2 × 6 m, gemengde materialen en de opgegeven NAP-peilen. Ontbrekende terreinafmetingen en professionele onderzoeken blijven expliciete aannames en blokkades.

## Varianten

De vaste volgorde is:

1. A — passieve koeling
2. B — lage kosten
3. C — robuustheid
4. D — binnen-buitenrelatie
5. E — gebalanceerd

Voor elke variant worden een JSON-contract en een schematische SVG gegenereerd. De gebruiker kiest daarna de voorkeursvariant; Phoenix activeert geen professionele engine en verleent geen vrijgave.
