# Project Phoenix — LibreOffice Office Adapter v1.0

## Classification

`EXTEND` — Phoenix already contains extensive DOCX/PDF/XLSX/document export
engines. Repository discovery found no actual `soffice` / `--convert-to`
integration.

## Proven Windows route

A read-only real-world probe proved:

- LibreOffice `26.2.5.2`
- `soffice.com`
- isolated `-env:UserInstallation=file:///...` profile
- Writer filter `pdf:writer_pdf_Export`
- real DOCX -> PDF
- non-empty output: 38,242 bytes

The first route without an isolated profile was rejected because LibreOffice could
return process success while no output file appeared.

## Integration

The adapter adds:

- central `LibreOfficeOfficeAdapter`;
- generic Office conversion with isolated temporary profiles;
- GUI document opening;
- thin bridge under the existing `baoees.document_export_engine` package;
- CLI runner;
- fail-closed output verification.

Supported input families:

- Writer: DOC/DOCX/ODT/RTF/TXT
- Calc: XLS/XLSX/ODS/CSV
- Impress: PPT/PPTX/ODP

Primary target is PDF. Same-family conversion to DOCX/XLSX/PPTX/ODT/ODS/ODP is
also available through LibreOffice filters.

No Microsoft Office and no `openpyxl` are required for the adapter.
