# CalculiX Input Argument Recovery v5.4.7

## Confirmed state
MSYS2 and CalculiX 2.23-1 are installed. The package verifier, registry class
reference, runtime PATH and launcher probe all pass.

The real solve still returned exit code 201 because Phoenix invoked:

`ccx.exe phoenix_calculix_acceptance`

## Recovery
v5.4.7 invokes the CalculiX input deck using:

`ccx.exe -i phoenix_calculix_acceptance`

The working directory contains:

`phoenix_calculix_acceptance.inp`

On solver failure, Phoenix now prints and preserves both:

- `calculix_stdout.txt`
- `calculix_stderr.txt`

The real C3D8 solve, DAT/FRD validation, Phoenix detection, commit, push and
final clean synchronization remain mandatory.

No third-party executable is committed to Git.
