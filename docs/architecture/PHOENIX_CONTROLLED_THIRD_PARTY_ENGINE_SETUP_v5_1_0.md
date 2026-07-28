# Controlled Third-Party Engine Installation and Configuration Pack v5.1.0

## Purpose
Install or register approved external engines without bundling unknown binaries in
the Phoenix repository.

## Automated route
IfcOpenShell Python is installed using the official documented PyPI route and its
approved pinned version.

## Controlled local-import route
IfcConvert, FreeCAD, QGIS, EnergyPlus, OpenSees and CalculiX are registered from a
local download/extraction folder after SHA-256 verification.

The process:
1. requires an explicit engine identifier;
2. finds only approved executable names;
3. requires the user-supplied SHA-256 to match;
4. copies the complete engine folder into `tools/third_party_engines`;
5. records the registered executable and hash;
6. runs a non-destructive version/acceptance probe;
7. prepares the relevant Phoenix environment variable;
8. reruns the adapter-layer detection.

## Why binaries are not bundled
Third-party downloads change independently, may require licence acceptance or
administrator rights, and CalculiX Windows distributions are provided through
third parties referenced by the upstream project. Phoenix therefore records the
chosen source and checksum instead of silently trusting a binary.
