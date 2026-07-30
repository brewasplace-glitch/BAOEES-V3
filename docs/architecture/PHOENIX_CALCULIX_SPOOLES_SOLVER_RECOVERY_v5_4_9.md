# CalculiX SPOOLES Solver Recovery v5.4.9

## Confirmed failure

The real C3D8 model was valid and CalculiX assembled the matrix, but the MSYS2
build selected PaStiX and terminated with Windows access-violation code
`3221225477` (`0xC0000005`).

## Recovery

The acceptance deck now explicitly selects:

`*STATIC, SOLVER=SPOOLES`

Phoenix additionally rejects a run when:

- solver output still contains `PaStiX`;
- solver output does not confirm `SPOOLES`;
- the solver exit code is non-zero;
- DAT or FRD evidence is missing or invalid.

The installed MSYS2 and CalculiX 2.23-1 package, runtime PATH, `-i` argument,
load-step order, repository safety, detector, commit and push gates remain
unchanged.

No third-party binary is committed to Git.
