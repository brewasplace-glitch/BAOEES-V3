# PROJECT PHOENIX — SCIA Professional Engineering Bridge Masterpack v1.0

## Target

- Baseline: `e8581a3e14bdb4ca92671aeaeb0094e67ddb5551`
- SCIA runtime: `SCIA Engineer 18.1`
- ESA_XML: `C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe`
- Integration: `ESA_XML_FIRST_WITH_OPTIONAL_LATER_OPENAPI_ADM`
- OpenAPI: not detected
- ADM: detected, reserved for later expansion
- SCIA 19.1: installed but not selected for autonomous runtime in v1.0

## Why ESA_XML first

SCIA's ESA_XML command-line program can open an ESA project, optionally apply XML data,
run a calculation and export project/document/result data. v1.0 therefore uses a controlled
existing `.ESA` seed/project plus optional XML update.

## v1.0 execution boundary

This masterpack installs the general Phoenix-to-SCIA execution/evidence bridge. It deliberately
does **not** fabricate a project-specific `.ESA` model. The first real PHOENIX-PAT-001 SCIA model
or controlled SCIA seed/template is supplied during the later end-to-end project step.

## Evidence

Every real bridge run records:
- command argv;
- working `.ESA` copy;
- stdout;
- stderr;
- SCIA log;
- requested PDF/document export when configured;
- requested XML result export when configured;
- expected project-generated Engineering Report exports when configured;
- SHA-256 evidence manifest;
- run status.

## Status semantics

A zero solver exit plus all required outputs results only in:

`CALCULATED_UNVERIFIED`

It does not mean:
- independently verified;
- professionally approved;
- code compliant;
- production released;
- FOR-CONSTRUCTION.

The next Phoenix masterpack supplies independent verification using equilibrium, analytical
spot checks, SCIA/CalculiX comparison and additional governed checks.
