# PHOENIX AUTO SYNC — LibreOffice Default Document Routing v1.0

Phoenix default Office routing now reuses the installed LibreOffice adapter.

Rules:
- Office-family file open -> LibreOffice.
- PDF/non-Office open -> system default viewer.
- Native Phoenix DOCX/PDF/XLSX generators remain unchanged.
- Existing DocumentExportEngine exposes LibreOffice open/convert bridge methods.
- Package-E review DOCX automatically receives a LibreOffice-generated PDF
  companion when the local LibreOffice engine is available.
- Companion-PDF failure is nonfatal and never changes review/approval gates.
