# Phoenix Architectural Compliance Installer Parser Recovery v6.7.1

## Confirmed v6.7.0 failure

The v6.7.0 installer failed before payload mutation because minified
PowerShell syntax produced an invalid token:

`return$p`

## Recovery

v6.7.1 preserves the v6.7.0 Python compliance engine and rule-profile payload,
but replaces the PowerShell installer completely with explicit, non-minified
functions and control flow.

The installer includes:

- verified branch and clean/synchronized preflight;
- robust Python 3 resolution;
- pre-payload architecture, detailed architecture and compliance runs;
- compliance unit tests;
- exact payload backup/copy/rollback;
- strict Git change validation;
- commit/push only after all checks pass;
- final clean/synchronized verification;
- no automatic legal compliance approval;
- permit-ready and execution-ready release gates remain locked for the generic
  unverified rule profile.
