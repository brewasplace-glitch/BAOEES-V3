# PROJECT PHOENIX - R9.5.2.7 Package D Weak-Storey Screening Review Masterpack v1.0

## Doel

R9.5.2.7 bouwt het evidence-intake framework voor `PKG-D-WEAK-STOREY-SCREENING-REVIEW`.
Het pakket betreft uitsluitend `WEAK_STOREY_STRENGTH_RATIO` en de professionele beoordeling
van de reeds bestaande kandidaat-screeningproxy voor gebruik bij de kandidaat-gate.

## Vereiste review-input

- `screening_proxy_accepted_for_candidate_gate`
- `screening_proxy_review_reference`
- `reviewer_scope`
- `review_status`

Toegestane `review_status` waarden:

- `INPUT_REQUIRED`
- `REVIEWED_ACCEPTED_FOR_CANDIDATE_GATE`
- `REVIEWED_NOT_ACCEPTED_FOR_CANDIDATE_GATE`

## Harde veiligheidsgrenzen

Phoenix accepteert of verwerpt de screeningproxy niet automatisch.
Phoenix verzint geen reviewer, revieweridentiteit, reviewreferentie, reviewerscope of reviewstatus.
Een kandidaat-gate acceptatie is geen code-compliance claim en geen finale professionele goedkeuring.
Package D vervangt geen Package-E onafhankelijke alternate-path evidence en valideert of verzint geen
normatieve numerieke criteria.

Een complete, expliciet geaccepteerde review kan uitsluitend als
`ELIGIBLE_FOR_LATER_R9_5_PROMOTION` worden gemarkeerd. Automatische promotie naar R9.5 is verboden.
`FOR-CONSTRUCTION`, professionele approval en production release blijven `LOCKED`.

## Integratie

De masterpack:

1. vereist branch `project-phoenix`;
2. vereist baseline `b66a3fcebde7a80323b31d1c68beb7cbf3f2dcd2`;
3. vereist een clean, local/remote gesynchroniseerde worktree;
4. vereist de geinstalleerde R9.5.2.6 Package-C module;
5. installeert policy, template, module, tests en documentatie;
6. integreert een locals-only Package-D hook direct na de bestaande Package-C runtime hook;
7. bewaakt het gerepareerde R9.5.2.2 path-literal contract;
8. voert dedicated, impact-, suite-aware en root-smoke regressies uit;
9. ruimt uitsluitend testgegenereerde bestanden onder `outputs/` op;
10. voert whitespace-, safety-, secret- en worktree-scope gates uit;
11. commit/pusht uitsluitend bij volledig groen resultaat;
12. rolt bij de eerste fout terug naar de schone baseline.
