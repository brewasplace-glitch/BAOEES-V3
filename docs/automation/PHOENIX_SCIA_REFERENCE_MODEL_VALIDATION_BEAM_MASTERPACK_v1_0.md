# PROJECT PHOENIX — SCIA Reference Model Validation — BEAM Masterpack v1.0

## Baseline

`d6fa925863ee69e936509dd64fd5be29c70d7cf5`

## Reference model

`PHX-GOLDEN-SCIA-BEAM-001`

The three engineering input files are the user-supplied:

- `Beam.esa`
- `Beam.xml`
- `Beam.xml.def`

An embedded preview extracted from `Beam.esa` is stored as `Beam_preview.jpg`.

## Source facts

The XML defines:
- load `LF1`;
- member `B1`;
- load case `LC1`;
- global `Z`;
- `Force`;
- `Uniform`;
- value `-1000`;
- full relative length `0 → 1`.

The supplied `.ESA` already contains a SCIA linear calculation protocol whose LC1 total is:
- loads Z = `-5.0 kN`;
- reactions in nodes Z = `+5.0 kN`.

The Golden Reference declaration therefore uses:
- `q = 1.0 kN/m`;
- `L = 5.0 m`;
- each support reaction = `2.5 kN`;
- `Mmax = qL²/8 = 3.125 kNm`.

These are reference-model benchmark facts, not general Phoenix engineering criteria.

## Runtime validation

`RunAll` performs:

1. exact SHA-256 and XML/source validation;
2. real SCIA Engineer 18.1 `ESA_XML LIN` on a working copy;
3. post-run SCIA protocol extraction;
4. global vertical equilibrium validation;
5. analytical beam benchmark;
6. a CalculiX B31 100-element second-solver reference model;
7. reaction-total comparison SCIA ↔ CalculiX.

If `ccx` is not discoverable, the status remains:
`REFERENCE_MODEL_CALCULIX_CROSSCHECK_PENDING`.

Phoenix must never fake `TECHNICALLY_CROSS_VERIFIED_REFERENCE_MODEL`.

## Boundary

This Golden Reference Model validates software integration only.
It is not PHOENIX-PAT-001 engineering evidence.
It is not professional approval.
It is not a code-compliance claim.
Production and FOR-CONSTRUCTION remain LOCKED.
