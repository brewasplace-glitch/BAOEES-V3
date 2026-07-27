# BB35 Pilot 1 - Concept Generation v1.3.3

## Canonical ZIP-header fix

Version 1.3.2 removed zlib variance by changing the internal dossier to
ZIP_STORED. Python's ZipInfo still supplied one operating-system-dependent
header field:

- Windows default create_system = 0;
- Linux default create_system = 3.

Version 1.3.3 explicitly fixes every relevant member header:

- ZIP_STORED;
- create_system = 3;
- create_version = 20;
- extract_version = 20;
- flag_bits = 0;
- internal_attr = 0;
- external_attr = regular Unix file 0644;
- empty extra fields and comments;
- fixed timestamps and member order;
- Zip64 disabled for this small dossier.

A regression test replaces ZipInfo with a simulated Windows-default
implementation and proves that the resulting dossier remains byte-identical.

## Status

- Scope: 7.00 x 10.00 m, two storeys, 140 m2 gross.
- Documents: CONCEPT - NOT FOR EXECUTION OR SUBMISSION.
- Final generation: blocked.
- BB36: locked.
