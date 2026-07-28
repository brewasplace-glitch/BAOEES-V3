# Naamgeving professionele bewijsretouren

Programma: `HBM-PERP-2026-001`

Gebruik:

`HBM_<REQ-ID>_<DOCUMENTTYPE>_<ORGANISATIE>_<REV>_<YYYYMMDD>.<ext>`

Voorbeeld:

`HBM_REQ-106_PARKEERBALANS_ADVIESBUREAU_R01_20260815.pdf`

Regels:

- één retourmanifest per REQ;
- geen spaties in bestandsnamen;
- revisie verplicht;
- datum in formaat YYYYMMDD;
- ieder bestand krijgt een SHA-256 in het manifest;
- gewijzigde bestanden krijgen een nieuwe revisie en checksum;
- bronbestanden én leesbare PDF-export meesturen waar van toepassing.
