# PHOENIX 4.41 - External release evidence open-source review

## Primary structured-evidence validator - jsonschema 4.26.0

`jsonschema` implements JSON Schema for Python. Version 4.26.0 is MIT licensed, requires Python 3.10+, and supports Python 3.14.

Phoenix uses JSON Schema Draft 2020-12 for release-evidence submission manifests.

## Integrity/signature engine - cryptography 50.0.1

`cryptography` 50.0.1 is licensed Apache-2.0 OR BSD-3-Clause, supports Python 3.14 and Windows, and is used only for optional Ed25519 detached signature verification.

A valid signature proves integrity/authenticity relative to the supplied public key. It does not prove the signer's legal authority, registration or engineering competence.

## Deterministic fallback

SHA256 evidence hashing and file-presence checks use the Python standard library and remain available even if no signature is supplied.

## Report stack

- python-docx 1.2.0;
- ReportLab 5.0.1;
- pypdf 5.9.0.

The final construction release remains a separate controlled action.
