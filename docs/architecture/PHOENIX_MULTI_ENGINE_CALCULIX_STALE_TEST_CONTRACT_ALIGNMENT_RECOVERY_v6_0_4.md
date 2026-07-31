# Multi-Engine CalculiX Stale Test Contract Alignment Recovery v6.0.4

## Confirmed system result

The v6.0.3 pre-payload run successfully qualified all six engines and unlocked
the production release gate.

The installer then stopped because tests inherited from v6.0.2 still expected
an inline CalculiX deck inside the unified runner.

## Removed stale assumptions

The aligned tests no longer require:

- a `threads` key from the removed inline-deck configuration;
- a literal `*STATIC,SOLVER=SPOOLES` statement in the unified runner;
- a literal `OMP_NUM_THREADS` assignment in the unified runner.

Those details belong to the verified standalone acceptance implementation:

`phoenix/adapters/open_source/calculix_acceptance_v5_4_9.py`

## Active test contract

v6.0.4 verifies:

1. configuration references the v5.4.9 acceptance module;
2. the runner invokes that module;
3. the runner validates its JSON evidence;
4. SPOOLES, C3D8, DAT and FRD contracts are represented semantically;
5. the execution marker is resolved using Python AST rather than fragile raw
   source substring matching;
6. the real six-engine pre-payload qualification must still pass.

No engine logic is weakened and no simulated result is accepted.
