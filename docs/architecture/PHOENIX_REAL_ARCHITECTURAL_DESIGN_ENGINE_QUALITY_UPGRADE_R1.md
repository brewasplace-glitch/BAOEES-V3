# PROJECT PHOENIX — Real Architectural Design Engine Quality Upgrade R1

## Doel

R1 voegt een harde architectonische kwaliteitslaag toe tussen `real_spatial` authoring en Phase-19 `EVIDENCE_VERIFIED`.

Phoenix controleert nu naast bestand-/IFC-aanwezigheid ook:
- aantal en diversiteit van ruimten;
- positieve kamergeometrie en minimum ruimte-oppervlak;
- ruimtelijke overlap per verdieping;
- wand- en openingdichtheid;
- semantische/topologische uniciteit van A–E;
- minimum architectonische kwaliteitsscore.

## Open-source-first review

- **IfcOpenShell** blijft de primaire BIM/IFC-basis.
- **TopologicPy** is kandidaat voor R2: adjacency graphs, circulation en topologische ruimtelijke analyse.
- **Ladybug Tools / Honeybee** is kandidaat voor R3: daglicht-, zon-, klimaat- en energiechecks.

R1 installeert bewust geen nieuwe externe dependency; eerst wordt de bestaande Phoenix-geometrie fail-closed gekwalificeerd.

## Governance

`CONCEPT_QA_ONLY_NOT_FOR_CONSTRUCTION`

De QA-score vervangt geen architect, constructeur, landmeter, bevoegd gezag of professionele vrijgave.
