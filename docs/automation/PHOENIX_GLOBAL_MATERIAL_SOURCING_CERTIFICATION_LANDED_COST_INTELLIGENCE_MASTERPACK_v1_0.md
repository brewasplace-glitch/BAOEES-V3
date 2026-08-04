# Phoenix Global Material Sourcing, Certification & Landed Cost Intelligence Masterpack v1.0

## Doel

Phoenix gebruikt lokale producten wanneer die beschikbaar én technisch geschikt zijn.
Wanneer een vereist product lokaal niet verkrijgbaar of niet engineering-gekwalificeerd is,
wordt een internationale fallback geactiveerd.

De selectievolgorde is:

1. lokale evidence;
2. regionale en internationale supplier-evidence;
3. technische/certificatie-gate;
4. actuele beschikbaarheids- en prijsgate;
5. complete landed-cost berekening tot de projectlocatie;
6. selectie van de goedkoopste technisch geldige optie op **totale geleverde kosten**.

## Landed cost

Phoenix kan een expliciete geldige "delivered to Paramaribo"-offerte gebruiken, of de
landed cost opbouwen uit productprijs, verpakking, origin haulage, export handling,
vracht, verzekering, destination handling, invoerrecht, belasting, inklaring en
last-mile transport.

Ontbrekende vracht, rechten, belastingen of FX worden niet verzonnen.

## Constructieve veiligheid

Een geïmporteerd constructief product wordt pas engineering-gekwalificeerd wanneer
een engineering_material_id, vereiste technische eigenschappen en traceerbare
certificatie-evidence beschikbaar zijn.

## Bronverwerving

De engine leest projectspecifieke JSON-evidence en expliciet geconfigureerde HTTPS
JSON-feeds via `project_manifest.global_material_source_urls`.

Er is bewust geen impliciete generieke webscraping/search-engine fallback. Als geen
betrouwbare provider/feed is geconfigureerd, blijft de sourcing-gate BLOCKED in plaats
van een actuele marktprijs of certificaat te fabriceren.

## Integratie

De masterpack koppelt de samengevoegde local/imported material selection aan:

- Architecture / project material supply gate;
- Digital Twin;
- Structural v8.3 solver-material gate;
- Cost & Planning;
- Minimum Deliverable STR_MATERIALS;
- QA/QC / closure.

Automatische bestelling, betaling en professionele goedkeuring blijven uitgeschakeld.
Production release blijft LOCKED.
