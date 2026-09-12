# PHOENIX 4.41 - Final structural package open-source review

## Primary issue-exchange option - IfcOpenShell BCF

IfcOpenShell 0.8.5 includes BCF support. BCF is an open buildingSMART collaboration format intended for exchange of coordination topics and issues between disciplines. The library supports BCF-XML 2.1 and 3.0 and BCF-API 3.0.

Phoenix therefore attempts a BCF 3.0 export of the open release holds.

## Deterministic fallback - JSON / CSV / Markdown

BCF is non-blocking. Every hold is always exported to machine-readable JSON, CSV and individual Markdown closure requests. This guarantees a usable package even if the BCF runtime is unavailable.

## Desktop BIM fallback - FreeCAD 1.1.3

FreeCAD remains an optional open-source desktop consumer for IFC/CAD inspection and is not a runtime release dependency.

## Report stack

- python-docx 1.2.0 - editable handover report;
- ReportLab 5.0.1 - independent PDF report;
- pypdf 5.9.0 - PDF verification.

None of these tools is allowed to change `FOR_CONSTRUCTION_RELEASE` while mandatory holds remain open.
