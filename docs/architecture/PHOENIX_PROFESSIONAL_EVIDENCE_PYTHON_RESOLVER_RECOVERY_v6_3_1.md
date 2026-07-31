# Phoenix Professional Evidence Python Resolver Recovery v6.3.1

## Confirmed failure

The v6.3.0 installer used a compressed `Where-Object` expression whose
`-notmatch` and `-and` operators were not separated safely. PowerShell treated
the WindowsApps filter as a positional argument and stopped before preflight.

## Recovery

v6.3.1 uses a dedicated `Resolve-Python3` function that:

1. checks `python.exe`, `py.exe`, and `python3.exe` separately;
2. excludes Microsoft WindowsApps aliases;
3. resolves `py.exe -3` to the real `sys.executable`;
4. verifies that the selected runtime is Python major version 3;
5. stops before repository mutation when no valid runtime is available.

The professional evidence engine content and safety policy remain unchanged.
Automatic professional approval remains disabled.
