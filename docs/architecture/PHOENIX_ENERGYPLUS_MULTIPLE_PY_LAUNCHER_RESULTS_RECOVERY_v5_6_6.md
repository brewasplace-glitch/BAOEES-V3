# EnergyPlus Multiple Python Launcher Results Recovery v5.6.6

`Get-Command py.exe` returned both the real Python launcher and the
WindowsApps alias. v5.6.6 enumerates each application result separately,
excludes WindowsApps, validates the launcher file, resolves `sys.executable`,
and validates the resulting Python 3 interpreter.

The existing EnergyPlus 26.1.0 installation is reused. No download, UAC or
reinstallation is performed.
