# BB35 Pilot 1 Professional Evidence Intake Validation and Closure Gate v2.3.0

## Purpose

This module operationalizes the six professional evidence workpacks created in v2.2.0. It validates received submissions and closes requirements only when both professional evidence and a project-leader acceptance decision pass all controls.

## Controlled requirements

- REQ-102 validated geometry and survey;
- REQ-103 current structural survey and connection design;
- REQ-104 geotechnical investigation and foundation advice;
- REQ-105 Bbl, fire, ventilation and installations;
- REQ-106 parking inventory, counts and professional balance using the confirmed 225-space basis;
- REQ-108 verified activity data and AERIUS package.

REQ-107 remains closed under `HBM-OCC-2026-001`.

## Safety and governance

- Templates, simulations and unsigned files cannot close a requirement.
- Every evidence file must exist and match its declared SHA-256.
- Professional name, organization, discipline, registration and signed declaration are mandatory.
- The project-leader decision must reference the exact manifest hash.
- Six accepted packages pass only the professional-evidence closure gate.
- Permit, tender, execution and BB36 release remain blocked until coordinated regeneration and final review.


## v2.3.1 checksum-order recovery

The checksum manifest is sorted by case-sensitive relative POSIX path strings.
This removes the WindowsPath case-insensitive ordering difference between files
such as `SUBMISSION_README.md` and `acceptance_rules.json`.
