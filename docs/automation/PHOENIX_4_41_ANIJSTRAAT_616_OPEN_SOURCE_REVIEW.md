# Open-source review — 2026-09-11

## Primary — pdfplumber
- Purpose: detailed PDF text/layout/object extraction.
- License: MIT.
- Active maintenance; current upstream supports modern Python versions.
- Fit: the architectural set is machine-generated PDF, which matches pdfplumber's strongest use case.

## Fallback — pypdf
- Purpose: pure-Python PDF text and metadata extraction.
- Open source and actively maintained.
- Fit: robust fallback when detailed layout extraction is unavailable.

## Decision
Use pdfplumber first and pypdf second. Do not use OCR for this machine-generated drawing set.
