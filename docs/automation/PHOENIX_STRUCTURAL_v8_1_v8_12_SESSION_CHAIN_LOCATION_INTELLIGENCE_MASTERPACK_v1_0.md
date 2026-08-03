# Phoenix Structural v8.1–v8.12 Session Chain & Location Intelligence Masterpack v1.0

## Doel

Deze masterpack vervangt de generieke blokkade
`V8_1_TO_V8_12_VALIDATED_INPUT_MAPPING_REQUIRED` door een echte,
fase-voor-fase Session Chain.

Phoenix voert iedere fase uit zodra het exact vereiste projectspecifieke
inputcontract beschikbaar is. Ontbrekende engineeringwaarden worden niet
verzonnen.

## Constructieve keten

- v8.0 -> v8.1: gevalideerde geometrische mapping uit architectuurmodel,
  detailed elements en v8.0 kandidaatmodel.
- v8.2: expliciete belastingen + combinaties vereist.
- v8.3: expliciete solverbasis, materiaaldata, doorsneden en elementtoewijzing vereist.
- v8.4: genormaliseerde solverresultaten + raw solver evidence vereist.
- v8.5: expliciete codebasis en member-verificatieregels vereist.
- v8.6: expliciete stabiliteits/tweede-orde/robuustheidsevidence vereist.
- v8.7: expliciete verbinding-/oplegging-/joint-evidence vereist.
- v8.8: projectspecifieke geotechnische funderingsinterface vereist.
- v8.9: funderingsontwerp, wapening, details en verificaties vereist.
- v8.10: engineering package + QA/QC evidence vereist.
- v8.11: echte menselijke engineering review en release-autorisatie vereist.
- v8.12: revision/change-impact/IFC document-control input vereist.

De keten stopt gecontroleerd bij de eerste ontbrekende echte input en meldt
precies welk contract ontbreekt.

## Location Intelligence

Projectlocatie wordt uitsluitend opgelost uit:
1. expliciete projectcontext/manifest;
2. expliciete locatie/adresregel in de projectomschrijving;
3. exacte match met de beperkte bekende-localiteitencatalogus.

De UI-taal wordt nooit als projectland gebruikt.

Location Intelligence schrijft:
- locatie;
- land/gebiedsdeel;
- regio;
- gemeente;
- jurisdiction key;
- lokale valuta via de bestaande Currency Catalog;
- eventuele expliciete coördinaten.

Geen kadastrale grens, bestemmingsplanregel of vergunningconclusie wordt
automatisch verzonnen.

## Koppelingen

Resolved location context wordt doorgegeven aan:
- Permit routing;
- Local Cost Intelligence;
- Digital Twin;
- project manifest.

## Veiligheid

- automatische design-load fabricatie: UIT
- automatische codebasisfabricatie: UIT
- automatische solver-resultaatfabricatie: UIT
- automatische geotechnische fabricatie: UIT
- automatische professionele goedkeuring: UIT
- automatische construction release: UIT
- productievrijgave: LOCKED

## FIXED R1 — legacy pilot safety marker restored

The first v1.0 installer reached the full repository regression suite:
**130 tests were executed and only one failed**.

The failed regression was
`test_10_structural_adapter_exposes_v8_chain_without_pilot_dependency`.
The new structural chain was already generic and did not invoke any BB35,
pilot, Moskee, Plutostraat or Bruynzeel runner, but the explicit metadata
marker `"legacy_pilot_dependency": False` had been removed when
`run_structural()` was replaced.

FIXED R1 restores that safety marker in the structural chain manifest and
adapter metadata. Structural calculations, mappings, location logic and
engineering gates are otherwise unchanged.
