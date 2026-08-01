# Phoenix Detailed Architectural PowerShell TrimStart Recovery v6.6.1

v6.6.0 stopped while building the payload target list because PowerShell could
not convert a multi-character string to `System.Char` for `TrimStart`.

v6.6.1 replaces every unsafe call with:

`TrimStart([char[]]@([char]92,[char]47))`

This removes leading backslash and forward-slash characters deterministically.
The detailed architectural engine, tests, rollback, commit/push logic and
release gates are unchanged.
