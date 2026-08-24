# Project Phoenix — LibreOffice Default Document Routing Wiring v1.0

## Classification

`EXTEND_ROUTING_ONLY`.

The existing LibreOffice adapter is reused. No new Office engine is built and no
native Phoenix document generator is replaced.

## Routing

Office-family documents:

- DOC / DOCX / ODT / RTF
- XLS / XLSX / ODS / CSV
- PPT / PPTX / ODP

are opened through `LibreOfficeOfficeAdapter`.

PDF and other artifacts continue through the operating-system default viewer.

## DocumentExportEngine

The existing `DocumentExportEngine` continues to generate its native TXT, JSON,
DOCX and PDF artifacts. It now exposes the already-installed LibreOffice bridge
for explicit open/conversion operations.

## Package E

`prepare_package_e_review()` keeps the editable DOCX as the review source and
automatically asks LibreOffice to create a companion PDF in the same output
folder. The PDF is added to the manifest when successful.

PDF companion generation is a convenience/output-access feature. Failure to
produce the companion does not fabricate evidence and does not change the
professional-review or production-release gates.
