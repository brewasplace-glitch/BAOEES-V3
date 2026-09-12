# PHOENIX 4.41 - DXF/DWG Open-source Review

## Selected primary viewer: LibreCAD 2.2.1.5

LibreCAD is GPLv2 and its official project states that it reads DXF/DWG and is built with `libdxfrw`.

Reason selected:
- direct 2D architectural CAD viewing;
- Windows installer;
- active stable release;
- open-source;
- lightweight compared with a full BIM/CAD suite.

## Independent DWG fallback/backend: GNU LibreDWG 0.14

LibreDWG is GPLv3-or-later. The 0.14 release publishes a Windows x64 binary and SHA256 checksum.
Phoenix pins the official `libredwg-0.14-win64.zip` SHA256 to:

`1ad7e15344d20b3426c3435b078d82fb84b35062815946b2cca9c5fc9810fea8`

`dwg2dxf` is used to create a DXF that the Phoenix-native DXF parser can inspect.

## Phoenix-native parser: ezdxf 1.4.4

ezdxf is MIT licensed and supports DXF reading/writing over the common AutoCAD DXF generations.
Phoenix uses it for deterministic programmatic inspection.

## Rejected as primary

QCAD Community Edition was not selected because its open-source Community Edition does not include the proprietary DWG add-on used by QCAD Professional.

FreeCAD remains useful for BIM/3D work, but for this requested 2D DXF/DWG viewing function LibreCAD is a smaller and more direct fit.


## FIX R2 — known LibreDWG 0.14 conversion limitation

A current upstream LibreDWG issue documents `dwg2dxf` output containing duplicate
handles that can make the resulting DXF unloadable, including in ezdxf 1.4.4.
Phoenix therefore treats the LibreDWG converter as an independent machine bridge,
not as the sole proof that a DWG can be faithfully parsed.

Direct interactive DWG opening in LibreCAD remains the primary viewer path.
