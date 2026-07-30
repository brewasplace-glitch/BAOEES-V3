# OpenSees StrictMode Property-Safe Recovery v5.5.3

Direct access to a missing property such as `$g.Path` fails under
`Set-StrictMode -Version Latest`.

v5.5.3 inspects `Path`, `Source` and `Definition` through
`$g.PSObject.Properties[$PropertyName]`. Missing properties are skipped.
The selected launcher and the resolved `sys.executable` path are both
validated with `Test-Path` before pip starts.

No repository mutation occurs before Python and OpenSeesPy verification.
