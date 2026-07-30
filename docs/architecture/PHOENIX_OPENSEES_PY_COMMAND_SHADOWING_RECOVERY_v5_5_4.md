# OpenSees `py` Command Shadowing Recovery v5.5.4

## Confirmed failure

PowerShell command names are case-insensitive. The installer defined a helper
function named `Py`, then used `Get-Command py`. PowerShell resolved the helper
function instead of the Windows `py.exe` launcher.

## Recovery

v5.5.4:

1. renames the helper function from `Py` to `Invoke-PhoenixPython`;
2. searches only application commands:
   - `py.exe`
   - `python.exe`
   - `python3.exe`
3. uses `Get-Command ... -CommandType Application`;
4. preserves the StrictMode-safe `PSObject.Properties` path resolution;
5. validates both the launcher and resolved `sys.executable` path;
6. starts pip only after Python resolution succeeds;
7. preserves real OpenSees analysis, detector, commit, push and clean-sync gates.

No repository mutation occurs before Python and OpenSeesPy verification.
