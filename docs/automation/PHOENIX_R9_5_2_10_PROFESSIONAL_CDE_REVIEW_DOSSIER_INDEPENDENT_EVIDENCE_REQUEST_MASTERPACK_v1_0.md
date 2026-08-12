# PROJECT PHOENIX — R9.5.2.10 Professional C/D/E Review Dossier & Independent Evidence Request Pack

## Doel

R9.5.2.10 maakt het resterende professionele werk voor PHOENIX-PAT-001 uitvoerbaar zonder
professionele besluiten te simuleren.

De huidige projectstatus waarop deze stap is gebaseerd:

- technische analyses vereist: 0;
- unresolved checks: alternate load path, soft-storey, torsional drift en weak-storey;
- unresolved packages: C, D en E;
- Production en FOR-CONSTRUCTION: LOCKED.

## Runtimevolgorde

1. R9.5.2.10 inventariseert bestaande evidence en controleert expliciete review returns;
2. alleen mechanisch complete en `submission_confirmed=true` returns worden naar combined intake gekopieerd;
3. R9.5.2.9 normaliseert de combined intake;
4. Package E, C en D blijven de inhoudelijke validators;
5. R9.5.2.8 blijft de enige controlled requalification gate.

## Package C

Het dossier toont de bestaande R9.3 evidence voor:

- SOFT_STOREY_STIFFNESS_RATIO;
- TORSIONAL_DRIFT_RATIO;
- WEAK_STOREY_STRENGTH_RATIO.

De reviewer moet zelf seismic applicability beslissen. Bij APPLICABLE moeten de drie criteria
elk een traceerbare source record en clause/reference krijgen.

## Package D

Het dossier toont de bestaande weak-storey candidate-screening evidence.
De professionele reviewer moet expliciet accepteren of afwijzen voor de candidate gate,
met review reference en reviewer scope.

## Package E

R9.3 alternate-path screening blijft `INTERNAL_SCREENING_ONLY`.
Het request pack vraagt daarom echte onafhankelijke engineering evidence inclusief:

- evidence reference;
- exact repository-relative source file;
- SHA-256;
- independent review status/reference;
- explicit independently verified decision;
- acceptance criterion + traceability;
- reviewer identity/signature reference;
- independence confirmation + basis.

R9.5.2.10 controleert alleen padveiligheid, file existence, SHA-integriteit en structurele compleetheid.
Package E blijft de engineering validator.

## Harde grenzen

Geen automatische professional approval, code-compliance claim, seismic applicability,
normatieve criteria, weak-storey acceptance, independent evidence, R9.5 success claim,
Production release of FOR-CONSTRUCTION release.

## Vereiste baseline

`dcd742e845014cf13b1c6ec04371c8e9d912ea1b`
