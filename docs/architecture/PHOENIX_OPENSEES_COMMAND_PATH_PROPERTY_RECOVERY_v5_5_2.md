# OpenSees Command Path Property Recovery v5.5.2

## Confirmed failure

PowerShell resolved the `py` command object, but `.Source` was empty on the
user's system.

## Recovery

v5.5.2 resolves a command path in this order:

1. `.Path`
2. `.Source`
3. `.Definition`

The selected value is converted to a string, trimmed, and validated with:

`Test-Path -LiteralPath <launcher> -PathType Leaf`

For `py.exe`, Phoenix then resolves the actual Python interpreter through
`sys.executable` and validates that path again before pip starts.

No repository mutation occurs before launcher resolution, Python resolution
and OpenSeesPy import verification succeed.
