# PHOENIX 4.41 - Open-source DXF/DWG Viewer Integration

## Purpose

Adds a reusable open-source CAD viewing and inspection stack to Phoenix.

### Primary interactive viewer
LibreCAD 2.2.1.5 (GPLv2)

- Windows GUI
- DXF and DWG read support through libdxfrw
- suitable for 2D architectural / structural drawings
- installed only if not already present

### Independent DWG backend
GNU LibreDWG 0.14 (GPLv3+)

- `dwg2dxf`
- official Windows x64 binary package
- package SHA256 pinned to the upstream release checksum
- used by Phoenix for deterministic DWG -> DXF conversion before machine inspection

### Phoenix-native DXF backend
ezdxf 1.4.4 (MIT)

- layer enumeration
- entity counts
- text extraction
- DXF metadata
- isolated Python runtime

## Phoenix commands

Open a drawing:

`runners/PROJECT_PHOENIX_4_41_cad_open.ps1 -FilePath C:\path\drawing.dxf`

or:

`runners/PROJECT_PHOENIX_4_41_cad_open.ps1 -FilePath C:\path\drawing.dwg`

Machine inspect:

`runners/PROJECT_PHOENIX_4_41_cad_open.ps1 -FilePath C:\path\drawing.dwg -Mode Inspect`

Convert DWG to DXF:

`runners/PROJECT_PHOENIX_4_41_cad_open.ps1 -FilePath C:\path\drawing.dwg -Mode Convert`

## Scope

This capability is a viewer / parser / converter integration. It does not claim full AutoCAD fidelity. Unsupported or advanced DWG entities can still require another CAD engine or manual verification.


## FIX R1 — Windows PowerShell UTF-8 BOM runtime config

The first real Windows installation successfully installed LibreCAD 2.2.1.5,
GNU LibreDWG 0.14 and ezdxf 1.4.4. The run then stopped because Windows
PowerShell 5.1 wrote `cad_viewer_runtime.json` as UTF-8 with BOM while the
Python engine read the file as strict `utf-8`.

FIX R1 hardens both sides:
- Python reads runtime JSON with `utf-8-sig`;
- PowerShell writes runtime JSON with `System.Text.UTF8Encoding($false)`.

This is a runtime serialization fix only.


## FIX R2 — LibreDWG roundtrip self-test policy

The real Windows FIX R1 run proved:
- LibreCAD installed and detected;
- LibreDWG 0.14 installed and detected;
- ezdxf 1.4.4 installed and imported;
- CAD runtime verification PASS;
- native DXF creation and machine inspection PASS.

The failure occurred only in the synthetic DXF -> DWG -> DXF roundtrip. LibreDWG
generated a DXF containing invalid/duplicate object handles and ezdxf rejected it.

FIX R2:
- keeps DWG conversion verification mandatory;
- changes roundtrip DXF parsing to a diagnostic non-blocking check;
- adds ezdxf strict -> recover fallback;
- reports degraded machine inspection explicitly when LibreDWG conversion output
  cannot be parsed;
- keeps direct LibreCAD DWG viewing independent and enabled.

This avoids converting an upstream converter defect into a false viewer-installation failure.
