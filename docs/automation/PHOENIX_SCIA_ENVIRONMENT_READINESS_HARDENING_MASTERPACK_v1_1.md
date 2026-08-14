# PROJECT PHOENIX — SCIA Environment Readiness Hardening Masterpack v1.1

Required baseline: `f0a1b578ebf5a659597a64e5c7a68a311787b42c`

## Purpose

This layer separates SCIA environment readiness into independently auditable stages.

1. Runtime files present.
2. Optional explicit built-in help contract probe.
3. License target syntax (`PORT@HOST`).
4. Read-only Windows service state.
5. Read-only TCP reachability.
6. Existing probe classification.
7. Explicit live ESA_XML probe.

No earlier stage is allowed to masquerade as final solver readiness.

## Key readiness rule

A reachable license endpoint is only:

`SCIA_LICENSE_ENDPOINT_REACHABLE_PROBE_REQUIRED`

It is **not** `SCIA_LIVE_ENVIRONMENT_READY`.

Only a successful explicitly authorized live probe with ESA_XML return code `0` may produce:

`SCIA_LIVE_ENVIRONMENT_READY`.

## SCIA 18.1 exit code contract

The target machine's own ESA_XML built-in help established:

- 0 — Succeeded
- 1 — Unable to initialize MFC
- 2 — Missing arguments
- 3 — Invalid arguments
- 4 — Unable to open ProjectFile
- 5 — Calculation failed
- 6 — Unable to initialize application environment
- 7 — Error during update ProjectFile by XMLUpdateFile
- 8 — Error during create export outputs
- 9 — Error during create XML outputs
- 10 — Error during update ProjectFile by XLSX Update

The currently observed SCIA failure is therefore classifiable as:

`BLOCKED_SCIA_APPLICATION_ENVIRONMENT`

without rerunning SCIA.

## Mutation boundaries

The engine never:

- starts or stops `lmadmin`;
- starts or stops FLEXnet services;
- changes Lockman settings;
- changes the license target;
- modifies the original Golden Reference `.ESA`.

The optional runtime-help probe executes ESA_XML without project or solver calculation.
The live probe is separately locked behind explicit `-AllowLiveProbe`.

## Safety

- environment readiness is not engineering approval;
- no automatic professional approval;
- no automatic code-compliance claim;
- Production remains LOCKED;
- FOR-CONSTRUCTION remains LOCKED.
