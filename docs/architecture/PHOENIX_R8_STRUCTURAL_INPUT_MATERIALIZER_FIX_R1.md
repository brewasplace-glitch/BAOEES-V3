# PHOENIX R8 Structural Input Materializer FIX R1

The first installer failed because legacy/minimal manifest unit fixtures were forced
through structural-input materialization. Those fixtures are valid for manifest/hash
testing but intentionally do not contain storeys, footprint, walls and openings.

FIX R1 adds an explicit eligibility gate:
- minimal/legacy manifest fixtures preserve `CONTRACT_BOUND_INPUTS_REQUIRED`;
- eligible authoritative real layouts materialize the existing structural adapter inputs;
- no structural solver is executed.
