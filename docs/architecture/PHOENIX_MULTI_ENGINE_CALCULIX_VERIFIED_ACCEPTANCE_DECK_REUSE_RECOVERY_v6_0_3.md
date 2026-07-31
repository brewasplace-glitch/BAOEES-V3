# Multi-Engine CalculiX Verified Acceptance Deck Reuse Recovery v6.0.3

## Confirmed failure

The v6.0.2 qualification no longer crashed, but its newly constructed C3D8
deck produced empty DAT/FRD results.

## Recovery

v6.0.3 does not maintain a second CalculiX acceptance implementation.

The unified suite invokes the already installed and previously proven module:

`phoenix/adapters/open_source/calculix_acceptance_v5_4_9.py`

That module provides the exact accepted contract:

- C3D8 solid cube;
- `*STATIC, SOLVER=SPOOLES`;
- `ccx.exe -i phoenix_calculix_acceptance`;
- CLOAD within the static step;
- non-empty DAT and FRD artifacts;
- DAT displacement validation;
- FRD dataset-marker validation;
- explicit rejection of PaStiX;
- explicit confirmation of SPOOLES;
- real SHA-256 artifact evidence.

The suite additionally records the wrapper stdout and stderr so a future
qualification failure remains diagnosable.

No engine is reinstalled. Production release remains locked unless all six
real engine qualifications pass.
