# Phoenix Architectural Suite v4.0.1 — Call-depth recovery

## Root cause
The v4.0.0 PowerShell installer defined a function named `Py` and then invoked
`py -3` inside that function. PowerShell command names are case-insensitive, so
the invocation resolved recursively to the function itself and caused a call
depth overflow.

## Recovery
v4.0.1 resolves the Python executable before installation and invokes its
absolute command path through `Invoke-Python`.

No v4.0.0 repository payload was committed because the failure occurred before
copy, test, commit and push completion.
