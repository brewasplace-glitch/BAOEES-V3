# PROJECT PHOENIX v8.3 Autonomous Solver Basis & Element Assignment Masterpack v1.0

## Doel
Deze masterpack laat Phoenix na een geslaagde v8.1/v8.2-keten autonoom een traceerbare lineair-elastische v8.3 solverbasis opbouwen, zonder materiaalsterkten, productcertificaten, solverresultaten of professionele goedkeuring te fabriceren.

## Kerncontract
- `PROJECT FACT` heeft altijd voorrang.
- `REFERENCE-GROUNDED DESIGN ASSUMPTION` is alleen toegestaan voor conceptanalyse en wordt expliciet gelogd.
- `UNRESOLVED` blijft een echte blocker wanneer de solver noodzakelijke eigenschappen mist.
- Leveranciersassortiment, producttekst of prijs mag nooit de vereiste ontwerpklasse bepalen.
- In `UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED` mag beschikbaarheid/certificering de conceptanalyse niet opnieuw blokkeren wanneer een traceerbaar analysemodel bestaat.
- In strict/certified mode blijft engineering-kwalificatie vereist.
- Solveruitvoering blijft standaard vergrendeld; de bestaande v8.3 CLI-gate blijft intact.
- Automatische normconformiteitsclaim, professionele goedkeuring en FOR-CONSTRUCTION/PRODUCTION release blijven uitgeschakeld/LOCKED.

## Nieuwe engine
`phoenix/autonomy/autonomous_solver_basis_v8_3.py`

De engine:
1. leest het v8.1 analytische model;
2. gebruikt het v8.2 action/load model;
3. classificeert member- en shell-elementen;
4. koppelt traceerbare lineair-elastische materiaaleigenschappen;
5. leidt voorlopige conceptdoorsneden uit projectgeometrie en geregistreerde Phoenix-referentieregels af;
6. maakt volledige `element_assignments.by_id`;
7. zet uitsluitend bestaande `PROVISIONAL_FIXED_BASE` support candidates om naar review-required solver boundary conditions;
8. schrijft een provenance/registercontract;
9. houdt release LOCKED.

## Referentie-eigenschappen
De meegeleverde config bevat uitsluitend analyse-referenties:
- beton C20/25 als Suriname-reference-grounded analyseklasse; E/dichtheid/Poisson uit de geregistreerde SCIA-materiaaltabel;
- generic masonry lineair-elastische referentie-eigenschappen uit de geregistreerde SCIA-materiaaltabel.

Deze waarden zijn uitdrukkelijk **geen projectspecifieke productverificatie** en **geen vereiste ontwerpklasse**. Ontbrekende materiaalsoorten (zoals timber zonder geschikte bron) blijven blokkeren.

## Structural chain integratie
De patch:
- probeert bij ontbrekende expliciete `structural_analysis_basis` eerst de autonome builder;
- bewaart de bestaande handmatige/expliciete route;
- maakt de tweede legacy `STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED` gate mode-aware;
- gebruikt voor de autonome basis een gecontroleerde by-id assignment applier;
- normaliseert bestaande v8.1 fixed-base candidates voor het solverpakket.

## Verwachte PAT-uitkomst
Voor `PHOENIX-PAT-001` in relaxed mode moet de oude materiaalbeschikbaarheids/certificeringsstop niet terugkomen. Bij voldoende v8.1/v8.2-input moet v8.3 minstens een echt OpenSees/CalculiX solverpakket genereren. De volgende gecontroleerde grens kan daarna `NORMALIZED_SOLVER_RESULTS_REQUIRED` voor v8.4 zijn.

## Niet toegestaan
- geen leverancier-range → ontwerpklasse afleiding;
- geen onbekende E/nu/dichtheid verzinnen;
- geen fake solverresultaten;
- geen auto-ordering/payment;
- geen auto professional approval;
- geen productie-/for-construction release.

## FIXED R3 — v8.1 candidate-map compatibility

The analytical-model contract may store candidate material/section assignments in top-level `material_candidates` and `section_candidates` maps. v8.3 now consumes those maps as fallback when an element-local field is absent. Element-local values always win. This is schema normalization only; no material, section, strength, or certification value is invented.

## FIXED R4 — idempotent release staging

Installer release validation now distinguishes required path presence from actual Git changes. A path already identical to HEAD is valid and is not required to appear in the staged diff. Unexpected staged paths remain forbidden, all required v8.3 paths must exist, and at least one intended v8.3 change must be staged before commit.
