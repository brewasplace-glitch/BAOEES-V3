# BB35 Pilot 1 — Sequential Review & Evidence Intake v1.4.2

The installer uses two payload phases:

1. install and validate Concept Review & Evidence Acquisition v1.4.0 against
   the original verified-input state;
2. install Uploaded Evidence Intake v1.4.1, which updates the input register;
3. validate the combined final state.

This order prevents the intake-updated register from changing the historical
v1.4.0 review-artifact regeneration.

The preflight requires the actual Concept Generation v1.3.3 manifest:

`concept_package_manifest.json`

The earlier incorrect name `concept_generation_manifest.json` is not used.
