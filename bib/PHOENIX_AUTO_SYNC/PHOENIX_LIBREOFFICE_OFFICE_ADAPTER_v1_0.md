# PHOENIX AUTO SYNC — LibreOffice Office Adapter v1.0

Phoenix now uses LibreOffice as the primary open-source Office application bridge.

Authoritative proven Windows automation route:

`soffice.com`
+ isolated temporary `UserInstallation` profile
+ explicit document-family export filter
+ real output existence/size/hash verification.

The adapter extends the existing document export stack. It does not replace
Phoenix's native DOCX, XLSX, PDF or reporting engines. Microsoft Office and
openpyxl are not required for LibreOffice conversion.
