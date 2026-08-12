# PROJECT PHOENIX — R9.5.2.6 Package C Seismic Scope & Criteria Masterpack v1.0

## Doel

R9.5.2.6 bouwt het framework voor `PKG-C-SEISMIC-SCOPE-AND-CRITERIA`.

Het pakket behandelt uitsluitend de drie seismische decision/source checks:

- `SOFT_STOREY_STIFFNESS_RATIO`
- `TORSIONAL_DRIFT_RATIO`
- `WEAK_STOREY_STRENGTH_RATIO`

## Harde veiligheidsgrenzen

Phoenix beslist **niet automatisch** of seismische beoordeling van toepassing is.
Phoenix verzint **geen** numerieke seismische criteria.
Phoenix claimt **geen** code compliance of professionele goedkeuring.
Een complete Package-C intake wordt alleen gemarkeerd als
`ELIGIBLE_FOR_LATER_R9_5_PROMOTION`; automatische promotie naar R9.5 is verboden.

Package D (`PKG-D-WEAK-STOREY-SCREENING-REVIEW`) blijft als afzonderlijke
professionele review-gate behouden.

`FOR CONSTRUCTION`, production release en professionele approval blijven `LOCKED`.

## Integratie

De masterpack:

1. vereist branch `project-phoenix`;
2. vereist baseline commit `b9879d71fefb74dde9a106fbd2adebb43e05f200`;
3. vereist local/remote synchronisatie en een clean worktree;
4. installeert policy, template, module, tests en documentatie;
5. integreert één Package-C hook direct na de bestaande Package-E hook in
   `phoenix/autonomy/structural_session_chain.py`;
6. voert syntax-, dedicated-, regressie-, whitespace- en secretcontroles uit;
7. commit en pusht uitsluitend wanneer alle gates slagen;
8. rolt bij de eerste fout terug naar de schone baseline.

## Volgende bouwstap

Na succesvolle R9.5.2.6-installatie is de volgende frameworkstap Package D:
`PKG-D-WEAK-STOREY-SCREENING-REVIEW`.
