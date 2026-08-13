# PROJECT PHOENIX — CalculiX + Analytical Verification Expansion v1.0

Required baseline: `5a495d330ff4a6fbc635b3a1b4fa6691b59bc9ff`

## Purpose

This pack expands the independent structural verification path while the SCIA live licence is unavailable.

### Analytical verification

Supported idealized reference cases:

1. Simply supported beam under UDL:
   - W = qL
   - RA = RB = qL/2
   - Mmax = qL²/8
2. Cantilever with point load at free end:
   - R = P
   - Mfixed = PL
   - optional tip deflection PL³/(3EI)
3. Axial bar:
   - stress = P/A
   - elongation = PL/(EA)

Phoenix does not infer that an arbitrary project member matches these idealizations. Unsupported cases stay `ANALYTICAL_SCOPE_NOT_SUPPORTED`.

### CalculiX Golden Reference

The engine generates a 100-element B31 second-solver model for `PHX-GOLDEN-SCIA-BEAM-001`.

Known software benchmark:
- span 5 m;
- q = 1 kN/m;
- total vertical load = 5 kN;
- analytical support reaction total = 5 kN;
- analytical reaction each = 2.5 kN;
- analytical maximum sagging moment = 3.125 kNm.

The 5 N numerical tolerance is scoped only to this software Golden Reference cross-check and is not a general engineering tolerance.

### Live-solver governance

Installation never runs CalculiX.

After installation, a live run requires the explicit PowerShell switch:

`-AllowLiveSolver`

`PHOENIX_TEST_MODE` disables live CalculiX even when the switch is supplied.

Raw solver artifacts are hashed and retained. A missing or unparsable `.dat` never becomes a fake PASS.

## Safety

- CalculiX second-solver comparison is technical verification, not professional review.
- No automatic professional approval.
- No automatic code-compliance claim.
- Production and FOR-CONSTRUCTION remain LOCKED.
